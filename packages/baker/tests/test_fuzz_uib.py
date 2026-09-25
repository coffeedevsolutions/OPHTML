"""S2's Python half: a hostile .uib gets a verdict, never a traceback.

A blob is a file somebody else wrote. `ps2ui check` and `ps2ui serve
--uib` read one through `read_uib`, whose promise is ValueError on a bad
file: check.py catches (OSError, ValueError) and prints the message.
Anything else is a traceback on a file a theme author was handed.

The C half is runtime/tests/fuzz_load.c under libFuzzer. This half is a
seeded mutation loop over the shipped examples' blobs, with the CRC
rewritten so a mutation reaches the parser rather than stopping at the
checksum, which is what a hostile file would do. Its first run found
struct.error, IndexError and KeyError escaping from eight places;
TestTheFixedSites below provokes each one directly, so a regression
names its site instead of a seed and an iteration.
"""
import os
import random
import struct
import sys
import tempfile
import unittest
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, HERE)

from ps2ui_bake import uib as U                     # noqa: E402
from ps2ui_bake.check import check_blob             # noqa: E402
from test_serve import ROOT, MEMCARD, OPLENV, blob  # noqa: E402

CONSOLE = os.path.join(ROOT, "examples", "console", "build", "ui.uib")
CHANNEL6 = os.path.join(ROOT, "examples", "channel6", "build", "ui.uib")

# Header field offsets, from the struct format rather than typed in:
# a format move changes the struct and this follows it.
_FIELDS = ("magic version feature_flags canvas_w canvas_h n_tex n_clut "
           "n_cmd n_focus initial off_tex off_clut off_cmd off_focus "
           "off_blob blob_len crc n_font n_slot off_font off_slot n_screen "
           "n_tint off_screen off_tint n_theme pad dar_num dar_den").split()


def _field(name):
    fmt = U._HEADER.format
    i = _FIELDS.index(name)
    off = struct.calcsize(fmt[:1] + fmt[1:1 + i])
    return off, fmt[1 + i]


def _get(data, name):
    off, code = _field(name)
    return struct.unpack_from("<" + code, data, off)[0]


def _put(data, name, value):
    off, code = _field(name)
    struct.pack_into("<" + code, data, off, value)


def raw(path):
    """An example's blob as bytes, with test_serve's skip-unless-CI rule
    (blob() is what applies it, and returns the parsed file)."""
    blob(path)
    with open(path, "rb") as fh:
        return fh.read()


def recrc(data):
    """The CRC a hostile file would carry: computed over its own bytes."""
    if len(data) < U._HEADER.size:
        return bytes(data)
    data = bytearray(data)
    struct.pack_into("<I", data, U._CRC_OFFSET, 0)
    struct.pack_into("<I", data, U._CRC_OFFSET, zlib.crc32(bytes(data)))
    return bytes(data)


class _Scratch(unittest.TestCase):
    def setUp(self):
        fd, self.path = tempfile.mkstemp(suffix=".uib")
        os.close(fd)
        self.addCleanup(os.unlink, self.path)

    def read(self, data):
        with open(self.path, "wb") as fh:
            fh.write(recrc(data))
        return U.read_uib(self.path)


class TestTheFixedSites(_Scratch):
    """One malformed field per site the mutation loop found."""

    def setUp(self):
        super().setUp()
        self.seed = bytearray(raw(MEMCARD))

    def assertRefused(self, data, *words):
        with self.assertRaises(ValueError) as cm:
            self.read(data)
        for w in words:
            self.assertIn(w, str(cm.exception))

    def test_a_table_past_the_end_is_a_valueerror(self):
        d = bytearray(self.seed)
        _put(d, "n_slot", 0xFFFF)
        self.assertRefused(d, "slot table", "runs past the end")

    def test_a_table_at_an_offset_the_runtime_refuses_is_a_valueerror(self):
        d = bytearray(self.seed)
        _put(d, "off_slot", _get(d, "off_slot") + 2)
        self.assertRefused(d, "slot table", "multiple of 4",
                           "PS2UI_ERR_ALIGN")

    def test_an_unknown_texture_format_is_a_valueerror(self):
        d = bytearray(self.seed)
        struct.pack_into("<H", d, _get(d, "off_tex"), 85)
        self.assertRefused(d, "texture 0 has format 85")

    def test_a_glyph_table_past_the_blob_is_a_valueerror(self):
        d = bytearray(self.seed)
        # glyph_count is the font entry's sixth uint16.
        struct.pack_into("<H", d, _get(d, "off_font") + 10, 0xFFFF)
        self.assertRefused(d, "font 0's glyph table", "runs past")

    def test_a_screen_range_past_the_focus_table_is_a_verdict(self):
        d = bytearray(self.seed)
        # A screen entry opens name_off, cmd_first, cmd_count (uint32
        # each), then focus_first and focus_count (uint16), so the
        # count sits at byte 14. The format string says the same.
        self.assertTrue(U._SCREEN.format.startswith("<IIIHH"))
        at = _get(d, "off_screen") + 14
        focus_count = struct.unpack_from("<H", d, at)[0]
        struct.pack_into("<H", d, at, focus_count + 40)
        rep = check_blob(self.read(d))
        self.assertGreater(rep.errors, 0)
        self.assertTrue(any("partition the focus table" in label and not ok
                            for ok, _, label in rep.results))

    def test_a_screen_range_past_the_command_table_is_a_verdict(self):
        # cmd_count is the entry's third uint32, at byte 8. Every check
        # after check_screens walks command ranges, so this is the case
        # check_blob's early return exists for.
        d = bytearray(self.seed)
        at = _get(d, "off_screen") + 8
        struct.pack_into("<I", d, at, struct.unpack_from("<I", d, at)[0] + 500)
        rep = check_blob(self.read(d))
        self.assertTrue(any("partition the command table" in label and not ok
                            for ok, _, label in rep.results))

    def test_a_font_naming_no_texture_is_a_verdict(self):
        d = bytearray(self.seed)
        struct.pack_into("<H", d, _get(d, "off_font"), 0x7FFF)
        rep = check_blob(self.read(d))
        self.assertTrue(any("font 0 names a real atlas texture" in label
                            and not ok for ok, _, label in rep.results))


class TestMutatedBlobs(_Scratch):
    """The loop itself, seeded, so a failure reproduces exactly."""

    ROUNDS = 150

    def mutate(self, rng, b):
        b = bytearray(b)
        for _ in range(rng.randint(1, 4)):
            r = rng.random()
            if r < 0.5:
                i = rng.randrange(min(len(b), 4096) if rng.random() < 0.7
                                  else len(b))
                b[i] = rng.randrange(256)
            elif r < 0.7:
                struct.pack_into("<H", b, rng.randrange(0, 84, 2), rng.choice(
                    [0, 1, 2, 0xFFFF, 0x7FFF, rng.randrange(65536)]))
            elif r < 0.85:
                struct.pack_into("<I", b, rng.randrange(0, 84, 4), rng.choice(
                    [0, 1, 3, 0xFFFFFFFF, len(b), len(b) - 4,
                     rng.randrange(1 << 32)]))
            else:
                del b[rng.randrange(U._HEADER.size, len(b)):]
        return b

    def _run(self, path):
        seed = raw(path)
        rng = random.Random(os.path.basename(os.path.dirname(
            os.path.dirname(path))))
        for n in range(self.ROUNDS):
            data = self.mutate(rng, seed)
            try:
                u = self.read(data)
            except ValueError:
                continue
            except Exception as exc:  # noqa: BLE001 -- the finding itself
                self.fail("read_uib raised %s, not ValueError, on mutation "
                          "%d of %s: %s" % (type(exc).__name__, n,
                                            os.path.relpath(path, ROOT), exc))
            try:
                check_blob(u, console=bool(n & 1))
            except Exception as exc:  # noqa: BLE001
                self.fail("check_blob raised %s on mutation %d of %s: %s"
                          % (type(exc).__name__, n,
                             os.path.relpath(path, ROOT), exc))

    def test_memcard(self):
        self._run(MEMCARD)

    def test_opl_env(self):
        self._run(OPLENV)

    def test_channel6(self):
        self._run(CHANNEL6)

    def test_console(self):
        self._run(CONSOLE)


if __name__ == "__main__":
    unittest.main()
