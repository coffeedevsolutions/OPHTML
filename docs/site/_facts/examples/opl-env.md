# facts: examples/opl-env

Session commands ran from the repository root, `/home/user/OPHTML`. `<scratch>`
is `/tmp/claude-0/-home-user-OPHTML/6b0c72b8-d98f-5f58-b749-f9808bb620d6/scratchpad/examples-opl-env`.
`./examples/opl-env/build.sh` was run exactly once, per this brief's explicit
exception to the standing "never run examples/*/build.sh" rule. `git status
--porcelain examples/opl-env` was empty before and after (`examples/opl-env/build/`
is gitignored). `git diff --exit-code examples/opl-env/screenshots` was run
immediately after the build and exited 0 with no output. `ps2ui-check
examples/opl-env/build/ui.uib`, `python3 tools/check-example-figures.py` and a
direct `examples/opl-env/check.py` run (the last as part of build.sh itself)
were all run against the blob build.sh just wrote, in this session.

`make -C runtime test` was NOT run in this session: `build.sh` does not call
it (see `example.opl-env.build.no-runtime-test` below), and the standing rule
in the orchestrator's preamble is "never run examples/*/build.sh" beyond the
one explicit exception this brief grants for `opl-env`'s own script, which does
not include a runtime-suite invocation to opt into.

Parent facts reused without restatement: `project.keys`, `project.keys.required`,
`project.screen-keys`, `project.screen-name`, `project.resolution`,
`cli.ps2ui.subcommands`, `cli.ps2ui.checkout`, `check.tap-shape`, `check.order`,
`check.arena-note`, `check.arena-note.bake`, `check.ci.wrapper`,
`check.catalogue.03`, `check.catalogue.35`, `check.catalogue.46`,
`theme.index`, `theme.tint-table.keying`, `theme.tint-table.shared-role`,
`theme.tint-table.literal`, `theme.runtime.feature-bit`, `theme.seeing.preview`,
`screens.rules`, `screens.project-file`, `compose.contract`,
`compose.scrim.alpha`, `compose.previewer`, `stream.authoring.form`,
`stream.authoring.shared`, `stream.psmct32-only`, `stream.reservation-charged`.

| id | fact | source | verified by | status |
|---|---|---|---|---|
| example.opl-env.build | `./examples/opl-env/build.sh` compiles all six screens, bakes them into one blob, runs `tools/check-blobs.sh` and the example's own `check.py` against the fresh blob, then re-renders the twelve committed per-theme screenshots from it | examples/opl-env/build.sh:41-75 | ran it once from the repo root; exit 0; last lines pasted on the page; `git status --porcelain examples/opl-env` was empty before and after | verified |
| example.opl-env.build.no-runtime-test | `build.sh`'s own header comment says it runs "the host runtime tests", but the script never invokes `make -C runtime test` or any other C-runtime suite; it runs `ps2ui build`, `tools/check-blobs.sh` and its own Python `check.py`, none of which touch `runtime/` | examples/opl-env/build.sh:1-75 (no `make` or `runtime` token outside comments) | `grep -n "make\|runtime" examples/opl-env/build.sh` in this session matched only the header comment and one unrelated comment line; the build's own stdout in this session shows no `make` invocation or `PASS: N checks, N failure(s)` line in the `test_runtime`/`test-narrow` shape | verified (a repository-document defect, not on the drift list; see `## follow-up`) |
| example.opl-env.screenshots-match | The twelve per-theme screenshots and the local `preview.png`/`states.png` build.sh's run just wrote are byte-identical to the ones already committed under `examples/opl-env/screenshots/` | examples/opl-env/build.sh:55-75 | `git diff --exit-code examples/opl-env/screenshots` exited 0 with no output, run immediately after the build | verified |
| example.opl-env.project | The project file lists six screens sharing one stylesheet, sets `strict: true` and `minFontSize: 11`, and a `preview` and `montage` path; it sets no `mode`, `canvas`, `displayAspect`, `focusWrap`, `palettizeImages` or `vramBudget`, so every one of those takes the baker's default | examples/opl-env/ps2ui.json:1-11 | read; matches parent `project.keys` defaults for the keys it omits | verified |
| example.opl-env.numbers | `ps2ui-check examples/opl-env/build/ui.uib` passes 107 checks with the trailer `640x448 at 4:3, 6 screen(s), 2158 commands, 21 textures, 137 slots`, the arena note `7319 bytes on the EE (7487 on a 64-bit host ...)`, and `ok 104 - VRAM 336 KiB within budget 736 KiB`. `ps2ui-bake`'s own bake line (part of the same build.sh run) reports 2 CLUTs and 10 streamed of the 21 textures. The full table is under `## example.opl-env.numbers` below | packages/baker/ps2ui_bake/check.py (parent `check.tap-shape`, `check.arena-note`); packages/baker/ps2ui_bake/vram.py | `ps2ui-check examples/opl-env/build/ui.uib`, output pasted on the page, exit 0; the same figures were printed by the `build.sh` run moments earlier | verified |
| example.opl-env.check-blobs | `tools/check-blobs.sh` checks this blob with `--strict` alone, no `--allow-dead` or `--allow-hairline`, and states in its own comment that opl-env carries "no exemptions" | tools/check-blobs.sh:28-35 | read; the `build.sh` run's `check-blobs: 1 blob(s) validated` line, exit 0, pasted on the page | verified |
| example.opl-env.ci-step | CI builds and checks this blob in the step named "OPL environment end to end", which runs `./examples/opl-env/build.sh` and nothing else; a later, separate step named "Committed screenshots match the renderer" re-runs `git diff --exit-code` over all three examples' `screenshots/` directories together, and a further step "Example figures match their blobs" runs `tools/check-example-figures.py` | .github/workflows/ci.yml:315-316 (build step), 259-260 (figures step), 329-346 (screenshot-diff step) | read | code-only (the workflow itself was not executed in this session, only the same shell commands it runs, each of which was run directly) |
| example.opl-env.figures-check | `python3 tools/check-example-figures.py` reads the blob `build.sh` just wrote (it does not bake) and diffs seven figures (blob size, arena, screens, slots, focus nodes, textures, fonts) against the fenced block under opl-env's README `## Measurements`, plus four figures `docs/PLAN.md` restates in prose | tools/check-example-figures.py:1-40, 46-70, 111-160 | `python3 tools/check-example-figures.py` printed `ok - opl-env: 7 of 7 documented figures match the blob` and `ok - docs/PLAN.md's 4 restated figures match too`, exit 0, pasted on the page | verified |
| example.opl-env.check-py | The example's own `check.py` (run from `build.sh`, not from the baker's unit suite, because it reads a build artefact) passed 93 checks: the tint table is role-keyed (2 entries share the untinted-art identity), colour lives in two tables that key on the same name (4 shared entries), the palette stays small (28 tints over 2100 painting commands), the second theme row moves 27 of 28 entries and leaves the identity alone, and every one of the six screens carries its own fitting telemetry slot pair | examples/opl-env/check.py:1-26 (module docstring, why here and not the unit suite) | build.sh's own run of `check.py`, `1..93` / `PASS: 93 checks, 0 failure(s)`, pasted on the page | verified |
| example.opl-env.mechanisms | The mechanisms table below; each row names the file and line the example uses it at | examples/opl-env/ui/*.html, ui/opl.css, window.h, check.py, ps2ui.json | grep over the `ui/` files, `window.h` and `ps2ui.json`, lines cited per row | verified |
| example.opl-env.streamed-count | Ten streamed texture slots: nine `row-{i}-art` (28x28, one per library row) and one `det-art` (120x72, the detail cover); the bake's own texture listing confirms 10 `streamed` rows against 11 `baked` rows, 21 total | examples/opl-env/ui/library.html:21; ui/detail.html:13; window.h:19-20 (the `row-0-art .. row-8-art` comment) | `build.sh`'s stdout in this session lists tex[8]-tex[16] and tex[19] as `streamed`, 10 rows total, against `ps2ui-check`'s `ok 6 - the streamed-texture feature bit matches the texture table (10 streamed)` | verified |
| example.opl-env.overlay | `confirm` is a separate screen (not a variant of library or detail) composited over whichever screen is already on the frame; the runtime never clears between the two `ps2ui_render` calls, and dismissing it is a `ps2ui_screen_set` back to the base | examples/opl-env/ui/confirm.html:4-9 | parent fact `compose.contract`; the comment at confirm.html:4-9 states the idiom the runtime facts page proves with `make -C runtime test` | verified (the comment); relies on parent `compose.contract` for the runtime behaviour, not re-run here |
| example.opl-env.theme-count | The blob carries 2 theme rows: `:root` (root, index 0) and `@theme light` (index 1) | examples/opl-env/ui/opl.css:30, 78 | `examples/opl-env/check.py`'s `ok 4 - the blob carries 2 theme rows, expected 2 (:root and @theme light)`, part of the build.sh run; parent fact `theme.index` | verified |
| example.opl-env.slot-count | 137 slots across six screens, none a fixed ceiling: every `data-slot` names a runtime-editable string and every screen also carries a `-telem`/`-telem2` pair for the driver's own readout | examples/opl-env/ui/*.html (`data-slot` on every screen); window.h is unrelated to slot count, it only windows which row shows which item | `ps2ui-check` trailer: `137 slots`; grep for `data-slot=` across `ui/*.html` in this session; parent fact `slot.rules` (not restated) | verified |
| example.opl-env.readme-comparison-stale | **Fixed in #134, and this row was still reading `verified` as though the defect were live.** `examples/opl-env/README.md`'s "Against the memcard example, for scale" line used to state memcard as a "175,120-byte blob ... 808 commands". It now derives every figure from `getsize`/`read_uib` over the built blobs and records the superseded numbers as superseded; the memcard blob built in this session is 176,208 bytes with 1,062 commands. Not a claim this page's brief asks it to verify (`check-example-figures.py` checks only opl-env's own figures and `docs/PLAN.md`, not this comparison sentence), and not fixed here | examples/opl-env/README.md:110-114 | `ls -la examples/memcard/build/ui.uib` (176208 bytes) and `ps2ui-check examples/memcard/build/ui.uib` (`1062 commands`) in this session, both from the memcard build already committed earlier in this run of the tree | fixed in #134, row corrected during the 0.7.0 step 5b audit |

## example.opl-env.numbers

Source: `ps2ui-check examples/opl-env/build/ui.uib` trailer and arena note
(parent `check.arena-note`, `check.tap-shape`), plus the `ps2ui-bake` texture
and VRAM lines from the same `build.sh` run.

| field | value |
|---|---|
| canvas | 640x448 at 4:3 |
| screens | 6 |
| commands | 2158 |
| textures | 21 (10 streamed, 11 baked) |
| CLUTs | 2 |
| slots | 137 |
| focus nodes | 51 |
| fonts | 6 |
| themes | 2 |
| arena, EE | 7319 bytes |
| arena, 64-bit host | 7487 bytes |
| blob size | 269,824 bytes |
| VRAM used | 336 KiB of 736 KiB budget (45%) |

## example.opl-env.mechanisms

| mechanism | where |
|---|---|
| One project file compiles six screens against one shared stylesheet, `--strict` and an 11px slot-text floor | [ps2ui.json](repo:examples/opl-env/ps2ui.json#L1-L8) |
| `data-tex-slot` reserves a streamed texture; nine 28x28 library-row slots and one 120x72 detail cover | [library.html](repo:examples/opl-env/ui/library.html#L21), [detail.html](repo:examples/opl-env/ui/detail.html#L13) |
| A confirm dialog is a separate screen composited over library or detail with no clear between renders | [confirm.html](repo:examples/opl-env/ui/confirm.html#L4-L9) |
| `:root` plus one `@theme` block gives every named colour a second, `light` value | [opl.css](repo:examples/opl-env/ui/opl.css#L30), [opl.css](repo:examples/opl-env/ui/opl.css#L78) |
| `data-repeat` writes out repeated rows, tiles and fields: nine library rows, six detail fields, seven filter facets, three landing resume cards | [library.html](repo:examples/opl-env/ui/library.html#L20), [detail.html](repo:examples/opl-env/ui/detail.html#L16), [filters.html](repo:examples/opl-env/ui/filters.html#L14) |
| `data-slot` on every screen for a driver-owned two-line telemetry readout, scoped by screen name | [library.html](repo:examples/opl-env/ui/library.html#L51-L54) |
| A host-side windowed list keeps nine fixed streamed reservations pointed at a scrolling selection | [window.h](repo:examples/opl-env/window.h#L18-L26) |
| The blob's own theming contract (role-keyed tints, the identity entry, per-screen readout fit) is checked straight off the baked file | [check.py](repo:examples/opl-env/check.py#L1-L26) |

## follow-up

Not on the brief's drift list, found while verifying:

1. `examples/opl-env/build.sh`'s header comment says it runs "the host runtime
   tests" (line 3), but the script never calls `make -C runtime test` or any
   other C-runtime suite. It runs `ps2ui build`, `tools/check-blobs.sh` (a
   blob-format check) and the example's own `check.py` (a theming-contract
   check against the baked bytes). Neither touches `runtime/`. Row
   `example.opl-env.build.no-runtime-test`.
2. `examples/opl-env/README.md`'s scale comparison to memcard ("175,120-byte
   blob, 6 slots, 808 commands") is stale: the memcard blob built in this
   session is 176,208 bytes with 1,062 commands (slots still match at 6).
   `tools/check-example-figures.py` does not check this sentence; it checks
   only opl-env's own measurement block and `docs/PLAN.md`. Row
   `example.opl-env.readme-comparison-stale`.
