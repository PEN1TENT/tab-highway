#!/usr/bin/env python3
"""Print the next song numbers that still need transcribing.

usage: python tools/next_ids.py library [-n 3] [--max 999]

A number counts as done when library/songs/<id>.tab.json exists.
Numbers listed in library/skip.json ({"skip": {"123": "reason"}}) are skipped
(e.g. not a guitar tab, unreadable scan, missing from Drive).
"""
import argparse
import json
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("library")
    ap.add_argument("-n", type=int, default=3)
    ap.add_argument("--max", type=int, default=999)
    a = ap.parse_args()
    lib = Path(a.library)
    done = {p.name.split(".")[0] for p in (lib / "songs").glob("*.tab.json")}
    skip_file = lib / "skip.json"
    skip = set(json.loads(skip_file.read_text(encoding="utf-8")).get("skip", {})) if skip_file.exists() else set()
    out = []
    for i in range(1, a.max + 1):
        sid = f"{i:03d}"
        if sid not in done and sid not in skip:
            out.append(sid)
        if len(out) == a.n:
            break
    print(" ".join(out))
    print(f"# done: {len(done)}  skipped: {len(skip)}", flush=True)


if __name__ == "__main__":
    main()
