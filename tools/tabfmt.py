#!/usr/bin/env python3
"""Pretty-print tabjson files in the house style: one event per line.

usage: python tools/tabfmt.py song.tab.json [more files...]   (rewrites in place)
       python -c "from tools.tabfmt import dumps"             (use from code)
"""
import json
import sys
from pathlib import Path


def _j(x):
    return json.dumps(x, ensure_ascii=False, separators=(", ", ": "))


def dumps(song: dict) -> str:
    lines = ["{"]
    head = [(k, v) for k, v in song.items() if k != "bars"]
    for k, v in head:
        if k == "meta":
            lines.append(f'  "meta": {json.dumps(v, ensure_ascii=False, indent=2).replace(chr(10), chr(10) + "  ")},')
        else:
            lines.append(f'  "{k}": {_j(v)},')
    lines.append('  "bars": [')
    bars = song.get("bars", [])
    for i, b in enumerate(bars):
        extra = ", ".join(f'"{k}": {_j(v)}' for k, v in b.items() if k != "ev")
        lines.append("    {" + (extra + ", " if extra else "") + '"ev": [')
        evs = b.get("ev", [])
        for j, e in enumerate(evs):
            lines.append("      " + _j(e) + ("," if j < len(evs) - 1 else ""))
        lines.append("    ]}" + ("," if i < len(bars) - 1 else ""))
    lines.append("  ]")
    lines.append("}")
    return "\n".join(lines) + "\n"


def main(argv):
    if not argv:
        print(__doc__)
        return 1
    for f in argv:
        p = Path(f)
        song = json.loads(p.read_text(encoding="utf-8"))
        p.write_text(dumps(song), encoding="utf-8")
        print("formatted", p)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
