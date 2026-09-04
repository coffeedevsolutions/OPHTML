"""Baker test suite: numeric rules, GS encodings, atlases, nine-patches,
quad flattening, the .uib round-trip, and the previewer's replay
semantics. stdlib unittest + Pillow only, same as the package.

Run:  cd packages/baker && python3 -m unittest discover -s tests -v
"""

import contextlib
import io
import json
from dataclasses import replace
import copy
import os
import shutil
import struct
import zlib
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from PIL import Image

from ps2ui_bake.rounding import (
    round_half_up, glyph_advance_px, kern_px, css_alpha_to_gs,
    css_channel_to_gs, gs_alpha_to_css,
)
from ps2ui_bake import gs
from ps2ui_bake.atlas import AtlasBuilder
from ps2ui_bake.ninepatch import (COVERAGE_FILL, COVERAGE_RING,
                                  rasterize_coverage, slice_quads,
                                  patch_key)
from ps2ui_bake.quads import (
    Flattener, DrawRecord, OP_QUAD, OP_TEXQUAD, OP_SCISSOR_PUSH, OP_SCISSOR_POP,
    STATE_ALWAYS, STATE_UNFOCUSED, STATE_FOCUSED, FOCUS_NONE, TEX_NONE,
)
from ps2ui_bake.uib import (write_uib, read_uib, MAGIC, VERSION,
                            FEAT_DYNAMIC_TEXT, FEAT_KERNING,
                            FEAT_SLOT_SPACING,
                            FEAT_ROLE_TINTS,
                            _CMD, _HEADER, _FOCUS, _FONT, _KERN,
                            _SLOT, _TINT)
from ps2ui_bake import preview

REPO = os.path.join(os.path.dirname(__file__), "..", "..", "..")
FONTS = os.path.join(REPO, "fonts")
METRICS = os.path.join(FONTS, "default.metrics.json")


# ONE LIST OF CANDIDATE FONTS, AND IT IS fonts/fonts.json.
#
# This used to be two hardcoded Linux paths while fonts.json carried
# six. Two lists for one job, and the shorter one was the one the test
# suite believed -- so the suite could not find a font on a machine the
# baker itself would have been fine on. The manifest is the thing the
# product reads; the tests read it too, and a path added for a user is
# added for the suite in the same edit.
def _manifest_ttf():
    try:
        from ps2ui_bake.cli import load_font_manifest
        return load_font_manifest(os.path.join(FONTS, "fonts.json"))
    except Exception:
        # Any reason at all: no manifest, no candidate on this machine,
        # a face missing. The caller's question is "can I build an
        # atlas", and every one of those answers it "no".
        return None


_MANIFEST = _manifest_ttf()
TTF = _MANIFEST["regular"]["ttf"] if _MANIFEST else None


# A MISSING FONT IS A SKIP, NOT AN ERROR, AND NOT A DECORATOR.
#
# With no TTF this suite used to report `errors=22` across seven
# classes -- a stranger's first `python3 -m unittest discover`, on any
# machine without DejaVu at one of two Linux paths, after they had done
# everything the tutorial asked. Four `skipIf(TTF is None)` sites
# existed and seven classes needed one.
#
# Decorating the other fifteen methods was the obvious fix and is the
# worse one, twice over. Class-level guards would skip 25 tests that do
# not touch a font and pass without one; method-level guards are
# fifteen things to remember, and the sixteenth test to reach for a
# font gets an error again. So the guard lives where the font is
# actually fetched: raising SkipTest from inside a test body is a skip,
# so every present and future path to a font is covered by the fetch
# rather than by a habit.
def require_ttf():
    if TTF is None:
        _no_fonts("no DejaVu Sans on this machine")
    return TTF


# ...AND WHERE IT MUST NOT BE QUIET, IT IS NOT.
#
# The same tripwire and the same wording as PS2UI_REQUIRE_CROSSCHECK
# and PS2UI_REQUIRE_EXAMPLES. A skip is the right answer on a stranger's
# laptop and the wrong one in CI, where the fonts are installed on
# purpose: 22 silent skips there would mean the kerning tables, the
# cross-language pen agreement and the slot spacing all stopped being
# checked, with the run still green. CI sets this, so a skip that
# should be impossible is a failure that names itself.
def _no_fonts(why):
    if os.environ.get("PS2UI_REQUIRE_FONTS") == "1":
        raise AssertionError(
            "PS2UI_REQUIRE_FONTS=1 but %s. This environment is supposed to "
            "have the fonts fonts/fonts.json names, so this is a broken "
            "environment rather than a test to skip." % why)
    raise unittest.SkipTest(
        "%s. fonts/fonts.json lists the paths that are looked in; install "
        "DejaVu Sans or add yours to that file." % why)


def require_raqm():
    """Both conditions, because the test needs both.

    A TTF alone is not enough for the fontgen success path: without
    Pillow's Raqm layout engine every advance comes out identical and
    the kern table comes out empty, which is exactly the silent wrong
    answer fontgen refuses to write. Guarding this on the TTF alone
    would turn "no Raqm" into a failure that reads like a kerning bug.
    """
    require_ttf()
    from PIL import features
    if not features.check("raqm"):
        _no_fonts("this Pillow has no Raqm layout engine")


# NOT GUARDED, DELIBERATELY. Most callers hand this to a Flattener over
# an IR with no text, which needs no atlas and passes with no font at
# all. An early version raised the skip here and took 43 such tests
# down with the 22 that needed it -- trading an error a reader can see
# for a skip they cannot, which is the worse of the two.
def font_paths():
    return {
        "regular": {"ttf": TTF, "metrics": METRICS},
        "bold": {"ttf": TTF, "metrics": METRICS},
    }


def tiny_ir(commands, focus_nodes=None, initial=None):
    return {
        "version": 1,
        "canvas": {"w": 320, "h": 240},
        "commands": commands,
        "focus": {"nodes": focus_nodes or [], "initial": initial},
        "warnings": [],
    }


class TestRounding(unittest.TestCase):
    def test_half_up_differs_from_python_round(self):
        # Python's round() is banker's rounding; ours must not be.
        self.assertEqual(round(2.5), 2)
        self.assertEqual(round_half_up(2.5), 3)
        self.assertEqual(round_half_up(3.5), 4)

    def test_glyph_advance_matches_layout_formula(self):
        # Mirrors packages/layout test: 'i' = 278 units at 13px -> 4.
        self.assertEqual(glyph_advance_px(278, 13), 4)
        # And against the real metrics file the layout stage uses.
        with open(METRICS, encoding="utf-8") as fh:
            adv = json.load(fh)["advances"]
        self.assertEqual(adv["105"], 278)

    def test_metrics_include_the_real_space(self):
        # Regression: an invisible U+00A0 in the fontgen charset literal
        # once shadowed U+0020, so every space measured at '?' width on
        # both hosts (consistently — which is why no test caught it
        # until dynamic-text slots rendered '?' for spaces).
        with open(METRICS, encoding="utf-8") as fh:
            adv = json.load(fh)["advances"]
        self.assertIn("32", adv)
        self.assertLess(adv["32"], adv["63"])  # space is narrower than '?'

    def test_negative_half_up(self):
        self.assertEqual(round_half_up(-0.5), 0)
        self.assertEqual(round_half_up(-1.5), -1)


class TestKerningExtraction(unittest.TestCase):
    """fontgen measures pairs rather than reading a kern table, so the
    things that can go wrong are shaper behaviours, not parse errors."""

    def setUp(self):
        with open(METRICS, encoding="utf-8") as fh:
            self.metrics = json.load(fh)
        self.kern = self.metrics.get("kerning", {})

    def test_the_classic_pairs_are_present_and_negative(self):
        # If these are missing the shaper applied no GPOS at all, which
        # is the failure mode an empty table cannot be told apart from.
        for pair, label in (("84,111", "To"), ("65,86", "AV"),
                            ("76,84", "LT"), ("80,46", "P.")):
            self.assertIn(pair, self.kern, label)
            self.assertLess(self.kern[pair], 0, label)

    def test_ligatures_are_not_mistaken_for_kerns(self):
        # DejaVu shapes "ff" as one glyph 15 units narrower than f + f.
        # The pen draws two glyphs, so adopting that as a kern would
        # make every measured width 15 units short of what is drawn.
        self.assertNotIn("102,102", self.kern)   # ff
        self.assertNotIn("102,105", self.kern)   # fi
        self.assertNotIn("102,108", self.kern)   # fl

    def test_only_nonzero_pairs_are_stored(self):
        # ~13k pairs measured, a few hundred kept: the table is a
        # sparse map, and a stored zero would just cost bytes.
        self.assertTrue(all(v != 0 for v in self.kern.values()))
        self.assertLess(len(self.kern), 2000)

    def test_keys_name_codepoints_in_order(self):
        for key in self.kern:
            prev, cur = key.split(",")
            self.assertTrue(prev.isdigit() and cur.isdigit(), key)
        # Kerning is directional: "AV" and "VA" are separate entries,
        # and a font may adjust one without the other.
        self.assertIn("84,111", self.kern)       # To
        self.assertNotIn("111,84", self.kern)    # oT is not kerned

    def test_every_kerned_codepoint_has_an_advance(self):
        adv = self.metrics["advances"]
        for key in self.kern:
            for cp in key.split(","):
                self.assertIn(cp, adv, key)


class TestFontgenRefusesWithoutRaqm(unittest.TestCase):
    """Without Raqm the advances come out identical and the kern table
    comes out empty, so regenerating would produce a diff that deletes
    every pair while every test still passes -- all three pens agree
    perfectly on zero kerning. fontgen must refuse, before writing."""

    def test_main_exits_nonzero_and_writes_nothing(self):
        # NAMES A TTF THAT DOES NOT EXIST, ON PURPOSE. The claim is
        # that fontgen refuses BEFORE writing, and the refusal is
        # checked before anything opens the font -- so a path that
        # could not be opened proves the ordering rather than relying
        # on it. It also means this test needs no font, which is why it
        # is the one test in this class that keeps running on a machine
        # with none. It used to be handed the module-level TTF and pass
        # while that was None.
        from unittest import mock
        from ps2ui_bake import fontgen
        with tempfile.TemporaryDirectory() as td:
            out = os.path.join(td, "m.json")
            with mock.patch.object(fontgen.features, "check",
                                   return_value=False):
                rc = fontgen.main([os.path.join(td, "absent.ttf"),
                                   "DejaVu Sans", "400", out])
            self.assertEqual(rc, 2)
            self.assertFalse(os.path.exists(out))

    def test_and_succeeds_with_raqm_present(self):
        # BOTH CONDITIONS. This is the arm that proves kerning is
        # actually extracted, so it needs a font AND the layout engine;
        # guarding it on the font alone turns a Pillow without Raqm
        # into a failure that reads like a kerning bug. That is not
        # hypothetical -- it is what pip's macOS wheel ships.
        require_raqm()
        from ps2ui_bake import fontgen
        with tempfile.TemporaryDirectory() as td:
            out = os.path.join(td, "m.json")
            rc = fontgen.main([TTF, "DejaVu Sans", "400", out])
            self.assertEqual(rc, 0)
            with open(out, encoding="utf-8") as fh:
                self.assertTrue(json.load(fh)["kerning"])


class TestAlphaDomain(unittest.TestCase):
    def test_opaque_css_is_gs_0x80(self):
        self.assertEqual(css_alpha_to_gs(255), 0x80)

    def test_zero_stays_zero(self):
        self.assertEqual(css_alpha_to_gs(0), 0)

    def test_midpoint(self):
        self.assertEqual(css_alpha_to_gs(128), 64)

    def test_round_trip_endpoints(self):
        self.assertEqual(gs_alpha_to_css(css_alpha_to_gs(255)), 255)
        self.assertEqual(gs_alpha_to_css(css_alpha_to_gs(0)), 0)

    def test_out_of_range_rejected(self):
        with self.assertRaises(ValueError):
            css_alpha_to_gs(256)
        with self.assertRaises(ValueError):
            gs_alpha_to_css(200)


class TestModulateDomain(unittest.TestCase):
    """Backlog B1: TEXQUAD vertex colors live in the GS 0x80-identity
    modulate domain; QUAD vertex RGB stays full-range."""

    def test_channel_identity_is_0x80(self):
        self.assertEqual(css_channel_to_gs(255), 0x80)
        self.assertEqual(css_channel_to_gs(0), 0)
        self.assertEqual(css_channel_to_gs(128), 64)

    def test_solid_quad_keeps_full_range_rgb(self):
        ir = tiny_ir([{
            "op": "rect", "x": 0, "y": 0, "w": 10, "h": 10,
            "fill": [200, 30, 30, 255], "borderWidth": 0, "borderColor": None,
            "radius": 0, "state": "always", "focusId": None,
        }])
        f = Flattener(ir, font_paths())
        f.run()
        self.assertEqual(f.records[0].rgba, (200, 30, 30, 0x80))

    def test_a_rounded_fill_is_tinted_by_its_own_colour(self):
        """WAS test_ninepatch_tint_is_modulate_identity, and the change
        is the point of P3b-6. The identity tint said "this texture
        already knows what colour it is" -- which put every rounded
        box's colour in its texels, where a tint table cannot reach it.
        The tint is now the fill, converted to the modulate domain like
        any other TEXQUAD colour.

        The identity has not gone away; it belongs to images, which
        really do carry their own colour."""
        ir = tiny_ir([{
            "op": "rect", "x": 0, "y": 0, "w": 40, "h": 40,
            "fill": [1, 2, 3, 255], "borderWidth": 0, "borderColor": None,
            "radius": 5, "state": "always", "focusId": None,
        }])
        f = Flattener(ir, font_paths())
        f.run()
        self.assertTrue(f.records)
        for r in f.records:
            self.assertEqual(r.op, OP_TEXQUAD)
            self.assertEqual(r.rgba, (1, 1, 2, 0x80))

    @unittest.skipIf(TTF is None, "DejaVu Sans not installed")
    def test_every_texquad_channel_at_most_0x80(self):
        # The baker never emits overbright; the C runtime test carries
        # the same fence over the real example blob.
        ir = tiny_ir([{
            "op": "text", "x": 0, "y": 0, "text": "hi", "size": 14,
            "weight": 400, "letterSpacing": 0, "color": [255, 255, 255, 255],
            "state": "always", "focusId": None,
        }])
        f = Flattener(ir, font_paths())
        f.run()
        for r in f.records:
            if r.op == OP_TEXQUAD:
                self.assertTrue(all(c <= 0x80 for c in r.rgba), r.rgba)


class TestGS(unittest.TestCase):
    def test_pack_rgba_converts_alpha_once(self):
        self.assertEqual(gs.pack_rgba_gs(1, 2, 3, 255), bytes((1, 2, 3, 0x80)))

    def test_csm1_swaps_bits_3_and_4(self):
        self.assertEqual(gs.clut_csm1_order(0), 0)
        self.assertEqual(gs.clut_csm1_order(8), 16)
        self.assertEqual(gs.clut_csm1_order(16), 8)
        self.assertEqual(gs.clut_csm1_order(24), 24)
        self.assertEqual(gs.clut_csm1_order(0x88), 0x90)

    def test_csm1_is_involution(self):
        for i in range(256):
            self.assertEqual(gs.clut_csm1_order(gs.clut_csm1_order(i)), i)

    def test_permute_round_trips(self):
        linear = bytes(range(256)) * 4
        linear = bytes(b for i in range(256) for b in (i, i, i, i))
        permuted = gs.permute_clut_csm1(linear)
        self.assertNotEqual(linear, permuted)
        self.assertEqual(gs.permute_clut_csm1(permuted), linear)

    def test_coverage_clut_is_alpha_ramp(self):
        clut = gs.coverage_clut()
        self.assertEqual(len(clut), 1024)
        self.assertEqual(clut[0:4], bytes((255, 255, 255, 0)))
        self.assertEqual(clut[255 * 4:256 * 4], bytes((255, 255, 255, 0x80)))


@unittest.skipIf(TTF is None, "DejaVu Sans not installed")
class TestAtlas(unittest.TestCase):
    def build(self, size=16):
        return AtlasBuilder(require_ttf(), METRICS, 400, size)

    def test_advance_comes_from_metrics_not_freetype(self):
        b = self.build(13)
        g = b.add("i")
        self.assertEqual(g.advance, glyph_advance_px(278, 13))

    def test_space_has_advance_but_no_ink(self):
        b = self.build()
        g = b.add(" ")
        self.assertEqual((g.w, g.h), (0, 0))
        self.assertGreater(g.advance, 0)

    def test_glyphs_do_not_overlap(self):
        b = self.build()
        for ch in "abcdefghijklmnopqrstuvwxyz":
            b.add(ch)
        atlas = b.build()
        boxes = [(g.u, g.v, g.u + g.w, g.v + g.h)
                 for g in atlas.glyphs.values() if g.w]
        for i, a in enumerate(boxes):
            for bb in boxes[i + 1:]:
                sep = a[2] <= bb[0] or bb[2] <= a[0] or a[3] <= bb[1] or bb[3] <= a[1]
                self.assertTrue(sep, f"{a} overlaps {bb}")

    def test_add_is_idempotent(self):
        b = self.build()
        self.assertIs(b.add("Q"), b.add("Q"))

    def test_ink_hangs_from_metrics_baseline(self):
        # Backlog B2: 'A' sits on the baseline, so across sizes its ink
        # bottom (bearing_y + h, measured from the line-box top) must
        # land on metrics_ascent_px within a pixel of AA slop — even
        # where Pillow's own ascent disagrees with the metrics ascent.
        for size in (12, 13, 15, 20, 26):
            b = self.build(size)
            g = b.add("A")
            baseline = b.metrics_ascent_px
            self.assertLessEqual(abs((g.bearing_y + g.h) - baseline), 1,
                                 f"size {size}: ink bottom {g.bearing_y + g.h} vs baseline {baseline}")
            # And a descender reaches below it.
            gy = b.add("g")
            self.assertGreater(gy.bearing_y + gy.h, baseline)

    def test_atlas_height_is_multiple_of_8(self):
        b = self.build()
        for ch in "The quick brown fox jumps over the lazy dog 0123456789":
            b.add(ch)
        self.assertEqual(b.build().image.height % 8, 0)


class TestNinePatch(unittest.TestCase):
    def test_patch_dimensions(self):
        p = rasterize_coverage(6, 2, COVERAGE_FILL)
        self.assertEqual(p.cell, 7)
        self.assertEqual(p.image.width, 15)

    def test_fill_and_ring_never_sum_past_full_coverage(self):
        """THE SEAM. The two masks are drawn from one geometry -- ring
        is outer minus the same inset shape the fill is -- so a corner
        texel that is half fill is half ring and the two composite to
        one solid pixel. Rasterized independently they would each be
        antialiased against nothing, sum past 255, and lay a dark
        hairline around every rounded box that no author wrote.

        Also the reason _mask downsamples with BOX and not LANCZOS: a
        windowed-sinc filter overshoots, and an overshoot here is this
        defect arriving through the resampler instead."""
        for radius, bw in ((4, 2), (3, 2), (8, 1), (6, 3)):
            f = rasterize_coverage(radius, bw, COVERAGE_FILL).image
            r = rasterize_coverage(radius, bw, COVERAGE_RING).image
            pairs = list(zip(f.getdata(), r.getdata()))
            self.assertTrue(all(a + b <= 255 for a, b in pairs),
                            f"radius {radius} bw {bw}: coverage sums past 1")
            # And they actually meet: somewhere on the corner arc both
            # are partial. Without this the check above passes for a
            # ring that is empty.
            self.assertTrue(any(0 < a < 255 and 0 < b < 255 for a, b in pairs),
                            f"radius {radius} bw {bw}: no shared corner texel")

    def test_coverage_preserves_the_area_it_rasterized(self):
        """A coverage texel is an AREA FRACTION, so the mask's total
        must equal the shape's area. That is what picks BOX as the
        downsample filter over the LANCZOS the premixed patch used: a
        resampling filter rings, and measured over these shapes LANCZOS
        loses or invents up to 0.47 px^2 of rounded corner where BOX is
        within 0.02.

        This is the check that pins the filter. The seam check above
        does NOT -- it passes under LANCZOS too, because ring is a
        clamped subtraction and the sum is bounded whatever the filter
        does. Two independent properties; the first version of the
        comment above had them as one.
        """
        from PIL import Image, ImageDraw
        from ps2ui_bake.ninepatch import SUPERSAMPLE as S
        for radius, bw in ((4, 0), (4, 2), (6, 3), (8, 1)):
            # THE SUBJECT, not a local reimplementation of it. The
            # first version of this test built its own BOX resize and
            # compared that against itself, so swapping the module's
            # filter to LANCZOS passed all 185 checks. A test that does
            # not call the thing it is about cannot fail for the reason
            # it was written.
            got = sum(rasterize_coverage(radius, bw, COVERAGE_FILL)
                      .image.getdata()) / 255.0
            # The exact area, rasterized at supersample and counted --
            # no resize, so nothing here shares a filter with the code
            # under test.
            size = 2 * max(radius, bw) + 3
            big = Image.new("L", (size * S,) * 2, 0)
            ImageDraw.Draw(big).rounded_rectangle(
                (bw * S, bw * S, (size - bw) * S - 1, (size - bw) * S - 1),
                radius=max(radius - bw, 0) * S, fill=255)
            exact = sum(big.getdata()) / 255.0 / (S * S)
            self.assertLess(
                abs(got - exact), 0.05,
                f"radius {radius} bw {bw}: coverage totals {got:.3f} px^2 "
                f"for a shape of {exact:.3f}")

    def test_a_coverage_patch_holds_no_colour(self):
        """The whole point: the same geometry is one texture whatever
        it is painted, which is what takes opl-env from 11 patch
        textures to 4 and from 88 KiB of VRAM to 32."""
        self.assertEqual(patch_key(4, 2, COVERAGE_FILL),
                         patch_key(4, 2, COVERAGE_FILL))
        self.assertNotEqual(patch_key(4, 2, COVERAGE_FILL),
                            patch_key(4, 2, COVERAGE_RING))

    def test_the_rings_centre_cell_is_empty(self):
        """A border does not cover the middle of the box. Emitting that
        cell anyway would cost a full-box textured draw per rounded
        element to composite a rectangle of zeros."""
        p = rasterize_coverage(4, 2, COVERAGE_RING)
        self.assertTrue(p.cell_empty(p.cell, p.cell,
                                     p.size - 2 * p.cell, p.size - 2 * p.cell))
        self.assertFalse(p.cell_empty(0, 0, p.cell, p.cell))

    def test_slices_tile_target_exactly(self):
        p = rasterize_coverage(6, 2, COVERAGE_FILL)
        target = (5, 7, 100, 60)
        covered = [[False] * 60 for _ in range(100)]
        for (dx, dy, dw, dh), _src in slice_quads(p, *target):
            for xx in range(dx - 5, dx - 5 + dw):
                for yy in range(dy - 7, dy - 7 + dh):
                    self.assertFalse(covered[xx][yy], "slices overlap")
                    covered[xx][yy] = True
        self.assertTrue(all(all(col) for col in covered), "slices leave gaps")

    def test_small_target_clamps_corners(self):
        p = rasterize_coverage(10, 0, COVERAGE_FILL)
        quads = list(slice_quads(p, 0, 0, 12, 12))
        for (dx, dy, dw, dh), _ in quads:
            self.assertGreaterEqual(dx, 0)
            self.assertGreaterEqual(dy, 0)
            self.assertLessEqual(dx + dw, 12)
            self.assertLessEqual(dy + dh, 12)




class TestFlattener(unittest.TestCase):
    def test_plain_fill_is_one_quad(self):
        ir = tiny_ir([{
            "op": "rect", "x": 1, "y": 2, "w": 30, "h": 20,
            "fill": [9, 9, 9, 255], "borderWidth": 0, "borderColor": None,
            "radius": 0, "state": "always", "focusId": None,
        }])
        f = Flattener(ir, font_paths())
        f.run()
        self.assertEqual(len(f.records), 1)
        r = f.records[0]
        self.assertEqual(r.op, OP_QUAD)
        self.assertEqual((r.x, r.y, r.w, r.h), (1, 2, 30, 20))
        self.assertEqual(r.rgba, (9, 9, 9, 0x80))

    def test_border_adds_four_edges(self):
        ir = tiny_ir([{
            "op": "rect", "x": 0, "y": 0, "w": 50, "h": 40,
            "fill": [1, 1, 1, 255], "borderWidth": 2,
            "borderColor": [7, 7, 7, 255], "radius": 0,
            "state": "always", "focusId": None,
        }])
        f = Flattener(ir, font_paths())
        f.run()
        self.assertEqual(len(f.records), 5)
        edge_area = sum(r.w * r.h for r in f.records[1:])
        self.assertEqual(edge_area, 50 * 2 * 2 + 2 * (40 - 4) * 2)

    def test_rounded_rect_is_two_tinted_coverage_layers(self):
        """P3b-6. Nine cells of fill coverage, eight of border ring --
        the ring's centre cell is the interior of the box and holds no
        coverage, so emitting it would cost a full-box textured draw to
        composite zeros.

        Two textures, not one, and the second is the price of the
        change: a premixed patch was 9 draws and 1 texture. What it
        buys is that both colours are now vertex tints, which is to say
        tint-table entries, which is to say things a theme can move.
        Premixed they were texels and a theme could not reach either.
        """
        ir = tiny_ir([{
            "op": "rect", "x": 0, "y": 0, "w": 60, "h": 40,
            "fill": [1, 1, 1, 255], "borderWidth": 2,
            "borderColor": [7, 7, 7, 255], "radius": 6,
            "state": "always", "focusId": None,
        }])
        f = Flattener(ir, font_paths())
        f.run()
        self.assertEqual(len(f.records), 17)
        self.assertTrue(all(r.op == OP_TEXQUAD for r in f.records))
        self.assertEqual(len(f.textures), 2)
        # Each layer carries ITS OWN colour, in the modulate domain.
        by_tint = {}
        for r in f.records:
            by_tint.setdefault(r.rgba, 0)
            by_tint[r.rgba] += 1
        self.assertEqual(by_tint, {(1, 1, 1, 0x80): 9, (4, 4, 4, 0x80): 8})

    def test_the_ring_carries_the_border_role_not_the_fill_role(self):
        """One element, two roles. `background: var(--panel); border:
        2px solid var(--edge)` is a chip whose interior and outline a
        theme moves independently, and the split is what makes that
        expressible at all -- premixed, neither reached the table.

        Fenced separately from the colours because the colours cannot
        catch it: handing the ring layer `fillVar` leaves every rgba in
        the test above unchanged, since the tint comes from the colour
        and only the NAME comes from the var. That sabotage passed the
        whole suite."""
        ir = tiny_ir([{
            "op": "rect", "x": 0, "y": 0, "w": 60, "h": 40,
            "fill": [1, 1, 1, 255], "fillVar": "--panel",
            "borderWidth": 2, "borderColor": [7, 7, 7, 255],
            "borderColorVar": "--edge", "radius": 6,
            "state": "always", "focusId": None,
        }])
        f = Flattener(ir, font_paths())
        f.run()
        by_var = {}
        for r in f.records:
            by_var[r.var] = by_var.get(r.var, 0) + 1
        self.assertEqual(by_var, {"--panel": 9, "--edge": 8})

    def test_two_rounded_boxes_of_one_shape_share_both_textures(self):
        """The saving, stated as a test. A coverage patch keys on
        geometry alone, so two boxes with the same radius and border
        width are one pair of textures however differently they are
        painted. Keyed on the colours too -- which is what premixing
        forced -- this is four textures, and opl-env's eleven."""
        rect = {
            "op": "rect", "x": 0, "y": 0, "w": 60, "h": 40,
            "fill": [1, 1, 1, 255], "borderWidth": 2,
            "borderColor": [7, 7, 7, 255], "radius": 6,
            "state": "always", "focusId": None,
        }
        ir = tiny_ir([rect, {**rect, "x": 100,
                             "fill": [200, 100, 50, 255],
                             "borderColor": [9, 9, 9, 255]}])
        f = Flattener(ir, font_paths())
        f.run()
        self.assertEqual(len(f.textures), 2)

    def test_identical_rounded_styles_share_a_texture(self):
        rect = {
            "op": "rect", "x": 0, "y": 0, "w": 60, "h": 40,
            "fill": [1, 1, 1, 255], "borderWidth": 0, "borderColor": None,
            "radius": 5, "state": "always", "focusId": None,
        }
        ir = tiny_ir([rect, {**rect, "x": 100}])
        f = Flattener(ir, font_paths())
        f.run()
        self.assertEqual(len(f.textures), 1)

    @unittest.skipIf(TTF is None, "DejaVu Sans not installed")
    def test_text_glyph_positions_follow_metric_advances(self):
        ir = tiny_ir([{
            "op": "text", "x": 10, "y": 10, "text": "ii",
            "size": 13, "weight": 400, "letterSpacing": 0,
            "color": [255, 0, 0, 255], "state": "always", "focusId": None,
        }])
        f = Flattener(ir, font_paths())
        f.run()
        glyphs = [r for r in f.records if r.op == OP_TEXQUAD]
        self.assertEqual(len(glyphs), 2)
        adv = glyph_advance_px(278, 13)
        self.assertEqual(glyphs[1].x - glyphs[0].x, adv)
        # Modulate domain: pure red tint is (0x80, 0, 0), not (255, 0, 0).
        self.assertEqual(glyphs[0].rgba, (0x80, 0, 0, 0x80))

    def test_focus_ids_remap_to_table_indices(self):
        nodes = [
            {"id": 42, "name": "a", "rect": [0, 0, 10, 10],
             "up": None, "down": 77, "left": None, "right": None},
            {"id": 77, "name": "b", "rect": [0, 20, 10, 10],
             "up": 42, "down": None, "left": None, "right": None},
        ]
        ir = tiny_ir([{
            "op": "rect", "x": 0, "y": 0, "w": 10, "h": 10,
            "fill": [1, 1, 1, 255], "borderWidth": 0, "borderColor": None,
            "radius": 0, "state": "focused", "focusId": 77,
        }], focus_nodes=nodes, initial=42)
        f = Flattener(ir, font_paths())
        f.run()
        self.assertEqual(f.records[0].focus, 1)
        self.assertEqual(f.records[0].state, STATE_FOCUSED)

    def test_unknown_op_rejected(self):
        ir = tiny_ir([{"op": "gradient"}])
        with self.assertRaises(ValueError):
            Flattener(ir, font_paths()).run()


class TestCaps(unittest.TestCase):
    """Backlog B10: the baker must reject blobs ps2ui_load() would."""

    def slots(self, n, capacity=31):
        return [{"name": f"s{i}", "capacity": capacity} for i in range(n)]

    def test_caps_match_the_runtime_header(self):
        # The fallback exists for pip installs with no runtime source.
        # If it drifts from ps2ui.h, an over-sized blob ships silently.
        from ps2ui_bake import caps
        self.assertTrue(os.path.exists(caps.header_path()), caps.header_path())
        self.assertEqual(caps.parse_header(), caps.FALLBACK)

    def test_fallback_used_when_header_is_missing(self):
        from ps2ui_bake import caps
        self.assertEqual(caps.parse_header("/nonexistent/ps2ui.h"), caps.FALLBACK)

    def test_the_table_ceilings_are_gone(self):
        """200 slots, 40 textures and 12 screens all used to be refused.

        The numbers are past 16/32/8 on purpose -- each was a ceiling
        ps2ui.h enforced, and 16 slots was the one blocking a real UI
        (the UC-3 scoping fixture measures 28 on one screen). If any of
        the three is quietly reinstated on either side, this is the
        test that says so before a bake starts failing."""
        from ps2ui_bake import caps
        errors, c = caps.check([None] * 40, [], self.slots(200),
                               [{} for _ in range(12)])
        self.assertEqual(errors, [])
        for gone in ("PS2UI_MAX_TEXTURES", "PS2UI_MAX_SLOTS",
                     "PS2UI_MAX_SCREENS"):
            self.assertNotIn(gone, c)

    def test_the_formats_own_uint16_count_still_bounds_the_tables(self):
        """What replaced them is not "nothing".

        Every count in the header is a uint16, so a table past 65535
        cannot be written at all -- checked here rather than discovered
        as a struct.pack failure with no explanation attached."""
        from ps2ui_bake import caps
        errors, _ = caps.check([], [], self.slots(0x10000), [{}])
        self.assertTrue(any("uint16" in e and "slots" in e for e in errors),
                        errors)
        errors, _ = caps.check([None] * 0x10000, [], [], [{}])
        self.assertTrue(any("uint16" in e and "textures" in e for e in errors),
                        errors)

    def test_the_summary_stopped_printing_a_denominator(self):
        """"15/16 slots" was useful while 16 was a wall. A fraction of
        65535 is a number with a decorative second half, and the figure
        that actually constrains a UI now is the arena, printed on its
        own line."""
        from ps2ui_bake import caps
        line = caps.summary([None] * 3, [None], self.slots(200),
                            [{}], caps.FALLBACK)
        self.assertIn("200 slots", line)
        self.assertNotIn("/", line)

    def test_slot_capacity_is_no_longer_capped_by_a_runtime_buffer(self):
        """The v6 resource model removed PS2UI_SLOT_BUFSZ.

        A capacity that used to be rejected as unloadable is now merely
        arena bytes, so the bake must accept it -- this test is the one
        that would have caught the check being left behind after the
        constant it read was deleted."""
        from ps2ui_bake import caps
        errors, c = caps.check([], [], self.slots(1, capacity=4096), [{}])
        self.assertEqual(errors, [])
        self.assertNotIn("PS2UI_SLOT_BUFSZ", c)
        # The format's own bound still applies.
        errors, _ = caps.check([], [], self.slots(1, capacity=0x10000), [{}])
        self.assertTrue(any("uint16" in e for e in errors))


class TestSlotCapacity(unittest.TestCase):
    """The blob records the capacity the author asked for.

    Regression fence. The flattener used to clamp capacity to 95 --
    PS2UI_SLOT_BUFSZ - 1, the runtime's old fixed per-slot buffer. When
    the v6 resource model removed that buffer, the clamp survived: the
    check that used to reject an over-capacity slot was replaced with a
    uint16 bound the clamp made unreachable, so an author asking for
    200 silently got 95, no warning at bake, truncated text at runtime.
    Worse than the limit it replaced, because the old one said so.
    """

    def bake(self, capacity):
        import subprocess
        import tempfile
        from ps2ui_bake.uib import read_uib
        here = os.path.dirname(os.path.abspath(__file__))
        root = os.path.normpath(os.path.join(here, "..", "..", ".."))
        html = ('<div style="display:flex"><span id="s" data-slot="s" '
                f'data-slot-capacity="{capacity}">x</span></div>')
        with tempfile.TemporaryDirectory() as td:
            hp = os.path.join(td, "p.html")
            cp = os.path.join(td, "p.css")
            jp = os.path.join(td, "p.json")
            up = os.path.join(td, "p.uib")
            open(hp, "w").write(html)
            open(cp, "w").write("body{display:flex}#s{font-size:16px;color:#fff}")
            r = subprocess.run(
                ["node", os.path.join(root, "packages", "layout", "bin",
                                      "ps2ui-layout.js"), hp, cp, "-o", jp],
                capture_output=True)
            if r.returncode != 0:
                # Node IS available where the gate is set, so this is a
                # broken layout compiler rather than a missing tool.
                unavailable(self, "the layout compiler would not run: "
                                  + r.stderr.decode()[:120])
            env = dict(os.environ,
                       PYTHONPATH=os.path.join(root, "packages", "baker"))
            r = subprocess.run([sys.executable, "-m", "ps2ui_bake", jp,
                                "-o", up], capture_output=True, env=env)
            if r.returncode != 0:
                return None, r.stderr.decode()
            return read_uib(up), r.stderr.decode()

    def test_capacity_survives_the_bake(self):
        uib, err = self.bake(200)
        # NOT A SKIP, AND THIS ONE NEVER SHOULD HAVE BEEN. The other
        # skips in this file guard a missing FIXTURE; this guarded the
        # test's own subject. bake() returns None only when the baker
        # refused -- a failing `node` is caught above -- so "bake
        # refused a capacity it should accept" is the exact defect this
        # test exists to find, and it was reported as OK. Worse in kind
        # than the four TestS7Discriminator skips that prompted the
        # audit, because no reordering or fixture could ever have made
        # it run: the condition it skipped on WAS the failure.
        self.assertIsNotNone(
            uib, f"the baker refused a capacity it should accept: {err[:300]}")
        self.assertEqual([s["capacity"] for s in uib.slots], [200],
                         "the blob must record what the author asked for")

    def test_a_capacity_the_format_cannot_hold_is_refused(self):
        """And the uint16 bound is reachable, which the clamp prevented."""
        uib, err = self.bake(70000)
        # Compare a number, not the object: assertIsNone on a UibFile
        # prints the entire blob into the failure message, which buries
        # the one fact the test is about.
        got = None if uib is None else [s["capacity"] for s in uib.slots]
        self.assertIsNone(got, f"a capacity past uint16 must fail the bake; "
                               f"blob recorded {got}")
        self.assertIn("uint16", err)


class TestStreamedTextures(unittest.TestCase):
    """v6 §3: a texture the app fills at runtime.

    The blob-level checks for these live in check.py and pass
    vacuously on every shipped example, because no example authors a
    streamed slot yet -- `all()` over an empty list is True. So they
    are exercised here against blobs built to break each one, which is
    the difference between a check and a decoration.
    """

    def build(self, tmp, **over):
        from ps2ui_bake import gs
        from ps2ui_bake.quads import DrawRecord, BakedTexture, OP_TEXQUAD
        from ps2ui_bake.uib import TEXKIND_STREAMED, write_uib, read_uib
        tex = BakedTexture(
            gs.PSMCT32, over.pop("w", 8), over.pop("h", 8), None,
            over.pop("data", b""),
            kind=over.pop("kind", TEXKIND_STREAMED),
            name=over.pop("name", "cover"),
            reservation=over.pop("reservation", 8 * 8 * 4))
        recs = [DrawRecord(OP_TEXQUAD, 0, 0xFFFF, 0, 0, 8, 8,
                           (128, 128, 128, 128), tex=0, u0=0, v0=0, u1=8, v1=8)]
        path = os.path.join(tmp, "s.uib")
        write_uib(path, {"w": 640, "h": 448}, recs, [tex], [], [], None)
        return read_uib(path)

    def errors_for(self, uib):
        from ps2ui_bake.check import check_blob
        rep = check_blob(uib, None, True)
        return [label for ok, sev, label in rep.results
                if not ok and sev == "error"]

    def test_a_well_formed_streamed_blob_passes(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            self.assertEqual(self.errors_for(self.build(td)), [])

    def test_the_feature_bit_is_set_by_the_table(self):
        import tempfile
        from ps2ui_bake.uib import FEAT_STREAMED_TEX
        with tempfile.TemporaryDirectory() as td:
            uib = self.build(td)
            self.assertTrue(uib.feature_flags & FEAT_STREAMED_TEX)
            # Clearing it must be caught: a reader that cannot stream
            # would accept the file and draw a slot nothing can fill.
            uib.feature_flags &= ~FEAT_STREAMED_TEX
            self.assertTrue(any("feature bit" in e
                                for e in self.errors_for(uib)))

    def test_an_unnamed_streamed_texture_is_refused(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            uib = self.build(td)
            uib.textures[0].name = None      # unaddressable
            self.assertTrue(any("named" in e for e in self.errors_for(uib)))

    def test_a_zero_reservation_is_refused(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            uib = self.build(td)
            uib.textures[0].reservation = 0
            self.assertTrue(any("reservation" in e
                                for e in self.errors_for(uib)))

    def test_texture_names_must_be_unique(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            uib = self.build(td)
            dup = copy.copy(uib.textures[0])
            uib.textures.append(dup)         # same name twice
            self.assertTrue(any("unique" in e for e in self.errors_for(uib)))

    def test_the_reservation_is_the_linear_texel_size(self):
        """What ps2ui_tex_set will demand, byte for byte."""
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            uib = self.build(td, w=16, h=16, reservation=16 * 16 * 4)
            self.assertEqual(uib.textures[0].reservation, 1024)
            self.assertEqual(uib.textures[0].data, b"")


class TestStreamedAuthoring(unittest.TestCase):
    """<img data-tex-slot="name"> end to end, HTML through to the blob.

    The runtime and format halves shipped first (v6 §3) with a fixture
    written straight from write_uib. This is the authoring half: the
    path an actual UI takes.
    """

    def bake(self, html, css):
        import subprocess
        import tempfile
        from ps2ui_bake.uib import read_uib
        here = os.path.dirname(os.path.abspath(__file__))
        root = os.path.normpath(os.path.join(here, "..", "..", ".."))
        with tempfile.TemporaryDirectory() as td:
            hp, cp = os.path.join(td, "p.html"), os.path.join(td, "p.css")
            jp, up = os.path.join(td, "p.json"), os.path.join(td, "p.uib")
            with open(hp, "w") as fh:
                fh.write(html)
            with open(cp, "w") as fh:
                fh.write(css)
            r = subprocess.run(
                ["node", os.path.join(root, "packages", "layout", "bin",
                                      "ps2ui-layout.js"), hp, cp, "-o", jp],
                capture_output=True)
            if r.returncode != 0:
                return None, r.stderr.decode()
            env = dict(os.environ,
                       PYTHONPATH=os.path.join(root, "packages", "baker"))
            r = subprocess.run([sys.executable, "-m", "ps2ui_bake", jp,
                                "-o", up], capture_output=True, env=env)
            if r.returncode != 0:
                return None, r.stderr.decode()
            return read_uib(up), r.stderr.decode()

    CSS = ("body{display:flex;flex-direction:column}"
           "#r{display:flex;flex-direction:row}"
           "img{width:64px;height:64px}")

    def test_a_streamed_slot_reaches_the_blob(self):
        uib, err = self.bake(
            '<div id="r"><img data-tex-slot="cover"></div>', self.CSS)
        self.assertIsNotNone(uib, err)
        from ps2ui_bake.uib import FEAT_STREAMED_TEX, TEXKIND_STREAMED
        streamed = [t for t in uib.textures if t.kind == TEXKIND_STREAMED]
        self.assertEqual(len(streamed), 1)
        t = streamed[0]
        self.assertEqual(t.name, "cover")
        self.assertEqual((t.width, t.height), (64, 64))
        # The reservation is the linear payload ps2ui_tex_set demands,
        # not the page-rounded VRAM cost -- the two are different
        # numbers and the app is told this one.
        self.assertEqual(t.reservation, 64 * 64 * 4)
        self.assertEqual(t.data, b"", "no texels travel in the blob")
        self.assertTrue(uib.feature_flags & FEAT_STREAMED_TEX)

    def test_the_slot_is_actually_drawn(self):
        """A reservation nothing draws is a slot the app can fill and
        nobody can see."""
        from ps2ui_bake.quads import OP_TEXQUAD
        from ps2ui_bake.uib import TEXKIND_STREAMED
        uib, err = self.bake(
            '<div id="r"><img data-tex-slot="cover"></div>', self.CSS)
        self.assertIsNotNone(uib, err)
        idx = [i for i, t in enumerate(uib.textures)
               if t.kind == TEXKIND_STREAMED][0]
        drawn = [r for r in uib.records
                 if r.op == OP_TEXQUAD and r.tex == idx]
        self.assertEqual(len(drawn), 1)
        self.assertEqual((drawn[0].w, drawn[0].h), (64, 64))

    def test_two_elements_share_one_slot(self):
        """That is what a name is for -- one reservation, two places."""
        from ps2ui_bake.quads import OP_TEXQUAD
        from ps2ui_bake.uib import TEXKIND_STREAMED
        uib, err = self.bake(
            '<div id="r"><img data-tex-slot="cover">'
            '<img data-tex-slot="cover"></div>', self.CSS)
        self.assertIsNotNone(uib, err)
        streamed = [t for t in uib.textures if t.kind == TEXKIND_STREAMED]
        self.assertEqual(len(streamed), 1, "one slot, not two")
        idx = [i for i, t in enumerate(uib.textures)
               if t.kind == TEXKIND_STREAMED][0]
        drawn = [r for r in uib.records
                 if r.op == OP_TEXQUAD and r.tex == idx]
        self.assertEqual(len(drawn), 2, "drawn in both places")

    def test_one_name_at_two_sizes_is_refused(self):
        """A slot has one reservation and the app is told one number,
        so this has to fail rather than silently pick a size."""
        uib, err = self.bake(
            '<div id="r"><img data-tex-slot="cover">'
            '<img class="big" data-tex-slot="cover"></div>',
            self.CSS + ".big{width:32px;height:32px}")
        self.assertIsNone(uib, "a size conflict must fail the bake")
        self.assertIn("one reservation", err)

    def test_the_reservation_counts_against_the_vram_budget(self):
        """Reserved VRAM is spent whether or not the app fills it."""
        from ps2ui_bake import vram
        uib, err = self.bake(
            '<div id="r"><img data-tex-slot="cover"></div>', self.CSS)
        self.assertIsNotNone(uib, err)
        lines, total, _budget, _ok = vram.report(
            uib.textures, uib.cluts, 640, 448, None)
        self.assertGreaterEqual(total, 64 * 64 * 4)
        self.assertTrue(any("streamed" in ln for ln in lines),
                        "the breakdown names it as a reservation, because "
                        "'0 B raw' would read as free")

    def test_the_breakdown_prints_the_number_tex_set_demands(self):
        """The two counts on a slot's row are different numbers and the
        integrator needs the smaller one: ps2ui_tex_set compares `len`
        against data_len, so a caller who passes the page-rounded VRAM
        figure gets a bare PS2UI_ERR_SIZE. Printing only the page
        figure put the wrong one of the two on the only line the bake
        says about their slot."""
        from ps2ui_bake import vram
        # 100x70, not the class's 64x64: a CT32 page is 64x32 texels, so
        # every power-of-two slot lands on an exact page boundary and
        # payload == pages, which would let the wrong number pass. The
        # first draft of this test did exactly that and its own guard
        # below caught it.
        uib, err = self.bake(
            '<div id="r"><img data-tex-slot="cover"></div>',
            self.CSS.replace("width:64px;height:64px",
                             "width:100px;height:70px"))
        self.assertIsNotNone(uib, err)
        lines, _total, _budget, _ok = vram.report(
            uib.textures, uib.cluts, 640, 448, None)
        row = [ln for ln in lines if "streamed" in ln][0]
        payload = 100 * 70 * 4                      # 28000, what tex_set wants
        pages = vram.page_rounded_size(100, 70, gs.PSMCT32)   # 49152
        self.assertNotEqual(payload, pages, "otherwise this proves nothing")
        self.assertIn(f"{payload} B payload", row)
        self.assertIn(f"{pages} B in pages", row)

    def test_the_report_totals_the_columns_it_prints(self):
        """Three figures, and each one had a way of being wrong.

        payload was never summed at all -- the per-texture rows have
        printed it since v6 and nothing added the column up. The
        allocator figure was WRONG for a commit: the report compared
        payload against the 8 KiB budget model and called the gap
        reclaimable, when gsKit's TexManager commits 256-byte blocks
        (tools/check-vram-model.py holds the port to the vendored C).
        And the two are easy to swap, since on a texture that happens
        to fill its pages they are equal.

        Asserted against the SUM OF THE PRINTED ROWS rather than a
        recomputed expectation, because a total that agrees with its
        own arithmetic and disagrees with the lines above it is the
        failure worth catching."""
        import re
        from ps2ui_bake import vram
        # 20x10, and the size is load-bearing. The three models
        # coincide for most textures: 64x64 CT32 (the fixture default)
        # is exactly two pages AND exactly its block group, so all
        # three are 16384; 100x70 separates payload but leaves
        # allocator == budget at 49152. Only a texture small enough
        # that its alignment group is under a page pulls them apart --
        # 800 / 2048 / 8192 here. Both larger sizes were tried first
        # and the guards at the bottom rejected them, which is what
        # those guards are for.
        uib, err = self.bake(
            '<div id="r"><img data-tex-slot="cover"></div>',
            self.CSS.replace("width:64px;height:64px",
                             "width:20px;height:10px"))
        self.assertIsNotNone(uib, err)
        lines, total, _budget, _ok = vram.report(
            uib.textures, uib.cluts, 640, 448, None)

        rows = sum(int(m.group(1))
                   for ln in lines
                   for m in [re.search(r"(\d+) B payload", ln)] if m)
        rows += vram.CLUT_PAYLOAD * len(uib.cluts)

        summary = [ln for ln in lines if "budget-charged" in ln]
        self.assertEqual(len(summary), 1, lines)
        m = re.search(r"payload (\d+) B -> allocator (\d+) B "
                      r"-> budget-charged (\d+) B", summary[0])
        self.assertIsNotNone(m, summary[0])
        payload, committed, charged = (int(g) for g in m.groups())

        self.assertEqual(payload, rows,
                         "the total disagrees with the rows it summarises")
        self.assertEqual(charged, total, "and with the budget figure below it")
        self.assertEqual(committed, vram.alloc_total(uib.textures),
                         "the allocator column is not the allocator model")

        reclaim = [ln for ln in lines if "reclaimable" in ln][0]
        self.assertIn(f"reclaimable {committed - payload} B", reclaim)

        # None of the three may coincide, or the assertions above stop
        # telling them apart -- which is exactly how the budget figure
        # got printed as the allocator's for a commit.
        self.assertLess(payload, committed, "no block overhead to see")
        self.assertLess(committed, charged, "no budget pessimism to see")

    def test_the_bake_summary_does_not_call_a_reservation_zero(self):
        """The per-texture row stopped saying '0 B raw'; the total one
        line beneath it summed len(t.data) and said '(0 KiB)' for the
        same blob. Same 'reads as free' problem, same fix.

        Kept separate from the reserved figure rather than added to it:
        this line announces the size of the file it just wrote, and a
        slot contributes nothing to that."""
        # 128x128 CT32 reserves 65536 B, so the KiB figure cannot round
        # to zero by accident and prove nothing.
        uib, err = self.bake('<div id="r"><img data-tex-slot="cover"></div>',
                             self.CSS.replace("64px", "128px"))
        self.assertIsNotNone(uib, err)
        summary = [ln for ln in err.splitlines() if "textures (" in ln][0]
        self.assertIn("0 KiB baked", summary, "no texels travel in the file")
        self.assertIn("64 KiB reserved by slots", summary)


class TestCoverPattern(unittest.TestCase):
    """The bench's fallback cover exists in two languages.

    tools/make_cover_raw.py generates it on the host for the reference
    PNG; runtime/sample/cover_pattern.h generates it on the EE when the
    bench has no drive attached. If they diverge, a sitting compares a
    console photograph against a picture of something else -- and the
    divergence is invisible, because both halves look like a plausible
    cover.

    Pinned as a CRC in the header both sides include. This is the
    Python half; runtime/tests/test_runtime.c is the C half.
    """

    def header(self):
        here = os.path.dirname(os.path.abspath(__file__))
        path = os.path.normpath(os.path.join(
            here, "..", "..", "..", "runtime", "sample", "cover_pattern.h"))
        self.assertTrue(os.path.exists(path), path)
        with open(path, encoding="utf-8") as fh:
            return fh.read()

    def synthetic(self, *a):
        here = os.path.dirname(os.path.abspath(__file__))
        tools = os.path.normpath(os.path.join(here, "..", "..", "..", "tools"))
        if tools not in sys.path:
            sys.path.insert(0, tools)
        from make_cover_raw import synthetic
        return synthetic(*a)

    def test_python_matches_the_crc_the_header_pins(self):
        import re
        import zlib
        m = re.search(r"#define\s+COVER_PATTERN_CRC_0_64X64\s+0x([0-9a-fA-F]+)u",
                      self.header(), re.I)
        self.assertIsNotNone(m, "the header must pin the CRC")
        pinned = int(m.group(1), 16)
        got = zlib.crc32(self.synthetic(0, 64, 64)) & 0xFFFFFFFF
        self.assertEqual(
            got, pinned,
            f"make_cover_raw.synthetic(0,64,64) hashes to 0x{got:08x}, the "
            f"header pins 0x{pinned:08x}. One generator moved; the ELF's "
            f"fallback and the reference PNG are no longer the same picture.")

    def test_the_pattern_can_tell_arrived_from_stale(self):
        """The property, asserted on this side too. A flat cover looks
        identical whether the texels arrived or a stale VRAM block is
        being drawn -- which is exactly what bench step S1 reads."""
        raw = self.synthetic(0, 64, 64)
        texels = {raw[i:i + 4] for i in range(0, len(raw), 4)}
        # Three today -- white, the hue, and the hue darkened -- so this
        # clears by exactly one. Noted rather than loosened: the CRC pin
        # makes any change to the pattern deliberate, and a fourth value
        # added to buy margin would be decoration.
        self.assertGreater(len(texels), 2, f"only {len(texels)} distinct texels")
        self.assertNotEqual(self.synthetic(0, 64, 64), self.synthetic(1, 64, 64))

    def test_the_pattern_varies_on_both_axes(self):
        """Three distinct values could still be horizontal stripes, and
        stripes are a shape stale VRAM plausibly takes: a framebuffer
        row and a texture read at the wrong stride both stripe. A
        checker cannot be mistaken for either.

        Mirrors the C check exactly. The pair used to be asymmetric --
        C compared every texel against texel zero, which is the white
        BORDER, so a border around a flat fill passed there and failed
        here. Review found it by collapsing the interior."""
        w = h = 64
        raw = self.synthetic(0, w, h)

        def px(x, y):
            i = (y * w + x) * 4
            return raw[i:i + 4]

        # Below and right of the corner block, not from the first
        # interior texel. Scanning from the edge, a horizontal-stripe
        # pattern still passes: the white corner block sits against the
        # stripes and supplies the horizontal variation itself, so the
        # check reads the block rather than the pattern. Same shape as
        # the C-side mistake review found, one level down.
        edge, cell = 2, 8
        lo = edge + cell + 1
        rng = [(x, y) for y in range(lo, h - edge) for x in range(lo, w - edge)]
        self.assertTrue(any(px(x, y) != px(x - 1, y) for x, y in rng),
                        "does not vary horizontally clear of the corner block")
        self.assertTrue(any(px(x, y) != px(x, y - 1) for x, y in rng),
                        "does not vary vertically clear of the corner block")

    def test_alpha_is_in_the_gs_domain(self):
        raw = self.synthetic(0, 32, 32)
        self.assertEqual(set(raw[3::4]), {0x80},
                         "0xFF would ask the GS for about twice the coverage "
                         "it has -- backlog B1 on a new path")


# A precondition this suite reaches for and did not find: a skip
# normally, a FAILURE when the environment says the suite must be
# complete.
#
# WHY THE FAILURE ARM EXISTS. A skip is reported as OK, so a test that
# never runs is indistinguishable from one that passes -- and four
# tests in this file had never run in CI. Their skip message said "the
# bench fixture is not built; ci.yml builds it", which was true of the
# workflow and false of the moment: ci.yml built that fixture at line
# 153 and ran this suite at line 57. Ninety-six lines too late, for as
# long as both had existed, with a green tick every time.
#
# Reordering the workflow alone would fix today's symptom and invite
# being reordered back. This makes the silence itself the thing that
# breaks, so the ordering is enforced by the suite rather than by
# whoever edits the YAML next. Both halves ship together: the reorder
# is the fix, this is the tripwire.
#
# The variable is still named for the cross-check that first needed it
# (ci.yml and docs/method.md name it), and it now means the broader
# thing: under it, every fixture this suite reaches for must exist.
def unavailable(case, why):
    if os.environ.get("PS2UI_REQUIRE_CROSSCHECK") == "1":
        case.fail(f"PS2UI_REQUIRE_CROSSCHECK=1 but {why}")
    case.skipTest(why)


class TestS7Discriminator(unittest.TestCase):
    """Bench step S7's calibration.

    A console clips the bottom row of capitals: E reads as F, L as I,
    2 as ?. Two mechanisms explain that, and they need separating:

      lost-baseline-row  only the row every non-descender ends on
      lost-last-row      the last row of every glyph quad

    "Lowercase is untouched" does NOT separate them, which is what the
    first write-up got wrong. Every non-descender in this face --
    capital, lowercase and digit alike -- ends on the SAME row, so a
    uniform last-row loss produces exactly the reported picture: an E
    loses a full-width bar and reads as F, while an `e` loses the
    two-texel bottom of a curve and still reads as `e`.

    What DOES separate them is a glyph one pixel tall that does not sit
    on the baseline. Under lost-last-row a hyphen loses its only row
    and vanishes; under lost-baseline-row it is untouched.

    MEASURED FROM THE DRAWN QUADS, not from the font table. The first
    version of this read uib.fonts, which describes SLOT text only --
    static text is flattened into TEXQUADs at bake time and never
    consults it. The S7 line is static, so the font table was the wrong
    object entirely and the check would have held while the line on
    screen changed underneath it.
    """

    BUILD = os.path.normpath(os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "..", "..", "..", "fixtures", "bench-stream", "build"))

    def line_and_quads(self):
        """The S7 line from the IR, and the quads the baker drew for it."""
        irp = os.path.join(self.BUILD, "covers.json")
        blob = os.path.join(self.BUILD, "bench.uib")
        if not (os.path.exists(irp) and os.path.exists(blob)):
            unavailable(self, "the bench fixture is not built "
                              "(fixtures/bench-stream/build.sh)")
        with open(irp) as fh:
            ir = json.load(fh)
        line = [c for c in ir["commands"]
                if c["op"] == "text" and c["text"].startswith("S7")]
        self.assertEqual(len(line), 1,
                         "the covers screen must carry exactly one S7 line")
        c = line[0]
        uib = read_uib(blob)
        lo, hi = c["y"] - 2, c["y"] + c["size"] + 4
        quads = [r for r in uib.records
                 if r.op == OP_TEXQUAD and lo <= r.y <= hi]
        return c, quads

    def test_the_line_carries_both_kinds_of_glyph(self):
        c, quads = self.line_and_quads()
        self.assertIn("-", c["text"], "hyphens are the instrument")
        self.assertIn("E", c["text"], "and a capital is the reference")
        self.assertGreater(len(quads), 8,
                           "the S7 line must actually reach the blob as "
                           "drawn quads, or there is nothing on screen")

    def test_the_hyphens_are_exactly_one_pixel_tall(self):
        """Losing one row of two leaves a thinner dash, which separates
        nothing. This is what makes the step readable at all."""
        _, quads = self.line_and_quads()
        thin = [r for r in quads if r.h == 1]
        self.assertGreaterEqual(
            len(thin), 8,
            f"expected the row of hyphens to draw as 1px quads; got "
            f"{sorted(set(r.h for r in quads))} as the heights on that line")

    def test_the_hyphens_do_not_end_where_the_capitals_do(self):
        """If they shared a bottom row, both candidate faults would
        erase both and the step would answer nothing."""
        _, quads = self.line_and_quads()
        thin = [r for r in quads if r.h == 1]
        tall = [r for r in quads if r.h > 4]
        self.assertTrue(thin and tall, "need both kinds on the line")
        hy_bot = max(r.y + r.h for r in thin)
        cap_bot = max(r.y + r.h for r in tall)
        self.assertLess(
            hy_bot, cap_bot,
            f"hyphens end at y={hy_bot} and capitals at y={cap_bot}; S7 "
            f"needs them apart or both mechanisms erase both")

    def test_capitals_lowercase_and_digits_share_a_bottom_row(self):
        """The observation the first write-up drew the wrong conclusion
        from, asserted so the correction cannot quietly rot back.

        Read from the font table deliberately: this is a claim about the
        FACE, not about one line of static text."""
        blob = os.path.join(self.BUILD, "bench.uib")
        if not os.path.exists(blob):
            unavailable(self, "the bench fixture is not built "
                              "(fixtures/bench-stream/build.sh)")
        g = read_uib(blob).fonts[0]["glyphs"]
        bottoms = {}
        for ch in "ELo2eanc":
            m = g.get(ord(ch))
            if m and m["h"]:
                bottoms[ch] = m["bearing_y"] + m["h"]
        self.assertEqual(
            len(set(bottoms.values())), 1,
            f"capitals, lowercase and digits should share one bottom row; "
            f"got {bottoms}. If they ever do not, 'lowercase is untouched' "
            f"starts carrying information it does not carry today.")


class TestArena(unittest.TestCase):
    """The host mirror of runtime/ps2ui.c's arena_compute.

    Two implementations of the same layout, so a change to one that the
    other does not follow is a failure rather than a silent divergence
    -- the same reason the kerning pens have an agreement test. The C
    side of the comparison is runtime/tests/test_runtime.c, which
    asserts ps2ui_arena_size against an independent carve of the same
    header; this side asserts the Python against the real blobs.
    """

    def write_fixture(self, path):
        """A small blob covering every arena region, written with the
        same writer the examples use so it tracks the format."""
        from ps2ui_bake import gs
        from ps2ui_bake.quads import DrawRecord, BakedTexture, OP_TEXQUAD
        from ps2ui_bake.uib import write_uib
        cluts = [bytes(256 * 4), bytes(256 * 4)]
        textures = [
            BakedTexture(gs.PSMT8, 16, 16, 0, bytes(16 * 16)),
            BakedTexture(gs.PSMT8, 16, 16, 0, bytes(16 * 16)),  # shares CLUT 0
            BakedTexture(gs.PSMT8, 8, 8, 1, bytes(8 * 8)),
        ]
        fonts = [{
            "tex": 0, "size": 8, "weight": 400, "ascent": 6,
            "line_height": 10,
            "glyphs": [{"codepoint": ord("A"), "u": 0, "v": 0, "w": 4,
                        "h": 6, "bearing_x": 0, "bearing_y": 0,
                        "advance": 5}],
        }]
        slots = [
            {"name": f"s{i}", "placeholder": "p", "x": 0, "text_y": 0,
             "w": 40, "font": 0, "align": 0, "ellipsis": False,
             "capacity": cap, "focus": 0xFFFF,
             "color_base": (128, 128, 128, 128),
             "color_focus": (128, 128, 128, 128)}
            for i, cap in enumerate((7, 31, 64))
        ]
        focus = [
            {"id": 0, "up": None, "down": 1, "left": None, "right": None,
             "name": "a", "rect": (0, 0, 10, 10)},
            {"id": 1, "up": 0, "down": None, "left": None, "right": None,
             "name": "b", "rect": (0, 20, 10, 10)},
        ]
        recs = [DrawRecord(OP_TEXQUAD, 0, 0xFFFF, 0, 0, 16, 16,
                           (128, 128, 128, 128), tex=0,
                           u0=0, v0=0, u1=16, v1=16)]
        write_uib(path, {"w": 640, "h": 448}, recs, textures, cluts,
                  focus, 0, fonts=fonts, slots=slots)

    def test_gstexture_size_differs_by_pointer_width(self):
        from ps2ui_bake import arena
        # The whole reason the report names a target: GSTEXTURE holds
        # two pointers, so the same blob needs a different arena on the
        # EE than in the host test suite.
        self.assertEqual(arena.sizeof_gstexture(arena.EE_PTR), 40)
        self.assertEqual(arena.sizeof_gstexture(arena.HOST64_PTR), 48)

    def test_arena_size_sums_its_own_breakdown(self):
        """On a blob this test writes, so it never depends on an
        earlier step having baked one."""
        import tempfile
        from ps2ui_bake import arena
        from ps2ui_bake.uib import read_uib
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "f.uib")
            self.write_fixture(path)
            u = read_uib(path)
        for ptr in (arena.EE_PTR, arena.HOST64_PTR):
            self.assertEqual(
                sum(n for _, n in arena.breakdown(u, ptr)),
                arena.arena_size(u, ptr),
                "the printed breakdown must account for every byte")

    def test_arena_matches_the_runtime(self):
        """Compare against the C, compiled and run for this host.

        Skipped rather than faked when the runtime cannot be built: a
        cross-language test that silently degrades to comparing Python
        with Python is worse than no test, because it reports agreement
        it never checked."""
        import os
        import subprocess
        import tempfile
        from ps2ui_bake import arena

        here = os.path.dirname(os.path.abspath(__file__))
        root = os.path.normpath(os.path.join(here, "..", "..", ".."))
        rt = os.path.join(root, "runtime")
        size_obj = os.path.join(rt, "build", "gsKit_texture_size.o")

        # Build the one object this needs rather than depending on some
        # earlier step having done it. Review found this test skipping
        # on every CI run: its guard looked for an artifact that ci.yml
        # builds AFTER the baker tests, so it printed
        # "skipped 'runtime not built'" and the suite went green having
        # checked nothing. It is the only test holding Python's
        # hand-modelled GSTEXTURE layout against the real sizeof, and
        # its sibling assertions cannot cover for it -- they compare
        # Python with its own literals.
        if not os.path.exists(size_obj):
            subprocess.run(["make", "-C", rt, "build/gsKit_texture_size.o"],
                           capture_output=True)

        # And when the environment says this must run, a skip is a
        # failure -- see unavailable() above, which this test is where
        # the reasoning was first written down and which now serves the
        # whole file rather than this one method.
        if not os.path.exists(size_obj):
            unavailable(self, "runtime not built (make -C runtime test)")

        src = r"""
        #include "ps2ui.h"
        #include <stdio.h>
        #include <stdlib.h>
        int main(int c, char **v) {
            for (int i = 1; i < c; i++) {
                FILE *f = fopen(v[i], "rb");
                long n; void *b;
                if (!f) return 2;
                fseek(f, 0, SEEK_END); n = ftell(f); fseek(f, 0, SEEK_SET);
                b = malloc((size_t)n);
                if (fread(b, 1, (size_t)n, f) != (size_t)n) return 2;
                fclose(f);
                printf("%zu\n", ps2ui_arena_size(b, (size_t)n));
            }
            return 0;
        }
        """
        with tempfile.TemporaryDirectory() as td:
            cs = os.path.join(td, "az.c")
            exe = os.path.join(td, "az")
            with open(cs, "w") as fh:
                fh.write(src)
            cc = subprocess.run(
                ["cc", "-std=c99", "-O1",
                 f"-I{rt}", f"-I{rt}/stub", f"-I{rt}/vendor/gsKit",
                 f"-I{rt}/vendor/host-shim",
                 cs, f"{rt}/ps2ui.c", f"{rt}/stub/gskit_stub.c", size_obj,
                 "-o", exe],
                capture_output=True)
            if cc.returncode != 0:
                unavailable(self, f"cannot build the runtime here: "
                                  f"{cc.stderr.decode()[:200]}")
            # A blob this test builds itself, so the comparison never
            # depends on some earlier step having baked one. That
            # dependency is what the skip guard was hiding: with the
            # guard on and no examples baked, CI failed with "no baked
            # blobs to compare" -- correct behaviour, and a sign the
            # test was reaching outside itself for its own input.
            #
            # write_uib is the same writer the examples use, so this
            # blob tracks the format automatically: no version pin to
            # forget, and the C reader on this branch reads exactly
            # what this branch's writer produces.
            #
            # Its shape exercises every arena term at a different
            # value, so a layout bug cannot hide behind a coincidence:
            # 3 textures but 2 CLUTs (the per-palette region), 3 slots
            # with three different capacities (the packed text
            # region), 2 focus nodes and 1 screen.
            fixture = os.path.join(td, "arena_fixture.uib")
            self.write_fixture(fixture)
            paths = [("self-built fixture", fixture)]

            # Real examples too, when they happen to be baked: they
            # carry realistic table sizes the fixture does not. Extra
            # coverage, never a dependency.
            for nm in ("memcard", "channel6"):
                p = os.path.normpath(os.path.join(
                    root, "examples", nm, "build", "ui.uib"))
                if os.path.exists(p):
                    paths.append((nm, p))
            out = subprocess.run([exe] + [p for _, p in paths],
                                 capture_output=True, check=True)
            got = [int(x) for x in out.stdout.split()]
            self.assertEqual(len(got), len(paths))
            for (nm, p), c_value in zip(paths, got):
                from ps2ui_bake.uib import read_uib
                # The C ran on this host, so compare against the host
                # pointer width -- comparing it to the EE number would
                # be a test of nothing but the difference between them.
                py = arena.arena_size(read_uib(p), arena.HOST64_PTR)
                self.assertEqual(
                    py, c_value,
                    f"{nm}: python says {py}, ps2ui_arena_size says {c_value}")


class TestBlobPen(unittest.TestCase):
    """ps2ui_bake.pen, against slot_measure's rules in ps2ui.c.

    Not a comparison against the C -- slot_measure is static and takes
    a whole ps2ui_ctx, so there is nothing to link against. What is
    checkable is each RULE the copies could drift on, stated as a case
    that fails if the rule is dropped. That is weaker than the arena
    and vram agreement tests and is labelled so rather than dressed up.
    """

    # '?' IS IN HERE ON PURPOSE, and the first reason given for it was
    # backwards. It was added because a sabotage inserting a '?'
    # fallback changed nothing without it -- and that "sabotage" is a
    # faithful transcription of find_glyph (ps2ui.c:1183). The line
    # written down as the thing to defend against was the runtime.
    #
    # The vacuity and the inversion had one root: a fixture with no '?'
    # is the single configuration in which skipping IS what the console
    # does, so it hid the question rather than raising it.
    FONT = {
        "glyphs": {ord("a"): {"advance": 10},
                   ord("b"): {"advance": 20},
                   ord("c"): {"advance": 5},
                   ord("?"): {"advance": 8}},
        # BOTH pairs around the snowman are here, and both are needed.
        # The kern is keyed on the codepoint the author wrote, not on
        # the '?' substituted for it, and that shows up on either side
        # of the substitution: (a, snowman) is the junction BEFORE it
        # and (snowman, b) the one AFTER. A sabotage re-keying to '?'
        # only changes the second, so a fixture carrying just the first
        # cannot see it -- which is how the first two versions of this
        # fixture let that sabotage pass.
        "kerns": {(ord("a"), ord("b")): -3,
                  (ord("a"), 0x2603): -6,
                  (0x2603, ord("b")): -4},
    }

    def w(self, text, spacing=0):
        from ps2ui_bake import pen
        return pen.slot_width(text, self.FONT["glyphs"],
                              self.FONT["kerns"], spacing)

    def test_advances_sum_and_the_pair_kern_applies_once(self):
        self.assertEqual(self.w("a"), 10)
        self.assertEqual(self.w("ab"), 10 + 20 - 3)
        self.assertEqual(self.w("ba"), 20 + 10, "the kern is directional")

    def test_letter_spacing_is_a_junction_cost_not_a_per_glyph_one(self):
        """n glyphs have n-1 junctions. Charging per glyph instead is
        the off-by-one that makes a measured line one spacing too wide
        and is invisible at spacing 0, which is every font here."""
        self.assertEqual(self.w("ac", 4), 10 + 4 + 5)
        self.assertEqual(self.w("aca", 4), 10 + 4 + 5 + 4 + 10)
        self.assertEqual(self.w("a", 4), 10, "no junction before the first")
        self.assertEqual(self.w("", 4), 0)

    def test_a_codepoint_with_no_glyph_falls_back_to_question_mark(self):
        """find_glyph (ps2ui.c:1183) returns '?' for a codepoint the
        atlas lacks. The `if (!g) continue;` four lines further on is
        the fallback's FALLBACK -- it fires only when '?' is absent too.

        This test previously asserted the opposite, citing that
        `continue` and pinning a rule the console does not follow. The
        pen it guards was short by one '?' advance per missing
        codepoint, which errs toward passing a line the console draws
        WIDER -- the wrong direction for a fit check.

        Two halves, and the second is the subtle one: the substituted
        glyph carries '?' metrics but the kern stays keyed on the
        ORIGINAL codepoint, because the runtime's caller never
        reassigns `cp` after the lookup."""
        self.assertEqual(self.w("\u2603"), self.w("?"),
                         "a lone missing glyph measures as '?'")
        # 'a<missing>b' takes '?' metrics for the middle glyph, and the
        # a/b kern does NOT apply -- 'b' kerns against the snowman, not
        # against 'a'. The (a, snowman) kern DOES apply, which is what
        # pins the keying to the original codepoint rather than to '?'.
        self.assertEqual(self.w("a\u2603b"), 10 - 6 + 8 - 4 + 20)
        self.assertNotEqual(self.w("a\u2603b"), self.w("ab"),
                            "the old assertion; it must now fail")

    def test_the_fallback_has_a_fallback(self):
        """With '?' absent from the atlas too, find_glyph returns null
        and the codepoint really is skipped. That is the only
        configuration the retired version of this pen described."""
        from ps2ui_bake import pen
        glyphs = {k: v for k, v in self.FONT["glyphs"].items()
                  if k != ord("?")}
        self.assertEqual(
            pen.slot_width("a\u2603b", glyphs, self.FONT["kerns"]), 27)

    def test_examples_use_the_shared_pen_rather_than_a_copy(self):
        """The private copy in examples/opl-env/check.py is what this
        module exists to retire; a fifth one appearing there again is
        the regression."""
        import os
        here = os.path.dirname(os.path.abspath(__file__))
        root = os.path.normpath(os.path.join(here, "..", "..", ".."))
        src = open(os.path.join(root, "examples", "opl-env", "check.py"),
                   encoding="utf-8").read()
        self.assertIn("pen.slot_width", src)
        self.assertNotIn('g["advance"]', src,
                         "check.py is accumulating advances again")


class TestVram(unittest.TestCase):
    def test_page_rounding_ct32(self):
        from ps2ui_bake import vram
        # 64x32 fits one CT32 page exactly; 65x33 spills into 4.
        self.assertEqual(vram.page_rounded_size(64, 32, gs.PSMCT32), 8192)
        self.assertEqual(vram.page_rounded_size(65, 33, gs.PSMCT32), 4 * 8192)
        # 640x448 framebuffer: 10 x 14 pages.
        self.assertEqual(vram.framebuffer_size(640, 448), 10 * 14 * 8192)

    def test_page_rounding_t8(self):
        from ps2ui_bake import vram
        self.assertEqual(vram.page_rounded_size(128, 64, gs.PSMT8), 8192)
        self.assertEqual(vram.page_rounded_size(256, 40, gs.PSMT8), 2 * 8192)

    def test_default_budget_subtracts_framebuffers(self):
        from ps2ui_bake import vram
        self.assertEqual(
            vram.default_budget(640, 448),
            4 * 1024 * 1024 - 3 * vram.framebuffer_size(640, 448),
        )

    def test_report_flags_over_budget(self):
        from ps2ui_bake import vram
        from ps2ui_bake.quads import BakedTexture
        big = [BakedTexture(gs.PSMCT32, 1024, 1024, None, b"")] * 4
        _lines, total, budget, ok = vram.report(big, [], 640, 448)
        self.assertGreater(total, budget)
        self.assertFalse(ok)

    def test_report_passes_small_set(self):
        from ps2ui_bake import vram
        from ps2ui_bake.quads import BakedTexture
        small = [BakedTexture(gs.PSMT8, 256, 64, 0, b"")]
        _lines, _total, _budget, ok = vram.report(small, [gs.coverage_clut()], 640, 448)
        self.assertTrue(ok)


class TestImages(unittest.TestCase):
    def _write_png(self, td, colors=4, size=(16, 12)):
        path = os.path.join(td, "art.png")
        img = Image.new("RGBA", size)
        palette = [(255, 0, 0, 255), (0, 255, 0, 255),
                   (0, 0, 255, 255), (255, 255, 0, 128)]
        for x in range(size[0]):
            for y in range(size[1]):
                img.putpixel((x, y), palette[(x + y) % colors])
        img.save(path)
        return path

    def image_cmd(self, src, w=16, h=12, palettize=False):
        return {
            "op": "image", "x": 5, "y": 5, "w": w, "h": h,
            "src": src, "palettize": palettize,
            "state": "always", "focusId": None,
        }

    def test_rgba_image_bakes_psmct32_texquad(self):
        with tempfile.TemporaryDirectory() as td:
            src = self._write_png(td)
            f = Flattener(tiny_ir([self.image_cmd(src)]), font_paths())
            f.run()
            self.assertEqual(len(f.records), 1)
            rec = f.records[0]
            self.assertEqual(rec.op, OP_TEXQUAD)
            self.assertEqual(rec.rgba, (0x80, 0x80, 0x80, 0x80))
            tex = f.textures[rec.tex]
            self.assertEqual(tex.fmt, gs.PSMCT32)
            self.assertEqual((tex.width, tex.height), (16, 12))
            # Alpha crossed into the GS domain exactly once.
            self.assertLessEqual(max(tex.data[3::4]), 0x80)

    def test_palettized_image_bakes_psmt8_with_clut(self):
        with tempfile.TemporaryDirectory() as td:
            src = self._write_png(td)
            f = Flattener(tiny_ir([self.image_cmd(src, palettize=True)]), font_paths())
            f.run()
            tex = f.textures[f.records[0].tex]
            self.assertEqual(tex.fmt, gs.PSMT8)
            self.assertIsNotNone(tex.clut)
            self.assertEqual(len(tex.data), 16 * 12)  # 1 byte per texel
            clut = f.cluts[tex.clut]
            self.assertLessEqual(max(clut[3::4]), 0x80)  # GS-domain alpha

    def _write_indexed_png(self, td, size=(16, 12)):
        """An indexed PNG whose index values carry meaning.

        Indices 0 and 8 differ only in bit 3, and 32 and 48 only in
        bit 4 -- the two bits CSM1 permutes. Palette entries are set so
        a correct CLUT upload renders the tile uniform and an
        unpermuted one renders a boundary; that only works if the baker
        leaves both the indices and the palette exactly as authored.
        """
        from PIL import Image
        path = os.path.join(td, "indexed.png")
        img = Image.new("P", size)
        pal = [0, 0, 0] * 256
        for idx, rgb in ((0, (0x30, 0x60, 0x90)), (8, (0x30, 0x60, 0x90)),
                         (16, (0xff, 0x00, 0x00)), (32, (0x30, 0x60, 0x90)),
                         (48, (0x30, 0x60, 0x90)), (40, (0xff, 0x00, 0x00))):
            pal[idx * 3:idx * 3 + 3] = list(rgb)
        img.putpalette(pal)
        quarter = size[0] // 4
        for x in range(size[0]):
            idx = (0, 8, 32, 48)[min(x // quarter, 3)]
            for y in range(size[1]):
                img.putpixel((x, y), idx)
        img.save(path)
        return path

    def test_indexed_png_keeps_its_own_indices_and_palette(self):
        # Re-quantizing an already-indexed image is lossy for nothing,
        # and it destroys any meaning the indices carried.
        with tempfile.TemporaryDirectory() as td:
            src = self._write_indexed_png(td)
            f = Flattener(tiny_ir([self.image_cmd(src, palettize=True)]),
                          font_paths())
            f.run()
            tex = f.textures[f.records[0].tex]
            self.assertEqual(tex.fmt, gs.PSMT8)
            # The authored index values survive, not a quantizer's.
            self.assertEqual(sorted(set(tex.data)), [0, 8, 32, 48])
            clut = f.cluts[tex.clut]
            self.assertEqual(len(clut), 256 * 4, "CLUT padded to 256 entries")

            def entry(i):
                return tuple(clut[i * 4:i * 4 + 3])

            # The pairs the swizzle test depends on: equal to each
            # other, and unlike the entry each would land on if the
            # permutation were skipped.
            self.assertEqual(entry(0), entry(8))
            self.assertEqual(entry(32), entry(48))
            self.assertNotEqual(entry(8), entry(16))
            self.assertNotEqual(entry(48), entry(40))

    def test_indexed_png_with_a_short_palette_is_padded_to_256(self):
        # A P-mode PNG only defines the entries it uses, and Pillow
        # hands back exactly those. The GS reads a 256-entry CLUT and
        # the runtime permutes all 256 of them, so a short palette has
        # to be padded or the upload walks off the end of the table.
        #
        # This case exists because the padding line was untested: the
        # other fixture authors a full 768-byte palette, so padding was
        # a no-op there and deleting it changed nothing.
        from PIL import Image
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "short.png")
            img = Image.new("P", (16, 12))
            img.putpalette([0x30, 0x60, 0x90,
                            0xff, 0x00, 0x00,
                            0x00, 0xff, 0x00,
                            0x00, 0x00, 0xff])
            for x in range(16):
                for y in range(12):
                    img.putpixel((x, y), x % 4)
            img.save(path)

            f = Flattener(tiny_ir([self.image_cmd(path, palettize=True)]),
                          font_paths())
            f.run()
            tex = f.textures[f.records[0].tex]
            clut = f.cluts[tex.clut]
            self.assertEqual(len(clut), 256 * 4,
                             "a 4-entry palette must still bake a full CLUT")
            self.assertEqual(tuple(clut[0:3]), (0x30, 0x60, 0x90))
            self.assertEqual(bytes(clut[4 * 4:]), bytes(256 * 4 - 16),
                             "unused entries are zero, not absent")

    def test_indexed_png_refuses_to_be_resized(self):
        # A quiet fall-back to quantizing is the failure this feature
        # exists to prevent: the author believes the indices survived,
        # they did not, and nothing says so.
        with tempfile.TemporaryDirectory() as td:
            src = self._write_indexed_png(td, size=(16, 12))
            f = Flattener(
                tiny_ir([self.image_cmd(src, w=32, h=24, palettize=True)]),
                font_paths())
            with self.assertRaises(ValueError) as cm:
                f.run()
            self.assertIn("indexed PNG", str(cm.exception))

    def test_palettize_all_requantizes_an_indexed_png_rather_than_failing(self):
        # The two opt-ins are not the same claim. `palettize` on an
        # <img> says "I care about this image's palette".
        # --palettize-images says "quantize everything to save VRAM" --
        # its author made no claim about any particular asset, so
        # failing their build over one indexed PNG answers a question
        # nobody asked, and the refusal message points at an attribute
        # they never wrote.
        with tempfile.TemporaryDirectory() as td:
            src = self._write_indexed_png(td, size=(16, 12))
            f = Flattener(
                tiny_ir([self.image_cmd(src, w=32, h=24, palettize=False)]),
                font_paths(), palettize_all=True)
            f.run()  # must not raise
            tex = f.textures[f.records[0].tex]
            self.assertEqual(tex.fmt, gs.PSMT8)
            self.assertEqual((tex.width, tex.height), (32, 24))

    def test_palettize_all_still_bakes_a_matching_indexed_png_verbatim(self):
        # Requantizing under the blanket flag is the fall-back, not the
        # rule: when no resize is needed there is nothing to trade away,
        # so the authored indices still survive.
        with tempfile.TemporaryDirectory() as td:
            src = self._write_indexed_png(td, size=(16, 12))
            f = Flattener(
                tiny_ir([self.image_cmd(src, w=16, h=12, palettize=False)]),
                font_paths(), palettize_all=True)
            f.run()
            tex = f.textures[f.records[0].tex]
            self.assertEqual(sorted(set(tex.data)), [0, 8, 32, 48])

    def test_indexed_png_without_palettize_is_still_rgba(self):
        # The verbatim path is opt-in through the same attribute as
        # before; an indexed source with no `palettize` is ordinary art.
        with tempfile.TemporaryDirectory() as td:
            src = self._write_indexed_png(td)
            f = Flattener(tiny_ir([self.image_cmd(src, palettize=False)]),
                          font_paths())
            f.run()
            self.assertEqual(f.textures[f.records[0].tex].fmt, gs.PSMCT32)

    def test_palettize_all_overrides_per_image(self):
        with tempfile.TemporaryDirectory() as td:
            src = self._write_png(td)
            f = Flattener(tiny_ir([self.image_cmd(src, palettize=False)]),
                          font_paths(), palettize_all=True)
            f.run()
            self.assertEqual(f.textures[f.records[0].tex].fmt, gs.PSMT8)

    def test_image_prescaled_to_layout_size(self):
        with tempfile.TemporaryDirectory() as td:
            src = self._write_png(td)
            f = Flattener(tiny_ir([self.image_cmd(src, w=32, h=24)]), font_paths())
            f.run()
            tex = f.textures[f.records[0].tex]
            self.assertEqual((tex.width, tex.height), (32, 24))

    def test_same_image_same_size_shares_texture(self):
        with tempfile.TemporaryDirectory() as td:
            src = self._write_png(td)
            f = Flattener(tiny_ir([self.image_cmd(src), self.image_cmd(src)]),
                          font_paths())
            f.run()
            self.assertEqual(len(f.textures), 1)

    def test_palettized_image_round_trips_through_preview(self):
        with tempfile.TemporaryDirectory() as td:
            src = self._write_png(td)
            f = Flattener(tiny_ir([self.image_cmd(src, palettize=True)]), font_paths())
            f.run()
            path = os.path.join(td, "t.uib")
            write_uib(path, {"w": 320, "h": 240}, f.records, f.textures,
                      f.cluts, [], None)
            img = preview.render(read_uib(path), background=(0, 0, 0, 255))
            # Pixel (5,5) is palette color (x+y)%4 = 0 -> pure red; 4
            # distinct colors quantize losslessly into 256 slots.
            r, g, b, _ = img.getpixel((5, 5))
            self.assertGreater(r, 240)
            self.assertLess(g, 15)

    def test_vram_savings_reported_for_psmt8(self):
        from ps2ui_bake import vram
        with tempfile.TemporaryDirectory() as td:
            src = self._write_png(td, size=(256, 128))
            f32 = Flattener(tiny_ir([self.image_cmd(src, w=256, h=128)]), font_paths())
            f32.run()
            f8 = Flattener(tiny_ir([self.image_cmd(src, w=256, h=128, palettize=True)]),
                           font_paths())
            f8.run()
            _l, total32, _b, _ok = vram.report(f32.textures, f32.cluts, 640, 448)
            _l, total8, _b, _ok = vram.report(f8.textures, f8.cluts, 640, 448)
            self.assertLess(total8, total32 / 2)


class TestUib(unittest.TestCase):
    def roundtrip(self, records, textures=(), cluts=(), nodes=(), initial=None):
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "t.uib")
            write_uib(path, {"w": 320, "h": 240}, list(records),
                      list(textures), list(cluts), list(nodes), initial)
            return read_uib(path)

    def test_struct_sizes_match_c_runtime(self):
        # v7: the header grew by off_tint, n_theme and its pad, with
        # n_tint taking the u16 that was already padding after
        # n_screen. The command did NOT grow: four colour bytes became
        # two u16 indices and the two that freed went into tint_focus,
        # inside padding that was already there to reach two qwords.
        self.assertEqual(_HEADER.size, 84)
        self.assertEqual(_CMD.size, 32)
        self.assertEqual(_FOCUS.size, 24)
        self.assertEqual(_TINT.size, 4)

    def test_records_round_trip_exactly(self):
        recs = [
            DrawRecord(OP_QUAD, STATE_ALWAYS, FOCUS_NONE, -4, 7, 10, 20, (1, 2, 3, 0x80)),
            DrawRecord(OP_TEXQUAD, STATE_FOCUSED, 3, 0, 0, 5, 5, (9, 9, 9, 64), 2, 1, 2, 3, 4),
            DrawRecord(OP_SCISSOR_PUSH, STATE_ALWAYS, FOCUS_NONE, 0, 0, 100, 100, (0, 0, 0, 0)),
            DrawRecord(OP_SCISSOR_POP, STATE_ALWAYS, FOCUS_NONE, 0, 0, 0, 0, (0, 0, 0, 0)),
        ]
        out = self.roundtrip(recs)
        # WIDENED, NOT LOST. A record written with rgba_themes=None is
        # a colour that is the same in every theme, and the writer
        # stores it as a full row rather than as an absence -- so the
        # reader hands back the vector the file actually holds. Not
        # special-cased to None at n_theme == 1: one shape for one
        # concept, or the previewer's theme path would be exercised
        # only by multi-theme blobs and untested by every other test
        # in this file.
        want = [replace(r, rgba_themes=((tuple(r.rgba),)
                                        if r.op in (OP_QUAD, OP_TEXQUAD)
                                        else None))
                for r in recs]
        self.assertEqual(out.records, want)
        self.assertEqual((out.canvas_w, out.canvas_h), (320, 240))

    def test_textures_cluts_and_focus_round_trip(self):
        from ps2ui_bake.quads import BakedTexture
        tex = BakedTexture(gs.PSMT8, 8, 8, 0, bytes(range(64)))
        clut = gs.coverage_clut()
        nodes = [{"id": 5, "name": "solo", "rect": [1, 2, 3, 4],
                  "up": None, "down": None, "left": None, "right": None}]
        out = self.roundtrip([], [tex], [clut], nodes, initial=0)
        self.assertEqual(out.textures[0].data, bytes(range(64)))
        self.assertEqual(out.cluts[0], clut)
        self.assertEqual(out.focus[0]["name"], "solo")
        self.assertEqual(out.focus[0]["rect"], (1, 2, 3, 4))
        self.assertEqual(out.focus[0]["up"], FOCUS_NONE)
        self.assertEqual(out.initial_focus, 0)

    def test_bad_magic_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "bad.uib")
            write_uib(path, {"w": 1, "h": 1}, [], [], [], [], None)
            with open(path, "rb") as fh:
                data = bytearray(fh.read())
            data[0] ^= 0xFF
            with open(path, "wb") as fh:
                fh.write(bytes(data))
            with self.assertRaises(ValueError):
                read_uib(path)

    def test_truncation_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "t.uib")
            nodes = [{"id": 1, "name": "x", "rect": [0, 0, 1, 1],
                      "up": None, "down": None, "left": None, "right": None}]
            write_uib(path, {"w": 1, "h": 1}, [], [], [], nodes, 0)
            with open(path, "rb") as fh:
                data = fh.read()
            with open(path, "wb") as fh:
                fh.write(data[:len(data) - 4])
            with self.assertRaises(ValueError):
                read_uib(path)


@unittest.skipIf(TTF is None, "DejaVu Sans not installed")
class TestDynamicText(unittest.TestCase):
    def slot_ir(self):
        return {
            "version": 1,
            "canvas": {"w": 320, "h": 240},
            "commands": [],
            "focus": {"nodes": [], "initial": None},
            "slots": [{
                "name": "title", "placeholder": "Hello",
                "x": 10, "textY": 20, "w": 120,
                "size": 14, "weight": 400, "lineHeight": 18,
                "align": "left", "ellipsis": True, "capacity": 24,
                "focusId": None,
                "colorBase": [200, 200, 200, 255],
                "colorFocus": [255, 255, 255, 255],
            }],
            "warnings": [],
        }

    def bake(self, ir):
        f = Flattener(ir, font_paths())
        f.run()
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "t.uib")
            write_uib(path, ir["canvas"], f.records, f.textures, f.cluts,
                      [], None, f.fonts, f.slots)
            return read_uib(path)

    def test_slot_and_font_round_trip(self):
        uib = self.bake(self.slot_ir())
        self.assertTrue(uib.feature_flags & 1)
        self.assertEqual(len(uib.slots), 1)
        s = uib.slots[0]
        self.assertEqual(s["name"], "title")
        self.assertEqual(s["placeholder"], "Hello")
        self.assertEqual(s["capacity"], 24)
        self.assertTrue(s["ellipsis"])
        # Colors crossed into the modulate domain exactly once.
        self.assertEqual(s["color_base"][3], 0x80)
        self.assertLessEqual(max(s["color_base"]), 0x80)

    def test_glyph_table_is_full_charset_and_sorted(self):
        uib = self.bake(self.slot_ir())
        font = uib.fonts[uib.slots[0]["font"]]
        cps = list(font["glyphs"].keys())
        # read_uib returns dict keyed by cp; verify the ASCII range and
        # the ellipsis made it in (runtime bsearch needs sorted, which
        # the writer guarantees; the reader's dict loses order, so
        # re-check sortedness on the raw records via struct scan).
        self.assertIn(ord("A"), cps)
        self.assertIn(ord("z"), cps)
        self.assertIn(0x2026, cps)
        g = font["glyphs"][ord("i")]
        self.assertEqual(g["advance"], glyph_advance_px(278, 14))

    def test_preview_renders_placeholder_and_override(self):
        uib = self.bake(self.slot_ir())
        ph = preview.render(uib, background=(0, 0, 0, 255))
        ov = preview.render(uib, background=(0, 0, 0, 255),
                            slot_text={"title": "XYZZY"})
        self.assertNotEqual(list(ph.getdata()), list(ov.getdata()))

    def test_crc_rejects_flipped_bit(self):
        f = Flattener(self.slot_ir(), font_paths())
        f.run()
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "t.uib")
            write_uib(path, {"w": 320, "h": 240}, f.records, f.textures,
                      f.cluts, [], None, f.fonts, f.slots)
            with open(path, "rb") as fh:
                data = bytearray(fh.read())
            data[len(data) // 2] ^= 0x01
            with open(path, "wb") as fh:
                fh.write(bytes(data))
            with self.assertRaisesRegex(ValueError, "crc"):
                read_uib(path)


class TestKerningPen(unittest.TestCase):
    """The baker's pen must place glyph n at the same integer x as
    layout's Font.layout(), because layout sized the box this draws in."""

    def text_ir(self, text, size=32, weight=400, spacing=0):
        cmd = {"op": "text", "text": text, "x": 0, "y": 0,
               "size": size, "weight": weight, "state": "always",
               "color": [255, 255, 255, 255], "focusId": None}
        if spacing:
            cmd["letterSpacing"] = spacing
        return tiny_ir([cmd])

    def pen_xs(self, text, **kw):
        f = Flattener(self.text_ir(text, **kw), font_paths())
        f.run()
        return [r for r in f.records if r.op == OP_TEXQUAD]

    def test_a_kerned_pair_pulls_the_second_glyph_left(self):
        # "To" is -170 units; at 32px that is -5px, and the 'o' must sit
        # 5px left of where an unkerned pen would put it.
        builder = AtlasBuilder(require_ttf(), METRICS, 400, 32)
        self.assertEqual(builder.kern(ord("T"), ord("o")), -5)
        kerned = self.pen_xs("To", size=32)
        unkerned_o = builder.add("T").advance + builder.add("o").bearing_x
        self.assertEqual(kerned[1].x, unkerned_o - 5)

    def test_the_first_glyph_is_never_kerned(self):
        builder = AtlasBuilder(require_ttf(), METRICS, 400, 32)
        self.assertEqual(builder.kern(None, ord("o")), 0)
        self.assertEqual(self.pen_xs("To", size=32)[0].x,
                         builder.add("T").bearing_x)

    def test_kerning_is_directional(self):
        builder = AtlasBuilder(require_ttf(), METRICS, 400, 32)
        self.assertLess(builder.kern(ord("T"), ord("o")), 0)
        self.assertEqual(builder.kern(ord("o"), ord("T")), 0)

    def test_letter_spacing_and_kerning_both_apply(self):
        builder = AtlasBuilder(require_ttf(), METRICS, 400, 32)
        plain = self.pen_xs("To", size=32)
        spaced = self.pen_xs("To", size=32, spacing=3)
        self.assertEqual(spaced[1].x - plain[1].x, 3)
        # And spacing does not apply before the first glyph.
        self.assertEqual(spaced[0].x, plain[0].x)

    def test_an_unkerned_string_is_unchanged(self):
        # The regression guard for every UI that has no kerned pairs:
        # its geometry must be byte-identical to before kerning existed.
        builder = AtlasBuilder(require_ttf(), METRICS, 400, 32)
        recs = self.pen_xs("iiiii", size=32)
        x = 0
        for r in recs:
            self.assertEqual(r.x, x + builder.add("i").bearing_x)
            x += builder.add("i").advance


class TestKernTable(unittest.TestCase):
    """The per-font table the runtime reads, and the format that carries
    it."""

    def bake(self, ir=None):
        """Flatten and round-trip through a real .uib file."""
        ir = ir or TestDynamicText().slot_ir()
        f = Flattener(ir, font_paths())
        f.run()
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "t.uib")
            write_uib(path, ir["canvas"], f.records, f.textures, f.cluts,
                      f.focus_nodes, None, fonts=f.fonts, slots=f.slots,
                      screens=f.screens)
            return f, read_uib(path)

    def test_pairs_are_pixels_at_this_font_size_not_units(self):
        require_ttf()
        f, _ = self.bake()
        font = f.fonts[0]
        size = font["size"]
        by_pair = {(k["prev"], k["cur"]): k["amount"] for k in font["kerns"]}
        with open(METRICS, encoding="utf-8") as fh:
            units = json.load(fh)["kerning"]
        for (prev, cur), amount in by_pair.items():
            self.assertEqual(amount, kern_px(units[f"{prev},{cur}"], size))

    def test_pairs_that_round_to_zero_are_dropped(self):
        require_ttf()
        f, _ = self.bake()
        font = f.fonts[0]
        self.assertTrue(all(k["amount"] != 0 for k in font["kerns"]))
        # A 14px UI keeps far fewer pairs than the metrics carry: a
        # sub-em adjustment only survives rounding once text is large.
        with open(METRICS, encoding="utf-8") as fh:
            self.assertLess(len(font["kerns"]),
                            len(json.load(fh)["kerning"]))

    def test_pairs_are_sorted_for_the_runtime_bsearch(self):
        require_ttf()
        f, _ = self.bake()
        for font in f.fonts:
            keys = [(k["prev"], k["cur"]) for k in font["kerns"]]
            self.assertEqual(keys, sorted(keys))

    def test_a_bigger_font_keeps_more_pairs(self):
        # The direct consequence of pre-rounding to pixels, and the
        # reason the table is per-size rather than per-face.
        kept = {}
        for size in (10, 14, 24, 40):
            b = AtlasBuilder(require_ttf(), METRICS, 400, size)
            for cp_str in b.metrics["advances"]:
                b.add(chr(int(cp_str)))
            kept[size] = len(Flattener._kern_table(b))
        self.assertLess(kept[10], kept[24])
        self.assertLess(kept[24], kept[40])

    def test_orphan_pairs_are_not_stored(self):
        require_ttf()
        # A pair naming a glyph the atlas never baked can never be
        # looked up; storing it would only cost blob.
        b = AtlasBuilder(require_ttf(), METRICS, 400, 32)
        b.add("T")   # deliberately no 'o'
        pairs = Flattener._kern_table(b)
        self.assertFalse([k for k in pairs if k["cur"] == ord("o")])

    def test_the_format_carries_the_table_and_declares_it(self):
        require_ttf()
        f, u = self.bake()
        self.assertEqual(u.feature_flags & FEAT_DYNAMIC_TEXT, FEAT_DYNAMIC_TEXT)
        self.assertEqual(u.feature_flags & FEAT_KERNING, FEAT_KERNING)
        written = {(k["prev"], k["cur"]): k["amount"] for k in f.fonts[0]["kerns"]}
        self.assertEqual(u.fonts[0]["kerns"], written)

    def test_the_font_entry_grew_and_the_version_moved_with_it(self):
        # A v4 reader would have walked the font table at a 16-byte
        # stride and misparsed every entry, so the struct growing is
        # what forces the version bump rather than a feature bit alone.
        self.assertEqual(_FONT.size, 24)
        self.assertEqual(_KERN.size, 12)
        # v6: the texture entry grew from 16 to 20 bytes for `kind` and
        # `name_off`, so a v5 reader would walk the texture table at
        # the wrong stride -- the same argument that made kerning a
        # version bump rather than a feature bit alone.
        # v7: commands and slots hold tint INDICES where they held
        # rgba, and the header grew a tint table. Neither stride nor
        # meaning survives a v6 reader, so this is a version bump for
        # the same reason as the two above.
        self.assertEqual(VERSION, 7)

    def test_the_feature_bit_states_what_the_tables_hold(self):
        require_ttf()
        # Stated, not inferred: with the bit clear the runtime may skip
        # the lookup wholesale, so a blob that carried pairs without
        # declaring them would kern in the previewer and not on console.
        _, kerned = self.bake()
        self.assertTrue(kerned.feature_flags & FEAT_KERNING)

        ir = TestDynamicText().slot_ir()
        f = Flattener(ir, font_paths())
        f.run()
        for font in f.fonts:
            font["kerns"] = []
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "t.uib")
            write_uib(path, ir["canvas"], f.records, f.textures, f.cluts,
                      f.focus_nodes, None, fonts=f.fonts, slots=f.slots,
                      screens=f.screens)
            bare = read_uib(path)
        self.assertEqual(bare.feature_flags & FEAT_KERNING, 0)
        # and the dynamic-text bit is untouched by it
        self.assertEqual(bare.feature_flags & FEAT_DYNAMIC_TEXT,
                         FEAT_DYNAMIC_TEXT)


# Skipped without node -- silently, so a green local run on a
# Python-only machine does not cover this. CI's toolchain job installs
# node, so the check always runs there.
@unittest.skipUnless(shutil.which("node"), "node is not installed")
class TestDataKeep(unittest.TestCase):
    """data-keep exempts geometry from the dead-geometry trim.

    The trim's safety argument is that removing a record which could
    never draw cannot change the image -- which is precisely what makes
    a deliberately-clipped quad useless as an instrument unless it can
    opt out."""

    def ir(self, keep):
        """A clip rect with two quads outside it, one opting out."""
        cmds = [
            {"op": "scissor_push", "x": 0, "y": 0, "w": 40, "h": 40,
             "state": "always", "focusId": None},
            {"op": "rect", "x": 200, "y": 0, "w": 20, "h": 20,
             "fill": [255, 0, 255, 255], "borderWidth": 0,
             "borderColor": None, "radius": 0,
             "state": "always", "focusId": None},
            {"op": "rect", "x": 240, "y": 0, "w": 20, "h": 20,
             "fill": [0, 255, 0, 255], "borderWidth": 0,
             "borderColor": None, "radius": 0,
             "state": "always", "focusId": None},
            {"op": "scissor_pop", "state": "always", "focusId": None},
        ]
        if keep:
            cmds[1]["keep"] = True
        return tiny_ir(cmds)

    def bake(self, keep):
        f = Flattener(self.ir(keep), font_paths())
        f.run()
        return f

    def test_without_it_both_dead_quads_go(self):
        f = self.bake(keep=False)
        self.assertEqual(f.dropped, 2)
        self.assertFalse([r for r in f.records if r.op == OP_QUAD])

    def test_with_it_the_marked_one_survives(self):
        f = self.bake(keep=True)
        self.assertEqual(f.dropped, 1)
        kept = [r for r in f.records if r.op == OP_QUAD]
        self.assertEqual(len(kept), 1)
        self.assertEqual(kept[0].rgba[:3], (255, 0, 255))
        self.assertEqual(kept[0].x, 200)   # still outside the clip

    def test_it_does_not_reach_the_blob(self):
        # Build-time only: the runtime draws the records it is given and
        # has no notion of one it should have dropped, so the flag has
        # nowhere to go and no reason to cost format space.
        f = self.bake(keep=True)
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "t.uib")
            write_uib(path, {"w": 320, "h": 240}, f.records, f.textures,
                      f.cluts, f.focus_nodes, None, screens=f.screens)
            u = read_uib(path)
        self.assertFalse(any(hasattr(r, "keep") and r.keep for r in u.records))

    def test_the_validator_can_be_told_a_dead_quad_is_deliberate(self):
        # ps2ui-check reads only the blob, and data-keep never reaches
        # it, so the validator cannot tell an instrument from waste --
        # and must not guess. --allow-dead declares the count, and one
        # more than declared still warns.
        from ps2ui_bake.check import check_blob
        f = self.bake(keep=True)
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "t.uib")
            write_uib(path, {"w": 320, "h": 240}, f.records, f.textures,
                      f.cluts, f.focus_nodes, None, screens=f.screens)
            u = read_uib(path)
        self.assertEqual(check_blob(u).warnings, 1)
        self.assertEqual(check_blob(u, allow_dead=1).warnings, 0)
        self.assertEqual(check_blob(u, allow_dead=0).warnings, 1)

    def test_it_never_rescues_geometry_that_could_draw(self):
        # The flag only ever subtracts from the dead set, so a quad
        # inside its clip is unaffected either way.
        ir = self.ir(keep=True)
        ir["commands"][1]["x"] = 5      # now inside the 40x40 clip
        f = Flattener(ir, font_paths())
        f.run()
        self.assertEqual(f.dropped, 1)  # only the green one, as before


class TestCrossLanguagePen(unittest.TestCase):
    """Node and Python must place every glyph on the same pixel.

    This is the seam the whole design rests on: layout measures the box
    in Node, the baker draws into it in Python, and nothing downstream
    can notice if they disagree — the text simply sits a few pixels off
    or runs past its box, on a television, months later.

    Together with the other two links the chain is closed: this test
    covers Node <-> Python, TestKernTable covers Python -> blob, and
    the runtime suite's linear-scan check covers blob <-> C.
    """

    CORPUS = [
        "To the Victor",
        "AV Ta Yo LT P. W. r. AW VA",
        "Shadow of the Colossus",
        "Library",
        "PS2",
        "iiiii",                    # nothing kerns
        "AVAVAVAVAVAVAVAVAVAVAVAV",  # every pair kerns
        "T",                        # one glyph, no pair at all
        "",                         # and none
    ]
    SIZES = [11, 13, 14, 16, 20, 32, 48]
    SPACINGS = [0, 1, 3]

    def js_pen(self):
        """{"size|spacing|text": [pen x per glyph]} from layout's pen."""
        src = os.path.join(REPO, "packages", "layout", "src", "text.js")
        script = (
            "import { loadFont } from %s;\n"
            "const f = loadFont(%s);\n"
            "const out = {};\n"
            "for (const size of %s)\n"
            "  for (const ls of %s)\n"
            "    for (const s of %s)\n"
            "      out[`${size}|${ls}|${s}`] ="
            " f.layout(s, size, ls).glyphs.map(g => g.x);\n"
            "console.log(JSON.stringify(out));\n"
        ) % (json.dumps(src), json.dumps(METRICS), json.dumps(self.SIZES),
             json.dumps(self.SPACINGS), json.dumps(self.CORPUS))
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "pen.mjs")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(script)
            out = subprocess.run([shutil.which("node"), path],
                                 capture_output=True, text=True, check=True)
        return json.loads(out.stdout)

    def py_pen(self, text, size, spacing):
        """The baker's pen, read back off the flattened records.

        Reconstructed rather than read from the DrawRecords directly:
        records carry x + bearing_x and exist only for inked glyphs, so
        a space would vanish from the comparison and every position
        would carry a bearing the other side does not add.
        """
        builder = AtlasBuilder(require_ttf(), METRICS, 400, size)
        xs = []
        pen = 0
        prev = None
        for ch in text:
            cp = ord(ch)
            if prev is not None:
                pen += spacing + builder.kern(prev, cp)
            xs.append(pen)
            pen += builder.add(ch).advance
            prev = cp
        return xs

    def test_the_two_pens_place_every_glyph_on_the_same_pixel(self):
        js = self.js_pen()
        self.assertEqual(
            len(js), len(self.SIZES) * len(self.SPACINGS) * len(self.CORPUS))
        for key, expect in js.items():
            size, spacing, text = key.split("|", 2)
            got = self.py_pen(text, int(size), int(spacing))
            self.assertEqual(got, expect, f"{text!r} at {size}px ls={spacing}")

    def test_the_comparison_would_notice_a_disagreement(self):
        # A test that compares two implementations is only worth
        # anything if it fails when they differ. Shift one side by the
        # kern it is supposed to apply and confirm the mismatch.
        self.assertNotEqual(self.py_pen("To", 32, 0),
                            [0, self.py_pen("To", 32, 0)[1] + 5])
        self.assertEqual(self.py_pen("To", 32, 0)[1],
                         AtlasBuilder(require_ttf(), METRICS, 400, 32).add("T").advance - 5)


class TestTintTable(unittest.TestCase):
    """v7: colour left the command and the slot for a shared table.

    The premise is that a UI's palette is tiny and repeated, so a theme
    is a table swap rather than a walk over every primitive. That is a
    measurable claim about the shipped blobs, not a design opinion, so
    it is measured here.
    """

    def write(self, records, slots=(), fonts=(), **kw):
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "t.uib")
            write_uib(path, {"w": 320, "h": 240}, list(records),
                      [], [], [], None, fonts=list(fonts),
                      slots=list(slots), **kw)
            return read_uib(path)

    def test_repeated_colour_interns_once(self):
        # Twenty quads, two colours. The whole design rests on this
        # being 2 and not 20.
        recs = []
        for i in range(20):
            rgba = (0x10, 0x20, 0x30, 0x80) if i % 2 else (0x40, 0x50, 0x60, 0x80)
            recs.append(DrawRecord(OP_QUAD, STATE_ALWAYS, FOCUS_NONE,
                                   i, 0, 4, 4, rgba))
        u = self.write(recs)
        self.assertEqual(len(u.themes), 1)
        self.assertEqual(len(u.themes[0]), 2)
        # And the indices actually point at the right rows -- a table
        # of the right SIZE with the wrong mapping would satisfy the
        # count above and render the UI in the wrong colours.
        for r, orig in zip(u.records, recs):
            self.assertEqual(r.rgba, orig.rgba)

    def test_scissors_do_not_intern(self):
        # A scissor has no colour. Interning its zeros would put an
        # entry in the table that no draw can ever reach.
        recs = [
            DrawRecord(OP_SCISSOR_PUSH, STATE_ALWAYS, FOCUS_NONE, 0, 0, 10, 10,
                       (0, 0, 0, 0)),
            DrawRecord(OP_QUAD, STATE_ALWAYS, FOCUS_NONE, 0, 0, 4, 4,
                       (1, 2, 3, 0x80)),
            DrawRecord(OP_SCISSOR_POP, STATE_ALWAYS, FOCUS_NONE, 0, 0, 0, 0,
                       (0, 0, 0, 0)),
        ]
        u = self.write(recs)
        self.assertEqual(len(u.themes[0]), 1)
        self.assertEqual(u.themes[0][0], (1, 2, 3, 0x80))

    def test_a_name_is_a_role_and_a_literal_is_not(self):
        """Two records with the same colour: named ones share an entry,
        an unnamed one gets its own.

        This is the whole of the keying rule. A role is what somebody
        called a colour; two literals that happen to agree are two
        coincidences that nobody offered to a theme, and they still
        collapse -- but they must not collapse INTO a named entry, or a
        theme moving the name would move them too.
        """
        rgba = (0x40, 0x50, 0x60, 0x80)
        recs = [
            DrawRecord(OP_QUAD, STATE_ALWAYS, FOCUS_NONE, 0, 0, 4, 4, rgba,
                       var="--panel"),
            DrawRecord(OP_QUAD, STATE_ALWAYS, FOCUS_NONE, 4, 0, 4, 4, rgba,
                       var="--panel"),
            DrawRecord(OP_QUAD, STATE_ALWAYS, FOCUS_NONE, 8, 0, 4, 4, rgba),
            DrawRecord(OP_QUAD, STATE_ALWAYS, FOCUS_NONE, 12, 0, 4, 4, rgba),
        ]
        u = self.write(recs)
        # Two entries, not one and not four: the pair of --panel records
        # share, the pair of literals share, and the two groups do not.
        self.assertEqual(len(u.themes[0]), 2)
        # Both groups still resolve to the same colour, which is what
        # makes this a keying test rather than a colour test.
        for r in u.records:
            self.assertEqual(r.rgba, rgba)

    def test_two_names_on_one_value_are_two_entries(self):
        """The case role-keying exists for: same colour, different roles.

        Under value-keying these fuse and no theme can tell them apart.
        """
        rgba = (0x11, 0x22, 0x33, 0x80)
        recs = [
            DrawRecord(OP_QUAD, STATE_ALWAYS, FOCUS_NONE, 0, 0, 4, 4, rgba,
                       var="--bg-page"),
            DrawRecord(OP_QUAD, STATE_ALWAYS, FOCUS_NONE, 4, 0, 4, 4, rgba,
                       var="--ink-on-accent"),
        ]
        u = self.write(recs)
        self.assertEqual(len(u.themes[0]), 2)
        self.assertEqual(u.themes[0][0], u.themes[0][1],
                         "and they hold the SAME colour -- the split is by "
                         "name, which is the only thing that distinguishes "
                         "them")

    def test_a_slot_keys_on_its_name_too(self):
        """COLOUR LIVES IN TWO TABLES AND THIS SEAM HAS BEEN THE GAP
        THREE TIMES -- the design missed slots, the v7 tint_focus fence
        missed them, and ps2ui_theme_set's first check missed them.

        A fourth: stripping the slot's var names from write_uib passed
        every test in this file and rebuilt opl-env clean, because
        nothing there happened to collide. This is the case that cannot
        pass without it -- a slot and a command holding the same colour
        under different names. Value-keyed, they fuse into one entry and
        a theme moving either moves both.
        """
        # THE DISCRIMINATOR IS SHARING, NOT SPLITTING, and the first
        # version of this test got that backwards. It gave the command
        # --panel and the slot --ink and asserted two entries -- which
        # holds with the slot keyed on the value too, since (None, rgba)
        # and ("--panel", rgba) are different keys either way. It passed
        # the sabotage.
        #
        # One name on both sides is the case that cannot: keyed on the
        # name they are ONE entry, and a slot keyed on the value falls
        # out to (None, rgba) and makes two.
        rgba = (0x30, 0x40, 0x50, 0x80)
        recs = [DrawRecord(OP_QUAD, STATE_ALWAYS, FOCUS_NONE, 0, 0, 4, 4,
                           rgba, var="--ink")]
        fonts = [{"tex": 0, "size": 12, "weight": 400, "ascent": 10,
                  "line_height": 14, "glyphs": [], "kerns": []}]
        slots = [{
            "name": "s", "placeholder": "", "x": 0, "text_y": 0, "w": 32,
            "font": 0, "align": 0, "ellipsis": False, "capacity": 8,
            "focus": FOCUS_NONE,
            "color_base": rgba, "color_focus": rgba,
            "color_base_var": "--ink", "color_focus_var": "--ink",
        }]
        u = self.write(recs, slots=slots, fonts=fonts)
        self.assertEqual(
            len(u.themes[0]), 1,
            "one name across a command and a slot is ONE role and one "
            "entry; two means the slot table was keyed on the value while "
            "the command list was keyed on the name, so a theme would "
            "recolour the panel and leave the label behind")
        self.assertEqual(u.slots[0]["tint_base"], 0)

    def test_one_name_is_not_one_entry_when_opacity_folds_in(self):
        """A ROLE IS NOT A FUNCTION OF ITS NAME ALONE, and P3b-4's
        row-writer is where that bites.

        `opacity` multiplies into the painted colour's alpha before the
        name is attached, so the layout output for

            #a { background: var(--panel) }
            #b { background: var(--panel); opacity: 0.5 }

        is one role carrying two colours. Two entries is the RIGHT
        answer -- they are different colours on screen and one entry
        could only serve both by picking a side -- so this is not a
        fence against fusing them. It is a fence against the belief
        that fusing them is what happens, held by a future row-writer
        that looks a theme's literal up by name and copies it into
        "the" entry: it would move the opaque panel, leave the
        half-alpha one baked, and change half the screen.

        Keyed on the name alone this collapses to 1 and the test
        fails. That is the sabotage it exists to catch.
        """
        recs = [
            DrawRecord(OP_QUAD, STATE_ALWAYS, FOCUS_NONE, 0, 0, 4, 4,
                       (51, 102, 153, 0x80), var="--panel"),
            DrawRecord(OP_QUAD, STATE_ALWAYS, FOCUS_NONE, 4, 0, 4, 4,
                       (51, 102, 153, 0x40), var="--panel"),
        ]
        u = self.write(recs)
        self.assertEqual(
            len(u.themes[0]), 2,
            "one name, two painted colours, two entries -- a theme has "
            "to move both or half the panels keep the old colour")
        self.assertEqual(u.themes[0][0][:3], u.themes[0][1][:3])
        self.assertNotEqual(u.themes[0][0][3], u.themes[0][1][3])

    def test_two_themes_write_two_rows_and_set_the_bit(self):
        """P3b-4. The row the format has had since v7, finally written.

        Also the bit: the runtime refuses n_theme > 1 without it,
        because a value-keyed table cannot tell two declarations that
        share a colour apart, so a second row would recolour things
        nobody asked for.
        """
        recs = [
            DrawRecord(OP_QUAD, STATE_ALWAYS, FOCUS_NONE, 0, 0, 4, 4,
                       (0x10, 0x20, 0x30, 0x80), var="--panel",
                       rgba_themes=((0x10, 0x20, 0x30, 0x80),
                                    (0xF0, 0xF0, 0xF0, 0x80))),
            # No vector at all: the nine-patch identity tint, which has
            # no declaration behind it and is identity in every theme.
            DrawRecord(OP_TEXQUAD, STATE_ALWAYS, FOCUS_NONE, 4, 0, 4, 4,
                       (128, 128, 128, 128)),
        ]
        u = self.write(recs, n_theme=2)
        self.assertTrue(u.feature_flags & FEAT_ROLE_TINTS)
        self.assertEqual(len(u.themes), 2)
        self.assertEqual(u.themes[0], [(0x10, 0x20, 0x30, 0x80),
                                       (128, 128, 128, 128)])
        self.assertEqual(
            u.themes[1], [(0xF0, 0xF0, 0xF0, 0x80), (128, 128, 128, 128)],
            "the named entry moves and the identity does not -- widened "
            "to a full row rather than stored short, so a consumer sees "
            "one shape whatever the theme count")

    def test_a_row_that_disagrees_with_its_own_colour_is_refused(self):
        """Row 0 IS the colour every other consumer sees. If they ever
        disagreed the blob would render one thing and every host-side
        check -- the previewer, the drift screenshots, ps2ui-check --
        would agree with the other, which is the shape of a defect that
        is only visible on a television."""
        recs = [DrawRecord(OP_QUAD, STATE_ALWAYS, FOCUS_NONE, 0, 0, 4, 4,
                           (1, 2, 3, 0x80),
                           rgba_themes=((9, 9, 9, 0x80), (4, 5, 6, 0x80)))]
        with self.assertRaises(ValueError) as cm:
            self.write(recs, n_theme=2)
        self.assertIn("row 0", str(cm.exception))

    def test_a_short_vector_is_refused(self):
        recs = [DrawRecord(OP_QUAD, STATE_ALWAYS, FOCUS_NONE, 0, 0, 4, 4,
                           (1, 2, 3, 0x80), rgba_themes=((1, 2, 3, 0x80),))]
        with self.assertRaises(ValueError) as cm:
            self.write(recs, n_theme=2)
        self.assertIn("1 themes, expected 2", str(cm.exception))

    def test_the_tint_report_carries_the_name_only_it_knows(self):
        """P3b-5. The var() name never reaches the blob -- the runtime
        selects a theme by index and has no use for it -- so write_uib
        is the last point in the pipeline where an entry can be tied
        back to the declaration that produced it.

        That makes "why did this not change colour" a two-tool
        question: `ps2ui-bake --tints` prints the names as it writes
        them, `ps2ui-check --tints` prints what a loader finds. Dropping
        the name here leaves the first tool answering the same half as
        the second, which reads as working.
        """
        recs = [
            DrawRecord(OP_QUAD, STATE_ALWAYS, FOCUS_NONE, 0, 0, 4, 4,
                       (0x10, 0x20, 0x30, 0x80), var="--panel",
                       rgba_themes=((0x10, 0x20, 0x30, 0x80),
                                    (0xF0, 0xF0, 0xF0, 0x80))),
            DrawRecord(OP_QUAD, STATE_ALWAYS, FOCUS_NONE, 4, 0, 4, 4,
                       (0x11, 0x22, 0x33, 0x80)),
        ]
        report = []
        with tempfile.TemporaryDirectory() as td:
            write_uib(os.path.join(td, "t.uib"), {"w": 320, "h": 240},
                      list(recs), [], [], [], None, n_theme=2,
                      tint_report=report)
        self.assertEqual([(i, var) for i, var, _ in report],
                         [(0, "--panel"), (1, None)],
                         "the named entry keeps its name and the literal "
                         "keeps its absence -- a literal is the author "
                         "declining to offer a colour to a theme, not a "
                         "missing name")
        self.assertEqual(report[0][2],
                         ((0x10, 0x20, 0x30, 0x80), (0xF0, 0xF0, 0xF0, 0x80)))

    def patched(self, path, mutate):
        """Apply `mutate(bytearray)` to a written blob and re-CRC it."""
        with open(path, "rb") as fh:
            raw = bytearray(fh.read())
        mutate(raw)
        struct.pack_into("<I", raw, 48, 0)
        struct.pack_into("<I", raw, 48, zlib.crc32(bytes(raw)) & 0xFFFFFFFF)
        with open(path, "wb") as fh:
            fh.write(bytes(raw))

    def test_an_index_past_the_table_is_named_not_an_indexerror(self):
        # The reader resolves indices, so a corrupt one lands in a list
        # subscript. Left alone that raises IndexError, which names a
        # Python builtin instead of the malformed field and reaches
        # ps2ui-check as a traceback rather than a verdict on the file.
        from ps2ui_bake.uib import _HEADER
        recs = [DrawRecord(OP_QUAD, STATE_ALWAYS, FOCUS_NONE, 0, 0, 4, 4,
                           (1, 2, 3, 0x80))]
        for off, which in ((12, "tint"), (14, "tint_focus")):
            with tempfile.TemporaryDirectory() as td:
                path = os.path.join(td, "t.uib")
                write_uib(path, {"w": 320, "h": 240}, list(recs),
                          [], [], [], None)
                with open(path, "rb") as fh:
                    off_cmd = _HEADER.unpack_from(fh.read(), 0)[12]

                def bump(raw, off_cmd=off_cmd, off=off):
                    struct.pack_into("<H", raw, off_cmd + off, 999)

                self.patched(path, bump)
                with self.assertRaises(ValueError) as cm:
                    read_uib(path)
                self.assertIn("tint table", str(cm.exception))
                self.assertIn(which, str(cm.exception))

    def test_a_slot_index_past_the_table_is_named_too(self):
        require_ttf()
        # Same fault one table over. Checked separately because slots
        # resolve BOTH indices where a command resolves only `tint`,
        # so a single loop would not have covered them.
        from ps2ui_bake.uib import _HEADER
        ir = TestDynamicText().slot_ir()
        f = Flattener(ir, font_paths())
        f.run()
        for off, which in ((22, "tint_base"), (24, "tint_focus")):
            with tempfile.TemporaryDirectory() as td:
                path = os.path.join(td, "t.uib")
                write_uib(path, ir["canvas"], f.records, f.textures, f.cluts,
                          f.focus_nodes, None, fonts=f.fonts, slots=f.slots,
                          screens=f.screens)
                with open(path, "rb") as fh:
                    off_slot = _HEADER.unpack_from(fh.read(), 0)[20]

                def bump(raw, off_slot=off_slot, off=off):
                    struct.pack_into("<H", raw, off_slot + off, 999)

                self.patched(path, bump)
                with self.assertRaises(ValueError) as cm:
                    read_uib(path)
                self.assertIn("tint table", str(cm.exception))
                self.assertIn(which, str(cm.exception))

    def test_the_writer_does_not_claim_role_keying(self):
        # It keys on the resolved colour, so it must not set the bit
        # that says otherwise -- the runtime would then accept a second
        # theme that cannot be correct.
        recs = [DrawRecord(OP_QUAD, STATE_ALWAYS, FOCUS_NONE, 0, 0, 4, 4,
                           (1, 2, 3, 0x80))]
        u = self.write(recs)
        self.assertFalse(u.feature_flags & FEAT_ROLE_TINTS)

    def test_more_than_one_theme_without_the_bit_is_refused(self):
        # The reader owes the same refusal as ps2ui_load. Patched by
        # hand because no writer can produce this yet, which is exactly
        # why the check has to build it.
        recs = [DrawRecord(OP_QUAD, STATE_ALWAYS, FOCUS_NONE, 0, 0, 4, 4,
                           (1, 2, 3, 0x80))]
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "t.uib")
            write_uib(path, {"w": 320, "h": 240}, recs, [], [], [], None)
            with open(path, "rb") as fh:
                raw = bytearray(fh.read())
            # n_theme, counted from the END of the header: it is
            # followed only by its pad and the two aspect fields, so
            # this survives a field being added ahead of it. A
            # positional index from the front did not -- the first
            # version of this line pointed at n_tint.
            fields = list(_HEADER.unpack_from(raw, 0))
            fields[-4] = 2
            _HEADER.pack_into(raw, 0, *fields)
            struct.pack_into("<I", raw, 48, 0)          # zero the crc
            struct.pack_into("<I", raw, 48,
                             zlib.crc32(bytes(raw)) & 0xFFFFFFFF)
            with open(path, "wb") as fh:
                fh.write(bytes(raw))
            with self.assertRaises(ValueError) as cm:
                read_uib(path)
            self.assertIn("FEAT_ROLE_TINTS", str(cm.exception))


class TestSlotSpacing(unittest.TestCase):
    """Letter-spacing travels with the slot (feature bit 2). The two
    former pad bytes carry it, so the stride is unchanged and the bit is
    what makes the field loud rather than a version bump."""

    def bake(self, spacing):
        ir = TestDynamicText().slot_ir()
        if spacing:
            ir["slots"][0]["letterSpacing"] = spacing
        f = Flattener(ir, font_paths())
        f.run()
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "t.uib")
            write_uib(path, ir["canvas"], f.records, f.textures, f.cluts,
                      f.focus_nodes, None, fonts=f.fonts, slots=f.slots,
                      screens=f.screens)
            return read_uib(path)

    def test_the_stride_moved_and_spacing_moved_with_it(self):
        # It DID move at v7: 32 -> 28. Unlike the command, the slot
        # entry carried no padding, so replacing color_base[4] and
        # color_focus[4] with two u16 indices freed four real bytes per
        # slot. letter_spacing is still the last field, which is what
        # the writer's feature-bit check now indexes from.
        self.assertEqual(_SLOT.size, 28)

    def test_spacing_round_trips_and_declares_itself(self):
        require_ttf()
        u = self.bake(3)
        self.assertEqual(u.slots[0]["letter_spacing"], 3)
        self.assertEqual(u.feature_flags & FEAT_SLOT_SPACING,
                         FEAT_SLOT_SPACING)

    def test_zero_spacing_means_what_the_pad_always_meant(self):
        require_ttf()
        # Every writer before the field wrote zeros there, so a blob
        # with no spacing anywhere must not claim the feature.
        u = self.bake(0)
        self.assertEqual(u.slots[0]["letter_spacing"], 0)
        self.assertEqual(u.feature_flags & FEAT_SLOT_SPACING, 0)

    def test_negative_spacing_survives(self):
        require_ttf()
        # CSS letter-spacing may be negative; the field is signed.
        u = self.bake(-1)
        self.assertEqual(u.slots[0]["letter_spacing"], -1)

    def test_out_of_range_spacing_is_refused_by_name(self):
        require_ttf()
        # The i16 boundary used to surface as a bare struct.error deep
        # in the packer; it must be an error naming the slot instead.
        ir = TestDynamicText().slot_ir()
        ir["slots"][0]["letterSpacing"] = 40000
        f = Flattener(ir, font_paths())
        with self.assertRaisesRegex(ValueError, r'slot "title".*i16'):
            f.run()
        ir["slots"][0]["letterSpacing"] = 32767  # the fence itself fits
        Flattener(ir, font_paths()).run()


class TestDisplayAspect(unittest.TestCase):
    """Widescreen: the framebuffer is not what the panel shows."""

    def bake(self, aspect, canvas=(640, 448)):
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "t.uib")
            write_uib(path, {"w": canvas[0], "h": canvas[1]}, [], [], [], [],
                      None, (), (), None, aspect)
            return read_uib(path)

    def test_aspect_round_trips(self):
        self.assertEqual(self.bake((16, 9)).display_aspect, (16, 9))
        self.assertEqual(self.bake((4, 3)).display_aspect, (4, 3))

    def test_display_size_is_derived_from_height(self):
        self.assertEqual(preview.display_size(self.bake((4, 3))), (597, 448))
        self.assertEqual(preview.display_size(self.bake((16, 9))), (796, 448))
        self.assertEqual(
            preview.display_size(self.bake((16, 9), canvas=(640, 512))), (910, 512))

    def test_display_space_resamples_only_when_needed(self):
        uib43 = self.bake((4, 3))
        img = Image.new("RGBA", (640, 448), (0, 0, 0, 255))
        self.assertEqual(preview.to_display_space(img, uib43).size, (597, 448))
        # A square-pixel target leaves the image alone.
        square = self.bake((10, 7))   # 640x448 is exactly 10:7
        self.assertEqual(preview.to_display_space(img, square).size, (640, 448))

    def test_default_is_four_three(self):
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "t.uib")
            write_uib(path, {"w": 640, "h": 448}, [], [], [], [], None)
            self.assertEqual(read_uib(path).display_aspect, (4, 3))


class TestPreview(unittest.TestCase):
    def bake(self, commands, **kw):
        ir = tiny_ir(commands, **kw)
        f = Flattener(ir, font_paths())
        f.run()
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "t.uib")
            initial = None
            if ir["focus"]["initial"] is not None:
                initial = f.focus_index.get(ir["focus"]["initial"])
            write_uib(path, ir["canvas"], f.records, f.textures, f.cluts,
                      ir["focus"]["nodes"], initial)
            return read_uib(path)

    def rect_cmd(self, **over):
        base = {
            "op": "rect", "x": 10, "y": 10, "w": 50, "h": 50,
            "fill": [200, 30, 30, 255], "borderWidth": 0, "borderColor": None,
            "radius": 0, "state": "always", "focusId": None,
        }
        base.update(over)
        return base

    def test_opaque_fill_lands_on_canvas(self):
        img = preview.render(self.bake([self.rect_cmd()]))
        self.assertEqual(img.getpixel((30, 30)), (200, 30, 30, 255))

    def test_translucent_fill_blends_in_css_domain(self):
        img = preview.render(
            self.bake([self.rect_cmd(fill=[255, 255, 255, 128])]),
            background=(0, 0, 0, 255),
        )
        r = img.getpixel((30, 30))[0]
        # 128/255 white over black through the GS 0..128 domain and back:
        # a small round-trip error is expected, gross errors (the 0xFF-
        # opaque bug would give 255) are not.
        self.assertTrue(124 <= r <= 132, f"got {r}")

    def test_scissor_clips_children(self):
        cmds = [
            {"op": "scissor_push", "x": 0, "y": 0, "w": 20, "h": 20,
             "state": "always", "focusId": None},
            self.rect_cmd(x=0, y=0, w=100, h=100, fill=[0, 255, 0, 255]),
            {"op": "scissor_pop", "state": "always", "focusId": None},
        ]
        img = preview.render(self.bake(cmds), background=(0, 0, 0, 255))
        self.assertEqual(img.getpixel((10, 10)), (0, 255, 0, 255))
        self.assertEqual(img.getpixel((30, 30)), (0, 0, 0, 255))

    def test_focus_state_filtering(self):
        nodes = [{"id": 1, "name": "n", "rect": [0, 0, 10, 10],
                  "up": None, "down": None, "left": None, "right": None}]
        cmds = [
            self.rect_cmd(state="unfocused", focusId=1, fill=[10, 10, 10, 255]),
            self.rect_cmd(state="focused", focusId=1, fill=[250, 250, 250, 255]),
        ]
        uib = self.bake(cmds, focus_nodes=nodes, initial=1)
        focused = preview.render(uib, focus_current=0)
        unfocused = preview.render(uib, focus_current=FOCUS_NONE)
        self.assertEqual(focused.getpixel((30, 30)), (250, 250, 250, 255))
        self.assertEqual(unfocused.getpixel((30, 30)), (10, 10, 10, 255))

    def test_modulate_round_trip_preserves_color(self):
        # A rounded rect goes: CSS fill -> patch texels (GS alpha) ->
        # identity modulate tint (0x80s) -> preview. The center pixel
        # must come back as the authored color, proving the tint path
        # divides by 128, not 255 (backlog B1).
        img = preview.render(
            self.bake([self.rect_cmd(radius=6, fill=[200, 30, 30, 255])]),
            background=(0, 0, 0, 255),
        )
        r, g, b, _ = img.getpixel((35, 35))
        self.assertTrue(abs(r - 200) <= 3 and abs(g - 30) <= 3 and abs(b - 30) <= 3,
                        f"got {(r, g, b)}")

    def test_unbalanced_scissors_rejected(self):
        cmds = [{"op": "scissor_push", "x": 0, "y": 0, "w": 5, "h": 5,
                 "state": "always", "focusId": None}]
        with self.assertRaises(ValueError):
            preview.render(self.bake(cmds))

    def test_montage_has_one_tile_per_focusable(self):
        nodes = [
            {"id": i, "name": f"n{i}", "rect": [0, 0, 5, 5],
             "up": None, "down": None, "left": None, "right": None}
            for i in (1, 2, 3)
        ]
        uib = self.bake([self.rect_cmd()], focus_nodes=nodes, initial=1)
        sheet = preview.montage(uib, columns=2, gap=4)
        # 3 states in 2 columns -> 2 rows
        self.assertEqual(sheet.width, 2 * 320 + 3 * 4)
        self.assertEqual(sheet.height, 2 * 240 + 3 * 4)


if __name__ == "__main__":
    unittest.main()


class TestCheck(unittest.TestCase):
    """ps2ui-check (backlog F22).

    Each test builds a blob that violates exactly one invariant and
    asserts the check fires. A validator nobody has watched fail is a
    validator that reports PASS on everything.
    """

    def build(self, records, **kw):
        from ps2ui_bake.check import check_blob
        kw.setdefault("textures", [])
        kw.setdefault("cluts", [])
        kw.setdefault("nodes", [])
        kw.setdefault("initial", None)
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "t.uib")
            write_uib(path, {"w": 320, "h": 240}, list(records),
                      list(kw["textures"]), list(kw["cluts"]),
                      list(kw["nodes"]), kw["initial"],
                      fonts=list(kw.get("fonts", ())),
                      slots=list(kw.get("slots", ())),
                      screens=kw.get("screens"))
            return check_blob(read_uib(path),
                              allow_dead=kw.get("allow_dead", 0),
                              allow_hairline=kw.get("allow_hairline", 0))

    def failures(self, report):
        return [label for ok, _sev, label in report.results if not ok]

    def quad(self, **kw):
        d = dict(op=OP_QUAD, state=STATE_ALWAYS, focus=FOCUS_NONE,
                 x=0, y=0, w=10, h=10, rgba=(1, 2, 3, 0x80))
        d.update(kw)
        return DrawRecord(d["op"], d["state"], d["focus"], d["x"], d["y"],
                          d["w"], d["h"], d["rgba"])

    def test_a_plain_blob_passes_everything(self):
        rep = self.build([self.quad()])
        self.assertEqual(self.failures(rep), [])
        self.assertEqual(rep.errors, 0)

    def test_alpha_above_the_gs_domain_is_an_error(self):
        # B1's failure shape: legal in CSS, twice as opaque on console.
        rep = self.build([self.quad(rgba=(1, 2, 3, 0xFF))])
        self.assertEqual(rep.errors, 1)
        self.assertTrue(any("0-128 domain" in f for f in self.failures(rep)))

    def test_texquad_naming_a_missing_texture_is_an_error(self):
        rec = DrawRecord(OP_TEXQUAD, STATE_ALWAYS, FOCUS_NONE, 0, 0, 8, 8,
                         (0x80, 0x80, 0x80, 0x80), 7, 0, 0, 8, 8)
        rep = self.build([rec])
        self.assertTrue(any("real texture" in f for f in self.failures(rep)))

    def test_unbalanced_scissor_is_an_error(self):
        rep = self.build([
            DrawRecord(OP_SCISSOR_PUSH, STATE_ALWAYS, FOCUS_NONE,
                       0, 0, 100, 100, (0, 0, 0, 0)),
            self.quad(),
        ])
        self.assertTrue(any("scissor" in f and "left open" in f
                            for f in self.failures(rep)))

    def test_scissor_underflow_is_an_error(self):
        rep = self.build([
            DrawRecord(OP_SCISSOR_POP, STATE_ALWAYS, FOCUS_NONE,
                       0, 0, 0, 0, (0, 0, 0, 0)),
        ])
        self.assertTrue(any("underflow" in f for f in self.failures(rep)))

    def test_focus_dependent_command_without_a_focus_index_is_an_error(self):
        rep = self.build([self.quad(state=STATE_FOCUSED)])
        self.assertTrue(any("names a focus node" in f
                            for f in self.failures(rep)))

    def test_quad_outside_its_scissor_is_a_warning_not_an_error(self):
        # Real and common: a nowrap run inside overflow:hidden bakes the
        # glyphs past the edge and lets the GS clip them.
        rep = self.build([
            DrawRecord(OP_SCISSOR_PUSH, STATE_ALWAYS, FOCUS_NONE,
                       0, 0, 50, 50, (0, 0, 0, 0)),
            self.quad(x=200, y=0),
            DrawRecord(OP_SCISSOR_POP, STATE_ALWAYS, FOCUS_NONE,
                       0, 0, 0, 0, (0, 0, 0, 0)),
        ])
        self.assertEqual(rep.errors, 0)
        self.assertTrue(any("never" not in f and "for nothing" in f
                            for f in self.failures(rep)))

    def test_quad_inside_its_scissor_is_not_flagged(self):
        rep = self.build([
            DrawRecord(OP_SCISSOR_PUSH, STATE_ALWAYS, FOCUS_NONE,
                       0, 0, 50, 50, (0, 0, 0, 0)),
            self.quad(x=10, y=10),
            DrawRecord(OP_SCISSOR_POP, STATE_ALWAYS, FOCUS_NONE,
                       0, 0, 0, 0, (0, 0, 0, 0)),
        ])
        self.assertEqual(self.failures(rep), [])

    def test_hairline_quad_is_a_warning(self):
        rep = self.build([self.quad(h=1)])
        self.assertEqual(rep.errors, 0)
        self.assertEqual(rep.warnings, 1)
        self.assertTrue(any("shimmer" in f for f in self.failures(rep)))

    def test_a_declared_hairline_is_not_a_warning(self):
        # Same argument as --allow-dead: a 1px quad is usually an
        # accident and sometimes the instrument. The test card's edge
        # rules and its interlace pair ARE the shimmer bring-up step 8
        # measures, and a blob cannot say so about itself.
        rep = self.build([self.quad(h=1), self.quad(w=1, y=20)],
                         allow_hairline=2)
        self.assertEqual(rep.warnings, 0)

    def test_fewer_hairlines_than_declared_warns(self):
        # The direction the first version could not see. --allow-hairline
        # named specific instruments -- the card's four edge rules and
        # the step 8 thin rule -- and accepted "at most N", so deleting
        # one left the check reporting 4 of 5 declared and passing. The
        # flag exists to assert those quads are present; a ceiling
        # cannot.
        rep = self.build([self.quad(h=1)], allow_hairline=2)
        self.assertEqual(rep.warnings, 1)
        self.assertTrue(any("is gone" in f for f in self.failures(rep)))

    def test_fewer_dead_commands_than_declared_warns(self):
        # Same fix on the flag that shipped the pattern first, so a
        # third flag cannot inherit the ceiling instead of the fix.
        rep = self.build([self.quad()], allow_dead=1)
        self.assertEqual(rep.warnings, 1)
        self.assertTrue(any("is gone" in f for f in self.failures(rep)))

    def test_one_more_hairline_than_declared_still_warns(self):
        # The half that makes --allow-hairline a declaration rather than
        # an off switch. Without this the flag could be implemented as
        # "skip the check" and nothing here would notice.
        rep = self.build([self.quad(h=1), self.quad(w=1, y=20)],
                         allow_hairline=1)
        self.assertEqual(rep.warnings, 1)
        self.assertTrue(any("1 1px quad(s) will shimmer" in f
                            for f in self.failures(rep)))

    def test_unreachable_focusable_is_an_error(self):
        # Two nodes, no edges between them: the D-pad can never reach the
        # second one, and on console that is a control that does nothing.
        nodes = [
            {"id": 1, "name": "a", "rect": [0, 0, 40, 40],
             "up": None, "down": None, "left": None, "right": None},
            {"id": 2, "name": "b", "rect": [80, 0, 40, 40],
             "up": None, "down": None, "left": None, "right": None},
        ]
        rep = self.build([self.quad()], nodes=nodes, initial=0)
        self.assertTrue(any("stranded" in f for f in self.failures(rep)))

    def test_check_cli_exit_codes(self):
        from ps2ui_bake.check import main
        with tempfile.TemporaryDirectory() as td:
            good = os.path.join(td, "good.uib")
            write_uib(good, {"w": 320, "h": 240}, [self.quad()], [], [], [], None)
            bad = os.path.join(td, "bad.uib")
            write_uib(bad, {"w": 320, "h": 240},
                      [self.quad(rgba=(1, 2, 3, 0xFF))], [], [], [], None)
            hair = os.path.join(td, "hair.uib")
            write_uib(hair, {"w": 320, "h": 240}, [self.quad(h=1)], [], [], [], None)

            buf = io.StringIO()
            stdout, sys.stdout = sys.stdout, buf
            try:
                self.assertEqual(main([good]), 0)
                self.assertEqual(main([bad]), 1)
                # A warning alone passes, and fails under --strict.
                self.assertEqual(main([hair]), 0)
                self.assertEqual(main([hair, "--strict"]), 1)
            finally:
                sys.stdout = stdout
            self.assertIn("PASS", buf.getvalue())

    def test_check_rejects_a_corrupt_file_without_traceback(self):
        from ps2ui_bake.check import main
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "junk.uib")
            with open(path, "wb") as fh:
                fh.write(b"not a uib at all, not even close")
            err = io.StringIO()
            stderr, sys.stderr = sys.stderr, err
            try:
                self.assertEqual(main([path]), 2)
            finally:
                sys.stderr = stderr
            self.assertIn("ps2ui-check", err.getvalue())

    def test_the_shipped_examples_pass(self):
        # The blobs in the repo are the real regression corpus; a check
        # that only ever sees synthetic input drifts from what the baker
        # actually emits.
        from ps2ui_bake.check import check_blob
        root = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "..", "..", "..")
        seen = 0
        rels = ("examples/memcard/build/ui.uib",
                "examples/channel6/build/ui.uib")
        for rel in rels:
            path = os.path.normpath(os.path.join(root, rel))
            if not os.path.exists(path):
                continue  # not built in this checkout
            seen += 1
            rep = check_blob(read_uib(path))
            self.assertEqual(rep.errors, 0, f"{rel}: {self.failures(rep)}")
        # HALF THE CORPUS IS NOT THE CORPUS. seen == 1 means one blob
        # was built and the other was not, and the loop above would
        # check half the regression set and report OK with nothing
        # said -- the same shape as everything else this change is
        # about, one notch smaller. CI never hits it (the baker step
        # runs before both example builds, so seen is always 0); a
        # developer who has built memcard and not channel6 does.
        self.assertIn(seen, (0, len(rels)),
                      f"{seen} of {len(rels)} example blobs are built: this "
                      "test covers the corpus or it covers none of it, "
                      "never part of it")
        if seen == 0:
            # Not the treatment the arena cross-check got. That one
            # could build what it needed in a second; these blobs need
            # node, the fonts and the asset pipeline, and the only
            # order that would make them exist here runs the
            # integration builds before the unit suite -- so a broken
            # baker would be reported by a shell script instead of by
            # this file. ci.yml's "Validate every blob against the
            # runtime's assumptions" step covers these exact bytes with
            # ps2ui-check by name, and DOES gate. Say that here so the
            # skip reads as a division of labour rather than a hole.
            #
            # THE DISTINCTION IS NOW LOAD-BEARING, because the S7 tests
            # above carried a skip message of the same shape that was
            # NOT true, and those four never ran in CI at all.
            #
            # The test to apply is NOT whether the cited step runs
            # first. This skip cites a step 116 lines below the one
            # that runs this suite, and is fine; the S7 four cited a
            # step 96 lines below, and were not. The difference is what
            # the cited step DOES: that one asserts this same property
            # over these same bytes, by name, and gates. Theirs merely
            # built a fixture, so for them ordering was everything and
            # the coverage was zero, not late.
            #
            # Written out because the first version of this reasoning,
            # and the rule in docs/method.md it came from, both got it
            # wrong in the ordering direction -- which would have
            # condemned this skip and blessed a badly-ordered one.
            self.skipTest("examples not built in this checkout; ci.yml "
                          "gates these blobs with ps2ui-check after the "
                          "example builds")


class TestDeadGeometryTrim(unittest.TestCase):
    """F24: draw records that cannot produce a pixel are dropped.

    The safety argument is the whole feature: removing a command that
    could never draw cannot change the image. These assert both halves —
    that it goes, and that nothing else moves.
    """

    def flatten(self, commands, canvas=None):
        ir = tiny_ir(commands)
        if canvas:
            ir["canvas"].update(canvas)
        f = Flattener(ir, font_paths())
        f.run()
        return f

    def rect(self, x, y, w, h, fill=(0x20, 0x30, 0x40, 255)):
        return {"op": "rect", "x": x, "y": y, "w": w, "h": h, "fill": list(fill),
                "radius": 0, "borderWidth": 0, "borderColor": None,
                "state": "always", "focusId": None}

    def test_quad_outside_its_scissor_is_dropped(self):
        f = self.flatten([
            {"op": "scissor_push", "x": 0, "y": 0, "w": 50, "h": 50},
            self.rect(10, 10, 20, 20),    # inside
            self.rect(200, 10, 20, 20),   # past the clip's right edge
            {"op": "scissor_pop"},
        ])
        quads = [r for r in f.records if r.op == OP_QUAD]
        self.assertEqual(len(quads), 1)
        self.assertEqual(f.dropped, 1)

    def test_quad_outside_the_canvas_is_dropped_without_any_scissor(self):
        f = self.flatten([self.rect(10, 10, 20, 20), self.rect(700, 10, 20, 20)])
        self.assertEqual(len([r for r in f.records if r.op == OP_QUAD]), 1)
        self.assertEqual(f.dropped, 1)

    def test_scissor_records_are_never_dropped(self):
        # Balance is a contract the runtime relies on: an empty clip
        # still has to be popped.
        f = self.flatten([
            {"op": "scissor_push", "x": 900, "y": 900, "w": 10, "h": 10},
            self.rect(10, 10, 20, 20),
            {"op": "scissor_pop"},
        ])
        ops = [r.op for r in f.records]
        self.assertEqual(ops.count(OP_SCISSOR_PUSH), 1)
        self.assertEqual(ops.count(OP_SCISSOR_POP), 1)
        self.assertEqual(f.dropped, 1)

    def test_a_partially_visible_quad_survives(self):
        # Clipping is the GS's job; only the wholly invisible go.
        f = self.flatten([
            {"op": "scissor_push", "x": 0, "y": 0, "w": 50, "h": 50},
            self.rect(40, 40, 40, 40),
            {"op": "scissor_pop"},
        ])
        self.assertEqual(f.dropped, 0)
        self.assertEqual(len([r for r in f.records if r.op == OP_QUAD]), 1)

    def test_nested_scissors_intersect(self):
        # Inner clip is the intersection, so a quad inside the outer but
        # outside the inner still cannot draw.
        f = self.flatten([
            {"op": "scissor_push", "x": 0, "y": 0, "w": 200, "h": 200},
            {"op": "scissor_push", "x": 0, "y": 0, "w": 50, "h": 50},
            self.rect(100, 10, 20, 20),
            {"op": "scissor_pop"},
            {"op": "scissor_pop"},
        ])
        self.assertEqual(f.dropped, 1)

    def test_trimming_cannot_change_the_rendered_image(self):
        # The property that makes this safe, asserted against the
        # previewer rather than argued.
        cmds = [
            {"op": "scissor_push", "x": 0, "y": 0, "w": 60, "h": 60},
            self.rect(5, 5, 20, 20, (0xC0, 0x20, 0x20, 255)),
            self.rect(300, 5, 20, 20, (0x20, 0xC0, 0x20, 255)),  # dead
            {"op": "scissor_pop"},
        ]
        with tempfile.TemporaryDirectory() as td:
            f = self.flatten(cmds)
            self.assertEqual(f.dropped, 1)
            trimmed = os.path.join(td, "trimmed.uib")
            write_uib(trimmed, {"w": 320, "h": 240}, f.records,
                      f.textures, f.cluts, [], None)
            after = preview.render(read_uib(trimmed), background=(0, 0, 0, 255))

            # Same blob with the dead record put back by hand.
            f2 = self.flatten(cmds)
            f2.records.insert(2, DrawRecord(
                OP_QUAD, STATE_ALWAYS, FOCUS_NONE, 300, 5, 20, 20,
                (0x20, 0xC0, 0x20, 0x80)))
            untrimmed = os.path.join(td, "untrimmed.uib")
            write_uib(untrimmed, {"w": 320, "h": 240}, f2.records,
                      f2.textures, f2.cluts, [], None)
            before = preview.render(read_uib(untrimmed), background=(0, 0, 0, 255))

        self.assertEqual(list(before.getdata()), list(after.getdata()))

    def test_a_texquad_glyph_tail_is_trimmed(self):
        require_ttf()
        # The case the whole pass exists for: nowrap text inside
        # overflow:hidden bakes every glyph and lets the GS clip.
        # Every other test here uses solid rects.
        ir = tiny_ir([
            {"op": "scissor_push", "x": 0, "y": 0, "w": 40, "h": 30},
            {"op": "text", "x": 4, "y": 4, "text": "wide enough to overflow",
             "size": 16, "weight": 400, "color": [255, 255, 255, 255],
             "state": "always", "focusId": None},
            {"op": "scissor_pop"},
        ])
        f = Flattener(ir, font_paths())
        f.run()
        self.assertGreater(f.dropped, 0, "glyphs past the clip should go")
        self.assertTrue(all(r.op != OP_TEXQUAD or r.x < 40 for r in f.records))

    def test_an_empty_clip_drops_everything_under_it(self):
        # Nested scissors that do not overlap: the intersection is zero
        # wide, and a quad straddling its left edge passes all four edge
        # tests. Only an area check catches it.
        f = self.flatten([
            {"op": "scissor_push", "x": 0, "y": 0, "w": 100, "h": 100},
            {"op": "scissor_push", "x": 100, "y": 0, "w": 50, "h": 100},
            self.rect(90, 10, 20, 20),
            {"op": "scissor_pop"},
            {"op": "scissor_pop"},
        ])
        self.assertEqual(f.dropped, 1)

    def test_screen_ranges_survive_trimming(self):
        # cmd_count is computed after the trim, so a dropped record must
        # not shift a later screen's range.
        a = tiny_ir([self.rect(10, 10, 20, 20), self.rect(900, 10, 20, 20)])
        b = tiny_ir([self.rect(30, 30, 20, 20)])
        f = Flattener(a, font_paths())
        f.run_screens([("one", a), ("two", b)])
        one, two = f.screens
        self.assertEqual(one["cmd_first"], 0)
        self.assertEqual(two["cmd_first"], one["cmd_first"] + one["cmd_count"])
        self.assertEqual(two["cmd_first"] + two["cmd_count"], len(f.records))
        self.assertEqual(f.dropped, 1)

    def test_two_screens_may_not_share_a_slot_name(self):
        require_ttf()
        # The runtime resolves a slot name over the WHOLE file and takes
        # the first match, so a duplicate makes one of the two
        # unreachable -- and an unreachable slot shows its placeholder
        # forever, which looks like a driver that stopped updating.
        # paint.js only checks within one document, so nothing caught
        # this until the per-screen readout wanted "telem" on all six.
        def with_slot(name):
            ir = tiny_ir([])
            ir["slots"] = [{
                "name": name, "placeholder": "x",
                "x": 0, "textY": 10, "w": 100,
                "size": 14, "weight": 400, "lineHeight": 18,
                "align": "left", "ellipsis": False, "capacity": 8,
                "focusId": None,
                "colorBase": [200, 200, 200, 255],
                "colorFocus": [255, 255, 255, 255],
            }]
            return ir

        a, b = with_slot("telem"), with_slot("telem")
        f = Flattener(a, font_paths())
        with self.assertRaises(ValueError) as cm:
            f.run_screens([("one", a), ("two", b)])
        self.assertIn("telem", str(cm.exception))
        self.assertIn("one", str(cm.exception))
        self.assertIn("two", str(cm.exception))

        # And the same two screens with screen-scoped names bake fine,
        # so the check is about collision and not about slots at all.
        a, b = with_slot("one-telem"), with_slot("two-telem")
        f = Flattener(a, font_paths())
        f.run_screens([("one", a), ("two", b)])
        self.assertEqual([s["name"] for s in f.slots],
                         ["one-telem", "two-telem"])

    def test_the_validator_and_the_baker_share_one_clip_model(self):
        # They used to carry two copies that already differed by a term.
        from ps2ui_bake import clip as clip_mod
        from ps2ui_bake import check as check_mod
        self.assertIs(check_mod.clip_mod, clip_mod)


class TestScissorDepth(unittest.TestCase):
    """PS2UI_MAX_SCISSOR_DEPTH, which nothing used to check.

    caps.py's regex always matched the constant, but FALLBACK did not
    list the key, so caps.update dropped it and no stage knew the limit
    existed. The runtime meanwhile refused pushes past its fixed stack
    while still popping them, which left the stack a level shallow and
    every later clip in the frame wrong.
    """

    def records(self, depth):
        from ps2ui_bake.quads import DrawRecord, OP_SCISSOR_PUSH, OP_SCISSOR_POP
        recs = []
        for _ in range(depth):
            recs.append(DrawRecord(OP_SCISSOR_PUSH, STATE_ALWAYS, FOCUS_NONE,
                                   0, 0, 100, 100, (0, 0, 0, 0)))
        for _ in range(depth):
            recs.append(DrawRecord(OP_SCISSOR_POP, STATE_ALWAYS, FOCUS_NONE,
                                   0, 0, 0, 0, (0, 0, 0, 0)))
        return recs

    def test_the_constant_is_actually_parsed(self):
        from ps2ui_bake import caps
        self.assertIn("PS2UI_MAX_SCISSOR_DEPTH", caps.parse_header())
        self.assertEqual(caps.parse_header()["PS2UI_MAX_SCISSOR_DEPTH"],
                         caps.FALLBACK["PS2UI_MAX_SCISSOR_DEPTH"])

    def test_peak_depth_is_measured_not_guessed(self):
        from ps2ui_bake import caps
        self.assertEqual(caps.max_scissor_depth(self.records(3)), 3)
        # Sibling clips nest to 1, not 2: the pop returns to the parent.
        self.assertEqual(
            caps.max_scissor_depth(self.records(1) + self.records(1)), 1)

    def test_a_blob_at_the_limit_is_refused_by_the_bake(self):
        from ps2ui_bake import caps
        limit = caps.parse_header()["PS2UI_MAX_SCISSOR_DEPTH"]
        errors, _ = caps.check([], [], [], [{"name": "s"}],
                               records=self.records(limit))
        self.assertTrue(any("scissor nesting" in e for e in errors))
        self.assertTrue(any("PS2UI_MAX_SCISSOR_DEPTH" in e for e in errors))

    def test_one_level_below_the_limit_passes(self):
        # The runtime's guard is `depth + 1 >= MAX`, so MAX - 1 is the
        # last usable level and must not be refused.
        from ps2ui_bake import caps
        limit = caps.parse_header()["PS2UI_MAX_SCISSOR_DEPTH"]
        errors, _ = caps.check([], [], [], [{"name": "s"}],
                               records=self.records(limit - 1))
        self.assertEqual([e for e in errors if "scissor" in e], [])


class TestConsoleScriptVersions(unittest.TestCase):
    """`--version`, and that it is not a second number."""

    def test_every_console_script_answers_version(self):
        # THE VERSION HAS TO REACH A PERSON. Every claim in the
        # repository agrees with every other one
        # (tools/check-versions.py), and for a long while none of them
        # was reachable from the command someone actually runs -- the
        # one place a stranger filing a bug would look.
        #
        # Adding the flag creates the obvious next hazard: a literal in
        # the CLI that starts out right and drifts. So this asserts the
        # OUTPUT against ps2ui_bake.__version__ and, below, that no CLI
        # spells a version out at all.
        import io
        import contextlib
        from ps2ui_bake import __version__, cli, check, fontgen
        from ps2ui_bake import ps2ui as front
        for mod, prog in ((cli, "ps2ui-bake"), (check, "ps2ui-check"),
                          (fontgen, "ps2ui-fontgen"), (front, "ps2ui")):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                try:
                    rc = mod.main(["--version"])
                except SystemExit as e:      # argparse's action="version"
                    rc = e.code
            self.assertEqual(rc, 0, prog)
            self.assertEqual(buf.getvalue().strip(),
                             "%s %s" % (prog, __version__), prog)

    def test_no_console_script_spells_a_version_out(self):
        # A literal that HAPPENS to match today passes the test above
        # and drifts tomorrow. __init__.py is the one place a version is
        # written in this package; every other module reads it.
        import os
        import re
        pkg = os.path.dirname(os.path.abspath(
            __import__("ps2ui_bake").__file__))
        for name in sorted(os.listdir(pkg)):
            if not name.endswith(".py") or name == "__init__.py":
                continue
            src = open(os.path.join(pkg, name), encoding="utf-8").read()
            # Code only: the docs and comments here quote real version
            # numbers on purpose (0.2.0, the format history), and a
            # scanner that flagged those would be deleted within a week.
            src = re.sub(r"#.*", "", src)
            src = re.sub(r'"""(?:.|\n)*?"""', "", src)
            # A DOTTED QUAD IS NOT A VERSION. serve.py binds
            # 127.0.0.1 and prints its URL, and the first version of
            # this flagged all three as spelled-out versions -- so the
            # boundaries below require the three parts to stand alone.
            # Loosening the scanner instead would have been the wrong
            # fix: it exists to catch a literal that drifts, and an IP
            # address is simply not one.
            found = re.findall(
                r"""["'][^"'\n]*(?<![\d.])\d+\.\d+\.\d+(?![\d.])"""
                r"""[^"'\n]*["']""", src)
            self.assertEqual(found, [], "%s spells out %s" % (name, found))


class TestNewcomerPath(unittest.TestCase):
    """What a person with pip, a TTF and no checkout actually meets.

    Every case here was found by writing docs/tutorial-uc3.md and
    running the commands from an empty directory. None of them could be
    seen from inside the repository, because the repository supplies
    exactly the two things that were missing: a fonts/ directory three
    levels above the package, and a build.sh that mkdir -p's first.
    """

    def test_the_default_font_manifest_is_a_repo_path(self):
        # Not an assertion that it is GOOD -- an assertion of what it
        # is, so the branch that handles its absence cannot be removed
        # as dead code by someone who only ever runs in a checkout.
        from ps2ui_bake.cli import default_fonts_path
        path = os.path.normpath(default_fonts_path())
        self.assertTrue(path.endswith(os.path.join("fonts", "fonts.json")))
        pkg = os.path.dirname(os.path.abspath(
            __import__("ps2ui_bake").__file__))
        self.assertFalse(
            os.path.normpath(path).startswith(os.path.normpath(pkg)),
            "the default manifest is outside the package, which is why "
            "an installed ophtml cannot find it")

    def test_a_named_manifest_that_is_absent_is_not_a_traceback(self):
        from ps2ui_bake.cli import load_font_manifest
        with self.assertRaises(FileNotFoundError) as cm:
            load_font_manifest("/nonexistent/fonts.json")
        msg = str(cm.exception)
        self.assertIn("ps2ui-fontgen", msg)
        self.assertIn("ps2ui-layout", msg)

    def test_a_home_relative_candidate_resolves_to_the_home_directory(self):
        """`~/Library/Fonts/...` is where macOS puts a user's own fonts.

        os.path.isabs("~/...") is False, so without expanduser the
        resolver joined it to the manifest's OWN directory and it could
        never match -- silently, because a candidate that does not
        exist is just the next one tried. The one spelling a Mac reader
        would reach for was the one spelling that could not work, and
        nothing said so.
        """
        from unittest import mock
        from ps2ui_bake.cli import load_font_manifest
        with tempfile.TemporaryDirectory() as home:
            face = os.path.join(home, "Library", "Fonts")
            os.makedirs(face)
            ttf = os.path.join(face, "Only.ttf")
            with open(ttf, "wb") as fh:
                fh.write(b"not a real font, and never opened here")
            man = os.path.join(home, "fonts.json")
            with open(man, "w", encoding="utf-8") as fh:
                json.dump({"regular": {"ttf": ["~/Library/Fonts/Only.ttf"],
                                       "metrics": "~/m.json"}}, fh)
            with mock.patch.dict(os.environ, {"HOME": home}):
                # expanduser reads $HOME, so this is the whole fixture.
                paths = load_font_manifest(man)
        self.assertEqual(paths["regular"]["ttf"], ttf)
        # The metrics path expands too, and for the same reason: it is
        # written by the same hand into the same file.
        self.assertEqual(paths["regular"]["metrics"],
                         os.path.join(home, "m.json"))

    def test_bake_creates_its_output_directories(self):
        # `-o build/ui.uib` into a tree with no build/ raised a bare
        # FileNotFoundError traceback. First command, first failure.
        import tempfile
        import json as _json
        from ps2ui_bake import cli
        ir = TestDynamicText().slot_ir()
        with tempfile.TemporaryDirectory() as tmp:
            src = os.path.join(tmp, "ui.json")
            with open(src, "w", encoding="utf-8") as fh:
                _json.dump(ir, fh)
            out = os.path.join(tmp, "deep", "nested", "ui.uib")
            shot = os.path.join(tmp, "other", "preview.png")
            rc = cli.main([src, "-o", out, "--preview", shot,
                           "--fonts", os.path.join(
                               FONTS, "fonts.json")])
            self.assertEqual(rc, 0)
            self.assertTrue(os.path.exists(out), "bake did not create -o's dir")
            self.assertTrue(os.path.exists(shot),
                            "bake did not create --preview's dir")

    def test_the_ir_and_the_manifest_must_mean_the_same_fonts(self):
        # ps2ui-layout and ps2ui-bake take font configuration
        # separately, so a project can compile with --font-dir one/ and
        # bake with --fonts other.json. Every glyph would then be drawn
        # at the first font's position with the second font's shape:
        # subtly wrong text on every screen, no error, and only a
        # console to see it on.
        #
        # The IR has carried the faces it was measured against since
        # v1 and the baker had never read it.
        from ps2ui_bake.cli import check_font_agreement, load_font_manifest
        paths = load_font_manifest(os.path.join(FONTS, "fonts.json"))

        agreeing = {"fonts": {"regular": {"family": "DejaVu Sans",
                                          "weight": 400},
                              "bold": {"family": "DejaVu Sans",
                                       "weight": 700}}}
        self.assertEqual(check_font_agreement(agreeing, paths), [])

        wrong_family = {"fonts": {"regular": {"family": "Liberation Sans",
                                              "weight": 400}}}
        out = check_font_agreement(wrong_family, paths)
        self.assertEqual(len(out), 1, out)
        self.assertIn("Liberation Sans", out[0])
        self.assertIn("DejaVu Sans", out[0])

        wrong_weight = {"fonts": {"bold": {"family": "DejaVu Sans",
                                           "weight": 400}}}
        self.assertEqual(len(check_font_agreement(wrong_weight, paths)), 1)

        missing_face = {"fonts": {"black": {"family": "DejaVu Sans",
                                            "weight": 900}}}
        out = check_font_agreement(missing_face, paths)
        self.assertEqual(len(out), 1, out)
        self.assertIn("'black'", out[0])

    def test_font_agreement_does_not_catch_a_same_family_rebuild(self):
        # STATED, NOT IMPLIED. Two builds of one family whose metrics
        # differ -- a re-run of fontgen over a newer TTF, or a different
        # charset -- agree on family and weight and diverge in the
        # advances. Catching that wants a digest of the tables in the
        # IR, which is a format-visible change and is not this. The
        # loud case is prevented; the quiet one is still only
        # avoidable, and a test says so rather than a comment alone.
        from ps2ui_bake.cli import check_font_agreement, load_font_manifest
        paths = load_font_manifest(os.path.join(FONTS, "fonts.json"))
        same_name = {"fonts": {"regular": {"family": "DejaVu Sans",
                                           "weight": 400}}}
        self.assertEqual(check_font_agreement(same_name, paths), [],
                         "if this starts failing, the check grew teeth "
                         "and the docs claiming otherwise are now wrong")

    def test_the_bake_actually_refuses_a_disagreeing_manifest(self):
        # THE CALL SITE, NOT THE FUNCTION. The three tests above pass
        # with the check unwired from main() -- deleting the call was
        # sabotaged and nothing failed, which is a fence that exists
        # and is not connected to anything. So this drives the CLI.
        import tempfile
        import json as _json
        from ps2ui_bake import cli
        ir = TestDynamicText().slot_ir()
        ir["fonts"] = {"regular": {"family": "Not A Real Family",
                                   "weight": 400}}
        with tempfile.TemporaryDirectory() as tmp:
            src = os.path.join(tmp, "ui.json")
            with open(src, "w", encoding="utf-8") as fh:
                _json.dump(ir, fh)
            out = os.path.join(tmp, "ui.uib")
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                rc = cli.main([src, "-o", out,
                               "--fonts", os.path.join(FONTS, "fonts.json")])
            self.assertEqual(rc, 1)
            self.assertIn("different fonts", err.getvalue())
            self.assertIn("Not A Real Family", err.getvalue())
            # And nothing was written: a blob positioned by one font and
            # drawn with another must not reach a console.
            self.assertFalse(os.path.exists(out))


class TestProjectFile(unittest.TestCase):
    """ps2ui.json: what it accepts, and what it refuses by name.

    The point of the file is that a build is one command and a
    newcomer reads four lines instead of seven invocations. That only
    holds if a key nobody reads is an error rather than a shrug --
    the same rule the layout compiler applies to `data-` attributes,
    and for the same reason: a silently ignored setting is one the
    author believes is in effect.
    """

    def write(self, tmp, data, name="ps2ui.json"):
        import json as _json
        path = os.path.join(tmp, name)
        with open(path, "w", encoding="utf-8") as fh:
            _json.dump(data, fh)
        return path

    def test_the_minimum_project_is_two_keys(self):
        from ps2ui_bake import project
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            path = self.write(tmp, {"screens": ["ui/a.html"],
                                    "css": "ui/app.css"})
            proj = project.load(path)
            self.assertEqual(len(proj.screens), 1)
            self.assertEqual(proj.screens[0].name, "a")
            # Defaults, so the file does not have to say them.
            self.assertTrue(proj.out_path.endswith(
                os.path.join("build", "ui.uib")))
            self.assertTrue(proj.preview_path("preview").endswith(
                os.path.join("build", "preview.png")))
            self.assertIsNone(proj.preview_path("montage"))
            # Every path is relative to the PROJECT, not the cwd.
            self.assertTrue(proj.screens[0].html.startswith(tmp))
            self.assertTrue(proj.screens[0].css.endswith("app.css"))

    def test_a_directory_means_the_ps2ui_json_inside_it(self):
        from ps2ui_bake import project
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            self.write(tmp, {"screens": ["a.html"], "css": "a.css"})
            self.assertEqual(len(project.load(tmp).screens), 1)

    def test_an_unknown_key_is_refused_by_name(self):
        from ps2ui_bake import project
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            path = self.write(tmp, {"screens": ["a.html"], "css": "a.css",
                                    "minfontsize": 11, "previews": "x.png"})
            with self.assertRaises(project.ProjectError) as cm:
                project.load(path)
            msg = str(cm.exception)
            self.assertIn("'minfontsize'", msg)
            self.assertIn("'previews'", msg)
            # And it lists what a project does take, so the fix is in
            # the message rather than in the source.
            self.assertIn("minFontSize", msg)

    def test_a_screen_may_be_an_object_and_its_keys_are_checked_too(self):
        from ps2ui_bake import project
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            path = self.write(tmp, {
                "css": "app.css",
                "screens": ["a.html",
                            {"html": "b.html", "focusWrap": True},
                            {"html": "c.html", "css": "other.css"}]})
            proj = project.load(path)
            self.assertFalse(proj.screens[0].focus_wrap)
            self.assertTrue(proj.screens[1].focus_wrap)
            self.assertTrue(proj.screens[2].css.endswith("other.css"))
            self.assertTrue(proj.screens[0].css.endswith("app.css"))

            bad = self.write(tmp, {"css": "app.css",
                                   "screens": [{"html": "b.html",
                                                "focuswrap": True}]},
                             name="bad.json")
            with self.assertRaises(project.ProjectError) as cm:
                project.load(bad)
            self.assertIn("focuswrap", str(cm.exception))

    def test_a_screen_with_no_stylesheet_says_both_places_to_put_one(self):
        from ps2ui_bake import project
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            path = self.write(tmp, {"screens": ["a.html"]})
            with self.assertRaises(project.ProjectError) as cm:
                project.load(path)
            self.assertIn("no stylesheet", str(cm.exception))

    def test_missing_and_malformed_projects_are_not_tracebacks(self):
        from ps2ui_bake import project
        import tempfile
        with self.assertRaises(project.ProjectError) as cm:
            project.load("/nonexistent/ps2ui.json")
        self.assertIn("screens", str(cm.exception))
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "ps2ui.json")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write("{ not json")
            with self.assertRaises(project.ProjectError) as cm:
                project.load(path)
            self.assertIn("not valid JSON", str(cm.exception))

    def test_the_examples_are_the_acceptance_test(self):
        # The design test: if a project file cannot express the shipped
        # examples it is the wrong design, and it was written by
        # converting them. Each one must load and name the same screens
        # its build.sh used to compile by hand.
        from ps2ui_bake import project
        for name, want in (("memcard", ["library", "saves"]),
                           ("channel6", ["games", "probe"]),
                           ("opl-env", ["landing", "library", "detail",
                                        "filters", "recent", "confirm"])):
            proj = project.load(os.path.join(REPO, "examples", name))
            self.assertEqual([s.name for s in proj.screens], want, name)
            for s in proj.screens:
                self.assertTrue(os.path.exists(s.html), s.html)
                self.assertTrue(os.path.exists(s.css), s.css)

    def test_build_prints_paths_relative_to_the_project_not_the_cwd(self):
        """"Every path is relative to the project" must hold for OUTPUT.

        The first version printed the absolute path of everything it
        wrote, because it passed absolute paths to the two tools it
        drives. The tutorial caught it -- a machine-specific temp path
        is not something a document can quote -- but only because the
        tutorial happens to `cd` into its project first, which makes
        the fix a no-op there. Sabotaging the chdir passed.

        So this builds from a DIFFERENT directory, which is how every
        example's build.sh invokes it: `ps2ui build "$here/ps2ui.json"`
        from the repository root.
        """
        import tempfile
        import json as _json
        from ps2ui_bake import ps2ui as front
        with tempfile.TemporaryDirectory() as tmp:
            proj_dir = os.path.join(tmp, "browser")
            os.makedirs(os.path.join(proj_dir, "ui"))
            with open(os.path.join(proj_dir, "ui", "s.html"), "w") as fh:
                fh.write('<screen name="s"><div class="r">Hi</div></screen>')
            with open(os.path.join(proj_dir, "ui", "s.css"), "w") as fh:
                fh.write('.r { color: #fff; background: #000; }')
            with open(os.path.join(proj_dir, "ps2ui.json"), "w") as fh:
                _json.dump({"screens": ["ui/s.html"], "css": "ui/s.css",
                            "fonts": os.path.join(FONTS, "fonts.json")}, fh)

            here = os.getcwd()
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                rc = front.main(["build", os.path.join(proj_dir,
                                                       "ps2ui.json")])
            out = err.getvalue()
            self.assertEqual(rc, 0, out)
            # The cwd is restored: a tool that leaves you somewhere else
            # breaks every caller that runs anything after it.
            self.assertEqual(os.getcwd(), here)
            self.assertIn("-> build/ui.uib", out)
            self.assertIn("preview -> build/preview.png", out)
            self.assertNotIn(tmp, out,
                             "ps2ui printed an absolute path; every path "
                             "is supposed to be relative to the project")
            self.assertTrue(os.path.exists(
                os.path.join(proj_dir, "build", "ui.uib")))

    # ------------------------------------------------------ ps2ui dev

    @contextlib.contextmanager
    def captured_fd2(self):
        """Capture fd 2, not sys.stderr.

        `ps2ui dev` is entirely a subprocess, and contextlib's
        redirect_stderr only rebinds Python's sys.stderr -- a child
        writes to the real fd 2 and the assertion sees an empty string.
        The first version of this test read that emptiness as "no
        absolute paths were printed", which is a check that passes
        because it looked at nothing.
        """
        import tempfile as _tf
        sink = []
        with _tf.TemporaryFile(mode="w+") as fh:
            saved = os.dup(2)
            os.dup2(fh.fileno(), 2)
            try:
                yield sink
            finally:
                os.dup2(saved, 2)
                os.close(saved)
                fh.seek(0)
                sink.append(fh.read())

    def dev_project(self, tmp, screens, fonts=True):
        """A project on disk, with real HTML/CSS the compiler accepts."""
        import json as _json
        os.makedirs(os.path.join(tmp, "ui"), exist_ok=True)
        for name in screens:
            with open(os.path.join(tmp, "ui", name + ".html"), "w") as fh:
                fh.write('<screen name="%s"><div class="r">Hi</div></screen>'
                         % name)
        with open(os.path.join(tmp, "ui", "app.css"), "w") as fh:
            fh.write('.r { color: #fff; background: #000; '
                     'width: 200px; height: 60px; }')
        data = {"screens": ["ui/%s.html" % n for n in screens],
                "css": "ui/app.css"}
        if fonts:
            data["fonts"] = os.path.join(FONTS, "fonts.json")
        path = os.path.join(tmp, "ps2ui.json")
        with open(path, "w") as fh:
            _json.dump(data, fh)
        return path

    def test_dev_names_every_screen_not_just_the_first(self):
        """THE REMEDY IT PRINTED DID NOT EXIST.

        `ps2ui dev` on a multi-screen project said "Name it: ps2ui dev
        --screen <first>", and the parser had no --screen at all, so the
        one thing it told you to do failed with "unrecognized
        arguments". Every example in this repository has more than one
        screen, so that was the only outcome available for any of them.

        It also named screens[0] as if it were a recommendation. The
        caller is choosing; a chooser needs the list.
        """
        from ps2ui_bake import ps2ui as front
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            path = self.dev_project(tmp, ["library", "saves", "settings"])
            # --once even though this must never reach a build. If the
            # screen check regresses, `dev` proceeds instead of erroring
            # -- and without --once it proceeds into a watch loop that
            # never returns, so the suite HANGS rather than failing.
            # A test that can hang is a test that reports nothing.
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                rc = front.main(["dev", path, "--once"])
            out = err.getvalue()
            self.assertEqual(rc, 1)
            for name in ("library", "saves", "settings"):
                self.assertIn(name, out,
                              "the error must name every screen, not one")
            self.assertIn("--screen", out)

    def test_dev_screen_selects_by_name_and_refuses_an_unknown_one(self):
        from ps2ui_bake import ps2ui as front, project
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            path = self.dev_project(tmp, ["library", "saves"])
            proj = project.load(path)
            self.assertEqual(front.pick_screen(proj, "saves").name, "saves")
            with self.assertRaises(front.ProjectError) as cm:
                front.pick_screen(proj, "nope")
            msg = str(cm.exception)
            self.assertIn("nope", msg)
            self.assertIn("library", msg)
            self.assertIn("saves", msg)

    def test_dev_one_screen_needs_no_flag(self):
        from ps2ui_bake import ps2ui as front, project
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            proj = project.load(self.dev_project(tmp, ["only"]))
            self.assertEqual(front.pick_screen(proj, None).name, "only")

    def test_dev_builds_with_a_fonts_manifest_and_stays_out_of_build(self):
        """TWO FAILURES THAT MADE `ps2ui dev` UNRUNNABLE, together.

        It appended `--fonts <manifest>` to a tool that did not accept
        the flag, so both landed in ps2ui-dev's positional list and it
        exited 2 with a bare usage dump. Every project here has a
        manifest, so the only configuration that ever reached a build
        was a single-screen project with no fonts at all.

        And it wrote into build/, where `ps2ui build` and every
        build.sh put the blob CI verifies -- clobbering ui.uib and
        preview.png, and leaving a ui.json that `ps2ui build` never
        writes, since it names intermediates after the screen.
        """
        from ps2ui_bake import ps2ui as front
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            path = self.dev_project(tmp, ["library", "saves"])
            build = os.path.join(tmp, "build")
            os.makedirs(build, exist_ok=True)
            sentinel = os.path.join(build, "ui.uib")
            with open(sentinel, "wb") as fh:
                fh.write(b"NOT-A-BLOB")

            here = os.getcwd()
            with self.captured_fd2() as sink:
                rc = front.main(["dev", path, "--screen", "saves", "--once"])
            out = sink[0]
            self.assertEqual(rc, 0, out)
            self.assertTrue(out.strip(), "captured nothing; the assertions "
                                         "below would pass vacuously")
            self.assertEqual(os.getcwd(), here)

            # It built, into its own directory. The IR is named after
            # the SCREEN, because a blob's screen names are its IR file
            # stems -- ps2ui-dev wrote a fixed ui.json, so every blob it
            # made had one screen called `ui`.
            for name in ("saves.json", "ui.uib", "preview.png"):
                self.assertTrue(
                    os.path.exists(os.path.join(build, "dev", name)),
                    "%s missing from build/dev: %s" % (name, out))
            # And left the build directory alone.
            with open(sentinel, "rb") as fh:
                self.assertEqual(fh.read(), b"NOT-A-BLOB",
                                 "ps2ui dev overwrote build/ui.uib")
            # Every path printed is relative to the project, the same
            # rule `ps2ui build` follows.
            self.assertNotIn(tmp, out,
                             "ps2ui dev printed an absolute path")
            self.assertIn("build/dev/preview.png", out)

            # AND IT BUILT THE SCREEN THAT WAS NAMED. Everything above
            # holds whichever screen `cmd_dev` picks, so without this
            # the --screen flag could be accepted and ignored and this
            # file would stay green -- pick_screen is unit-tested just
            # above, and a unit test of a helper says nothing about
            # whether the caller reached it. That is the shape this
            # repository keeps finding: a fence connected to nothing.
            from ps2ui_bake.uib import read_uib
            blob = read_uib(os.path.join(build, "dev", "ui.uib"))
            self.assertEqual([sc["name"] for sc in blob.screens], ["saves"],
                             "ps2ui dev built a screen other than the one "
                             "--screen named")

    def test_out_override_moves_the_intermediates_with_it(self):
        from ps2ui_bake import project
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            path = self.write(tmp, {"screens": ["ui/games.html"],
                                    "css": "ui/app.css"})
            # FULL RELATIVE PATHS, not just the stem. The first version
            # of this asserted endswith("games.json"), which checks the
            # filename and says nothing about the DIRECTORY -- and the
            # directory is the entire reason the `dist/ui.uib` case
            # below cannot collide. Pinning ir_path to the project's
            # default build/ passed that assertion. "Covered by
            # construction" was true of the code and false of the test.
            def ir(proj):
                return os.path.relpath(proj.ir_path(proj.screens[0]),
                                       proj.root)

            proj = project.load(path)
            self.assertEqual(ir(proj), os.path.join("build", "games.json"))

            # Extends the default stem: the remainder is the suffix,
            # which is what restores games-16x9 as a SCREEN NAME -- the
            # blob's screen names are the IR file stems.
            proj.set_out_override("build/ui-16x9.uib")
            self.assertEqual(ir(proj),
                             os.path.join("build", "games-16x9.json"))

            # Same stem, another directory: nothing to disambiguate,
            # because the intermediates follow the blob. Asserting the
            # directory is what makes that a check rather than a claim.
            proj = project.load(path)
            proj.set_out_override("dist/ui.uib")
            self.assertEqual(ir(proj), os.path.join("dist", "games.json"))

            # Shares nothing: use the whole name rather than guess a
            # suffix. Two builds that share nothing must still not
            # share intermediates.
            proj = project.load(path)
            proj.set_out_override("build/widescreen.uib")
            self.assertEqual(ir(proj),
                             os.path.join("build", "games-widescreen.json"))

    def test_a_second_build_does_not_stand_on_the_first(self):
        """The regression, reproduced: two builds into one directory.

        channel6 bakes a second blob at 16:9 from the same sources, and
        `-o` moved only the blob. The second build overwrote the first's
        intermediate JSON and its display preview -- so `ps2ui check`
        validated a 4:3 blob while preview-display.png showed the 16:9
        render under the 4:3 name, and two documents sent a reader to a
        file that was no longer produced.
        """
        import tempfile
        import json as _json
        from ps2ui_bake import ps2ui as front
        from ps2ui_bake.uib import read_uib
        with tempfile.TemporaryDirectory() as tmp:
            os.makedirs(os.path.join(tmp, "ui"))
            with open(os.path.join(tmp, "ui", "games.html"), "w") as fh:
                fh.write('<screen name="games"><div class="r">Hi</div></screen>')
            with open(os.path.join(tmp, "ui", "app.css"), "w") as fh:
                fh.write('.r { color: #fff; background: #000; }')
            with open(os.path.join(tmp, "ps2ui.json"), "w") as fh:
                _json.dump({"screens": ["ui/games.html"], "css": "ui/app.css",
                            "previewDisplay": "build/preview-display.png",
                            "fonts": os.path.join(FONTS, "fonts.json")}, fh)
            proj_file = os.path.join(tmp, "ps2ui.json")
            b = lambda *p: os.path.join(tmp, "build", *p)

            self.assertEqual(front.main(["build", proj_file]), 0)
            first_display = open(b("preview-display.png"), "rb").read()
            first_blob = open(b("ui.uib"), "rb").read()

            self.assertEqual(front.main(
                ["build", proj_file, "--mode", "ntsc16x9",
                 "-o", "build/ui-16x9.uib",
                 "--preview-display", "build/preview-16x9-display.png",
                 "--preview", "none"]), 0)

            # Nothing the first build wrote was touched.
            self.assertEqual(open(b("preview-display.png"), "rb").read(),
                             first_display,
                             "the second build overwrote the first's "
                             "display preview")
            self.assertEqual(open(b("ui.uib"), "rb").read(), first_blob)
            # The second build's own preview exists and differs.
            self.assertTrue(os.path.exists(b("preview-16x9-display.png")))
            self.assertNotEqual(
                open(b("preview-16x9-display.png"), "rb").read(),
                first_display)
            # `--preview none` skipped it rather than writing it twice.
            self.assertEqual(
                sorted(f for f in os.listdir(b()) if f.endswith(".png")),
                ["preview-16x9-display.png", "preview-display.png",
                 "preview.png"])
            # And the screen NAMES stayed distinct, which is the half
            # that only the intermediates carry.
            self.assertEqual([s["name"] for s in read_uib(b("ui.uib")).screens],
                             ["games"])
            self.assertEqual(
                [s["name"] for s in read_uib(b("ui-16x9.uib")).screens],
                ["games-16x9"])

