#!/usr/bin/env python3
"""Turn a tab PDF into numbered, upscaled "system" strips that are easy to read.

usage: python tools/prepare.py song.pdf [--out work] [--id 032]

Writes  work/<id>/sys01.png, sys02.png, ...   one image per system (notation + TAB)
        work/<id>/manifest.json               what was found, for the transcriber

Works for:
  - PDFs that are one tall stitched screenshot (most of the Drive library)
  - multi-page PDFs, scans and photos (falls back to overlapping strips when
    staff lines can't be found reliably)
Text-based PDFs are rendered to images first, so they work too.
"""
import argparse
import io
import json
import re
import sys
from pathlib import Path

import numpy as np
from PIL import Image

try:
    import pymupdf as fitz
except ImportError:  # older PyMuPDF
    import fitz

TARGET_W = 1600          # width of output strips
MIN_LINE_FRAC = 0.095    # a staff line is an unbroken run at least this share of the width


def page_images(pdf_path):
    """Yield one PIL image per page (embedded image if the page is just a picture)."""
    doc = fitz.open(pdf_path)
    for page in doc:
        imgs = page.get_images(full=True)
        if len(imgs) == 1 and not page.get_text().strip():
            x = doc.extract_image(imgs[0][0])
            yield Image.open(io.BytesIO(x["image"])).convert("RGB")
        else:
            pix = page.get_pixmap(dpi=200)
            yield Image.frombytes("RGB", (pix.width, pix.height), pix.samples)


def longest_run(row):
    """Length of the longest run of True values in a 1-D bool array."""
    row = np.convolve(row.astype(np.int8), np.ones(7, dtype=np.int8), mode="same") > 0  # bridge small gaps
    padded = np.concatenate(([False], row, [False])).astype(np.int8)
    d = np.diff(padded)
    starts, ends = np.where(d == 1)[0], np.where(d == -1)[0]
    return int((ends - starts).max()) if len(starts) else 0


def find_staves(img):
    """Return staves as lists of line y-positions (top to bottom)."""
    g = np.asarray(img.convert("L"), dtype=np.uint8)
    dark = g < 180
    W = dark.shape[1]
    # a staff line is a long unbroken dark run; this also finds short final systems
    rows = [r for r in np.where(dark.sum(1) > W * 0.05)[0] if longest_run(dark[r]) > W * MIN_LINE_FRAC]
    lines = []
    for r in rows:
        if lines and r - lines[-1][-1] <= 2:
            lines[-1].append(r)
        else:
            lines.append([r])
    ys = [int(np.mean(l)) for l in lines]
    max_gap = max(12, W * 0.03)
    staves = []
    for y in ys:
        if staves and y - staves[-1][-1] < max_gap:
            staves[-1].append(y)
        else:
            staves.append([y])
    return [s for s in staves if len(s) in (5, 6)]


def group_systems(staves):
    """Pair each notation staff with the TAB staff under it.

    TAB staves have wider line spacing (~1.5x) than notation staves, so staves
    are classified by spacing rather than by line count (ledger lines and beams
    sometimes add a fake 6th line to a notation staff)."""
    if not staves:
        return []
    sp = [(s[-1] - s[0]) / (len(s) - 1) for s in staves]
    narrow = min(sp)
    is_tab = [x > narrow * 1.25 for x in sp]
    if not any(is_tab):          # only one kind of staff on the page: treat all as TAB
        is_tab = [True] * len(staves)
    systems, i = [], 0
    while i < len(staves):
        s = staves[i]
        if not is_tab[i] and i + 1 < len(staves) and is_tab[i + 1] \
                and staves[i + 1][0] - s[-1] < sp[i] * 14:
            systems.append((s[0], staves[i + 1][-1], sp[i]))
            i += 2
        elif is_tab[i]:
            systems.append((s[0], s[-1], sp[i]))   # TAB with notation missed above it
            i += 1
        else:
            i += 1                                   # stray notation staff: falls inside a neighbour's crop
    return systems


def crop_systems(img, systems):
    """Crop each system, cutting halfway between neighbours so nothing is clipped."""
    H = img.height
    out = []
    for k, (top, bot, sp) in enumerate(systems):
        lone_tab = (bot - top) / sp < 7          # TAB staff whose notation wasn't detected
        if k == 0:
            a = max(0, int(top - sp * (18 if lone_tab else 10)))
        elif lone_tab:   # its notation sits in the gap above: take the whole gap
            a = max(int(systems[k - 1][1] + sp * 1.5), int(top - sp * 18))
        else:
            a = (systems[k - 1][1] + top) // 2
        b = (bot + systems[k + 1][0]) // 2 if k + 1 < len(systems) else min(H, int(bot + sp * 4))
        out.append(img.crop((0, int(a), img.width, int(b))))
    return out


def strips(img, h_frac=0.28, overlap=0.25):
    """Fallback: overlapping horizontal strips."""
    h = max(200, int(img.width * h_frac * 1.4))
    step = int(h * (1 - overlap))
    return [img.crop((0, y, img.width, min(img.height, y + h))) for y in range(0, max(1, img.height - h // 3), step)]


def upscale(im):
    if im.width >= TARGET_W:
        return im
    f = TARGET_W / im.width
    return im.resize((TARGET_W, int(im.height * f)), Image.LANCZOS)


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pdf")
    ap.add_argument("--out", default="work")
    ap.add_argument("--id", help="song id (default: leading number of the file name)")
    a = ap.parse_args(argv)

    pdf = Path(a.pdf)
    m = re.match(r"(\d+)", pdf.name)
    sid = a.id or (m.group(1) if m else pdf.stem)
    out = Path(a.out) / sid
    out.mkdir(parents=True, exist_ok=True)
    for old in out.glob("sys*.png"):
        old.unlink()

    manifest = {"id": sid, "pdf": pdf.name, "pages": [], "strips": []}
    n = 0
    for p, img in enumerate(page_images(pdf), 1):
        systems = group_systems(find_staves(img))
        mode = "systems" if systems else "strips"
        crops = crop_systems(img, systems) if systems else strips(img)
        manifest["pages"].append({"page": p, "size": [img.width, img.height], "mode": mode, "count": len(crops)})
        if p == 1:
            # page header (title, tempo, tuning/capo notes) for metadata
            top = systems[0][0] if systems else img.height // 8
            hdr = img.crop((0, 0, img.width, max(40, int(top - (systems[0][2] * 7 if systems else 0)))))
            if hdr.height > 30:
                upscale(hdr).save(out / "header.png")
                manifest["header"] = "header.png"
        for c in crops:
            n += 1
            name = f"sys{n:02d}.png"
            upscale(c).save(out / name)
            manifest["strips"].append({"file": name, "page": p, "mode": mode})
    (out / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1))
    modes = {pg["mode"] for pg in manifest["pages"]}
    print(f"{pdf.name}: {len(manifest['pages'])} page(s), {n} strip(s) [{', '.join(sorted(modes))}] -> {out}/")
    if "strips" in modes:
        print("  note: staff lines not detected on some pages (scan/photo?) - strips overlap, read carefully")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
