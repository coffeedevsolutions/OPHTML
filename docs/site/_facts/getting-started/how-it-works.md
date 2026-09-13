# facts: getting-started/how-it-works

This page emits no new facts. It is a concept page: every claim cites a
fact id a parent page already verified. No command ran in this session; the
table below lists which parent id backs each claim and where that id lives.

| id | fact | source | verified by | status |
|---|---|---|---|---|
| ir.version | `ui.json` carries `version: 1`; the baker refuses any other value before reading anything else | reference/ir-format | parent fact `ir.version` in `_facts/reference/ir-format.md` | verified |
| ir.schema | `ui.json` top-level keys, in emission order: `version`, `canvas`, `fonts`, `themes`, `commands`, `focus`, `slots`, `warnings` | reference/ir-format | parent fact `ir.schema` in `_facts/reference/ir-format.md` | verified |
| ir.baker.reads | The baker reads `canvas`, `commands`, `focus`, `slots` and `warnings` from `ui.json`; it does not read `fonts`, `canvas.par` or `canvas.display` | reference/ir-format | parent fact `ir.baker.reads` in `_facts/reference/ir-format.md` | verified |
| ir.geometry.integral | Every `x`, `y`, `w`, `h` on every emitted command is an integer, fixed at compile time | reference/ir-format | parent fact `ir.geometry.integral` in `_facts/reference/ir-format.md` | verified |
| ir.geometry.focus-paint-only | A `:focus` rule that changes geometry is a compile error, so a focused and an unfocused command share one layout | reference/ir-format | parent fact `ir.geometry.focus-paint-only` in `_facts/reference/ir-format.md` | verified |
| ir.multi-screen | One `ui.json` is one screen; several files become named screens in one blob | reference/ir-format | parent fact `ir.multi-screen` in `_facts/reference/ir-format.md` | verified |
| uib.header.magic | The `.uib` magic is 0x31424955, the format version is 7 | reference/uib-format | parent fact `uib.header.magic` in `_facts/reference/uib-format.md` | verified |
| uib.layout.order | A `.uib` is a header, eight fixed-stride tables, padding to 16 bytes, then the blob | reference/uib-format | parent fact `uib.layout.order` in `_facts/reference/uib-format.md` | verified |
| uib.invariants.crc | The blob carries its own CRC-32, recomputed by `ps2ui_load` at every load | reference/uib-format | parent fact `uib.invariants.crc` in `_facts/reference/uib-format.md` | verified |
| uib.pledge | v7 is the last incompatible layout; new behaviour is a feature bit, held by `tools/check-format-frozen.py` | reference/uib-format | parent fact `uib.pledge` in `_facts/reference/uib-format.md` | verified |
| uib.pledge.version-hold | `PS2UI_VERSION` in the runtime header equals the baker's format version, both 7; `tools/check-versions.py` holds them equal | reference/uib-format | parent fact `uib.pledge.version-hold` in `_facts/reference/uib-format.md` | contradicts-readme |
| loop.order | The runtime lifecycle: size the arena, declare it, `ps2ui_load`, `ps2ui_upload` once, then per frame clear, `ps2ui_render`, flip | runtime/frame-loop | parent fact `loop.order` in `_facts/runtime/frame-loop.md` | verified |
| loop.never-clears | `ps2ui_render` issues no clear and computes no layout; it replays the command list the build baked | runtime/frame-loop | parent fact `loop.never-clears` in `_facts/runtime/frame-loop.md` | verified |
| loop.geometry.on-canvas | Every primitive a render submits lies inside the canvas rectangle, because the geometry was fixed at build time | runtime/frame-loop | parent fact `loop.geometry.on-canvas` in `_facts/runtime/frame-loop.md` | verified |
| loop.no-unload | There is no unload, free, close or destroy entry point; the 29 public functions are the whole runtime API | runtime/frame-loop | parent fact `loop.no-unload` in `_facts/runtime/frame-loop.md` | verified |
| arena.validate-first | The arena is carved only after every blob check passes, so a refused load never touches it | runtime/frame-loop | parent fact `arena.validate-first` in `_facts/runtime/frame-loop.md` | verified |
| loop.version.constant | `PS2UI_VERSION` is the frozen `.uib` format version, 7, checked by `ps2ui_load`; the runtime never negotiates a format | runtime/frame-loop | parent fact `loop.version.constant` in `_facts/runtime/frame-loop.md` | contradicts-readme |
| fonts.weight-rule | There is no weight axis. `font-weight >= 600` selects the bold face, both compiler and baker apply the same test | authoring/text-and-fonts | parent fact `fonts.weight-rule` in `_facts/authoring/text-and-fonts.md` | verified |
| fonts.weight.ir | `ui.json` carries the CSS weight number, not the face name; the split into a face happens on each side of the seam | authoring/text-and-fonts | parent fact `fonts.weight.ir` in `_facts/authoring/text-and-fonts.md` | verified |
| text.rounding.cross-language | The layout pen and the baker pen place every glyph of a test corpus on the same pixel, across sizes and letter-spacings | authoring/text-and-fonts | parent fact `text.rounding.cross-language` in `_facts/authoring/text-and-fonts.md` | verified |
| text.missing-glyph.three-pens | Three pens diverge on a missing glyph: the layout pen only measures the `?` advance, the baker's atlas rasterizes the real character, the runtime and blob pen substitute the `?` glyph outright | authoring/text-and-fonts | parent fact `text.missing-glyph.three-pens` in `_facts/authoring/text-and-fonts.md` | verified |
| serve.frames | The previewer renders every frame with `preview.render` server-side and serves PNG bytes; the browser never draws UI pixels | cli/previewer | parent fact `serve.frames` in `_facts/cli/previewer.md` | verified |
| serve.aspects | The previewer offers four aspect modes: `framebuffer`, `authored`, `force-4:3`, `force-16:9`, all resamplings of the one render | cli/previewer | parent fact `serve.aspects` in `_facts/cli/previewer.md` | verified |
| serve.limits | The previewer cannot show `ps2ui_visible_set` and the list window, a hardware fault the command list is innocent of, two screens composited in one frame, or a streamed texture's pixels | cli/previewer | parent fact `serve.limits` in `_facts/cli/previewer.md` | code-only |
| serve.limits.no-jump | A previewer warning names a screen and a message, never a command index, so it cannot jump to the command it is about | cli/previewer | parent fact `serve.limits.no-jump` in `_facts/cli/previewer.md` | verified |

Status column above copies the status the parent facts file recorded for
that id. Two rows are `contradicts-readme`: this page states the truth
column of drift row D12 (`PS2UI_VERSION` is the frozen format version, not
an anti-drift mechanism) and never repeats the claim column.

## disputes

None. No parent fact was found wrong.
