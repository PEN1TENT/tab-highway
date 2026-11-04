#!/usr/bin/env python3
"""Save a PDF downloaded with the Google Drive connector's download_file_content tool.

That tool returns JSON {"id", "title", "mimeType", "content": <base64>}. Large results are
saved by Claude to a text file instead of being shown; pass that file here.

usage: python tools/drive_decode.py <tool-result-file> [out-dir]     (default out-dir: inbox)
prints the path of the written PDF
"""
import base64
import json
import sys
from pathlib import Path


def main(argv):
    if not argv:
        print(__doc__)
        return 1
    raw = Path(argv[0]).read_text(encoding="utf-8")
    d = json.loads(raw[raw.index("{"):])
    out = Path(argv[1] if len(argv) > 1 else "inbox")
    out.mkdir(parents=True, exist_ok=True)
    name = d.get("title") or f"{d['id']}.pdf"
    p = out / name
    p.write_bytes(base64.b64decode(d["content"]))
    (out / (name + ".drive_id")).write_text(d.get("id", ""))
    print(p)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
