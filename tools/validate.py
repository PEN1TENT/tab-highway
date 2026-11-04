#!/usr/bin/env python3
"""Validate tabjson v1 song files.

usage: python tools/validate.py path/to/*.tab.json [--quiet]
       python tools/validate.py library/songs/          (a folder = all *.tab.json inside)

Exit code 0 when every file passes, 1 otherwise.
"""
import json
import sys
from pathlib import Path

PPQ = 24
TECHS = {"h", "s", "b", "x", "harm", "pm"}


def bar_len(ts):
    num, den = ts
    return num * PPQ * 4 // den


def check_song(song):
    """Return a list of human-readable problems (empty list = valid)."""
    errs = []
    if song.get("format") != "tabjson":
        errs.append('format must be "tabjson"')
    if song.get("version") != 1:
        errs.append("version must be 1")
    if song.get("ppq") != PPQ:
        errs.append(f"ppq must be {PPQ}")
    tuning = song.get("tuning")
    if not (isinstance(tuning, list) and len(tuning) == 6 and all(isinstance(x, int) for x in tuning)):
        errs.append("tuning must be 6 MIDI ints (string 1 first)")
    if not isinstance(song.get("id"), str) or not song["id"]:
        errs.append("id missing")
    meta = song.get("meta") or {}
    if not meta.get("title"):
        errs.append("meta.title missing")
    if not isinstance(song.get("bpm"), (int, float)) or song["bpm"] <= 0:
        errs.append("bpm must be > 0")
    if song.get("feel", "straight") not in ("straight", "swing8", "swing16"):
        errs.append('feel must be "straight", "swing8" or "swing16"')
    ts = song.get("ts")
    if not (isinstance(ts, list) and len(ts) == 2):
        errs.append("ts must be [num, den]")
        ts = [4, 4]
    bars = song.get("bars")
    if not isinstance(bars, list) or not bars:
        errs.append("bars missing/empty")
        return errs

    carry = 0  # ticks a tied note from the previous bar runs into this one
    for i, bar in enumerate(bars, 1):
        where = f"bar {i}" + (f" (sheet {bar['src']})" if "src" in bar else "")
        if "ts" in bar:
            ts = bar["ts"]
        L = bar_len(ts)
        evs = bar.get("ev")
        if not isinstance(evs, list) or not evs:
            errs.append(f"{where}: no events (write a whole-bar rest if empty)")
            continue
        last_t = -1
        spans = []
        for j, e in enumerate(evs):
            t, d = e.get("t"), e.get("d")
            if not isinstance(t, int) or not isinstance(d, int) or t < 0 or d <= 0:
                errs.append(f"{where} ev {j}: t/d must be ints, t>=0, d>0 (got t={t}, d={d})")
                continue
            if t < last_t:
                errs.append(f"{where} ev {j}: events not sorted by t")
            last_t = t
            if t >= L:
                errs.append(f"{where} ev {j}: starts at {t}, bar is only {L} ticks")
            if e.get("rest"):
                if e.get("n"):
                    errs.append(f"{where} ev {j}: rest with notes")
            else:
                ns = e.get("n")
                if not isinstance(ns, list) or not ns:
                    errs.append(f"{where} ev {j}: no notes and not a rest")
                    ns = []
                strings = []
                for k, n in enumerate(ns):
                    if not (isinstance(n, list) and 2 <= len(n) <= 4):
                        errs.append(f"{where} ev {j} note {k}: must be [string, fret(, tech)]")
                        continue
                    s, f = n[0], n[1]
                    if s not in range(1, 7):
                        errs.append(f"{where} ev {j}: string {s} not in 1..6")
                    if not isinstance(f, int) or not 0 <= f <= 24:
                        errs.append(f"{where} ev {j}: fret {f} not in 0..24")
                    if len(n) >= 3 and n[2] not in TECHS:
                        errs.append(f"{where} ev {j}: unknown technique {n[2]!r}")
                    strings.append(s)
                if len(strings) != len(set(strings)):
                    errs.append(f"{where} ev {j}: two notes on the same string")
            spans.append((t, t + d))
        # coverage: [0, L) must be covered without gaps (a tie from the previous bar counts)
        spans.sort()
        reach = carry
        for a, b in spans:
            if a > reach:
                errs.append(f"{where}: gap from tick {reach} to {a} (missing rest or wrong length?)")
            reach = max(reach, b)
        if reach < L:
            errs.append(f"{where}: bar ends early at tick {reach} of {L} (missing rest or wrong length?)")
        carry = max(0, reach - L)
    return errs


def iter_files(args):
    for a in args:
        p = Path(a)
        if p.is_dir():
            yield from sorted(p.glob("*.tab.json"))
        else:
            yield p


def main(argv):
    quiet = "--quiet" in argv
    files = list(iter_files([a for a in argv if not a.startswith("--")]))
    if not files:
        print(__doc__)
        return 1
    bad = 0
    for f in files:
        try:
            song = json.loads(Path(f).read_text(encoding="utf-8"))
        except Exception as ex:  # noqa: BLE001
            print(f"FAIL {f}: not valid JSON: {ex}")
            bad += 1
            continue
        errs = check_song(song)
        if errs:
            bad += 1
            print(f"FAIL {f}: {len(errs)} problem(s)")
            for e in errs[:40]:
                print("   -", e)
        elif not quiet:
            nnotes = sum(len(e.get("n", [])) for b in song["bars"] for e in b["ev"])
            print(f"ok   {f}  ({len(song['bars'])} bars, {nnotes} notes)")
    print(f"\n{len(files) - bad}/{len(files)} valid")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
