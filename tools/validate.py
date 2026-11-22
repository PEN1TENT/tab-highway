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
VALID_TS_DENS = (1, 2, 4, 8, 16)
VALID_STATUSES = {"draft", "verified", "needs-review"}


def _is_int(x):
    return isinstance(x, int) and not isinstance(x, bool)


def _is_num(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def _valid_ts(ts):
    return (
        isinstance(ts, list)
        and len(ts) == 2
        and _is_int(ts[0])
        and ts[0] >= 1
        and _is_int(ts[1])
        and ts[1] in VALID_TS_DENS
    )


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
    if not (isinstance(tuning, list) and len(tuning) == 6 and all(_is_int(x) for x in tuning)):
        errs.append("tuning must be 6 MIDI ints (string 1 first)")
    if "capo" in song:
        capo = song["capo"]
        if not (_is_int(capo) and 0 <= capo <= 12):
            errs.append(f"capo must be an int in 0..12 (got {capo!r})")
    if not isinstance(song.get("id"), str) or not song["id"]:
        errs.append("id missing")
    meta = song.get("meta") or {}
    if not isinstance(meta, dict):
        errs.append("meta must be an object")
        meta = {}
    if not meta.get("title"):
        errs.append("meta.title missing")
    tr = meta.get("transcription")
    if isinstance(tr, dict) and tr.get("status") is not None:
        if tr["status"] not in VALID_STATUSES:
            errs.append(f"meta.transcription.status must be one of {sorted(VALID_STATUSES)} (got {tr['status']!r})")
    if not _is_num(song.get("bpm")) or song["bpm"] <= 0:
        errs.append("bpm must be > 0")
    if song.get("feel", "straight") not in ("straight", "swing8", "swing16"):
        errs.append('feel must be "straight", "swing8" or "swing16"')
    ts = song.get("ts")
    if not _valid_ts(ts):
        errs.append(f"ts must be [num>=1, den in {VALID_TS_DENS}] (got {ts!r})")
        ts = [4, 4]
    bars = song.get("bars")
    if not isinstance(bars, list) or not bars:
        errs.append("bars missing/empty")
        return errs

    carry = 0  # ticks a tied note from the previous bar runs into this one
    for i, bar in enumerate(bars, 1):
        where = f"bar {i}" + (f" (sheet {bar['src']})" if "src" in bar else "")
        if "ts" in bar:
            if _valid_ts(bar["ts"]):
                ts = bar["ts"]
            else:
                errs.append(f"{where}: invalid ts {bar['ts']!r}")
        if "bpm" in bar:
            if not _is_num(bar["bpm"]) or bar["bpm"] <= 0:
                errs.append(f"{where}: bpm must be > 0 (got {bar['bpm']!r})")
        L = bar_len(ts)
        evs = bar.get("ev")
        if not isinstance(evs, list) or not evs:
            errs.append(f"{where}: no events (write a whole-bar rest if empty)")
            carry = max(0, carry - L)
            continue
        last_t = -1
        spans = []
        note_reach = carry
        for j, e in enumerate(evs):
            t, d = e.get("t"), e.get("d")
            if not _is_int(t) or not _is_int(d) or t < 0 or d <= 0:
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
                if t + d > L:
                    errs.append(f"{where} ev {j}: rest runs past bar end ({t}+{d} > {L})")
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
                    if not (_is_int(s) and 1 <= s <= 6):
                        errs.append(f"{where} ev {j}: string {s} not in 1..6")
                    if not (_is_int(f) and 0 <= f <= 24):
                        errs.append(f"{where} ev {j}: fret {f} not in 0..24")
                    if len(n) >= 3 and n[2] not in TECHS:
                        errs.append(f"{where} ev {j}: unknown technique {n[2]!r}")
                    if len(n) == 4:
                        if n[2] != "b" or not _is_num(n[3]):
                            errs.append(f"{where} ev {j} note {k}: 4th item only valid as numeric bend amount for 'b'")
                    strings.append(s)
                if len(strings) != len(set(strings)):
                    errs.append(f"{where} ev {j}: two notes on the same string")
                note_reach = max(note_reach, t + d)
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
        carry = max(0, note_reach - L)
    if carry > 0:
        errs.append(f"tied note runs {carry} tick(s) past end of song")
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
