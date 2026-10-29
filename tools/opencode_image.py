#!/usr/bin/env python
"""从 opencode 会话库取出用户粘贴/拖入的图片，存成本地文件供打标器使用。

opencode 把对话里的图片以 base64 内联存进 opencode.db（session_message.data 的 files 字段），
磁盘上没有对应文件。本脚本只读打开数据库，取最近一条带图片的用户消息，把图片解码到输出目录。

用法:
    python opencode_image.py --out .work            # 取最近一条消息里的全部图片
    python opencode_image.py --out .work --list     # 只列出最近几条带图消息，不写文件
    python opencode_image.py --out .work --nth 2    # 往前数第 2 条带图消息

默认只看当前目录所在项目的会话（当前目录位于会话工作目录之内）；--any-dir 取消这个限制。
库结构随 opencode 版本变化（按 v2.0 编写），读不到时让用户改给本地路径。

退出码: 0=成功, 1=找不到数据库或图片, 2=命令行参数错误
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import sqlite3
import sys
from pathlib import Path

EXT = {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp", "image/gif": ".gif"}


def default_db() -> Path:
    if os.environ.get("OPENCODE_DB"):
        return Path(os.environ["OPENCODE_DB"])
    base = os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share"
    return Path(base) / "opencode" / "opencode.db"


def image_messages(db: Path, directory: str | None, limit: int):
    """按时间倒序产出 (消息时间, 图片列表)；图片为 files 里 mime 以 image/ 开头的项。"""
    norm = lambda p: p.replace("\\", "/").rstrip("/").lower() + "/"
    con = sqlite3.connect(f"file:{db.as_posix()}?mode=ro", uri=True)
    rows = con.execute(
        "select m.time_created, m.data, s.directory from session_message m join session_v2 s on s.id = m.session_id "
        "where m.type = 'user' and m.data like '%\"mime\":\"image/%' order by m.time_created desc")
    found = 0
    for tc, data, session_dir in rows:
        # 当前目录在会话的工作目录之内才算本项目（skill 目录也在项目里）
        if directory and not norm(directory).startswith(norm(session_dir)):
            continue
        files = [f for f in json.loads(data).get("files", []) if str(f.get("mime", "")).startswith("image/") and f.get("data")]
        if files:
            yield tc, files
            found += 1
            if found >= limit:
                return


def decode(data: str) -> bytes:
    if data.startswith("data:"):
        data = data.split(",", 1)[1]
    return base64.b64decode(data)


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except AttributeError:
            pass
    ap = argparse.ArgumentParser(description="从 opencode 会话库取出粘贴的图片")
    ap.add_argument("--out", type=Path, required=True, help="输出目录")
    ap.add_argument("--nth", type=int, default=1, help="往前数第几条带图消息（默认 1 = 最近一条）")
    ap.add_argument("--list", action="store_true", help="只列出，不写文件")
    ap.add_argument("--any-dir", action="store_true", help="不限当前目录的会话")
    ap.add_argument("--db", type=Path, default=default_db())
    args = ap.parse_args()
    if args.nth < 1:
        ap.error("--nth 从 1 开始")

    if not args.db.exists():
        print(f"找不到 opencode 数据库：{args.db}", file=sys.stderr)
        return 1
    directory = None if args.any_dir else os.getcwd()
    try:
        msgs = list(image_messages(args.db, directory, max(args.nth, 5)))
    except (sqlite3.Error, json.JSONDecodeError) as e:
        print(f"读取 opencode 数据库失败（库结构可能已随版本变化）：{e}", file=sys.stderr)
        return 1
    if len(msgs) < args.nth:
        where = "任何会话" if args.any_dir else f"目录 {directory} 的会话"
        print(f"{where}里只找到 {len(msgs)} 条带图消息", file=sys.stderr)
        return 1

    if args.list:
        for i, (tc, files) in enumerate(msgs, 1):
            print(f"{i}. {tc}  " + ", ".join(f.get("name") or f["mime"] for f in files))
        return 0

    tc, files = msgs[args.nth - 1]
    args.out.mkdir(parents=True, exist_ok=True)
    for i, f in enumerate(files, 1):
        path = args.out / f"pasted_{tc}_{i}{EXT.get(f['mime'], '.img')}"
        path.write_bytes(decode(f["data"]))
        print(f"{path}  {f.get('name', '')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
