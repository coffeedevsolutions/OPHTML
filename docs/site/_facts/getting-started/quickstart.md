# facts: getting-started/quickstart

Session: all eight `docs/tutorial-uc3.md` blocks (fontgen, the three heredocs,
build, check, `serve --selftest`, `vendor-runtime`) ran in one shell under
`sh -e` from an empty scratch directory,
`/tmp/claude-0/-home-user-OPHTML/6b0c72b8-d98f-5f58-b749-f9808bb620d6/scratchpad/getting-started/quickstart/run/browser`,
with `TTF_REGULAR=/home/user/OPHTML/fonts/vendor/DejaVuSans.ttf` and
`TTF_BOLD=/home/user/OPHTML/fonts/vendor/DejaVuSans-Bold.ttf`. Exit 0. Nothing
under `examples/*/build/` was touched. `ps2ui serve --port 8600` (no
`--selftest`) then ran against that same scratch project, answered a `curl`
with 200, and was stopped by `kill`; port 8600 was confirmed closed
afterwards. A second, separate `ps2ui serve --port 8600` run backed the
Playwright screenshot and was stopped the same way.

Parent facts reused without restatement: `install.commands`,
`install.requirements`, `project.keys`, `project.keys.required`,
`project.refusals`, `cli.ps2ui.subcommands`, `cli.ps2ui.files`,
`cli.ps2ui.vendor-runtime`, `cli.ps2ui.serve.options`,
`cli.ps2ui.serve.selftest`, `cli.ps2ui.serve.port`, `serve.routes`,
`serve.controls`, `serve.aspects`.

| id | fact | source | verified by | status |
|---|---|---|---|---|
| quickstart.blocks | All eight `docs/tutorial-uc3.md` blocks run in order from an empty directory under `sh -e`, exit 0, with no other input than the two TTF paths. | docs/tutorial-uc3.md blocks 1-8; tools/check-tutorial.py (`ASSERTED_BLOCKS = {1, 5, 6, 7}`, `BLOCK` regex, the shim table) | this session: the full transcript below, one shell, exit 0 at the end | verified |
| quickstart.outputs | The arena line, the check trailer and the `--selftest` lines quoted on the page are this session's own output, not copied from `docs/tutorial-uc3.md` or README.md. | packages/baker/ps2ui_bake/ps2ui.py `cmd_build`, `cmd_check`; packages/baker/ps2ui_bake/serve.py `run_selftest` | this session: `ps2ui build` printed `ps2ui-bake: arena 1516 bytes (static uint8_t arena[1516] __attribute__((aligned(16))))`; `ps2ui check` printed `PASS: 51 checks, 0 error(s), 0 warning(s)`; `ps2ui serve --selftest` printed six `ok -` lines and `PASS: 6 route(s)`. Full text under `## quickstart.outputs` below | verified |
| quickstart.arena.blob-specific | The arena figure is a property of this blob (six rows, thirteen slots), not a constant. This session's 1516 differs from README.md's Quick start snippet, which shows `arena[1662]` for a different project. Restates drift row D13; the truth column says quote a bake from this session, which this row does. | packages/baker/ps2ui_bake/ps2ui.py `cmd_build` (prints `arena <N> bytes`); ARCHITECTURE.md drift row D13 | this session's `ps2ui build` line above, compared against README.md's Quick start C snippet | verified |
| quickstart.check.host-figure | `ps2ui check` prints two arena figures, the EE one and a 64-bit host one, because `GSTEXTURE` holds pointers that are 4 bytes on the EE and 8 bytes on a 64-bit host. `ps2ui build` prints only the EE figure. Restates drift row D13's second sentence. | packages/baker/ps2ui_bake/check.py (the arena comment line) | this session: `ps2ui check` printed `# arena: 1516 bytes on the EE (1532 on a 64-bit host; GSTEXTURE holds pointers, so the two differ)` | verified |
| quickstart.serve.live | `ps2ui serve --port 8600` (no flags beyond `--port`) binds `127.0.0.1:8600`, compiles the project once, prints the compiler's line and the URL line, and serves until stopped. The port is free again immediately after the process is killed. Restates parent fact `cli.ps2ui.serve.port` on a different port. | packages/baker/ps2ui_bake/serve.py `run` | this session: printed `ps2ui-layout: 14 paint commands, 6 focusables -> build/serve/library.json` then `ps2ui serve: http://127.0.0.1:8600/ -- ctrl-c to stop`; a `curl` to that URL answered `200`; after `kill`, a TCP connect to `127.0.0.1:8600` was refused | verified |
| quickstart.vendor-runtime.scratch-only | `ps2ui vendor-runtime src/` writes `ps2ui.c` and `ps2ui.h` into `src/` under the scratch project only. Nothing under the repository's `runtime/` or `examples/*/build/` is touched. Restates parent fact `cli.ps2ui.vendor-runtime`; out of scope for this page's prose per the brief (the C side belongs to `runtime/frame-loop`), but run here because it is one of the eight tutorial blocks this page must execute to prove the tutorial still holds end to end. | packages/baker/ps2ui_bake/vendor.py | this session: `ls src/` in the scratch project showed exactly `ps2ui.c` and `ps2ui.h`, both new files; `git status` on the repository shows no change under `runtime/` | verified |
| quickstart.demo.reproducible | The committed sources at `assets/getting-started/quickstart/demo/ui/library.html`, `.../library.css` are the exact files the scratch tutorial run wrote in steps 2-3. Running them through `ps2ui-layout` then `ps2ui-bake` with the repository's own `fonts/fonts.json`, the same two-command chain `authoring/css`'s demo images use, reproduces `preview.png` byte for byte. | packages/layout/bin/ps2ui-layout.js; packages/baker/ps2ui_bake/preview.py | this session: `cmp` between the scratch build's `build/preview.png` and a fresh render from the committed `demo/` sources reported no difference | verified |
| quickstart.project.minimum | The project file this page writes sets `screens`, `css`, `strict` and `montage`; `strict` and `montage` are already optional; the whole accepted key set is `screens`, `css`, `fonts`, `out`, `preview`, `montage`, `previewDisplay`, `mode`, `canvas`, `displayAspect`, `strict`, `minFontSize`, `focusWrap`, `palettizeImages`, `vramBudget`. Restates parent fact `project.keys` without changing its wording. | packages/baker/ps2ui_bake/project.py:39-55 | docs/tutorial-uc3.md step 4; parent fact `project.keys`, not re-verified independently here | verified |

## quickstart.outputs

Fontgen (step 1):

```
ps2ui-fontgen: 115 glyphs, 284 kern pairs -> fonts/default.metrics.json
ps2ui-fontgen: 115 glyphs, 163 kern pairs -> fonts/default-bold.metrics.json
ps2ui-fontgen: manifest -> fonts/fonts.json
```

Build (step 5), trimmed to the two lines the page keeps and the arena line:

```
ps2ui-layout: 14 paint commands, 6 focusables -> build/library.json
ps2ui-bake: 1 screen(s), 24 records, 2 textures (32 KiB baked), 1 CLUTs -> build/ui.uib
ps2ui-bake: arena 1516 bytes (static uint8_t arena[1516] __attribute__((aligned(16))))
ps2ui-bake: preview -> build/preview.png
ps2ui-bake: montage -> build/states.png
```

Check (step 6), trailer:

```
# arena: 1516 bytes on the EE (1532 on a 64-bit host; GSTEXTURE holds pointers, so the two differ)
# build/ui.uib: 640x448 at 4:3, 1 screen(s), 24 commands, 2 textures, 13 slots
PASS: 51 checks, 0 error(s), 0 warning(s)
```

Selftest (step 7):

```
ok - / 29569 bytes
ok - /frame.png 8755 bytes
ok - /state 4859 bytes
ok - /rev 15 bytes
ok - an unknown route is 404
ok - the frame is byte-identical to --preview
PASS: 6 route(s)
```

Live serve (step 8):

```
ps2ui-layout: 14 paint commands, 6 focusables -> build/serve/library.json
ps2ui serve: http://127.0.0.1:8600/ -- ctrl-c to stop
```

## disputes

None. No parent fact was found wrong.
