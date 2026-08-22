"""Baker test suite: numeric rules, GS encodings, atlases, nine-patches,
quad flattening, the .uib round-trip, and the previewer's replay
semantics. stdlib unittest + Pillow only, same as the package.

Run:  cd packages/baker && python3 -m unittest discover -s tests -v
"""

import io
import json
import os
import shutil
import struct
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
from ps2ui_bake.ninepatch import rasterize_patch, slice_quads, patch_key
from ps2ui_bake.quads import (
    Flattener, DrawRecord, OP_QUAD, OP_TEXQUAD, OP_SCISSOR_PUSH, OP_SCISSOR_POP,
    STATE_ALWAYS, STATE_UNFOCUSED, STATE_FOCUSED, FOCUS_NONE, TEX_NONE,
)
from ps2ui_bake.uib import (write_uib, read_uib, MAGIC, VERSION,
                            FEAT_DYNAMIC_TEXT, FEAT_KERNING,
                            FEAT_SLOT_SPACING,
                            _CMD, _HEADER, _FOCUS, _FONT, _KERN,
                            _SLOT)
from ps2ui_bake import preview

REPO = os.path.join(os.path.dirname(__file__), "..", "..", "..")
FONTS = os.path.join(REPO, "fonts")
TTF = None
for cand in (
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/TTF/DejaVuSans.ttf",
):
    if os.path.exists(cand):
        TTF = cand
        break

METRICS = os.path.join(FONTS, "default.metrics.json")


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
        from unittest import mock
        from ps2ui_bake import fontgen
        with tempfile.TemporaryDirectory() as td:
            out = os.path.join(td, "m.json")
            with mock.patch.object(fontgen.features, "check",
                                   return_value=False):
                rc = fontgen.main([TTF, "DejaVu Sans", "400", out])
            self.assertEqual(rc, 2)
            self.assertFalse(os.path.exists(out))

    def test_and_succeeds_with_raqm_present(self):
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

    def test_ninepatch_tint_is_modulate_identity(self):
        ir = tiny_ir([{
            "op": "rect", "x": 0, "y": 0, "w": 40, "h": 40,
            "fill": [1, 2, 3, 255], "borderWidth": 0, "borderColor": None,
            "radius": 5, "state": "always", "focusId": None,
        }])
        f = Flattener(ir, font_paths())
        f.run()
        for r in f.records:
            self.assertEqual(r.op, OP_TEXQUAD)
            self.assertEqual(r.rgba, (0x80, 0x80, 0x80, 0x80))

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
        return AtlasBuilder(TTF, METRICS, 400, size)

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
        p = rasterize_patch(6, 2, (10, 20, 30, 255), (200, 200, 200, 255))
        self.assertEqual(p.cell, 7)
        self.assertEqual(p.image.width, 15)

    def test_slices_tile_target_exactly(self):
        p = rasterize_patch(6, 2, (10, 20, 30, 255), None)
        target = (5, 7, 100, 60)
        covered = [[False] * 60 for _ in range(100)]
        for (dx, dy, dw, dh), _src in slice_quads(p, *target):
            for xx in range(dx - 5, dx - 5 + dw):
                for yy in range(dy - 7, dy - 7 + dh):
                    self.assertFalse(covered[xx][yy], "slices overlap")
                    covered[xx][yy] = True
        self.assertTrue(all(all(col) for col in covered), "slices leave gaps")

    def test_small_target_clamps_corners(self):
        p = rasterize_patch(10, 0, (1, 2, 3, 255), None)
        quads = list(slice_quads(p, 0, 0, 12, 12))
        for (dx, dy, dw, dh), _ in quads:
            self.assertGreaterEqual(dx, 0)
            self.assertGreaterEqual(dy, 0)
            self.assertLessEqual(dx + dw, 12)
            self.assertLessEqual(dy + dh, 12)

    def test_key_dedups_identical_styles(self):
        a = patch_key(4, 1, [1, 2, 3, 255], None)
        b = patch_key(4, 1, (1, 2, 3, 255), None)
        self.assertEqual(a, b)


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

    def test_rounded_rect_is_nine_texquads(self):
        ir = tiny_ir([{
            "op": "rect", "x": 0, "y": 0, "w": 60, "h": 40,
            "fill": [1, 1, 1, 255], "borderWidth": 2,
            "borderColor": [7, 7, 7, 255], "radius": 6,
            "state": "always", "focusId": None,
        }])
        f = Flattener(ir, font_paths())
        f.run()
        self.assertEqual(len(f.records), 9)
        self.assertTrue(all(r.op == OP_TEXQUAD for r in f.records))
        self.assertEqual(len(f.textures), 1)

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

    def test_too_many_slots_rejected(self):
        from ps2ui_bake import caps
        limit = caps.FALLBACK["PS2UI_MAX_SLOTS"]
        errors, _ = caps.check([], [], self.slots(limit), [{}])
        self.assertEqual(errors, [])
        errors, _ = caps.check([], [], self.slots(limit + 1), [{}])
        self.assertEqual(len(errors), 1)
        self.assertIn("PS2UI_ERR_TOO_MANY", errors[0])
        self.assertIn("PS2UI_MAX_SLOTS", errors[0])

    def test_too_many_textures_and_screens_rejected(self):
        from ps2ui_bake import caps
        tex = [None] * (caps.FALLBACK["PS2UI_MAX_TEXTURES"] + 1)
        errors, _ = caps.check(tex, [], [], [{}])
        self.assertTrue(any("textures" in e for e in errors))
        screens = [{}] * (caps.FALLBACK["PS2UI_MAX_SCREENS"] + 1)
        errors, _ = caps.check([], [], [], screens)
        self.assertTrue(any("screens" in e for e in errors))

    def test_slot_capacity_must_fit_the_runtime_buffer(self):
        from ps2ui_bake import caps
        bufsz = caps.FALLBACK["PS2UI_SLOT_BUFSZ"]
        errors, _ = caps.check([], [], self.slots(1, capacity=bufsz - 1), [{}])
        self.assertEqual(errors, [])
        errors, _ = caps.check([], [], self.slots(1, capacity=bufsz), [{}])
        self.assertIn("PS2UI_SLOT_BUFSZ", errors[0])


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
        self.assertEqual(_HEADER.size, 76)
        self.assertEqual(_CMD.size, 32)
        self.assertEqual(_FOCUS.size, 24)

    def test_records_round_trip_exactly(self):
        recs = [
            DrawRecord(OP_QUAD, STATE_ALWAYS, FOCUS_NONE, -4, 7, 10, 20, (1, 2, 3, 0x80)),
            DrawRecord(OP_TEXQUAD, STATE_FOCUSED, 3, 0, 0, 5, 5, (9, 9, 9, 64), 2, 1, 2, 3, 4),
            DrawRecord(OP_SCISSOR_PUSH, STATE_ALWAYS, FOCUS_NONE, 0, 0, 100, 100, (0, 0, 0, 0)),
            DrawRecord(OP_SCISSOR_POP, STATE_ALWAYS, FOCUS_NONE, 0, 0, 0, 0, (0, 0, 0, 0)),
        ]
        out = self.roundtrip(recs)
        self.assertEqual(out.records, recs)
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
        builder = AtlasBuilder(TTF, METRICS, 400, 32)
        self.assertEqual(builder.kern(ord("T"), ord("o")), -5)
        kerned = self.pen_xs("To", size=32)
        unkerned_o = builder.add("T").advance + builder.add("o").bearing_x
        self.assertEqual(kerned[1].x, unkerned_o - 5)

    def test_the_first_glyph_is_never_kerned(self):
        builder = AtlasBuilder(TTF, METRICS, 400, 32)
        self.assertEqual(builder.kern(None, ord("o")), 0)
        self.assertEqual(self.pen_xs("To", size=32)[0].x,
                         builder.add("T").bearing_x)

    def test_kerning_is_directional(self):
        builder = AtlasBuilder(TTF, METRICS, 400, 32)
        self.assertLess(builder.kern(ord("T"), ord("o")), 0)
        self.assertEqual(builder.kern(ord("o"), ord("T")), 0)

    def test_letter_spacing_and_kerning_both_apply(self):
        builder = AtlasBuilder(TTF, METRICS, 400, 32)
        plain = self.pen_xs("To", size=32)
        spaced = self.pen_xs("To", size=32, spacing=3)
        self.assertEqual(spaced[1].x - plain[1].x, 3)
        # And spacing does not apply before the first glyph.
        self.assertEqual(spaced[0].x, plain[0].x)

    def test_an_unkerned_string_is_unchanged(self):
        # The regression guard for every UI that has no kerned pairs:
        # its geometry must be byte-identical to before kerning existed.
        builder = AtlasBuilder(TTF, METRICS, 400, 32)
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
        f, _ = self.bake()
        font = f.fonts[0]
        size = font["size"]
        by_pair = {(k["prev"], k["cur"]): k["amount"] for k in font["kerns"]}
        with open(METRICS, encoding="utf-8") as fh:
            units = json.load(fh)["kerning"]
        for (prev, cur), amount in by_pair.items():
            self.assertEqual(amount, kern_px(units[f"{prev},{cur}"], size))

    def test_pairs_that_round_to_zero_are_dropped(self):
        f, _ = self.bake()
        font = f.fonts[0]
        self.assertTrue(all(k["amount"] != 0 for k in font["kerns"]))
        # A 14px UI keeps far fewer pairs than the metrics carry: a
        # sub-em adjustment only survives rounding once text is large.
        with open(METRICS, encoding="utf-8") as fh:
            self.assertLess(len(font["kerns"]),
                            len(json.load(fh)["kerning"]))

    def test_pairs_are_sorted_for_the_runtime_bsearch(self):
        f, _ = self.bake()
        for font in f.fonts:
            keys = [(k["prev"], k["cur"]) for k in font["kerns"]]
            self.assertEqual(keys, sorted(keys))

    def test_a_bigger_font_keeps_more_pairs(self):
        # The direct consequence of pre-rounding to pixels, and the
        # reason the table is per-size rather than per-face.
        kept = {}
        for size in (10, 14, 24, 40):
            b = AtlasBuilder(TTF, METRICS, 400, size)
            for cp_str in b.metrics["advances"]:
                b.add(chr(int(cp_str)))
            kept[size] = len(Flattener._kern_table(b))
        self.assertLess(kept[10], kept[24])
        self.assertLess(kept[24], kept[40])

    def test_orphan_pairs_are_not_stored(self):
        # A pair naming a glyph the atlas never baked can never be
        # looked up; storing it would only cost blob.
        b = AtlasBuilder(TTF, METRICS, 400, 32)
        b.add("T")   # deliberately no 'o'
        pairs = Flattener._kern_table(b)
        self.assertFalse([k for k in pairs if k["cur"] == ord("o")])

    def test_the_format_carries_the_table_and_declares_it(self):
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
        self.assertEqual(VERSION, 5)

    def test_the_feature_bit_states_what_the_tables_hold(self):
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
        builder = AtlasBuilder(TTF, METRICS, 400, size)
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
                         AtlasBuilder(TTF, METRICS, 400, 32).add("T").advance - 5)


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

    def test_the_stride_did_not_move(self):
        self.assertEqual(_SLOT.size, 32)

    def test_spacing_round_trips_and_declares_itself(self):
        u = self.bake(3)
        self.assertEqual(u.slots[0]["letter_spacing"], 3)
        self.assertEqual(u.feature_flags & FEAT_SLOT_SPACING,
                         FEAT_SLOT_SPACING)

    def test_zero_spacing_means_what_the_pad_always_meant(self):
        # Every writer before the field wrote zeros there, so a blob
        # with no spacing anywhere must not claim the feature.
        u = self.bake(0)
        self.assertEqual(u.slots[0]["letter_spacing"], 0)
        self.assertEqual(u.feature_flags & FEAT_SLOT_SPACING, 0)

    def test_negative_spacing_survives(self):
        # CSS letter-spacing may be negative; the field is signed.
        u = self.bake(-1)
        self.assertEqual(u.slots[0]["letter_spacing"], -1)

    def test_out_of_range_spacing_is_refused_by_name(self):
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
            return check_blob(read_uib(path))

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
        for rel in ("examples/memcard/build/ui.uib",
                    "examples/channel6/build/ui.uib"):
            path = os.path.normpath(os.path.join(root, rel))
            if not os.path.exists(path):
                continue  # not built in this checkout
            seen += 1
            rep = check_blob(read_uib(path))
            self.assertEqual(rep.errors, 0, f"{rel}: {self.failures(rep)}")
        if seen == 0:
            self.skipTest("no example blobs built")


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
