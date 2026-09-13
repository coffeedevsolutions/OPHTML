# facts: project/glossary

This page states no new facts. Every row below names the parent fact id a
glossary definition restates, with the parent page as source. The status is
the one the parent facts file recorded; none of it was re-verified here.

| id | fact | source | verified by | status |
|---|---|---|---|---|
| arena.contract | The arena is caller-provided, at least `ps2ui_arena_size()` bytes, `PS2UI_ARENA_ALIGN` (16) aligned, and must stay alive for the context's lifetime | runtime/frame-loop | cited from `_facts/runtime/frame-loop.md` | verified |
| text.missing-glyph.three-pens | The baker's atlas uses the `?` advance and rasterizes the real character from the TTF; the runtime and blob pen substitute the `?` glyph | authoring/text-and-fonts | cited from `_facts/authoring/text-and-fonts.md` | verified |
| fonts.manifest.two-readers | `ps2ui-layout --fonts` reads only `metrics`; `ps2ui-bake --fonts` reads `ttf` and `metrics`. Only the baker rasterizes | authoring/text-and-fonts | cited from `_facts/authoring/text-and-fonts.md` | verified |
| uib.invariants | The blob section starts on a 16-aligned file offset; every baked texture's `data_off` is 16-aligned; the runtime refuses a misaligned address | reference/uib-format | cited from `_facts/reference/uib-format.md` | verified |
| uib.invariants.crc | `crc32` at offset 48 is the zlib CRC-32 of the whole file with those 4 bytes zeroed; the runtime recomputes it at load | reference/uib-format | cited from `_facts/reference/uib-format.md` | verified |
| clut.contract | `ps2ui_clut_set` repoints one CLUT without moving a texel; every texture sharing the index changes together | runtime/streaming-art | cited from `_facts/runtime/streaming-art.md` | verified |
| api.functions.clut_csm1 | `uint32_t ps2ui_clut_csm1(uint32_t index)` swaps bits 3 and 4 of a CLUT index; exposed for tests | runtime/api-reference | cited from `_facts/runtime/api-reference.md` | verified |
| uib.layout.order | Tables follow the header in the order tex, clut, cmd, focus, font, slot, screen, tint, then padding, then the blob | reference/uib-format | cited from `_facts/reference/uib-format.md` | verified |
| compose.contract | Render never clears, so two `screen_set`/`render` pairs sum into one frame; `ctx->stats` and `gsKit_TexManager_nextFrame` describe only the last render | authoring/screens-and-overlays | cited from `_facts/authoring/screens-and-overlays.md` | verified |
| header.display-aspect | The blob header carries `canvas_w`, `canvas_h`, `display_aspect_num` and `display_aspect_den` as an exact ratio | authoring/video-modes | cited from `_facts/authoring/video-modes.md` | verified |
| focus.node | `focusable` on an element makes one focus node; the node carries the element's laid-out rect and four neighbour ids. Nothing else creates a node | authoring/focus-and-navigation | cited from `_facts/authoring/focus-and-navigation.md` | verified |
| loop.blend.equation | `ps2ui_render` writes `GS_SETREG_ALPHA(0, 1, 0, 1, 0)`, which is `Cv = (Cs - Cd) * As >> 7 + Cd`, every call | runtime/frame-loop | cited from `_facts/runtime/frame-loop.md` | verified |
| loop.clear.app-owns | The app owns the clear; gsKit does not save and restore `PrimAlphaEnable` around `gsKit_clear` | runtime/frame-loop | cited from `_facts/runtime/frame-loop.md` | code-only |
| ir.schema | Top-level IR keys, in emission order: `version`, `canvas`, `fonts`, `themes`, `commands`, `focus`, `slots`, `warnings` | reference/ir-format | cited from `_facts/reference/ir-format.md` | verified |
| text.kerning.sub-em | Kerning is a sub-em adjustment, so a pair's pixel kern shrinks with the size and many pairs round away at small sizes | authoring/text-and-fonts | cited from `_facts/authoring/text-and-fonts.md` | verified |
| list.window.minimum-scroll | The window slides the minimum distance that puts `sel` back on screen, never centring | authoring/lists | cited from `_facts/authoring/lists.md` | verified |
| list.window.no-wrap | A list clamps at both ends and never wraps | authoring/lists | cited from `_facts/authoring/lists.md` | verified |
| uib.records.tint | Tint table is theme-major: row `t` starts at `off_tint + t * n_tint * 4`; each entry is r g b a with alpha in 0..128 | reference/uib-format | cited from `_facts/reference/uib-format.md` | verified |
| serve.montage | `/montage.png` is `preview.montage` of the current screen: one tile per focusable, three per row, that focusable current | cli/previewer | cited from `_facts/cli/previewer.md` | verified |
| uib.records.tex | Texture entry: format u8, kind u8, width u16, height u16, clut u16, data_off u32, data_len u32, name_off u32 | reference/uib-format | cited from `_facts/reference/uib-format.md` | verified |
| aspect.par | `par = (num/den) / (canvasW/canvasH)`, derived from the canvas and display ratio | authoring/video-modes | cited from `_facts/authoring/video-modes.md` | verified |
| text.rounding.pen-walk | The pen is one walk: kern before the glyph, record the position, then advance; `measure`, `wrapText` and `ellipsize` all go through it | authoring/text-and-fonts | cited from `_facts/authoring/text-and-fonts.md` | verified |
| serve.options | `ps2ui serve [project] [--uib BLOB] [--port PORT] [--screen NAME] [--theme THEME] [--no-watch] [--selftest]` | cli/previewer | cited from `_facts/cli/previewer.md` | verified |
| theme.tint-table.keying | An entry is keyed on the pair (var name, whole theme vector). Two use sites of one name collapse to one entry; two literals that agree never collapse into a named one | authoring/theming | cited from `_facts/authoring/theming.md` | verified |
| loop.scissor.restored | `ps2ui_render` reapplies the full-canvas scissor before returning, so a caller drawing after it inherits the whole screen | runtime/frame-loop | cited from `_facts/runtime/frame-loop.md` | verified |
| screens.rules | Each IR passed to one bake becomes a screen named by the IR file's stem; stems must be unique; textures, CLUTs, atlases and font tables are shared across screens; every IR must carry the same canvas | authoring/screens-and-overlays | cited from `_facts/authoring/screens-and-overlays.md` | verified |
| slot.baked | Geometry, font index, size, weight, letter-spacing, alignment, ellipsis policy, both colours and both theme vectors are compiled into the slot record. Only the string arrives at runtime | authoring/dynamic-text | cited from `_facts/authoring/dynamic-text.md` | verified |
| slot.runtime.semantics | `ps2ui_slot_set` copies text into the slot's own buffer, truncates at capacity bytes, and drops a trailing partial UTF-8 sequence | authoring/dynamic-text | cited from `_facts/authoring/dynamic-text.md` | verified |
| stream.authoring.form | A streamed slot is authored as `<img data-tex-slot="NAME">` with explicit width and height and no `src`; the blob carries geometry, the name and a PSMCT32 reservation, and no texels | runtime/streaming-art | cited from `_facts/runtime/streaming-art.md` | verified |
| tex.contract | `ps2ui_tex_set` points a streamed slot at the caller's texels; nothing is copied, and the pointer must stay alive and unmoved | runtime/streaming-art | cited from `_facts/runtime/streaming-art.md` | verified |
| lint.overscan.inset | The title-safe inset is 5% of the canvas per side, rounded, computed from `canvasW`/`canvasH` | authoring/crt-linter | cited from `_facts/authoring/crt-linter.md` | verified |
| uib.header | The header is 84 bytes: magic, version, feature flags, canvas size, counts, offsets, crc32, aspect | reference/uib-format | cited from `_facts/reference/uib-format.md` | verified |
| uib.pledge | v7 is the last incompatible layout; additions go in feature bits; `tools/check-format-frozen.py` holds every struct format string, MAGIC, VERSION and every assigned bit | reference/uib-format | cited from `_facts/reference/uib-format.md` | verified |
| vram.total | `VRAM_TOTAL` is `4 * 1024 * 1024` bytes and `PAGE_BYTES` is 8192 | authoring/vram-budget | cited from `_facts/authoring/vram-budget.md` | verified |
| vram.default-budget | `default_budget(w, h)` returns `VRAM_TOTAL` minus three framebuffers at the canvas size | authoring/vram-budget | cited from `_facts/authoring/vram-budget.md` | verified |

## Follow-up

None found while writing this page. Every claim above restates a parent
fact already marked `verified` or `code-only`; no parent fact was found
wrong.
