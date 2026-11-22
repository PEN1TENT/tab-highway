import base64
import copy
import json
import re
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tools import build_index, drive_decode, validate  # noqa: E402


def _base_song():
    return {
        "format": "tabjson",
        "version": 1,
        "id": "test-song",
        "meta": {
            "title": "Test Song",
            "artist": "Tester",
            "transcription": {"status": "draft"},
        },
        "tuning": [64, 59, 55, 50, 45, 40],
        "capo": 0,
        "ppq": 24,
        "bpm": 100,
        "ts": [4, 4],
        "bars": [
            {"ev": [{"t": 0, "d": 96, "n": [[1, 0]]}]},
        ],
    }


def _import_prepare():
    try:
        import tools.prepare as prepare
        return prepare
    except ImportError:
        dummy = types.ModuleType("pymupdf")
        with mock.patch.dict(sys.modules, {"pymupdf": dummy}):
            sys.modules.pop("tools.prepare", None)
            import tools.prepare as prepare
            sys.modules.pop("tools.prepare", None)
            return prepare


class ValidateTests(unittest.TestCase):
    def test_demo_song_valid(self):
        demo = json.loads((ROOT / "demo/songs/demo-etude-1.tab.json").read_text(encoding="utf-8"))
        self.assertEqual(validate.check_song(demo), [])

    def test_overflowing_rest_rejected(self):
        s = _base_song()
        s["bars"] = [
            {"ev": [{"t": 0, "d": 120, "rest": True}]},
            {"ev": [{"t": 24, "d": 72, "n": [[1, 0]]}]},
        ]
        errs = validate.check_song(s)
        self.assertTrue(any("rest runs past bar end" in e for e in errs), errs)
        self.assertTrue(any("gap from tick 0 to 24" in e for e in errs), errs)

    def test_bar_bpm_validation(self):
        for bad in (0, -60, "120", True):
            s = _base_song()
            s["bars"][0]["bpm"] = bad
            errs = validate.check_song(s)
            self.assertTrue(any("bpm must be > 0" in e for e in errs), (bad, errs))

    def test_ts_and_bar_ts_validation(self):
        for bad_ts in ([4, 0], [4, 3], [0, 4], [True, 4], "4/4"):
            s = _base_song()
            s["ts"] = bad_ts
            errs = validate.check_song(s)
            self.assertTrue(any("ts must be" in e for e in errs), (bad_ts, errs))

            s2 = _base_song()
            s2["bars"][0]["ts"] = bad_ts
            errs2 = validate.check_song(s2)
            self.assertTrue(any("invalid ts" in e for e in errs2), (bad_ts, errs2))

    def test_capo_validation(self):
        for bad_capo in (-1, 13, 1.5, True, "2"):
            s = _base_song()
            s["capo"] = bad_capo
            errs = validate.check_song(s)
            self.assertTrue(any("capo" in e for e in errs), (bad_capo, errs))

    def test_note_fourth_item_validation(self):
        s = _base_song()
        s["bars"][0]["ev"] = [{"t": 0, "d": 96, "n": [[1, 2, "b", 1.5]]}]
        self.assertEqual(validate.check_song(s), [])

        for bad_note in ([1, 2, "h", 1], [1, 2, "b", "half"], [1, 2, "b", True]):
            s2 = _base_song()
            s2["bars"][0]["ev"] = [{"t": 0, "d": 96, "n": [bad_note]}]
            errs = validate.check_song(s2)
            self.assertTrue(any("4th item" in e for e in errs), (bad_note, errs))

    def test_status_validation(self):
        s = _base_song()
        s["meta"]["transcription"]["status"] = "invalid-status"
        errs = validate.check_song(s)
        self.assertTrue(any("status" in e for e in errs), errs)

    def test_trailing_tie_rejected(self):
        s = _base_song()
        s["bars"] = [{"ev": [{"t": 0, "d": 120, "n": [[1, 0]]}]}]
        errs = validate.check_song(s)
        self.assertTrue(any("past end of song" in e for e in errs), errs)

    def test_booleans_rejected_as_ints(self):
        s = _base_song()
        s["tuning"] = [64, 59, 55, 50, 45, True]
        s["bpm"] = True
        s["bars"][0]["ev"] = [{"t": False, "d": 96, "n": [[True, False]]}]
        errs = validate.check_song(s)
        self.assertTrue(any("tuning" in e for e in errs), errs)
        self.assertTrue(any("bpm must be > 0" in e for e in errs), errs)
        self.assertTrue(any("t/d must be ints" in e for e in errs), errs)

        s2 = _base_song()
        s2["bars"][0]["ev"] = [{"t": 0, "d": 96, "n": [[True, False]]}]
        errs2 = validate.check_song(s2)
        self.assertTrue(any("string True not in 1..6" in e for e in errs2), errs2)
        self.assertTrue(any("fret False not in 0..24" in e for e in errs2), errs2)

    def test_empty_bar_does_not_leak_carry(self):
        s = _base_song()
        s["bars"] = [
            {"ev": [{"t": 0, "d": 200, "n": [[1, 0]]}]},
            {"ev": []},
            {"ev": [{"t": 0, "d": 96, "n": [[1, 0]]}]},
        ]
        errs = validate.check_song(s)
        self.assertTrue(any("bar 2: no events" in e for e in errs), errs)
        self.assertFalse(any("past end of song" in e for e in errs), errs)


class DriveDecodeTests(unittest.TestCase):
    def test_sanitizes_traversal_and_slashes(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            out_dir = tmp_path / "inbox"
            payload = {
                "id": "099",
                "title": "../../evil/099_song.pdf",
                "content": base64.b64encode(b"%PDF-1.4\n").decode("ascii"),
            }
            raw_file = tmp_path / "result.json"
            raw_file.write_text("prefix\n" + json.dumps(payload), encoding="utf-8")

            rc = drive_decode.main([str(raw_file), str(out_dir)])
            self.assertEqual(rc, 0)
            written = list(out_dir.iterdir())
            names = {p.name for p in written}
            self.assertIn(".._.._evil_099_song.pdf", names)
            self.assertIn(".._.._evil_099_song.pdf.drive_id", names)
            self.assertFalse((tmp_path / "evil").exists())


class BuildIndexTests(unittest.TestCase):
    def test_missing_songs_dir_returns_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            rc = build_index.main([tmp])
            self.assertEqual(rc, 1)
            self.assertFalse((Path(tmp) / "index.json").exists())


class PrepareTests(unittest.TestCase):
    def test_group_systems_ignores_tight_outlier(self):
        try:
            prepare = _import_prepare()
        except ImportError as ex:
            self.skipTest(f"prepare dependencies missing: {ex}")

        # Real notation staves: spacing 10 (height 40), TAB staves: spacing 16 (height 80)
        # Plus one tight outlier cluster (e.g. chord box) with spacing 3
        staves = [
            [10, 13, 16, 19, 22],             # tight outlier: sp = 3
            [100, 110, 120, 130, 140],        # notation 1: sp = 10
            [180, 196, 212, 228, 244, 260],   # TAB 1: sp = 16
            [320, 330, 340, 350, 360],        # notation 2: sp = 10
            [400, 416, 432, 448, 464, 480],   # TAB 2: sp = 16
        ]
        systems = prepare.group_systems(staves)
        self.assertEqual(systems, [(100, 260, 10.0), (320, 480, 10.0)])

    def test_crop_systems_always_non_empty(self):
        try:
            prepare = _import_prepare()
            from PIL import Image
        except ImportError as ex:
            self.skipTest(f"prepare dependencies missing: {ex}")

        img = Image.new("RGB", (400, 100), "white")
        crops = prepare.crop_systems(img, [(10, 50, 10.0), (120, 150, 10.0)])
        self.assertEqual(len(crops), 2)
        for c in crops:
            self.assertGreater(c.height, 0)


class BuiltinSyncTests(unittest.TestCase):
    def test_builtin_matches_demo_etude(self):
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        m = re.search(r"const BUILTIN = (\{.*?\});", html)
        self.assertIsNotNone(m, "BUILTIN constant not found in index.html")
        builtin = json.loads(m.group(1))
        demo = json.loads((ROOT / "demo/songs/demo-etude-1.tab.json").read_text(encoding="utf-8"))
        self.assertEqual(builtin, demo)


if __name__ == "__main__":
    unittest.main()
