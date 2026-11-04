# Tab Highway 🎸

Turn guitar tab into a **sliding-note highway** you can play along with, like a rhythm game but for real guitar.

**▶ Live demo:** https://pen1tent.github.io/tab-highway/

- Notes slide toward a hit line, one lane per string (e B G D A E, the same order as a tab).
- A fretboard under the lanes shows what to fret now and what's coming next.
- Built-in plucked-string sound, metronome click and count-in.
- Speed from 40% to 120%, plus loops over any range of bars, for practice.
- **Play along with the real recording:** load an audio file, set the offset (or tap **N** on the first note) and the notes follow the track.
- Songs are plain JSON in the open **[tabjson format](FORMAT.md)**, so any app can read them.

## Use it

Open the live page, or run it locally:

```bash
git clone https://github.com/PEN1TENT/tab-highway
cd tab-highway
python -m http.server 8000      # then open http://localhost:8000
```

The page lists every song in `library/index.json` (your own library, see below) and `demo/index.json`.
You can also open or drop any `.tab.json` file onto the highway.

| key | action |
|---|---|
| `Space` | play / pause |
| `R` | restart (from loop start) |
| `←` `→` | previous / next bar |
| `N` | while a track plays: tap on the first note to sync |

## Song format

See **[FORMAT.md](FORMAT.md)** and the JSON Schema in [`schema/`](schema/tabjson-v1.schema.json).
In short: bars of timed events, `ppq = 24` ticks per quarter note, notes as `[string, fret, technique?]`:

```json
{ "t": 0, "d": 12, "n": [[5, 3], [2, 1]] }
```

## Build a library from tab PDFs (with Claude)

The `tools/` folder plus a Claude Code skill turn image-only tab PDFs (screenshots, scans, photos)
into tabjson files, a few songs per session:

```bash
git clone https://github.com/<you>/<your-private-library> library   # your songs live here (git-ignored)
pip install pymupdf pillow numpy
claude            # then:  /transcribe-tab 3
```

| tool | what it does |
|---|---|
| `tools/prepare.py` | PDF → one upscaled image per system (notation + TAB), finds staff lines automatically |
| `tools/drive_decode.py` | saves a PDF downloaded through the Google Drive connector |
| `tools/validate.py` | checks songs: valid strings/frets, and every bar adds up exactly |
| `tools/tabfmt.py` | formats songs one event per line (clean diffs) |
| `tools/build_index.py` | rebuilds a library's `index.json` |
| `tools/next_ids.py` | which song numbers are still to do |

The full procedure Claude follows is in [`.claude/skills/transcribe-tab/SKILL.md`](.claude/skills/transcribe-tab/SKILL.md).

> **Copyright:** tabs and songs belong to their arrangers and artists. Keep transcriptions of
> other people's work in a **private** library unless you have permission to share them.
> This repo only ships code, the format, and an original demo piece.

## License

Code: MIT (see [LICENSE](LICENSE)). The demo song is original and free to use.
