"""Baker test suite: numeric rules, GS encodings, atlases, nine-patches,
quad flattening, the .uib round-trip, and the previewer's replay
semantics. stdlib unittest + Pillow only, same as the package.

Run:  cd packages/baker && python3 -m unittest discover -s tests -v
"""

import io
import json
import os
import struct
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from PIL import Image

from ps2ui_bake.rounding import (
    round_half_up, glyph_advance_px, css_alpha_to_gs, css_channel_to_gs,
    gs_alpha_to_css,
)
from ps2ui_bake import gs
from ps2ui_bake.atlas import AtlasBuilder
from ps2ui_bake.ninepatch import rasterize_patch, slice_quads, patch_key
from ps2ui_bake.quads import (
    Flattener, DrawRecord, OP_QUAD, OP_TEXQUAD, OP_SCISSOR_PUSH, OP_SCISSOR_POP,
    STATE_ALWAYS, STATE_UNFOCUSED, STATE_FOCUSED, FOCUS_NONE, TEX_NONE,
)
from ps2ui_bake.uib import write_uib, read_uib, MAGIC, _CMD, _HEADER, _FOCUS
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

    def test_negative_half_up(self):
        self.assertEqual(round_half_up(-0.5), 0)
        self.assertEqual(round_half_up(-1.5), -1)


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


class TestUib(unittest.TestCase):
    def roundtrip(self, records, textures=(), cluts=(), nodes=(), initial=None):
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "t.uib")
            write_uib(path, {"w": 320, "h": 240}, list(records),
                      list(textures), list(cluts), list(nodes), initial)
            return read_uib(path)

    def test_struct_sizes_match_c_runtime(self):
        self.assertEqual(_HEADER.size, 48)
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
