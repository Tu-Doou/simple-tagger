#!/usr/bin/env python
"""快速反推：一条命令完成取图、打标、规范化、查词表、切局部图。

输出是给 agent 看的精简清单（按置信度分档，带分数），原始打标结果写进 run.json 备查。
局部图按画幅自动切：竖图切上中下三段，横图切左中右三段，近方形切四角；相邻段有重叠，
每段单独存文件（并行读回时每张都能用满看图分辨率，拼成一张反而看不清）。

用法:
    python quick_tag.py <图片>                  # 本地图片
    python quick_tag.py --pasted                # 取 opencode 里最近一条粘贴的图（在项目目录内运行）
    python quick_tag.py <图片> --no-crops       # 不切局部图

退出码: 0=成功, 1=取图/打标/词表失败, 2=命令行参数错误
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from anima_validate import clean_tags, detect_multi, find_conflicts, fold_redundant, normalize_tag  # noqa: E402
from tag_vocab import check_tags, load_active  # noqa: E402

WORK = HERE.parent / ".work"
HIGH, MID = 0.6, 0.35   # 分档：≥HIGH 高，MID~HIGH 中，其余低


def crop_boxes(w: int, h: int) -> list[tuple[str, tuple[float, float, float, float]]]:
    if h >= w * 1.2:
        return [("top", (0, 0, 1, .4)), ("middle", (0, .3, 1, .7)), ("bottom", (0, .6, 1, 1))]
    if w >= h * 1.2:
        return [("left", (0, 0, .4, 1)), ("center", (.3, 0, .7, 1)), ("right", (.6, 0, 1, 1))]
    return [("top-left", (0, 0, .6, .6)), ("top-right", (.4, 0, 1, .6)),
            ("bottom-left", (0, .4, .6, 1)), ("bottom-right", (.4, .4, 1, 1))]


def save_crops(image: Path, out: Path) -> list[str]:
    from PIL import Image, ImageOps
    with Image.open(image) as src:
        img = ImageOps.exif_transpose(src).convert("RGB")
    w, h = img.size
    lines = []
    for name, (x0, y0, x1, y1) in crop_boxes(w, h):
        part = img.crop((round(x0 * w), round(y0 * h), round(x1 * w), round(y1 * h)))
        scale = 1024 / max(part.size)
        if scale > 1:
            part = part.resize((round(part.width * scale), round(part.height * scale)), Image.LANCZOS)
        path = out / f"quick_{name}.png"
        part.save(path)
        lines.append(f"  {path}  ({name})")
    return lines


def fetch_pasted(out: Path) -> Path:
    from opencode_image import decode, default_db, image_messages
    db = default_db()
    if not db.exists():
        raise RuntimeError(f"找不到 opencode 数据库：{db}")
    for tc, files in image_messages(db, os.getcwd(), 1):
        f = files[0]
        ext = {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp"}.get(f["mime"], ".img")
        path = out / f"pasted_{tc}{ext}"
        path.write_bytes(decode(f["data"]))
        return path
    raise RuntimeError(f"目录 {os.getcwd()} 的会话里没有带图消息；请用户给出本地路径")


def run_tagger(image: Path) -> dict:
    from pixai_config import THRESHOLDS
    from pixai_tagger import PixAICPUTagger, PixAITagger, resolve_device
    started = time.perf_counter()
    device = resolve_device("auto")
    tagger = PixAICPUTagger() if device == "cpu" else PixAITagger(device=device)
    record = tagger.tag(image, dict(THRESHOLDS))
    record["performance"]["model_load_seconds"] = time.perf_counter() - started
    return record


def fmt(pairs: list[tuple[str, float]]) -> str:
    return ", ".join(f"{t} {s:.2f}" for t, s in pairs) or "（无）"


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except AttributeError:
            pass
    ap = argparse.ArgumentParser(description="快速反推：打标 + 规范化 + 局部图")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("image", nargs="?", type=Path)
    src.add_argument("--pasted", action="store_true", help="取 opencode 最近一条粘贴的图")
    ap.add_argument("--out", type=Path, default=WORK, help=f"输出目录（默认 {WORK}）")
    ap.add_argument("--no-crops", action="store_true")
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    try:
        image = fetch_pasted(args.out) if args.pasted else args.image
        if not image.is_file():
            print(f"图片不存在：{image}", file=sys.stderr)
            return 1
        record = run_tagger(image)
    except Exception as e:  # 打标器与数据库的报错原样交给 agent
        print(f"失败：{e}", file=sys.stderr)
        return 1
    (args.out / "run.json").write_text(json.dumps([record], ensure_ascii=False, indent=2), encoding="utf-8")

    vocab, why = load_active()
    if vocab is None:
        print(f"词表不可用：{why}", file=sys.stderr)
        return 1

    # 规范化 → 别名换规范名 → 去重 → 上位词折叠；词表外与人物/作品/画师/元数据类不进清单
    raw = {normalize_tag(k): v for k, v in record["general"].items()}
    tags, _ = clean_tags(list(raw))
    scores: dict[str, float] = {}
    dropped: list[str] = []
    for r in check_tags(vocab, tags):
        if r["status"] == "unknown" or r["user_decides"]:
            dropped.append(r["tag"])
            continue
        name = r.get("canonical", r["tag"])
        scores[name] = max(scores.get(name, 0.0), raw[r["tag"]])
    folded, drops, _ = fold_redundant(list(scores), scores)
    final = {t: scores[t] for t in folded}

    ranked = sorted(final.items(), key=lambda p: -p[1])
    is_multi, markers = detect_multi(list(final))
    conflicts = find_conflicts(list(final), is_multi=is_multi)
    chars = [(normalize_tag(k), v) for k, v in record["character"].items()]

    print(f"图片 {image}  {record['original_size'][0]}x{record['original_size'][1]}")
    print(f"人物候选（不进成品）：{fmt(chars)}")
    if is_multi:
        print(f"多人图（{', '.join(markers)}）：快速模式不处理，改走多角色模式")
    print(f"\n[高 ≥{HIGH}] {fmt([p for p in ranked if p[1] >= HIGH])}")
    print(f"[中 {MID}~{HIGH}] {fmt([p for p in ranked if MID <= p[1] < HIGH])}")
    print(f"[低 <{MID}] {fmt([p for p in ranked if p[1] < MID])}")
    if conflicts:
        print("\n[槽位冲突 · 看图选一个]")
        for c in conflicts:
            print(f"  {c['slot']}: {' | '.join(c['candidates'])}")
    notes = [f"折叠 {d}（被 {k} 覆盖）" for d, k in drops] + [f"已删 {t}（词表外或人物/作品类）" for t in dropped]
    if notes:
        print("\n[已处理] " + "；".join(notes))
    if not args.no_crops:
        print("\n[局部图 · 同一轮并行读]")
        print("\n".join(save_crops(image, args.out)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
