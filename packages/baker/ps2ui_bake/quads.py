"""Quad flattening: IR paint commands -> GS-shaped draw records.

Output records mirror the .uib command layout one-to-one:

    op      QUAD | TEXQUAD | SCISSOR_PUSH | SCISSOR_POP
    state   ALWAYS | UNFOCUSED | FOCUSED
    focus   focus-table index (or NONE)
    rect    integer destination
    color   RGBA with GS-domain alpha (converted here, once)
    tex     texture index + texel source rect for TEXQUAD

Rectangles with square corners flatten to solid quads (fill + four
border edges). Rounded rectangles flatten to nine-patch TEXQUADs.
Text flattens to one TEXQUAD per inked glyph, tinted by vertex color.

The flattener owns paint-order truth: records appear in exactly the
order the GS must draw them. The previewer and the console runtime
both just walk the list.
"""

from dataclasses import dataclass, replace
from typing import Optional

from .rounding import css_alpha_to_gs
from . import gs
from .atlas import AtlasBuilder
from .ninepatch import patch_key, rasterize_patch, slice_quads

OP_QUAD = 0
OP_TEXQUAD = 1
OP_SCISSOR_PUSH = 2
OP_SCISSOR_POP = 3

STATE_ALWAYS = 0
STATE_UNFOCUSED = 1
STATE_FOCUSED = 2
_STATE_NAMES = {"always": STATE_ALWAYS, "unfocused": STATE_UNFOCUSED, "focused": STATE_FOCUSED}

FOCUS_NONE = 0xFFFF
TEX_NONE = 0xFFFF


@dataclass(frozen=True)
class DrawRecord:
    op: int
    state: int
    focus: int
    x: int
    y: int
    w: int
    h: int
    rgba: tuple  # (r, g, b, a_gs)
    tex: int = TEX_NONE
    u0: int = 0
    v0: int = 0
    u1: int = 0
    v1: int = 0


@dataclass
class BakedTexture:
    fmt: int          # gs.PSMT8 | gs.PSMCT32
    width: int
    height: int
    clut: Optional[int]  # clut index or None
    data: bytes


class Flattener:
    def __init__(self, ir: dict, font_paths: dict):
        """font_paths: {"regular": {"ttf": ..., "metrics": ...},
                        "bold":    {"ttf": ..., "metrics": ...}}"""
        self.ir = ir
        self.font_paths = font_paths
        self.textures: list[BakedTexture] = []
        self.cluts: list[bytes] = []
        self.records: list[DrawRecord] = []
        self._atlases = {}      # (weight_bucket, size) -> (AtlasBuilder, tex_index)
        self._patches = {}      # patch_key -> (NinePatch, tex_index)
        self._coverage_clut = None
        # box-id -> focus-table index, from the IR focus graph
        self.focus_index = {
            node["id"]: i for i, node in enumerate(ir["focus"]["nodes"])
        }

    # ------------------------------------------------------------ helpers

    def _focus_of(self, cmd) -> int:
        fid = cmd.get("focusId")
        if fid is None:
            return FOCUS_NONE
        return self.focus_index.get(fid, FOCUS_NONE)

    def _gs_color(self, rgba255) -> tuple:
        r, g, b, a = rgba255
        return (r, g, b, css_alpha_to_gs(a))

    def _coverage_clut_index(self) -> int:
        if self._coverage_clut is None:
            self.cluts.append(gs.coverage_clut())
            self._coverage_clut = len(self.cluts) - 1
        return self._coverage_clut

    def _atlas_for(self, weight: int, size: int):
        bucket = "bold" if weight >= 600 else "regular"
        key = (bucket, size)
        if key not in self._atlases:
            paths = self.font_paths[bucket]
            builder = AtlasBuilder(paths["ttf"], paths["metrics"], weight, size)
            self.textures.append(None)  # reserve the slot; finalized in finish()
            self._atlases[key] = (builder, len(self.textures) - 1)
        return self._atlases[key]

    def _patch_for(self, radius, border_w, fill, border_color):
        key = patch_key(radius, border_w, fill, border_color)
        if key not in self._patches:
            patch = rasterize_patch(radius, border_w, fill, border_color)
            rgba = patch.image.convert("RGBA")
            data = gs.encode_psmct32(rgba.getdata())
            self.textures.append(BakedTexture(
                gs.PSMCT32, rgba.width, rgba.height, None, data,
            ))
            self._patches[key] = (patch, len(self.textures) - 1)
        return self._patches[key]

    # -------------------------------------------------------------- rects

    def _flatten_rect(self, cmd):
        state = _STATE_NAMES[cmd["state"]]
        focus = self._focus_of(cmd)
        x, y, w, h = cmd["x"], cmd["y"], cmd["w"], cmd["h"]
        fill = cmd["fill"]
        bw = cmd["borderWidth"]
        bc = cmd["borderColor"]
        radius = cmd["radius"]

        if radius > 0:
            patch, tex = self._patch_for(radius, bw, fill, bc)
            # The patch is premixed fill+border; tint white, real alpha in texels.
            white = (255, 255, 255, 128)
            for (dx, dy, dw, dh), (su, sv, sw, sh) in slice_quads(patch, x, y, w, h):
                self.records.append(DrawRecord(
                    OP_TEXQUAD, state, focus, dx, dy, dw, dh, white,
                    tex, su, sv, su + sw, sv + sh,
                ))
            return

        if fill:
            self.records.append(DrawRecord(
                OP_QUAD, state, focus, x, y, w, h, self._gs_color(fill),
            ))
        if bw > 0 and bc:
            c = self._gs_color(bc)
            edges = (
                (x, y, w, bw),                    # top
                (x, y + h - bw, w, bw),           # bottom
                (x, y + bw, bw, h - 2 * bw),      # left
                (x + w - bw, y + bw, bw, h - 2 * bw),  # right
            )
            for ex, ey, ew, eh in edges:
                if ew > 0 and eh > 0:
                    self.records.append(DrawRecord(
                        OP_QUAD, state, focus, ex, ey, ew, eh, c,
                    ))

    # --------------------------------------------------------------- text

    def _flatten_text(self, cmd):
        state = _STATE_NAMES[cmd["state"]]
        focus = self._focus_of(cmd)
        builder, tex = self._atlas_for(cmd["weight"], cmd["size"])
        tint = self._gs_color(cmd["color"])
        pen_x = cmd["x"]
        top_y = cmd["y"]
        spacing = cmd.get("letterSpacing", 0)
        for ch in cmd["text"]:
            glyph = builder.add(ch)
            if glyph.w > 0:
                self.records.append(DrawRecord(
                    OP_TEXQUAD, state, focus,
                    pen_x + glyph.bearing_x, top_y + glyph.bearing_y,
                    glyph.w, glyph.h, tint,
                    tex, glyph.u, glyph.v, glyph.u + glyph.w, glyph.v + glyph.h,
                ))
            pen_x += glyph.advance + spacing

    # ---------------------------------------------------------------- run

    def run(self) -> None:
        for cmd in self.ir["commands"]:
            op = cmd["op"]
            if op == "rect":
                self._flatten_rect(cmd)
            elif op == "text":
                self._flatten_text(cmd)
            elif op == "scissor_push":
                self.records.append(DrawRecord(
                    OP_SCISSOR_PUSH, STATE_ALWAYS, FOCUS_NONE,
                    cmd["x"], cmd["y"], cmd["w"], cmd["h"], (0, 0, 0, 0),
                ))
            elif op == "scissor_pop":
                self.records.append(DrawRecord(
                    OP_SCISSOR_POP, STATE_ALWAYS, FOCUS_NONE,
                    0, 0, 0, 0, (0, 0, 0, 0),
                ))
            else:
                raise ValueError(f"unknown IR command op: {op}")
        self._finish_atlases()

    def _finish_atlases(self):
        clut = self._coverage_clut_index() if self._atlases else None
        for (bucket, size), (builder, tex_index) in self._atlases.items():
            atlas = builder.build()
            self.textures[tex_index] = BakedTexture(
                gs.PSMT8, atlas.image.width, atlas.image.height,
                clut, gs.encode_psmt8(atlas.image.getdata()),
            )
