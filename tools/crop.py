#!/usr/bin/env python
"""裁切图片局部并放大，供看图核对细节（手、鞋、饰品、文字）。

区域用 0~1 的比例坐标，不必先知道图片分辨率。

用法:
    python crop.py <图片> --box 0.3,0.5,0.7,1.0 --out .work/crop.png
    # --box 为 左,上,右,下；--size 为输出长边像素（默认 1024，只放大不缩小）

退出码: 0=成功, 1=图片无法读取, 2=命令行参数错误
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image


def parse_box(text: str) -> tuple[float, float, float, float]:
    try:
        x0, y0, x1, y1 = (float(v) for v in text.split(","))
    except ValueError:
        raise argparse.ArgumentTypeError("--box 需要 4 个逗号分隔的数：左,上,右,下")
    if not (0 <= x0 < x1 <= 1 and 0 <= y0 < y1 <= 1):
        raise argparse.ArgumentTypeError("--box 需满足 0 ≤ 左 < 右 ≤ 1、0 ≤ 上 < 下 ≤ 1")
    return x0, y0, x1, y1


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except AttributeError:
            pass
    ap = argparse.ArgumentParser(description="裁切图片局部并放大")
    ap.add_argument("image", type=Path)
    ap.add_argument("--box", type=parse_box, required=True, help="左,上,右,下（0~1 比例）")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--size", type=int, default=1024, help="输出长边像素，只放大不缩小")
    args = ap.parse_args()

    try:
        img = Image.open(args.image).convert("RGB")
    except OSError as e:
        print(f"无法读取图片：{e}", file=sys.stderr)
        return 1

    w, h = img.size
    x0, y0, x1, y1 = args.box
    part = img.crop((round(x0 * w), round(y0 * h), round(x1 * w), round(y1 * h)))
    scale = args.size / max(part.size)
    if scale > 1:
        part = part.resize((round(part.width * scale), round(part.height * scale)), Image.LANCZOS)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    part.save(args.out)
    print(f"{args.out}  {part.width}x{part.height}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
