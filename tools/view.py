#!/usr/bin/env python3
"""Make cheaper / clearer images to read after tools/prepare.py.

usage:
  python tools/view.py group  NNN [--per 3]   work/NNN/gXX.png: 3 strips stacked per image (fewest reads;
                                              good for clear 8th/16th fingerstyle)
  python tools/view.py halves NNN             work/NNN/hXX.png: each strip as left half over right half at
                                              full size (dense 32nds, triplets, small print)
  python tools/view.py slice  NNN [--step 900] work/NNN/cXX.png: the raw page cut into overlapping 2x chunks.
                                              Use when prepare.py paired notation with the wrong TAB staff
                                              (widely spaced systems) - a strip shows notation with no TAB.
"""
import argparse
import glob
import re
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
import prepare  # noqa: E402


def trimmed(f):
    im = Image.open(f).convert("L")
    a = np.array(im) < 200
    rows = np.where(a.sum(1) > 3)[0]
    return im.crop((0, max(0, rows[0] - 8), im.width, min(im.height, rows[-1] + 8)))


def group(n, per):
    strips = [trimmed(f) for f in sorted(glob.glob(f"work/{n}/sys*.png"))]
    W = max(s.width for s in strips)
    k = 0
    for i in range(0, len(strips), per):
        grp = strips[i:i + per]
        out = Image.new("L", (W, sum(s.height for s in grp) + 20 * (len(grp) - 1)), 255)
        y = 0
        for s in grp:
            out.paste(s, (0, y))
            y += s.height + 20
        k += 1
        out.save(f"work/{n}/g{k:02d}.png")
    print(f"{n}: {len(strips)} strips -> {k} group images (g01..)")


def halves(n):
    files = sorted(glob.glob(f"work/{n}/sys*.png"))
    for f in files:
        im = trimmed(f)
        W, h = im.width, im.width // 2 + 60
        out = Image.new("L", (h, im.height * 2 + 30), 255)
        out.paste(im.crop((0, 0, h, im.height)), (0, 0))
        out.paste(im.crop((W - h, 0, W, im.height)), (0, im.height + 30))
        out.save(f.replace("sys", "h"))
    print(f"{n}: {len(files)} half images (h01..)")


def slice_page(n, step):
    pdf = next(Path("inbox").glob(f"{n}_*.pdf"))
    k = 0
    for img in prepare.page_images(pdf):
        W, H = img.size
        for y in range(0, H, step):
            c = img.crop((0, y, W, min(H, y + step + 80)))
            if W < 1200:
                c = c.resize((c.width * 2, c.height * 2), Image.LANCZOS)
            k += 1
            c.save(f"work/{n}/c{k:02d}.png")
    print(f"{n}: {k} page chunks (c01..)")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mode", choices=["group", "halves", "slice"])
    ap.add_argument("id")
    ap.add_argument("--per", type=int, default=3)
    ap.add_argument("--step", type=int, default=900)
    a = ap.parse_args()
    n = re.sub(r"\D", "", a.id).zfill(3)
    Path(f"work/{n}").mkdir(parents=True, exist_ok=True)
    {"group": lambda: group(n, a.per), "halves": lambda: halves(n), "slice": lambda: slice_page(n, a.step)}[a.mode]()


if __name__ == "__main__":
    main()
