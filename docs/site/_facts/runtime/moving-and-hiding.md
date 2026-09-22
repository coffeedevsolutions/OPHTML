# facts: runtime/moving-and-hiding

Session commands were run from the repository root. `<scratch>` is
`/tmp/claude-0/-home-user-OPHTML/6b0c72b8-d98f-5f58-b749-f9808bb620d6/scratchpad/runtime-moving-and-hiding`.

Commands behind the rows below:

- `make -C runtime test` printed `PASS: 5 checks, 0 failure(s)` (test_narrow) and
  `PASS: 410 checks, 0 failure(s)` (test_runtime). "ok N" below is the test_runtime
  numbering as printed.
- `<scratch>/probe.c`, a host program over `examples/memcard/build/ui.uib`. Compiled from
  `runtime/` with
  `cc -std=gnu99 -Wall -Wextra -Werror -O2 -I. -Istub -Ivendor/gsKit -Ivendor/host-shim ps2ui.c stub/gskit_stub.c <scratch>/probe.c build/gsKit_texture_size.o -o <scratch>/probe`,
  exit 0. Its output, verbatim:

  ```text
  focus tile-okami rect at offset (0,0): x=464 y=209 w=128 h=129
  focus tile-okami rect at offset (80,-60): x=464 y=209 w=128 h=129
  hidden tile-okami: visible_get=0 rect x=464 y=209 w=128 h=129
  prims 446 -> 400, skipped_hidden=46 slots_hidden=0
  visible_get unknown name: -1 (PS2UI_VISIBLE_UNKNOWN=-1)
  focus_set reaches the hidden node: 1
  saves: hiding save-ico 310 -> 274 prims, skipped_hidden=24 slots_hidden=1
  library's save-ico: -1 (unknown on this screen)
  after a reset called on saves, library's tile-okami reads 1
  composite: library at (0,-60) drew 446 prims, saves at (0,0) added 310
  offset_set(40000, 0) -> -12, PS2UI_ERR_RANGE=-12, off_x stays 0
  ```

- `python3 -m unittest test_baker.TestPreviewOffset test_baker.TestPreviewOffsetMovesText -v`
  from `packages/baker/tests`: `Ran 5 tests`, `OK`.
- Two compiles under `<scratch>`:
  `ps2ui-layout row.html row.css --fonts fonts/fonts.json -o row.json` and
  `ps2ui-layout row.html row-none.css --fonts fonts/fonts.json -o row-none.json`,
  the second adding `#b { display: none; }` and nothing else.
- Three renders of `examples/memcard/build/ui.uib` through
  `preview.render(..., screen='library', offset=(dx, dy))`, saved under
  `docs/site/assets/runtime/moving-and-hiding/`.
- `ps2ui serve examples/memcard --selftest` printed
  `ok - the framebuffer frame is byte-identical to --preview` and `PASS: 6 route(s)`.
- `ps2ui serve --help`.

Parent facts reused without restatement: `api.functions.visible_set`,
`api.functions.visible_get`, `api.functions.visible_reset`, `api.functions.offset_set`,
`api.functions.offset_get`, `api.functions.move`, `api.functions.focus_set`,
`api.functions.render`, `api.scope.rules.visible`, `api.scope.rules.visible-reset`,
`api.constants.visible-unknown`, `api.structs.ctx-readable`,
`api.structs.ctx-written-through`, `api.structs.stats`, `api.ordering.render-composites`,
`api.ordering.stats-per-render`, `api.drift.focus-rect`, `focus.runtime`,
`focus.runtime.geometry`, `list.api.semantics.apply_visibility`.

| id | fact | source | verified by | status |
|---|---|---|---|---|
| visible.semantics | `ps2ui_visible_set(ctx, name, visible)` clears or sets one bit per focus node. A hidden node's commands are skipped by the render loop, its slots are skipped by the slot loop, and `ps2ui_move` walks past it. The node keeps its rect, nothing reflows, and `ps2ui_focus_set` still reaches it by name. `ps2ui_visible_get` answers 1 shown, 0 hidden, `PS2UI_VISIBLE_UNKNOWN` for a name the current screen does not have | runtime/ps2ui.h:693-730; runtime/ps2ui.c:1117-1120 (command loop), runtime/ps2ui.c:1319-1322 (slot loop), runtime/ps2ui.c:1525-1538 (move), runtime/ps2ui.c:1593-1617 | ok 157-173; `<scratch>/probe` printed `hidden tile-okami: visible_get=0 rect x=464 y=209 w=128 h=129`, `prims 446 -> 400`, `visible_get unknown name: -1` and `focus_set reaches the hidden node: 1` | verified |
| visible.unit | The unit is a focus node's subtree, because that is the only grouping the baked command list carries. A command's `focus` field and a slot's `focus` field are what the two skips test | runtime/ps2ui.h:703-705; runtime/ps2ui.c:897-904 (`node_hidden`), runtime/ps2ui.c:1117, runtime/ps2ui.c:1319 | `<scratch>/probe` hid `save-ico` on the saves screen, which owns slot `save-0`, and printed `skipped_hidden=24 slots_hidden=1`; hiding `tile-okami`, which owns no slot, printed `slots_hidden=0` | verified |
| visible.slots | Slots live outside the command list, so the slot loop repeats the check. Hiding a node removes its glyphs as well as its panel | runtime/ps2ui.c:1315-1322 | `<scratch>/probe`: `saves: hiding save-ico 310 -> 274 prims, skipped_hidden=24 slots_hidden=1` | verified |
| visible.scope | `visible_set` and `visible_get` resolve a name inside the current screen's focus range only, through `focus_index_by_name`. A name on another screen reads `PS2UI_VISIBLE_UNKNOWN` | runtime/ps2ui.c:1557-1572, runtime/ps2ui.c:1593-1617 | parent fact `api.scope.rules.visible`; ok 169-171; `<scratch>/probe` printed `library's save-ico: -1 (unknown on this screen)` | verified |
| visible.reset.scope | `ps2ui_visible_reset` memsets the whole hidden bitmap, sized from the header's `n_focus`, so one call from any screen shows every node in the blob | runtime/ps2ui.c:1619-1624 | parent fact `api.scope.rules.visible-reset`; ok 172, 173; `<scratch>/probe` hid `tile-okami` on library, called reset while `saves` was current, and printed `after a reset called on saves, library's tile-okami reads 1` | verified |
| visible.bits | The bitmap is carved from the arena and sized from `n_focus`, so every node a blob declares can be hidden. There is no fixed ceiling | runtime/ps2ui.h:710-715; runtime/ps2ui.c:899-901, runtime/ps2ui.c:1602-1605 | ok 167 `every focus node on this screen can be hidden and shown` | verified |
| visible.stats | A skipped command increments `stats.skipped_hidden` and a skipped slot increments `stats.slots_hidden`. Hidden records are counted, not lost | runtime/ps2ui.c:1117-1120, runtime/ps2ui.c:1319-1322; runtime/ps2ui.h:310-331 | parent fact `api.structs.stats`; ok 177, 179, 180; `<scratch>/probe`: `prims 446 -> 400, skipped_hidden=46` | verified |
| visible.display-none | `display: none` is compile-time and closes the gap: the box is dropped before layout, the following siblings move up, and no focus node is emitted. Runtime visibility is the other thing, and the only one a fixed command list can offer | packages/layout/src/box.js:176; runtime/ps2ui.h:695-698 | the two `<scratch>` compiles: `row.json` printed `4 paint commands, 3 focusables` with `a [40,40,120,90]`, `b [176,40,120,90]`, `c [312,40,120,90]`; `row-none.json`, differing only by `#b { display: none; }`, printed `3 paint commands, 2 focusables` with `a [40,40,120,90]` and `c [176,40,120,90]` | verified |
| offset.contract | `ps2ui_offset_set(ctx, dx, dy)` sets a draw-time translation applied to every command position the next `ps2ui_render` submits and to every scissor rect derived from a command. It is not applied to the canvas rect the scissor stack is seeded with. Geometry queries keep answering in UI coordinates. Out of int16 returns `PS2UI_ERR_RANGE` and leaves the old offset. It changes no file and no format version | runtime/ps2ui.h:732-767; runtime/ps2ui.c:883-884, runtime/ps2ui.c:1093-1097, runtime/ps2ui.c:1133-1136, runtime/ps2ui.c:1574-1585 | ok 402-410; `<scratch>/probe` printed the same rect for `tile-okami` at offset (0,0) and at (80,-60), and `offset_set(40000, 0) -> -12, PS2UI_ERR_RANGE=-12, off_x stays 0` | verified |
| offset.sinks | The offset is added where coordinates reach gsKit, not at the call sites that read `c->x`. `draw_texquad` adds it for every textured primitive, including the two glyph-pen calls in `render_slots`; the untextured quad path adds it inline | runtime/ps2ui.c:866-891 (the comment and `draw_texquad`), runtime/ps2ui.c:1133-1136 (quad), runtime/ps2ui.c:1369, runtime/ps2ui.c:1387 (glyph pen) | ok 405 `every primitive moved by exactly the offset`; TestPreviewOffsetMovesText exists for the same reason on the host side and passed | verified |
| offset.scissor | A scissor pushed by a command takes the offset, because a panel's clip slides with the panel. The seed rect, `stack[0]`, is built from the canvas size and does not, because it is the display edge. Content pushed far enough is clipped by the display | runtime/ps2ui.c:1083-1097; runtime/ps2ui.h:408-412 | ok 406 (the canvas scissor does not move); the `(0,-60)` render, `docs/site/assets/runtime/moving-and-hiding/offset-up.png`, is cut at the top edge and keeps a full-canvas background | verified |
| offset.queries | Every geometry query stays in UI coordinates, the coordinates the blob was authored in. An app drawing its own art beside the UI adds the offset itself, reading it back with `ps2ui_offset_get` | runtime/ps2ui.h:748-757; runtime/ps2ui.c:1587-1591 | ok 408; `<scratch>/probe` read `ctx.focus_nodes[ctx.focus]` before and after `offset_set(80, -60)` and printed `x=464 y=209 w=128 h=129` both times | verified |
| offset.range | The accepted range is the int16 a command's own x and y use, -32768 to 32767. A refused call returns `PS2UI_ERR_RANGE` and writes neither `off_x` nor `off_y`. A `NULL` context returns `PS2UI_ERR_BOUNDS` | runtime/ps2ui.c:1574-1585 | ok 407; `<scratch>/probe`: `offset_set(40000, 0) -> -12, PS2UI_ERR_RANGE=-12, off_x stays 0` | verified |
| offset.no-format-change | The offset is a transform over commands that already exist. No record, header field or version changed for it, so it works on a blob baked by any 0.x toolchain, and a freshly loaded context starts at (0, 0) | runtime/ps2ui.h:744-747; CHANGELOG.md:1180-1187 | ok 402 `a freshly loaded context has no offset`; ok 409, 410 (setting it back to zero restores the original frame byte for byte); the three renders in this session all read the same unmodified `examples/memcard/build/ui.uib` | verified |
| offset.compose | The offset composes with `ps2ui_render`'s no-clear rule: set an offset, render the scrolling screen, set (0, 0), render the dialog. The second render is not translated | runtime/ps2ui.h:758-760; runtime/ps2ui.c:940 | parent fact `api.ordering.render-composites`; `<scratch>/probe` printed `composite: library at (0,-60) drew 446 prims, saves at (0,0) added 310` into one unreset frame | verified |
| offset.new | The draw-time offset is the 0.6.0 addition (F27). Runtime visibility shipped in 0.3.0 | CHANGELOG.md:1180-1187 (0.6.0 Added); CHANGELOG.md:1714-1716 (0.3.0 Added) | `grep -n '^## ' CHANGELOG.md` puts line 1073 under `## 0.3.0` and line 539 under `## 0.6.0`. The previous version of this row said 541 and 35, which F41(a) showed had drifted into the 0.6.0 offset entry and the open section's prose as the file grew from the top | verified |
| preview.offset | `preview.render(uib, ..., offset=(dx, dy))` is the host mirror of `ps2ui_offset_set`. It applies the offset in `clip_rect`, the funnel every command rect passes through, seeds the scissor stack with an unoffset canvas rect, and raises `ValueError` naming `PS2UI_ERR_RANGE` outside int16 | packages/baker/ps2ui_bake/preview.py:126-128, packages/baker/ps2ui_bake/preview.py:143-151, packages/baker/ps2ui_bake/preview.py:171-177 | `TestPreviewOffset` (4 checks) and `TestPreviewOffsetMovesText` (1 check) ran and passed; the three renders in this session produced `offset-0.png`, `offset-up.png` and `offset-right.png` | verified |
| preview.no-visibility | `preview.render` has no visibility parameter, so `ps2ui_visible_set` and the list-window APIs are outside what the previewer shows. The module states it as a boundary | packages/baker/ps2ui_bake/serve.py:36-43 | `grep -n 'visib' packages/baker/ps2ui_bake/preview.py` matches nothing; the `render` signature at preview.py:126-128 lists `focus_current`, `background`, `slot_text`, `screen`, `tex_fills`, `theme` and `offset` | verified |
| serve.no-offset | Neither `ps2ui serve` nor `ps2ui-bake --preview` has an offset control. `render_png` calls `preview.render` without the `offset` argument, so a served frame is always at (0, 0). The offset is reachable from the Python API only. README.md:372-374 says both commands apply the same offset | packages/baker/ps2ui_bake/serve.py:233-239, packages/baker/ps2ui_bake/serve.py:788-791; README.md:435-438 | `ps2ui serve --help` printed `--uib`, `--port`, `--screen`, `--theme`, `--no-watch`, `--selftest` and no offset flag; `ps2ui-bake --help` printed `--preview`, `--montage`, `--preview-display` and no offset flag; `grep -n offset packages/baker/ps2ui_bake/serve.py packages/baker/ps2ui_bake/cli.py packages/baker/ps2ui_bake/ps2ui.py` matches nothing | contradicts-readme |
| serve.parity | `ps2ui serve --selftest` asserts the served frame is byte-identical to what `--preview` writes, which is what keeps the browser page and the baker one renderer | packages/baker/ps2ui_bake/serve.py:805-822 | `ps2ui serve examples/memcard --selftest` printed `ok - the framebuffer frame is byte-identical to --preview` and `PASS: 6 route(s)` | verified |

## follow-up

`runtime/ps2ui.h:735-741`, the `RENDER-TIME ONLY, DELIBERATELY` paragraph under
`ps2ui_offset_set`, names `ps2ui_focus_rect` as the query that keeps answering in UI
coordinates. That function is not declared anywhere in the header, which drift row D2
already records for the same comment. Recorded here because the paragraph is the one a
reader reaches while looking up the offset, and the accurate replacement is
`ctx->focus_nodes[ctx->focus]`, the field this session read in `<scratch>/probe` to prove
the paragraph's actual claim.

`README.md:435-438` says `ps2ui serve` and `ps2ui-bake --preview` "apply the same offset
(`preview.render(..., offset=(dx, dy))`)". Neither does. `grep -n offset` over `serve.py`,
`cli.py` and `ps2ui.py` matches nothing, `ps2ui serve --help` and `ps2ui-bake --help` list
no offset flag, and `render_png` (serve.py:233-239) calls `preview.render` with
`focus_current`, `screen`, `slot_text` and `theme` only. The parameter exists on
`preview.render` and is reachable from a Python one-liner, which is how this page's three
images were made. Either add the flag and a serve control, or narrow the README sentence
to the Python API. No drift row covers this one.
