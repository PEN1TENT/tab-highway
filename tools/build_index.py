#!/usr/bin/env python3
"""Rebuild <library>/index.json from <library>/songs/*.tab.json.

usage: python tools/build_index.py path/to/library     (e.g. demo, or ../tab-library)
"""
import json
import sys
from pathlib import Path


def main(argv):
    if not argv:
        print(__doc__)
        return 1
    lib = Path(argv[0])
    songs = []
    for f in sorted((lib / "songs").glob("*.tab.json")):
        s = json.loads(f.read_text(encoding="utf-8"))
        m = s.get("meta", {})
        songs.append({
            "id": s["id"],
            "title": m.get("title", s["id"]),
            "artist": m.get("artist", ""),
            "bpm": s.get("bpm"),
            "bars": len(s.get("bars", [])),
            "status": (m.get("transcription") or {}).get("status", "draft"),
            "file": f"songs/{f.name}",
        })
    index = {"format": "tabjson-index", "version": 1, "songs": songs}
    (lib / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"wrote {lib / 'index.json'} ({len(songs)} songs)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
