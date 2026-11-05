"""Shorthand for writing songs from Python (much less typing than raw JSON).

    import sys; sys.path.insert(0, "tools")
    from dsl import N, eighths, build
    B = {}
    B[1] = [N(0, 12, "e0 B1 G0 D2 A3"), N(12, 12, "D2"), N(24, 6, "B3h"), N(30, 6, "E0x"), N(36, 60)]
    ...
    build(B, nbars, {1: "Intro"}, meta_without_bars, "library/songs/NNN.tab.json")

N(t, d, "e0 B1 G2") -> event. Strings: e B G D A E. Suffix h = hammer/pull, s = slide, x = dead note.
N(t, d) with no notes -> rest.  B[k] = B[j] reuses a bar (deep-copied on build).
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from tabfmt import dumps  # noqa: E402

S = {"e": 1, "B": 2, "G": 3, "D": 4, "A": 5, "E": 6}


def N(t, d, spec=None):
    if spec is None:
        return {"t": t, "d": d, "rest": True}
    notes = []
    for tok in spec.split():
        s, rest, tech = S[tok[0]], tok[1:], None
        if rest[-1] in "hsx":
            tech, rest = rest[-1], rest[:-1]
        notes.append([s, int(rest)] + ([tech] if tech else []))
    return {"t": t, "d": d, "n": notes}


def eighths(*specs, start=0):
    return [N(start + 12 * i, 12, s) for i, s in enumerate(specs) if s]


def build(B, nbars, labels, meta, out, extra=None):
    bars = []
    for i in range(1, nbars + 1):
        b = {"src": i}
        if i in labels:
            b["label"] = labels[i]
        if extra and i in extra:
            b.update(extra[i])
        b["ev"] = json.loads(json.dumps(sorted(B[i], key=lambda e: e["t"])))
        bars.append(b)
    song = dict(meta)
    song["bars"] = bars
    Path(out).write_text(dumps(song), encoding="utf-8")
