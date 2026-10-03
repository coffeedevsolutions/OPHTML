# facts: examples/channel6

Session commands ran from the repository root, `/home/user/OPHTML`. `<scratch>`
is `/tmp/claude-0/-home-user-OPHTML/6b0c72b8-d98f-5f58-b749-f9808bb620d6/scratchpad/examples-channel6`
(created but unused: every command below reads or writes only inside
`examples/channel6/` and `docs/site/assets/examples/channel6/`).
`./examples/channel6/build.sh` was run exactly once, per this brief's explicit
exception to the standing "never run examples/*/build.sh" rule. `git status
--porcelain examples/channel6` was empty before and after (`examples/channel6/build/`
is gitignored). `git diff --exit-code examples/channel6/screenshots` was run
immediately after the build and exited 0 with no output. `ps2ui-check` was run
directly on both blobs, `examples/channel6/check.py` was re-run standalone
against the fresh `ui.uib`, and `tools/check-blobs.sh` was run by name against
both channel6 blobs, all in this session, all against the bytes `build.sh` had
just written.

Parent facts reused without restatement: `project.keys`, `project.screen-keys`,
`project.screen-name`, `project.keys.mode-override`, `project.out-override`,
`project.one-blob`, `cli.ps2ui.subcommands`, `cli.ps2ui.checkout`,
`check.tap-shape`, `check.tap-shape.notes`, `check.order`, `check.arena-note`,
`check.arena-note.bake`, `check.ci.wrapper`, `check.allow.exact`,
`check.catalogue.48`, `screens.rules`, `screens.project-file`,
`screens.canvas.refusal`, `compose.contract`, `compose.previewer.workaround`,
`theme.tint-table.literal`, `theme.runtime.feature-bit`,
`stream.authoring.form` (channel6 uses none of it; cited only to say so).

| id | fact | source | verified by | status |
|---|---|---|---|---|
| example.channel6.build | `./examples/channel6/build.sh` runs `ps2ui build` twice (the 4:3 project default, then a second `--mode ntsc16x9 -o build/ui-16x9.uib` bake of the same project file), renders the probe screen's preview and montage by hand (the project's own `preview`/`montage` keys cover only the `games` screen), composites the browser over a synthetic frame with `preview_in_game.py`, copies four PNGs onto the committed screenshots, then runs `check.py` against the fresh `ui.uib` | examples/channel6/build.sh:24-57 | ran it once from the repo root; exit 0; last lines pasted on the page; `git status --porcelain examples/channel6` was empty before and after | verified |
| example.channel6.screenshots-match | The four screenshots this build.sh run wrote (`games.png`, `probe.png`, `states.png`, `in-game.png`) are byte-identical to the ones already committed under `examples/channel6/screenshots/` | examples/channel6/build.sh:51-55 | `git diff --exit-code examples/channel6/screenshots` exited 0 with no output, run immediately after the build | verified |
| example.channel6.project | The project file lists two screens sharing one stylesheet; `probe.html` alone sets `focusWrap: true`, so the browser dead-ends at its grid edges and the probe screen wraps. It sets no top-level `mode`, `canvas`, `strict`, `vramBudget` or `palettizeImages`, so those take the baker's default; the 16:9 blob is a second `ps2ui build` invocation with `--mode`, `-o`, `--preview-display`, `--preview none`, `--montage none`, not a second project | examples/channel6/ps2ui.json:1-10; examples/channel6/build.sh:15-29 | read; the build.sh run's second `ps2ui build ... --mode ntsc16x9 -o build/ui-16x9.uib` line, exit 0, matches parent `project.keys.mode-override` and `project.one-blob` | verified |
| example.channel6.numbers | `ps2ui-check examples/channel6/build/ui.uib` passes 75 checks with the trailer `640x448 at 4:3, 2 screen(s), 1242 commands, 25 textures, 15 slots`, the arena note `10624 bytes on the EE (10824 on a 64-bit host ...)`, and `ok 72 - VRAM 368 KiB within budget 736 KiB`. The 16:9 blob (`ui-16x9.uib`) reports the identical counts and arena figure, differing only in its trailer's `640x448 at 16:9` and its screen names (`games-16x9`, `probe-16x9`). The bake's own transcript reports 9 CLUTs and 4 fonts (570 kern pairs) neither trailer line carries. The full table is under `## example.channel6.numbers` below | packages/baker/ps2ui_bake/check.py (parent `check.tap-shape`, `check.arena-note`); packages/baker/ps2ui_bake/vram.py | `ps2ui-check examples/channel6/build/ui.uib` and `ps2ui-check examples/channel6/build/ui-16x9.uib`, both output pasted on the page, both exit 0; the same figures were printed by the `build.sh` run moments earlier | verified |
| example.channel6.blob-size | `ui.uib` is 252,624 bytes; `ui-16x9.uib` is 252,640 bytes, 16 bytes larger for the longer screen names (`games-16x9`/`probe-16x9` against `games`/`probe`) | examples/channel6/build/ui.uib, ui-16x9.uib | `ls -la` on both files in this session, in the same run that built them | verified |
| example.channel6.check-blobs | `tools/check-blobs.sh` checks both channel6 blobs with `--allow-dead 1 --strict`, because the probe screen's CLIP cell parks one instrument quad outside its own scissor on purpose (`data-keep`) and the baker's dead-geometry trim cannot tell that apart from waste | tools/check-blobs.sh:43-49 | read; `sh tools/check-blobs.sh examples/channel6/build/ui.uib examples/channel6/build/ui-16x9.uib` printed `PASS: 75 checks, 0 error(s), 0 warning(s)` for each (the one warning `ps2ui-check` shows unflagged becomes an `ok ... declared deliberate` line under `--allow-dead 1`) and `check-blobs: 2 blob(s) validated`, exit 0, pasted on the page | verified |
| example.channel6.ci-steps | CI builds and checks this example across three separate steps: "Channel-6 browser end to end" runs `./examples/channel6/build.sh` and nothing else; "Committed screenshots match the renderer" re-runs `git diff --exit-code` over channel6's `screenshots/` alongside memcard's and opl-env's; "Validate every blob against the runtime's assumptions" runs `tools/check-blobs.sh` by name against both channel6 blobs plus memcard's and opl-env's | .github/workflows/ci.yml:266-277 (build step), 329-346 (screenshot-diff step), 399-420 (check-blobs step) | read | code-only (the workflow itself was not executed in this session, only the same shell commands it runs, each of which was run directly) |
| example.channel6.check-py | The example's own `check.py` (run inside `build.sh`, and re-run standalone in this session against the same blob) passed 47 checks: the format's own count fields, the two screens' focus graphs and D-pad reachability, `games`'s no-wrap dead-end against `probe`'s wrap, both screens' slot capacities and placeholders, the vanish rows for bring-up steps 4 and 5, the CSM1 swizzle tile's authored indices and region order for step 3, and the scissor `data-keep` pair for step 7 | examples/channel6/check.py:1-25 (module docstring, why here and not `make -C runtime test`) | `build.sh`'s own run of `check.py`, `1..47` / `PASS: 47 checks, 0 failure(s)`, pasted on the page; a second standalone run in this session (`PYTHONPATH=packages/baker python3 examples/channel6/check.py examples/channel6/build/ui.uib`) printed the same trailer | verified |
| example.channel6.mechanisms | The mechanisms table below; each row names the file and line the example uses it at | examples/channel6/ui/games.html, ui/probe.html, ui/channel6.css, ps2ui.json, build.sh, preview_in_game.py, check.py | grep over the `ui/` files, `ps2ui.json`, `build.sh`, `preview_in_game.py` and `check.py`, lines cited per row | verified |
| example.channel6.focus-wrap-split | `game-aurora`'s `left` edge is `FOCUS_NONE` (the browser dead-ends) and `probe-type`'s `right` edge is not (the probe screen wraps), the one setting this project varies per screen via the `focusWrap` object form | runtime/ps2ui.c (focus edges, parent `screens.scope`); examples/channel6/ps2ui.json:4 | `check.py`'s own `ok 14 - games does not wrap: left off the first cover dead-ends` and `ok 15 - probe wraps: right off the last column comes back around`, part of the build.sh run and the standalone re-run | verified |
| example.channel6.data-keep | `data-keep` on `.tell` and `.tell-twin` (probe.html:53-54) is the one place this example overrides the baker's dead-geometry trim: without it, the CLIP cell's out-of-clip instrument quad would be deleted at build time on the same reasoning that deletes real waste, and bring-up step 7 would have nothing to prove the scissor is not silently absent | examples/channel6/ui/probe.html:53-54; examples/channel6/ui/channel6.css:395-405 (the comment on why); check.py:356-431 | `check.py`'s `ok 42` through `ok 47` walk the scissor stack this pair depends on, part of both check.py runs in this session; `ps2ui-check`'s unflagged `ok 74` names the same one dead command by index (894) | verified |
| example.channel6.no-repeat-no-theme-no-stream | channel6 has no `data-repeat`, no `@theme`, no `:root` custom property and no `data-tex-slot`: every tile, cell and cover is written out, the blob carries one theme row (`FEAT_ROLE_TINTS` clear), and all 25 textures bake in place, none streamed | examples/channel6/ui/games.html, ui/probe.html, ui/channel6.css | grep for `data-repeat`, `@theme`, `:root`, `data-tex-slot` over `examples/channel6/ui/*` returned nothing; `ps2ui-check`'s `ok 6 - the streamed-texture feature bit matches the texture table (0 streamed)` and `ok 44 - 1 theme(s) with FEAT_ROLE_TINTS clear` | verified |
| example.channel6.readme-check-count-stale | **Fixed in #134, and this row was still reading `verified` as though the defect were live.** `examples/channel6/README.md`'s "Build" section used to say `check.py` runs "24 checks, and a red one names what broke." It now says 47, twice, matching the run. The `check.py` run in this session, both inside `build.sh` and standalone, prints `1..47` / `PASS: 47 checks, 0 failure(s)`. Not a claim this page's brief lists among the ones to verify, and not fixed here | examples/channel6/README.md:106, examples/channel6/README.md:108 | the two `check.py` runs in this session, both `PASS: 47 checks` | fixed in #134, row corrected during the 0.7.0 step 5b audit |
| example.channel6.readme-arena-current | `examples/channel6/README.md`'s "What the runtime's tables cost" section quotes `arena 10624 bytes` and `25 textures, 9 CLUTs, 15 slots, 2 screens` as the current bake's own printed numbers, not a hardcoded snippet; both match this session's build.sh run exactly, so drift row D13 (README.md Quick start's unrelated `arena[1662]`) does not touch this file | examples/channel6/README.md:143-146 | build.sh's own transcript in this session: `runtime tables: 25 textures, 9 CLUTs, 15 slots, 2 screens` and `ps2ui-bake: arena 10624 bytes (static uint8_t arena[10624] ...)`, byte-identical to the README's quoted block | verified |
| example.channel6.readme-fixed-f005 | `examples/channel6/README.md` and `examples/channel6/ui/channel6.css` both name the TYPE cell's tint-not-applied failure without citing a `GSTEXTURE::Function` field, and instead cite finding F-005 (gsKit has no such field). Fixed on this branch, not a drift row this brief lists but confirmed current in this session | examples/channel6/README.md:248; examples/channel6/ui/channel6.css:474 | grep for `GSTEXTURE::Function` and `F-005` over both files in this session, output pasted above | verified |

## example.channel6.numbers

Source: `ps2ui-check examples/channel6/build/ui.uib` trailer and arena note
(parent `check.arena-note`, `check.tap-shape`), the `ps2ui-bake` texture and
VRAM lines, and `ls -la` on both blobs, all from the same `build.sh` run.

| field | value |
|---|---|
| canvas | 640x448 at 4:3 (`ui.uib`); 640x448 at 16:9 (`ui-16x9.uib`) |
| screens | 2 |
| commands | 1242 |
| textures | 25 |
| CLUTs | 9 |
| slots | 15 |
| fonts | 4 |
| kern pairs | 570 |
| dead commands trimmed at bake | 20 |
| dead commands remaining, declared | 1 (of 1, `--allow-dead 1`) |
| arena, EE | 10624 bytes |
| arena, 64-bit host | 10824 bytes |
| VRAM used | 368 KiB of 736 KiB budget (50%) |
| blob size, `ui.uib` | 252,624 bytes |
| blob size, `ui-16x9.uib` | 252,640 bytes |

## example.channel6.mechanisms

| mechanism | where |
|---|---|
| One project file compiles two screens against one shared stylesheet; only `probe.html` sets `focusWrap: true` | examples/channel6/ps2ui.json:1-10 |
| `focusable`/`autofocus` sets initial focus per screen; `games` dead-ends at its grid edges, `probe` wraps | examples/channel6/ui/games.html:18; ui/probe.html:17; ps2ui.json:4 |
| `data-slot` with `data-slot-capacity` for 13 games-screen slots and 2 probe-screen slots | examples/channel6/ui/games.html:12, 20; ui/probe.html:12, 43 |
| `data-keep` protects the CLIP cell's out-of-clip scissor instrument from the bake-time dead-geometry trim | examples/channel6/ui/probe.html:53-54; ui/channel6.css:387-397 |
| A second `ps2ui build --mode ntsc16x9 -o build/ui-16x9.uib` of the same project bakes the widescreen blob; no `variants` key exists | examples/channel6/build.sh:26-29 |
| `preview_in_game.py` renders the blob on full transparency and `alpha_composite`s it over a synthetic driving-game frame | examples/channel6/preview_in_game.py:87-94 |
| `check.py` re-reads the baked blob and asserts the focus graph, slot capacities, vanish-row colours and the swizzle tile's region order, beyond what `ps2ui-check` checks | examples/channel6/check.py:109-433 |

## follow-up

Not on the brief's drift list, found while verifying:

1. `examples/channel6/README.md`'s "Build" section states `check.py` runs "24
   checks, and a red one names what broke." Both runs of `check.py` in this
   session (inside `build.sh` and standalone) print `1..47` and
   `PASS: 47 checks, 0 failure(s)`. Row `example.channel6.readme-check-count-stale`.
