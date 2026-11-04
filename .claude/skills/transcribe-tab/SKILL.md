---
name: transcribe-tab
description: Transcribe guitar tab PDFs from the Drive library into tabjson song files for tab-highway, a few songs per run. Use when asked to "transcribe tabs", "do the next songs", "/transcribe-tab 3", or to fix a transcribed song.
---

# Transcribe tab PDFs → tabjson

Goal: turn the next few PDFs from the Drive folder into valid `library/songs/<id>.tab.json`
files (format: `FORMAT.md`), commit them to the private library repo, and stop.
One run = **N songs** (argument, default 3). Each song costs roughly 10–25 image reads,
so keep N small and stop cleanly if the session is getting long.

## Setup (check once per run)

- Run from the `tab-highway` repo root.
- The private library repo must be cloned at `library/` (it is git-ignored here):
  `git clone https://github.com/PEN1TENT/tab-library library` if missing.
- Python deps: `pip install pymupdf pillow numpy` (add `--break-system-packages` if pip refuses).
- Drive folder id: `1eoOos6-g8awSARAxe4P5CErm8N0qUcdx` (PDFs named `NNN_title.pdf`).

## Steps for each song

1. **Pick ids:** `python tools/next_ids.py library -n N` → e.g. `051 052 053`.

2. **Get the PDF** (skip if it's already in `inbox/`):
   - Google Drive connector: `search_files` with
     `parentId = '1eoOos6-g8awSARAxe4P5CErm8N0qUcdx' and title contains 'NNN_'`
     → `download_file_content(fileId)`. The result is too big to show, so it is saved to a
     file; run `python tools/drive_decode.py <that-file> inbox`.
   - No Drive connector? Ask the user to drop the PDFs into `inbox/` instead.
   - Not found in Drive → add `"NNN": "not in Drive"` to `library/skip.json` and move on.

3. **Cut it into strips:** `python tools/prepare.py inbox/NNN_*.pdf --out work`
   → `work/NNN/header.png` + `sys01.png, sys02.png …` (one system = notation + TAB each).

4. **Read `header.png`** for title, artist, tempo (♩=), time signature, capo, tuning
   (e.g. "Drop D" → `[64,59,55,50,45,38]`, capo 2 → `"capo": 2`).

5. **Read every strip in order** (`Read work/NNN/sys01.png` …) and write the bars. Rules:
   - **Frets come from the TAB, rhythm comes from the notation above it.** Line them up by
     horizontal position. TAB lines top→bottom are strings 1 (e) → 6 (E).
   - Work in ticks, ppq = 24: 16th = 6, 8th = 12, quarter = 24, dotted quarter = 36,
     half = 48, whole = 96, 8th triplet = 8 (bracket "3"), 16th triplet = 4, 32nd = 3.
   - **Tied notes:** write the note once with `d` covering the whole tie, even past the
     bar line. A bracketed TAB number like `(5)` is the tail of a tie: **don't write it**.
   - **Arc between two different frets on one string:** hammer-on/pull-off → put
     `"h"` on the *second* note. A slash `/` or `\` between frets → `"s"` on the second note.
   - `x` on the TAB → `[string, 0, "x"]`. Harmonics `<12>` → `"harm"`. Bends → `"b"`.
   - Notes stacked vertically = same `t`. Bass notes usually last longer than the
     melody above them: give them their own event with their own `d`.
   - **Write every rest** (`{"t":0,"d":48,"rest":true}`): validation needs them.
   - Repeat signs / D.S. / coda: write the bars out in playing order; put the printed
     bar number in `"src"`.
   - Many bars repeat a pattern. Reuse is fine, but **check every bar against the image**:
     small changes (one fret, a tie) are common.
   - Don't guess silently. If a spot is unreadable, write your best reading and list
     the bar in `meta.transcription.notes`, then set `status` to `"needs-review"`.

6. **Write the file** `library/songs/NNN.tab.json`:
   - `id` = `"NNN"`, `meta.source` = `{"file": "<pdf name>", "drive_id": "<id>"}`,
     `meta.transcription` = `{"by": "<model name>", "date": "<today>", "status": "draft", "notes": "..."}`.
   - For long songs, write it in pieces: write the first systems, run
     validate, then add the rest with Edit.

7. **Check it:** `python tools/tabfmt.py library/songs/NNN.tab.json && python tools/validate.py library/songs/NNN.tab.json`.
   Every reported gap/overflow is a real mistake: re-read that strip and fix it.
   Don't "fix" a bar by padding rests unless the image really shows a rest.

8. **Save progress** (after each song, so an interrupted run loses nothing):
   ```
   python tools/build_index.py library
   cd library && git add songs index.json skip.json 2>/dev/null; git commit -m "Add NNN <title>" && git push; cd ..
   ```

9. Delete `work/NNN/` and the PDF from `inbox/` when the song is committed.

## At the end of the run

Report: songs added (id, title, bars, status), songs skipped and why, and the bars
you flagged for review. Nothing else.

## Fixing a song later

The user may say "bar 12 of 032 is wrong". Re-run steps 2–3 for that id, read the strip that
holds the bar (`src` numbers match the sheet), fix the events, then steps 7–8.
