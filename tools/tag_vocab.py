#!/usr/bin/env python
"""Tag 词表：安装、查词、校验（不依赖 LLM）。

词表放在 vocab/，当前生效的词表及其来源记录在 vocab/manifest.json。
格式为 a1111-sd-webui-tagcomplete 的 CSV：name,category,post_count,"alias1,alias2"
category：0 一般 · 1 画师 · 3 作品 · 4 角色 · 5 元数据

用法:
    python tag_vocab.py info
    python tag_vocab.py search skirt pleated --limit 20
    python tag_vocab.py check "1girl, pleated skirt, sitting on desk"
    # 安装/更新词表：只在用户确认来源与日期后执行
    python tag_vocab.py install <url> --model Anima --source-date 2025-01-03

退出码: 0=通过, 1=有词表外或需用户决定的 tag / 词表不可用, 2=命令行参数错误
"""
from __future__ import annotations

import argparse
import csv
import difflib
import hashlib
import io
import json
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
VOCAB_DIR = REPO / "vocab"
MANIFEST = VOCAB_DIR / "manifest.json"

CATEGORIES = {0: "general", 1: "artist", 3: "copyright", 4: "character", 5: "meta"}
# 这些类别的 tag 不由助手主动写入成品：人物与作品交给用户，画师与元数据不进提示词。
USER_DECIDES = {"artist", "copyright", "character", "meta"}


def normalize(tag: str) -> str:
    return " ".join(tag.replace("_", " ").split()).lower()


def read_manifest() -> dict | None:
    if not MANIFEST.is_file():
        return None
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


class Vocab:
    def __init__(self, path: Path):
        self.entries: dict[str, tuple[str, int]] = {}   # name -> (category, post_count)
        self.aliases: dict[str, str] = {}               # alias -> name
        with path.open(encoding="utf-8", newline="") as handle:
            for row in csv.reader(handle):
                if len(row) < 3:
                    continue
                name = normalize(row[0])
                try:
                    cat, count = CATEGORIES.get(int(row[1]), "other"), int(row[2])
                except ValueError:
                    continue
                self.entries.setdefault(name, (cat, count))
                if len(row) > 3 and row[3]:
                    for alias in row[3].split(","):
                        alias = normalize(alias)
                        if alias and not alias.startswith("/"):
                            self.aliases.setdefault(alias, name)
        self._names: list[str] | None = None

    def lookup(self, tag: str) -> dict:
        tag = normalize(tag)
        if tag in self.entries:
            cat, count = self.entries[tag]
            return {"tag": tag, "status": "ok", "category": cat, "post_count": count}
        if tag in self.aliases:
            name = self.aliases[tag]
            cat, count = self.entries[name]
            return {"tag": tag, "status": "alias", "canonical": name, "category": cat, "post_count": count}
        if self._names is None:
            self._names = sorted(self.entries, key=lambda n: -self.entries[n][1])[:60000]
        close = difflib.get_close_matches(tag, self._names, n=5, cutoff=0.75)
        return {"tag": tag, "status": "unknown", "suggestions": close}

    def search(self, words: list[str], category: str | None, min_count: int, limit: int) -> list[dict]:
        words = [normalize(w) for w in words]
        hits: dict[str, str | None] = {}
        for name in self.entries:
            if all(w in name for w in words):
                hits[name] = None
        for alias, name in self.aliases.items():
            if name not in hits and all(w in alias for w in words):
                hits[name] = alias
        rows = []
        for name, via in hits.items():
            cat, count = self.entries[name]
            if (category and cat != category) or count < min_count:
                continue
            rows.append({"tag": name, "category": cat, "post_count": count, **({"via_alias": via} if via else {})})
        rows.sort(key=lambda r: -r["post_count"])
        return rows[:limit]


def load_active() -> tuple[Vocab | None, str]:
    """返回 (词表, 说明)。词表不可用时返回 None 和原因。"""
    manifest = read_manifest()
    if not manifest:
        return None, "未安装词表（vocab/manifest.json 不存在）"
    path = VOCAB_DIR / manifest["file"]
    if not path.is_file():
        return None, f"词表文件缺失：{path}"
    return Vocab(path), f"{manifest['file']}（{manifest.get('model', '?')}，来源日期 {manifest.get('source_date', '?')}）"


def check_tags(vocab: Vocab, tags: list[str]) -> list[dict]:
    """逐个查词：ok / alias / unknown，并标出需要用户决定的类别。"""
    results = []
    for tag in tags:
        r = vocab.lookup(tag)
        r["user_decides"] = r.get("category") in USER_DECIDES
        results.append(r)
    return results


def problems_from_check(results: list[dict]) -> list[str]:
    problems = []
    for r in results:
        if r["status"] == "unknown":
            hint = f"；近似：{', '.join(r['suggestions'])}" if r["suggestions"] else ""
            problems.append(f"词表外 tag：{r['tag']}{hint}")
        elif r["status"] == "alias":
            problems.append(f"别名 tag：{r['tag']} → 改用 {r['canonical']}")
        if r["user_decides"]:
            problems.append(f"{r['category']} 类 tag 交给用户决定，助手不主动写入：{r['tag']}")
    return problems

# ---------------------------------------------------------------- 子命令

def cmd_info(args) -> int:
    manifest = read_manifest()
    if not manifest:
        print("未安装词表。找到合适词表并经用户确认后，用 install 安装。")
        return 1
    vocab, _ = load_active()
    if args.json:
        print(json.dumps({**manifest, "available": vocab is not None}, ensure_ascii=False, indent=2))
    else:
        for key, value in manifest.items():
            print(f"{key}: {value}")
        print(f"available: {vocab is not None}")
    return 0 if vocab else 1


def cmd_search(args) -> int:
    vocab, why = load_active()
    if not vocab:
        print(why, file=sys.stderr)
        return 1
    rows = vocab.search(args.words, args.category, args.min_count, args.limit)
    if args.json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
    else:
        for r in rows:
            via = f"  (别名 {r['via_alias']})" if "via_alias" in r else ""
            print(f"{r['tag']}\t{r['category']}\t{r['post_count']}{via}")
        if not rows:
            print("无匹配")
    return 0


def cmd_check(args) -> int:
    vocab, why = load_active()
    if not vocab:
        print(why, file=sys.stderr)
        return 1
    tags = [t for t in (x.strip() for x in args.tags.split(",")) if t]
    results = check_tags(vocab, tags)
    problems = problems_from_check(results)
    if args.json:
        print(json.dumps({"vocab": why, "results": results, "problems": problems}, ensure_ascii=False, indent=2))
    else:
        print(f"[词表] {why}")
        for p in problems:
            print("  ! " + p)
        if not problems:
            print(f"  {len(tags)} 个 tag 全部在词表内")
    return 1 if problems else 0


def cmd_install(args) -> int:
    print(f"下载 {args.url} ...", file=sys.stderr)
    with urllib.request.urlopen(args.url, timeout=120) as resp:
        data = resp.read()
    text = data.decode("utf-8-sig")
    rows = [row for row in csv.reader(io.StringIO(text)) if len(row) >= 3]
    valid = sum(1 for row in rows if row[1].strip().isdigit() and row[2].strip().isdigit())
    if valid < 1000 or valid < len(rows) * 0.95:
        print(f"格式不符：{valid}/{len(rows)} 行是 name,category,count 格式；未安装", file=sys.stderr)
        return 1
    VOCAB_DIR.mkdir(exist_ok=True)
    name = args.file or Path(args.url.split("?")[0]).name
    (VOCAB_DIR / name).write_bytes(data)
    old = read_manifest()
    manifest = {
        "file": name,
        "model": args.model,
        "format": "tagcomplete-csv",
        "source_url": args.url,
        "source_date": args.source_date,
        "installed_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "rows": len(rows),
        "sha256": hashlib.sha256(data).hexdigest(),
    }
    if args.note:
        manifest["note"] = args.note
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if old and old.get("file") != name:
        print(f"旧词表 {old['file']} 保留在 vocab/，已不再生效", file=sys.stderr)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    ap = argparse.ArgumentParser(description="Tag 词表：安装、查词、校验")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("info", help="显示当前词表的来源、日期与对应模型")
    p.add_argument("--json", action="store_true")
    p.set_defaults(fn=cmd_info)

    p = sub.add_parser("search", help="按关键词查 tag（名字或别名包含全部关键词），按帖子数排序")
    p.add_argument("words", nargs="+")
    p.add_argument("--category", choices=sorted(set(CATEGORIES.values())), default="general")
    p.add_argument("--min-count", type=int, default=50, help="过滤冷门 tag（默认帖子数 ≥ 50）")
    p.add_argument("--limit", type=int, default=20)
    p.add_argument("--json", action="store_true")
    p.set_defaults(fn=cmd_search)

    p = sub.add_parser("check", help="校验逗号分隔的 tag 串是否都在词表内")
    p.add_argument("tags")
    p.add_argument("--json", action="store_true")
    p.set_defaults(fn=cmd_check)

    p = sub.add_parser("install", help="下载并启用一份词表（须先经用户确认来源与日期）")
    p.add_argument("url")
    p.add_argument("--model", required=True, help="该词表对应的绘画模型")
    p.add_argument("--source-date", required=True, help="词表本身的数据日期（如上游最后更新日期）")
    p.add_argument("--file", help="保存的文件名（默认取 URL 末段）")
    p.add_argument("--note", help="备注，如上游仓库与提交说明")
    p.set_defaults(fn=cmd_install)

    args = ap.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
