# tabjson v1: song format

One song = one UTF-8 JSON file named `<id>.tab.json`.
It is built to be:

- **easy to write by hand or by an LLM** reading a tab sheet (short keys, one event per line),
- **easy to check mechanically** (every bar must add up exactly, see [Validation](#validation)),
- **easy to play**. The player turns it into a timeline in a few lines of code.

## Example

```json
{
  "format": "tabjson",
  "version": 1,
  "id": "demo-etude-1",
  "meta": {
    "title": "Highway Etude No. 1",
    "artist": "tab-highway demo",
    "source": { "file": "", "drive_id": "" },
    "transcription": { "by": "claude", "date": "2026-11-04", "status": "verified", "notes": "" }
  },
  "tuning": [64, 59, 55, 50, 45, 40],
  "capo": 0,
  "ppq": 24,
  "bpm": 80,
  "ts": [4, 4],
  "bars": [
    { "ev": [
      { "t": 0,  "d": 12, "n": [[5, 3]] },
      { "t": 12, "d": 12, "n": [[4, 2]] },
      { "t": 24, "d": 6,  "n": [[3, 0]] },
      { "t": 30, "d": 6,  "n": [[3, 2, "h"]] },
      { "t": 36, "d": 60, "n": [[2, 1], [1, 0]] }
    ]}
  ]
}
```

## Top level

| key | type | meaning |
|---|---|---|
| `format` | `"tabjson"` | always this string |
| `version` | `1` | format version |
| `id` | string | unique id, also the file name (`<id>.tab.json`). For the Drive library it's the 3-digit number in the PDF name, e.g. `"032"` |
| `meta.title`, `meta.artist` | string | song info |
| `meta.arranger` | string, optional | who arranged the tab |
| `meta.source` | object | where it came from: `file` (PDF name), `drive_id` |
| `meta.transcription` | object | `by` (who/what transcribed it), `date`, `status` (`"draft"`, `"verified"`, `"needs-review"`), `notes` (free text: doubtful bars, etc.) |
| `tuning` | 6 ints | MIDI note of each **open** string, string 1 (high e) first. Standard: `[64,59,55,50,45,40]` |
| `capo` | int | capo fret (frets in the file are relative to the capo) |
| `ppq` | int | ticks per quarter note. **Always 24** in v1 |
| `bpm` | number | starting tempo (quarter notes per minute) |
| `ts` | `[num, den]` | starting time signature |
| `bars` | array | bars **in playing order** (repeats and D.S./coda written out, not as symbols) |

## Bars

| key | type | meaning |
|---|---|---|
| `ev` | array | events in the bar, sorted by `t` |
| `bpm` | number, optional | tempo change starting at this bar |
| `ts` | `[num, den]`, optional | time-signature change starting at this bar |
| `label` | string, optional | section name: `"Intro"`, `"Verse"`, `"Chorus"` … |
| `src` | int, optional | the bar number printed on the sheet (useful when repeats are written out) |

## Events

| key | type | meaning |
|---|---|---|
| `t` | int | start, in ticks from the start of the bar |
| `d` | int | written length in ticks, **ties included** |
| `n` | array | notes: `[string, fret]` or `[string, fret, tech]` |
| `rest` | `true`, optional | a rest (then `n` is omitted) |

String 1 = high e … string 6 = low E. Notes that start together (chords, bass + melody)
go in one event, or in separate events with the same `t` when their lengths differ.

### Tick table (ppq = 24)

| note | ticks | | note | ticks |
|---|---|---|---|---|
| whole | 96 | | dotted quarter | 36 |
| half | 48 | | dotted eighth | 18 |
| quarter | 24 | | eighth triplet | 8 |
| eighth | 12 | | sixteenth triplet | 4 |
| sixteenth | 6 | | 32nd | 3 |

A 4/4 bar is 96 ticks long, a 3/4 bar 72, a 6/8 bar 72.

### Techniques (`tech`, third item of a note)

| code | meaning | picked? |
|---|---|---|
| `h` | hammer-on **or** pull-off *into* this note | no (legato) |
| `s` | slide *into* this note from the previous note on the string | no (legato) |
| `b` | bend (optional 4th item: bend amount in semitones, default 1) | yes |
| `x` | dead / muted note | yes |
| `harm` | natural harmonic | yes |
| `pm` | palm mute | yes |

### Ties
A note tied across beats or bar lines is written **once**, at its first onset,
with `d` covering the whole tied length (it may run past the bar line).
The bracketed tied note in the TAB, e.g. `(5)`, is **not** written again.

## Validation

`python tools/validate.py <files>` checks every song:

1. `format`, `version`, `ppq = 24`, 6-string `tuning`.
2. strings 1–6, frets 0–24, `t` and `d` positive integers, events sorted.
3. **Bar coverage:** the union of all `[t, t+d)` intervals (rests included) must
   cover the bar from 0 to its length **with no gaps**, and no event may *start*
   at or after the bar end. Only tied notes may run past the bar line.
   A misread rhythm almost always breaks this rule, so it catches most transcription mistakes.

Writing every rest explicitly (`{"t":0,"d":48,"rest":true}`) is what makes check 3 possible.

## Library index

`index.json` in a library folder lists the songs for the player:

```json
{ "format": "tabjson-index", "version": 1,
  "songs": [ { "id": "032", "title": "ดึกแล้ว", "artist": "Hydra", "bpm": 76, "bars": 32, "status": "draft", "file": "songs/032.tab.json" } ] }
```

`python tools/build_index.py <library-folder>` regenerates it from the song files.
