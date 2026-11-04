# tab-highway

Static web player (`index.html`, no build step) + Python tools for the tabjson song format.

- Song format spec: `FORMAT.md` (ppq = 24, bars → events → `[string, fret, tech?]`). Keep `schema/` and `tools/validate.py` in sync with it.
- `library/` is the user's **private** song library (separate repo `PEN1TENT/tab-library`, git-ignored here). Never commit song transcriptions of third-party tabs to this public repo; only `demo/` songs that are original.
- Transcribing PDFs → follow `.claude/skills/transcribe-tab/SKILL.md`.
- After changing songs: `python tools/tabfmt.py <file>`, `python tools/validate.py <dir>`, `python tools/build_index.py <library>`.
- `index.html` embeds `demo/songs/demo-etude-1.tab.json` as a fallback (the `BUILTIN` constant). If the demo changes, re-embed it.
- Test the player with `python -m http.server` and a headless browser; check there are no console errors and that notes get scheduled after pressing Play.
