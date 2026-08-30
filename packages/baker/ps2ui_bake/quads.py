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

import sys
from dataclasses import dataclass, replace
from typing import Optional

from .rounding import (css_alpha_to_gs, css_channel_to_gs, glyph_advance_px,
                       kern_px, round_half_up)
from . import gs
from .atlas import AtlasBuilder
from .ninepatch import (COVERAGE_FILL, COVERAGE_RING, patch_key,
                        rasterize_coverage, slice_quads)

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
    # The var() name behind this record's colour, or None when the
    # author wrote a literal. It is what the tint table keys on: a role
    # is the name someone chose, and two literals that happen to agree
    # are two coincidences, not one role. None is therefore not a
    # missing value -- it is the author declining to offer this colour
    # to a theme, and it collapses by value exactly as it did at v7.
    var: str = None
    # THE SAME COLOUR IN EVERY THEME, index 0 being this record's own
    # `rgba`. None means "one theme", which is what a blob with no
    # @theme block has. Not derived from `rgba` and a per-theme literal
    # anywhere downstream, and that is the design: the fold from a
    # declaration to a painted colour happens once, in layout, over the
    # whole vector at once (paint.js foldAlpha), so a theme's value can
    # never be computed from another theme's. See #77.
    rgba_themes: tuple = None
    # data-keep: exempt from the dead-geometry trim. Build-time only --
    # it never reaches the .uib, because the runtime draws whatever
    # records it is given and has no notion of a record it should have
    # dropped.
    keep: bool = False


# How a texture's texels arrive (uib format v6). Defined here rather
# than in uib.py because they are a property of BakedTexture, and
# uib.py already imports from this module -- the other direction would
# be a cycle. uib.py re-exports them, so `from .uib import
# TEXKIND_STREAMED` keeps working.
TEXKIND_BAKED = 0
TEXKIND_STREAMED = 1


@dataclass
class BakedTexture:
    fmt: int          # gs.PSMT8 | gs.PSMCT32
    width: int
    height: int
    clut: Optional[int]  # clut index or None
    data: bytes
    # Offset of `data` within the blob section. Only the reader knows it
    # (the writer computes offsets at serialization time), so it is None
    # on a texture the Flattener built and set on one read_uib returned.
    # ps2ui-check uses it to assert 16-alignment for in-place DMA.
    data_off: Optional[int] = None
    # v6: how the texels arrive. A STREAMED texture carries no data --
    # the app supplies it at runtime through ps2ui_tex_set -- so it
    # needs a name to be addressable and a reservation stating the
    # exact payload the runtime will demand.
    kind: int = TEXKIND_BAKED
    name: Optional[str] = None
    reservation: int = 0


class Flattener:
    def __init__(self, ir: dict, font_paths: dict, palettize_all: bool = False):
        """font_paths: {"regular": {"ttf": ..., "metrics": ...},
                        "bold":    {"ttf": ..., "metrics": ...}}
        palettize_all: quantize every image to PSMT8+CLUT regardless of
        per-element opt-in."""
        self.ir = ir
        self.font_paths = font_paths
        self.palettize_all = palettize_all
        self.textures: list[BakedTexture] = []
        self.cluts: list[bytes] = []
        self.records: list[DrawRecord] = []
        self._atlases = {}      # (weight_bucket, size) -> (AtlasBuilder, tex_index)
        self._patches = {}      # patch_key -> (NinePatch, tex_index)
        self._images = {}       # (src, w, h) -> tex_index
        self._streamed = {}     # slot name -> tex_index
        self._coverage_clut = None
        self.fonts = []         # dynamic-text font tables (filled by run())
        self.slots = []         # dynamic-text slots (filled by run())
        self.screens = []       # screen ranges (filled by run()/run_screens())
        self.dropped = 0        # draw records trimmed as unable to draw (F24)
        self.focus_nodes = []   # globally-indexed focus nodes for the writer
        self._font_index = {}   # (bucket, size) -> font table index
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
        """Vertex color for an untextured QUAD: GS flat shading reads
        full-range 0..255 RGB; only alpha crosses into the 0..128 domain."""
        r, g, b, a = rgba255
        return (r, g, b, css_alpha_to_gs(a))

    def _gs_modulate_color(self, rgba255) -> tuple:
        """Vertex color for a TEXQUAD drawn with TEX MODULATE: the GS
        multiplies texels as Cv = Ct * Cf >> 7, so *every* channel must
        be in the 0x80-identity domain (backlog B1)."""
        return tuple(css_channel_to_gs(v) for v in rgba255)

    @staticmethod
    def _gs_vec(fn, vec):
        """Convert a whole theme vector with the conversion its record
        uses. Taking the function rather than a flag is deliberate: a
        QUAD and a TEXQUAD carrying one CSS literal convert to DIFFERENT
        GS values (flat shading is 0..255 RGB, modulate is 0x80-identity
        on every channel), so a row written with the wrong one is wrong
        by a factor of two and looks merely dim. Passing the caller's
        own conversion makes picking the wrong one impossible."""
        return tuple(fn(c) for c in vec) if vec else None

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

    def _patch_for(self, radius, border_w, part):
        """One coverage mask, PSMT8, on the shared coverage CLUT.

        The same shape a glyph has, for the same reason: coverage in
        the texels, colour in the tint. Keyed on geometry alone, so
        every box with this radius and border width shares it whatever
        colour it is painted.
        """
        key = patch_key(radius, border_w, part)
        if key not in self._patches:
            patch = rasterize_coverage(radius, border_w, part)
            img = patch.image
            self.textures.append(BakedTexture(
                gs.PSMT8, img.width, img.height,
                self._coverage_clut_index(), gs.encode_psmt8(img.getdata()),
            ))
            self._patches[key] = (patch, len(self.textures) - 1)
        return self._patches[key]

    # -------------------------------------------------------------- rects

    def _flatten_rect(self, cmd):
        state = _STATE_NAMES[cmd["state"]]
        focus = self._focus_of(cmd)
        keep = bool(cmd.get("keep"))
        x, y, w, h = cmd["x"], cmd["y"], cmd["w"], cmd["h"]
        fill = cmd["fill"]
        bw = cmd["borderWidth"]
        bc = cmd["borderColor"]
        radius = cmd["radius"]

        if radius > 0:
            # TWO LAYERS, EACH WITH ITS OWN ROLE (P3b-6). The fill goes
            # down first and the border ring over it, both coverage
            # masks modulated by a real tint -- so `background:
            # var(--panel); border: 2px solid var(--edge)` on a rounded
            # box reaches the tint table twice, under two names, and a
            # theme moves both. Premixed, it reached the table not at
            # all.
            #
            # Fill first, then ring: the masks are complementary by
            # construction, so the order is not load-bearing for the
            # pixels, but it is the order a browser paints in and the
            # order the square-cornered branch below uses.
            layers = (
                (COVERAGE_FILL, fill, cmd.get("fillVar"),
                 cmd.get("fillThemes")),
                (COVERAGE_RING, bc if bw > 0 else None,
                 cmd.get("borderColorVar"), cmd.get("borderColorThemes")),
            )
            for part, colour, var, themes in layers:
                if not colour:
                    continue
                patch, tex = self._patch_for(radius, bw, part)
                tint = self._gs_modulate_color(colour)
                tvec = self._gs_vec(self._gs_modulate_color, themes)
                for (dx, dy, dw, dh), (su, sv, sw, sh) in slice_quads(
                        patch, x, y, w, h):
                    # A cell this mask does not touch is a draw that
                    # produces nothing: the ring's centre cell is the
                    # whole interior of the box, and emitting it would
                    # cost a full-box textured draw per rounded element
                    # to composite zeros.
                    if patch.cell_empty(su, sv, sw, sh):
                        continue
                    self.records.append(DrawRecord(
                        OP_TEXQUAD, state, focus, dx, dy, dw, dh, tint,
                        tex, su, sv, su + sw, sv + sh, keep=keep,
                        var=var, rgba_themes=tvec,
                    ))
            return

        if fill:
            self.records.append(DrawRecord(
                OP_QUAD, state, focus, x, y, w, h, self._gs_color(fill),
                keep=keep, var=cmd.get("fillVar"),
                rgba_themes=self._gs_vec(self._gs_color, cmd.get("fillThemes")),
            ))
        if bw > 0 and bc:
            c = self._gs_color(bc)
            # The border's own name, not the fill's. One element can
            # carry two roles -- `background: var(--panel); border: 1px
            # solid var(--edge)` -- and reusing fillVar here would fuse
            # them into whichever the theme moved first.
            bvar = cmd.get("borderColorVar")
            cvec = self._gs_vec(self._gs_color, cmd.get("borderColorThemes"))
            edges = (
                (x, y, w, bw),                    # top
                (x, y + h - bw, w, bw),           # bottom
                (x, y + bw, bw, h - 2 * bw),      # left
                (x + w - bw, y + bw, bw, h - 2 * bw),  # right
            )
            for ex, ey, ew, eh in edges:
                if ew > 0 and eh > 0:
                    self.records.append(DrawRecord(
                        OP_QUAD, state, focus, ex, ey, ew, eh, c, keep=keep,
                        var=bvar, rgba_themes=cvec,
                    ))

    # -------------------------------------------------------------- images

    @staticmethod
    def _clut_from_palette(pal) -> bytes:
        """RGBA palette bytes -> a full 256-entry GS CLUT.

        Shared because the two palettize paths disagree about length and
        agree about everything else: FASTOCTREE always hands back 256
        entries, while an authored P-mode PNG hands back only the ones
        it defines. Padding here keeps that difference from being a
        property of which branch you happen to be in."""
        clut = bytearray()
        for i in range(0, len(pal), 4):
            clut += gs.pack_rgba_gs(pal[i], pal[i + 1], pal[i + 2], pal[i + 3])
        return bytes(clut) + bytes(256 * 4 - len(clut))

    def _image_texture(self, src: str, w: int, h: int, palettize: bool,
                       strict: bool = False) -> int:
        """Decode + pre-scale an image to its laid-out size. Keyed by
        (src, w, h, palettize): the same asset at two sizes is two
        textures, because the GS never scales at runtime here.

        palettize=False bakes PSMCT32 (32bpp, exact colors).
        palettize=True quantizes to <=256 colors and bakes PSMT8 with a
        per-image CLUT — 8 bits per texel, a 4x VRAM cut, for art that
        survives a palette (opt in via the `palettize` attribute on
        <img>, or --palettize-images for the whole bake)."""
        from PIL import Image  # deferred so text-only bakes never import it twice

        key = (src, w, h, palettize, strict)
        if key not in self._images:
            try:
                raw = Image.open(src)
                raw.load()
            except OSError as err:
                raise ValueError(f"image: cannot decode {src!r}: {err}") from err

            # An already-indexed PNG keeps its own palette and its own
            # index values. Re-quantizing one is lossy for nothing, and
            # it destroys any meaning the indices carried -- which is
            # the whole point for bring-up step 3, where the tile is
            # built from indices chosen to differ only in the two bits
            # CSM1 permutes, so a correct CLUT upload renders uniform
            # and a wrong one renders a boundary.
            if palettize and raw.mode == "P" and raw.size != (w, h):
                # The two opt-ins mean different things and only one of
                # them is a claim about indices.
                #
                # `palettize` on an <img> says "I care about this
                # image's palette", so silently requantizing it would
                # destroy the thing that was asked for -- refuse.
                #
                # --palettize-images says "quantize everything to save
                # VRAM". Its author made no claim about any particular
                # asset, so failing their build over one indexed PNG is
                # answering a question nobody asked, with a remedy that
                # points at an attribute they never wrote. Warn and
                # requantize, which is exactly what the flag requested.
                if strict:
                    raise ValueError(
                        f"image: {src!r} is an indexed PNG at "
                        f"{raw.size[0]}x{raw.size[1]} but is laid out at "
                        f"{w}x{h}. Indexed sources are baked verbatim to "
                        f"preserve their palette, which resizing cannot "
                        f"do. Author it at the laid-out size, or remove "
                        f"`palettize` to have it requantized instead."
                    )
                print(
                    f"warning: {src!r} is an indexed PNG at "
                    f"{raw.size[0]}x{raw.size[1]} laid out at {w}x{h}; "
                    f"--palettize-images requantized it, so its authored "
                    f"palette and index values did not survive. Author it "
                    f"at the laid-out size to keep them.",
                    file=sys.stderr,
                )
            elif palettize and raw.mode == "P":
                pal = raw.getpalette(rawmode="RGBA") or []
                self.cluts.append(self._clut_from_palette(pal))
                self.textures.append(BakedTexture(
                    gs.PSMT8, w, h, len(self.cluts) - 1, raw.tobytes(),
                ))
                self._images[key] = len(self.textures) - 1
                return self._images[key]

            img = raw.convert("RGBA")
            if img.size != (w, h):
                img = img.resize((w, h), Image.LANCZOS)
            if palettize:
                # FASTOCTREE is the quantizer that keeps RGBA (alpha
                # lands in the palette entries, not a separate band).
                q = img.quantize(colors=256, method=Image.Quantize.FASTOCTREE)
                self.cluts.append(
                    self._clut_from_palette(q.getpalette(rawmode="RGBA")))
                self.textures.append(BakedTexture(
                    gs.PSMT8, w, h, len(self.cluts) - 1, q.tobytes(),
                ))
            else:
                self.textures.append(BakedTexture(
                    gs.PSMCT32, w, h, None, gs.encode_psmct32(img.getdata()),
                ))
            self._images[key] = len(self.textures) - 1
        return self._images[key]

    def _streamed_texture(self, name: str, w: int, h: int) -> int:
        """A slot the app fills at runtime: geometry, a name and a
        reservation, no texels (uib v6 §3).

        PSMCT32 only. A palettized streamed slot would have to name a
        CLUT that exists at bake time, and nothing authors one yet --
        deferring is better than inventing a syntax the runtime has
        never been asked to read.

        Two elements naming the same slot share one texture, which is
        the point of a name. At different sizes they cannot: the
        reservation is one number and the app is told one number, so
        that is an authoring error rather than a silent pick."""
        prev = self._streamed.get(name)
        if prev is not None:
            t = self.textures[prev]
            if (t.width, t.height) != (w, h):
                raise ValueError(
                    f"image: streamed slot {name!r} is laid out at "
                    f"{t.width}x{t.height} in one place and {w}x{h} in "
                    f"another; a slot has one reservation, so give them "
                    f"the same size or different names"
                )
            return prev
        self.textures.append(BakedTexture(
            gs.PSMCT32, w, h, None, b"",
            kind=TEXKIND_STREAMED, name=name, reservation=w * h * 4,
        ))
        self._streamed[name] = len(self.textures) - 1
        return self._streamed[name]

    def _flatten_image(self, cmd):
        state = _STATE_NAMES[cmd["state"]]
        focus = self._focus_of(cmd)
        x, y, w, h = cmd["x"], cmd["y"], cmd["w"], cmd["h"]
        if w <= 0 or h <= 0:
            return
        if cmd.get("streamed"):
            tex = self._streamed_texture(cmd["name"], w, h)
            self.records.append(DrawRecord(
                OP_TEXQUAD, state, focus, x, y, w, h, (128, 128, 128, 128),
                tex, 0, 0, w, h,
            ))
            return
        # Both opt-ins reach the texture builder separately: only the
        # per-image attribute is a claim about indices, so only it
        # refuses to requantize one.
        attr = bool(cmd.get("palettize"))
        tex = self._image_texture(
            cmd["src"], w, h, attr or self.palettize_all, strict=attr,
        )
        # Identity tint in the modulate domain; the texels carry the art.
        self.records.append(DrawRecord(
            OP_TEXQUAD, state, focus, x, y, w, h, (128, 128, 128, 128),
            tex, 0, 0, w, h,
        ))

    # --------------------------------------------------------------- text

    def _flatten_text(self, cmd):
        state = _STATE_NAMES[cmd["state"]]
        focus = self._focus_of(cmd)
        builder, tex = self._atlas_for(cmd["weight"], cmd["size"])
        tint = self._gs_modulate_color(cmd["color"])
        tint_var = cmd.get("colorVar")
        tint_vec = self._gs_vec(self._gs_modulate_color, cmd.get("colorThemes"))
        pen_x = cmd["x"]
        top_y = cmd["y"]
        spacing = cmd.get("letterSpacing", 0)
        # The same pen walk as layout's Font.layout(): kern before the
        # glyph, draw, then advance. Both hosts must place glyph n at
        # the same integer x, because layout sized the box and this
        # draws into it.
        prev_cp = None
        for ch in cmd["text"]:
            cp = ord(ch)
            if prev_cp is not None:
                pen_x += spacing + builder.kern(prev_cp, cp)
            glyph = builder.add(ch)
            if glyph.w > 0:
                self.records.append(DrawRecord(
                    OP_TEXQUAD, state, focus,
                    pen_x + glyph.bearing_x, top_y + glyph.bearing_y,
                    glyph.w, glyph.h, tint,
                    tex, glyph.u, glyph.v, glyph.u + glyph.w, glyph.v + glyph.h,
                    var=tint_var, rgba_themes=tint_vec,
                ))
            pen_x += glyph.advance
            prev_cp = cp

    # ---------------------------------------------------------------- run

    def run(self) -> None:
        """Single-screen compatibility wrapper."""
        self.run_screens([("main", self.ir)])

    def _trim_dead_geometry(self, first, canvas):
        """Drop draw records that cannot produce a pixel (backlog F24).

        A `nowrap` run inside `overflow: hidden` bakes every glyph and
        lets the GS clip, so the tail of a long string is quads the
        console submits every frame and can never see. ps2ui-check found
        twenty of them in the channel-6 probe on its first run.

        The scissor model lives in clip.py, shared with ps2ui-check so
        the two cannot drift; see that module for why sharing it is the
        right call here. Removing a record that could never draw cannot
        change the image, which is the property that makes this safe:
        the example previews are byte-identical across this change.
        """
        # Imported here, not at module scope: clip.py takes the op
        # codes from this module, and a top-level import either way
        # closes the cycle.
        from . import clip as clip_mod
        dead = set(clip_mod.dead_indices(
            self.records, first, len(self.records) - first,
            canvas["w"], canvas["h"]))
        # data-keep survives. The trim's safety argument is "removing a
        # record that could never draw cannot change the image", and
        # that is exactly what makes a deliberately-clipped quad
        # useless as an instrument: bring-up step 7 needs geometry that
        # provably cannot draw, so that seeing it on a television means
        # the scissor is not being applied. Trimming it would delete
        # the test.
        dead -= {i for i in dead if self.records[i].keep}
        if not dead:
            return 0
        self.records[first:] = [
            r for i, r in enumerate(self.records[first:], start=first)
            if i not in dead
        ]
        return len(dead)

    def run_screens(self, named_irs) -> None:
        """Flatten several IRs into one blob (backlog F4).

        named_irs: [(screen_name, ir), ...]. Textures, CLUTs, patches,
        atlases and font tables are shared/deduped across screens (one
        Flattener = one texture space). Commands, focus nodes and slots
        concatenate into contiguous per-screen ranges; focus indices
        become global, with each screen's D-pad graph only linking
        inside its own range."""
        canvas = named_irs[0][1]["canvas"]
        for name, ir in named_irs:
            if ir["canvas"] != canvas:
                raise ValueError(
                    f"screen {name!r}: canvas {ir['canvas']} differs from "
                    f"{canvas} — all screens share one video mode")

        for name, ir in named_irs:
            self.ir = ir
            base = len(self.focus_nodes)
            self.focus_index = {
                n["id"]: base + i for i, n in enumerate(ir["focus"]["nodes"])
            }
            for i, n in enumerate(ir["focus"]["nodes"]):
                def gidx(v):
                    return self.focus_index[v] if v is not None else None
                self.focus_nodes.append({
                    "id": base + i, "name": n["name"], "rect": n["rect"],
                    "up": gidx(n["up"]), "down": gidx(n["down"]),
                    "left": gidx(n["left"]), "right": gidx(n["right"]),
                })

            cmd_first = len(self.records)
            slot_first = len(self.slots)
            for cmd in ir["commands"]:
                op = cmd["op"]
                if op == "rect":
                    self._flatten_rect(cmd)
                elif op == "text":
                    self._flatten_text(cmd)
                elif op == "image":
                    self._flatten_image(cmd)
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
            self.dropped += self._trim_dead_geometry(cmd_first, canvas)
            self._collect_slots()

            initial = ir["focus"]["initial"]
            self.screens.append({
                "name": name,
                "cmd_first": cmd_first,
                "cmd_count": len(self.records) - cmd_first,
                "focus_first": base,
                "focus_count": len(self.focus_nodes) - base,
                "slot_first": slot_first,
                "slot_count": len(self.slots) - slot_first,
                "initial": self.focus_index.get(initial) if initial is not None else None,
            })

        # Slots registered glyphs into the shared atlases, so they must
        # finish before the atlas textures freeze.
        self._finish_slots()
        self._finish_atlases()

    def _finish_atlases(self):
        clut = self._coverage_clut_index() if self._atlases else None
        for (bucket, size), (builder, tex_index) in self._atlases.items():
            atlas = builder.build()
            self.textures[tex_index] = BakedTexture(
                gs.PSMT8, atlas.image.width, atlas.image.height,
                clut, gs.encode_psmt8(atlas.image.getdata()),
            )

    # ------------------------------------------------------ dynamic text

    def _collect_slots(self):
        """Turn IR slots into .uib slot entries + full glyph tables.

        A slot's text arrives at runtime, so its font atlas must carry
        the whole metrics charset (not just the glyphs static text
        happened to use) and export a searchable glyph table. Colors
        cross into the modulate domain here, same as static text.

        Appends to self.slots/self.fonts — called once per screen, with
        font tables deduped across screens via self._font_index."""
        font_index = self._font_index
        for sl in self.ir.get("slots", []):
            builder, tex_index = self._atlas_for(sl["weight"], sl["size"])
            key = ("bold" if sl["weight"] >= 600 else "regular", sl["size"])
            if key not in font_index:
                # Full charset: every codepoint the metrics know.
                for cp_str in builder.metrics["advances"]:
                    builder.add(chr(int(cp_str)))
                builder.add("…")  # the runtime ellipsis
                line_h = sl.get("lineHeight") or (
                    builder.metrics_ascent_px
                    + glyph_advance_px(builder.metrics["descent"], sl["size"]))
                self.fonts.append({
                    "tex": tex_index,
                    "size": sl["size"],
                    "weight": sl["weight"],
                    "ascent": builder.metrics_ascent_px,
                    "line_height": line_h,
                    "glyphs": [],  # filled in _finish_slots from the builder
                    "_builder": builder,
                })
                font_index[key] = len(self.fonts) - 1
            self.slots.append({
                "name": sl["name"],
                "placeholder": sl["placeholder"],
                "x": sl["x"], "text_y": sl["textY"], "w": sl["w"],
                "font": font_index[key],
                "align": {"left": 0, "center": 1, "right": 2}.get(sl["align"], 0),
                "letter_spacing": self._slot_spacing(sl),
                "ellipsis": bool(sl["ellipsis"]),
                # Not clamped. This was min(capacity, 95) -- 95 being
                # PS2UI_SLOT_BUFSZ - 1, the runtime's old fixed per-slot
                # buffer. That buffer is gone (v6 resource model): the
                # runtime sizes each slot from the capacity recorded
                # here, so clamping silently gave an author who asked
                # for 200 a 95-byte slot, with no warning at bake and
                # truncated text at runtime. The bound that remains is
                # the format's own uint16, enforced in caps.check.
                "capacity": int(sl["capacity"]),
                "focus": self.focus_index.get(sl.get("focusId"), FOCUS_NONE)
                if sl.get("focusId") is not None else FOCUS_NONE,
                "color_base": self._gs_modulate_color(sl["colorBase"]),
                "color_focus": self._gs_modulate_color(sl["colorFocus"]),
                "color_base_var": sl.get("colorBaseVar"),
                "color_focus_var": sl.get("colorFocusVar"),
                "color_base_themes": self._gs_vec(
                    self._gs_modulate_color, sl.get("colorBaseThemes")),
                "color_focus_themes": self._gs_vec(
                    self._gs_modulate_color, sl.get("colorFocusThemes")),
            })

    def _finish_slots(self):
        for f in self.fonts:
            builder = f.pop("_builder")
            f["kerns"] = self._kern_table(builder)
            f["glyphs"] = [{
                "codepoint": g.codepoint, "u": g.u, "v": g.v,
                "w": g.w, "h": g.h,
                "bearing_x": g.bearing_x, "bearing_y": g.bearing_y,
                "advance": g.advance,
            } for g in builder.glyphs.values()]

    @staticmethod
    def _slot_spacing(sl):
        """The slot entry stores letter-spacing as an i16. Out of range
        would die in struct.pack with a message naming nothing; refuse
        here naming the slot, like every other does-not-fit error."""
        v = int(sl.get("letterSpacing", 0))
        if not -32768 <= v <= 32767:
            raise ValueError(
                f"slot \"{sl['name']}\": letter-spacing {v}px does not fit "
                f"the format's i16 field (-32768..32767px). If this is not "
                f"a typo, the .uib slot entry is the thing to change.")
        return v

    @staticmethod
    def _kern_table(builder):
        """Kern pairs for one baked font, resolved to pixels at its size.

        The runtime cannot divide by 1000 per glyph pair, so the pairs
        are pre-rounded here by the same rule both hosts already use.
        Most of the metrics' pairs round to zero at UI sizes and are
        dropped: a sub-em adjustment only survives once the text is
        large, which is exactly where kerning is visible.

        Restricted to pairs whose codepoints the font actually baked --
        a kern for a glyph not in the atlas can never be looked up, and
        would only cost blob.
        """
        have = builder.glyphs.keys()
        pairs = []
        for key, units in builder.kerning.items():
            prev_s, cur_s = key.split(",")
            prev, cur = int(prev_s), int(cur_s)
            if prev not in have or cur not in have:
                continue
            amount = kern_px(units, builder.size)
            if amount:
                pairs.append({"prev": prev, "cur": cur, "amount": amount})
        # Sorted so the runtime can binary search, same as the glyphs.
        pairs.sort(key=lambda k: (k["prev"], k["cur"]))
        return pairs
