# facts: examples/memcard

Session commands ran from the repository root, `/home/user/OPHTML`. `<scratch>` is
`/tmp/claude-0/-home-user-OPHTML/6b0c72b8-d98f-5f58-b749-f9808bb620d6/scratchpad/examples-memcard`.
`./examples/memcard/build.sh` was run exactly once, per this brief's explicit
exception to the standing "never run examples/*/build.sh" rule. `git status
--porcelain examples/memcard` was clean before and after; `git diff --exit-code
examples/memcard/screenshots` exited 0 both times a diff was checked. A second,
read-only reproduction of the build (`ps2ui build <scratch>/memcard/ps2ui.json`,
a copy of the sources only) was used to capture the full compiler and baker
transcript without a second run of the real build.sh; its blob was not compared
byte-for-byte, but a direct `ps2ui-bake` call on the committed IR files was, and
matched (see `example.memcard.bake-cmd`). `make -C runtime test` was run once
more on its own (the rule permits it) to capture the full PASS lines for both
targets; it reused the default `UIB = ../examples/memcard/build/ui.uib` and
changed nothing under `examples/memcard/`.

Parent facts reused without restatement: `project.keys`, `project.screen-keys`,
`project.screen-name`, `cli.ps2ui.subcommands`, `cli.ps2ui.files`,
`check.tap-shape`, `check.order`, `check.arena-note`, `check.arena-note.bake`,
`check.ci.wrapper`, `slot.capacity.default`, `slot.rules`, `slot.memcard`,
`slot.overflow`, `list.model` (memcard uses none of the list API; cited only to
say so).

| id | fact | source | verified by | status |
|---|---|---|---|---|
| example.memcard.build | `./examples/memcard/build.sh` compiles both screens, bakes them, runs `make -C runtime test` against the fresh blob, then re-renders the three committed screenshots from that blob | examples/memcard/build.sh:18-37 | ran it once from the repo root; exit 0; last lines pasted on the page; `git status --porcelain examples/memcard` was empty before and after | verified |
| example.memcard.screenshots-match | The screenshots this build.sh run wrote are byte-identical to the ones already committed | examples/memcard/build.sh:26-37 | `git diff --exit-code examples/memcard/screenshots` exited 0 with no output, run immediately after the build | verified |
| example.memcard.project | The project file lists two screens sharing one stylesheet and two preview outputs; it sets no `mode`, `canvas`, `focusWrap` or `vramBudget`, so every one of those takes the baker's default | examples/memcard/ps2ui.json:1-6 | read; matches parent `project.keys` defaults for the keys it omits | verified |
| example.memcard.numbers | `ps2ui-check examples/memcard/build/ui.uib` passes 63 checks with the trailer `640x448 at 4:3, 2 screen(s), 1062 commands, 11 textures, 6 slots`, the arena note `1662 bytes on the EE (1750 on a 64-bit host ...)`, and `ok 60 - VRAM 160 KiB within budget 736 KiB` (21%, from the same bake). The full table is under `## example.memcard.numbers` below | packages/baker/ps2ui_bake/check.py (parent `check.tap-shape`, `check.arena-note`, `check.vram.default`); packages/baker/ps2ui_bake/vram.py | `ps2ui-check examples/memcard/build/ui.uib`, output pasted on the page, exit 0; a direct `ps2ui-bake` run in this session printed `textures 163840 B of 753664 B budget (21%)` for the same blob | verified |
| example.memcard.check-blobs | `tools/check-blobs.sh` checks this blob with `--strict` alone, no `--allow-dead` or `--allow-hairline` | tools/check-blobs.sh:28-30 | read; `ps2ui-check examples/memcard/build/ui.uib --strict` printed `PASS: 63 checks, 0 error(s), 0 warning(s)`, exit 0, pasted on the page | verified |
| example.memcard.ci-step | CI builds this blob in the step named "Example builds end to end (includes runtime tests)", which runs `./examples/memcard/build.sh` and nothing else | .github/workflows/ci.yml:153-154 | read | code-only (the workflow itself was not executed in this session, only the same shell command it runs) |
| example.memcard.runtime-tests | `make -C runtime test` runs `test_runtime` (410 checks, this blob plus three generated fixtures) then `test-narrow` (5 checks, this blob plus the huge-arena fixture), in that order, so the narrow suite's `PASS: 5 checks` line prints after the main suite's `PASS: 410 checks` line despite the target list naming `test-narrow` last as a prerequisite | runtime/Makefile:6 (`UIB ?= ../examples/memcard/build/ui.uib`), :23-24, :246-247 | `make -C runtime test` in this session: `PASS: 5 checks, 0 failure(s)` at output line 49, `PASS: 410 checks, 0 failure(s)` at line 464, both exit 0 | verified |
| example.memcard.bake-cmd | A direct `ps2ui-bake` call on the committed IR files reproduces the committed blob byte for byte and prints the arena line the way the baker always prints it: the EE figure only | packages/baker/ps2ui_bake/cli.py (parent `check.arena-note.bake`) | `PYTHONPATH=packages/baker python3 -m ps2ui_bake examples/memcard/build/library.json examples/memcard/build/saves.json -o <scratch>/memcard.uib --fonts fonts/fonts.json` printed `ps2ui-bake: arena 1662 bytes (static uint8_t arena[1662] __attribute__((aligned(16))))`; `cmp` against `examples/memcard/build/ui.uib` reported no difference | verified |
| example.memcard.mechanisms | The mechanisms table below; each row names the file and line the example uses it at | examples/memcard/ui/library.html, ui/saves.html, ui/library.css, ps2ui.json, build.sh | grep over the four `ui/` files and the two project files, lines cited per row | verified |
| example.memcard.no-repeat | memcard has no `data-repeat`, no `@theme` or `:root`, no overlay screen and no streamed texture: every tile and row is written out, the blob carries one theme row, both screens are top-level and every texture is baked in place | examples/memcard/ui/library.html, ui/saves.html; `ps2ui-check` note `n_theme` implied by `ok 44` passing with a single row | grep for `data-repeat`, `@theme`, `:root`, `overlay` and `streamed` over `examples/memcard/ui/*` returned nothing; `ps2ui-check` printed no theme-count or overlay-related failures | verified |

## example.memcard.numbers

Source: `ps2ui-check examples/memcard/build/ui.uib` trailer and arena note (parent `check.arena-note`, `check.tap-shape`), plus the VRAM line.

| field | value |
|---|---|
| canvas | 640x448 at 4:3 |
| screens | 2 |
| commands | 1062 |
| textures | 11 |
| slots | 6 |
| CLUTs | 1 |
| arena, EE | 1662 bytes |
| arena, 64-bit host | 1750 bytes |
| VRAM used | 160 KiB of 736 KiB budget (21%) |

## example.memcard.mechanisms

| mechanism | where |
|---|---|
| One project file compiles two screens against one shared stylesheet | examples/memcard/ps2ui.json:2-3 |
| `focusable` plus `autofocus` sets the initial focus per screen | examples/memcard/ui/library.html:11; ui/saves.html:12 |
| `:focus` changes only fill and border colour; geometry never does | examples/memcard/ui/library.css:48-52, 109-112, 178-181 |
| `data-slot` with `data-slot-capacity` for runtime-editable counts and titles | examples/memcard/ui/library.html:25; ui/saves.html:25, 29, 33, 37, 41 |
| `white-space: nowrap` plus `text-overflow: ellipsis` truncates long titles | examples/memcard/ui/library.css:138-140, 148-150, 186-188 |
| `preview.render` per screen and `preview.montage` for one sheet of every focus state | examples/memcard/build.sh:33-35 |
