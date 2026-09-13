# facts: getting-started/tutorial-game-browser

Session: all eight `docs/tutorial-uc3.md` blocks (fontgen, the three
heredocs, build, check, `serve --selftest`, `vendor-runtime`) ran in one
shell under `sh -e` from an empty scratch directory,
`/tmp/claude-0/-home-user-OPHTML/6b0c72b8-d98f-5f58-b749-f9808bb620d6/scratchpad/getting-started/tutorial-game-browser/run/work/browser`,
with `TTF_REGULAR=/home/user/OPHTML/fonts/vendor/DejaVuSans.ttf` and
`TTF_BOLD=/home/user/OPHTML/fonts/vendor/DejaVuSans-Bold.ttf`. Exit 0.
Nothing under `examples/*/build/` was touched. A copy of
`tools/check-tutorial.py` with `DOC` repointed at
`docs/site/getting-started/tutorial-game-browser.md` and `ROOT` pinned to
the repository root was then run from the repository root: same four
asserted blocks (1, 5, 6, 7), all passing, exit 0.

Parent facts reused without restatement: `quickstart.blocks`,
`quickstart.outputs`, `quickstart.arena.blob-specific`,
`quickstart.check.host-figure`, `quickstart.demo.reproducible`,
`quickstart.project.minimum`, `project.keys`, `project.keys.required`,
`repeat.rules`, `repeat.rules.substitution`, `slot.rules`,
`slot.capacity.default`, `theme.syntax`, `theme.index`,
`loop.checked-form`, `loop.order`, `loop.two-renders`,
`loop.nextframe.once`, `loop.stats.per-render`, `list.model`,
`list.api.semantics`, `list.refill.loop`, `integrate.toolchain`,
`integrate.toolchain.gskit-not-on-path`, `integrate.vendor.behaviour`.

| id | fact | source | verified by | status |
|---|---|---|---|---|
| tutorial.blocks | The eight `docs/tutorial-uc3.md` `sh` blocks, first lines in order: `mkdir -p browser/ui && cd browser`, `cat > ui/library.html <<'EOF'`, `cat > ui/library.css <<'EOF'`, `cat > ps2ui.json <<'EOF'`, `ps2ui build`, `ps2ui check`, `ps2ui serve --selftest`, `ps2ui vendor-runtime src/`. Blocks 1, 5, 6 and 7 carry an asserted output block (`tools/check-tutorial.py` `ASSERTED_BLOCKS`). | docs/tutorial-uc3.md; tools/check-tutorial.py `BLOCK`, `ASSERTED_BLOCKS` | this session: `BLOCK.finditer` over `docs/tutorial-uc3.md` printed the same 8 first lines and the same 4 asserted positions, pasted above | verified |
| tutorial.page.byte-identical | The page's eight `sh` blocks and their four `text` blocks are byte-identical to `docs/tutorial-uc3.md`'s, compared with the same `BLOCK` regex over both files. | tools/check-tutorial.py `BLOCK`; docs/site/getting-started/tutorial-game-browser.md | this session: a script matched `BLOCK` against both files and compared `(cmd, out)` pairs positionally; all 8 pairs equal | verified |
| tutorial.page.checker-passes | A copy of `tools/check-tutorial.py`, `DOC` repointed at this page and `ROOT` pinned to the repository root, reports the same 4 asserted blocks passing and exits 0. | tools/check-tutorial.py | this session: `ok - tutorial block 1: 3 output line(s) as documented` through block 8, then `ok - docs/tutorial-uc3.md: 8 block(s), 4 of 4 asserted as expected, from an empty directory`, exit 0 (the script's own closing line still names the tutorial file; `DOC` was the only path repointed) | verified |
| tutorial.outputs | The fontgen, build, check and `--selftest` output on the page is this session's own run against the tutorial's project, not copied from `docs/tutorial-uc3.md` or README.md. Identical to `quickstart.outputs` because both pages build the same project. | packages/baker/ps2ui_bake/ps2ui.py `cmd_build`, `cmd_check`; packages/baker/ps2ui_bake/serve.py `run_selftest` | this session: `ps2ui build` printed `ps2ui-bake: arena 1516 bytes ...`; `ps2ui check` printed `PASS: 51 checks, 0 error(s), 0 warning(s)`; `ps2ui serve --selftest` printed six `ok -` lines and `PASS: 6 route(s)`, all pasted on the page | verified |
| tutorial.arena.project-specific | The arena figure the page quotes is 1516 bytes, this project's own bake, not README.md's `arena[1662]` (drift D13). `ps2ui check` also prints the 64-bit host figure (1532), which the page's prose does not quote a number for since the checked `text` block that carries it is not part of this tutorial's own asserted output. | packages/baker/ps2ui_bake/ps2ui.py `cmd_build`; ARCHITECTURE.md drift row D13 | this session's `ps2ui build` and `ps2ui check` runs above; `docs/tutorial-uc3.md`'s own step 6 `text` block omits the arena comment line, and the page's step 6 output block matches it exactly (byte-identical block, `tutorial.page.byte-identical`) | verified |
| tutorial.step8.nextframe-order | Step 8's C loop, kept from the tutorial and not executed, calls `gsKit_TexManager_nextFrame` once, after `gsKit_queue_exec`/`gsKit_sync_flip`, never between two renders. This matches `runtime/sample/main.c`'s real loop, which the page's prose states directly rather than repeating drift row D14's claim. | runtime/sample/main.c:2737-2747; ARCHITECTURE.md drift row D14 | read `runtime/sample/main.c` lines 2637-2747 in this session: one `gsKit_TexManager_nextFrame(gs)` call, after the flip, outside the two-render composite branch; parent fact `loop.nextframe.once` | verified |
| tutorial.step8.checked-form | The page's C snippet for load/upload is the checked form from `runtime/sample/main.c` (solid red on a refused load, solid yellow on a refused upload), not the unchecked calls `docs/tutorial-uc3.md`'s own step 8 snippet and README.md's Quick start snippet both show (drift D6 targets the README copy; the tutorial's own snippet has the same shape and is not itself drift-tagged, so this page departs from it here on purpose). | runtime/sample/main.c:1645-1663; ARCHITECTURE.md drift row D6 | read `runtime/sample/main.c` lines 1645-1663 in this session; parent fact `loop.checked-form`; the page's snippet is a trimmed quote of those lines, not the tutorial's own `ps2ui_load(&ui, ...); ps2ui_upload(&ui, gs);` pair | verified |
| tutorial.step8.list-refill | The page's refill loop is the tutorial's own step 8 snippet, unchanged, binding `ps2ui_list_init(&list, "row-", 6)` to the six rows `data-repeat="6"` stamped in step 2. | docs/tutorial-uc3.md step 8; parent fact `list.refill.loop` | this session's step-2 and step-5 builds: `build/library.json` carries focus nodes `row-0`..`row-5`; parent `list.refill.loop` ran the same loop against this project's blob | verified |
| tutorial.assets.preview | `preview.png` is a previewer render of the same committed sources quickstart's own `preview.png` uses (`docs/site/assets/getting-started/quickstart/demo/ui/library.html`, `.css`), and is byte-identical to it. | packages/layout/bin/ps2ui-layout.js; packages/baker/ps2ui_bake/preview.py | this session: `cmp` between `docs/site/assets/getting-started/quickstart/preview.png` and the freshly rendered `docs/site/assets/getting-started/tutorial-game-browser/preview.png` reported no difference | verified |
| tutorial.assets.states | `states.png` is `preview.montage` over a blob baked from the same committed sources, via `ps2ui-bake --montage`, run outside the tutorial's own `sh` blocks so the montage step is not asserted output. | packages/baker/ps2ui_bake/preview.py `montage`; packages/baker/ps2ui_bake/cli.py (`--montage`) | this session: `ps2ui-bake ... --montage docs/site/assets/getting-started/tutorial-game-browser/states.png` wrote a 19382-byte PNG | verified |
| tutorial.assets.serve | `serve.png` is a Playwright capture of `ps2ui serve --port 8700` against the scratch project this session built from the tutorial's own steps 1-4, taken after step 7's `--selftest` run, with no warnings shown. The server was stopped afterward and port 8700 confirmed closed. | packages/baker/ps2ui_bake/serve_page.html | this session: Playwright (`executablePath: /opt/pw-browsers/chromium`, viewport 1280x800) waited for `#frame` to report a `naturalWidth`, then screenshotted; `kill` on the server, then a `curl` to `127.0.0.1:8700` timed out | verified (checked: false per the manifest, browser-chrome capture) |

## disputes

None. No parent fact was found wrong.
