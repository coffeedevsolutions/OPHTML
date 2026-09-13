# facts: runtime/first-boot

Session commands behind the rows below, all run from the repository root.

- `python3 tools/make_testcard.py --self-test`
- `python3 tools/read_testcard.py --self-test`
- `make -C runtime syntax-check`
- `python3 tools/make_testcard.py <scratch>/testcard.uib --preview <scratch>/testcard-preview.png`
- `PYTHONPATH=packages/baker python3 -c "from ps2ui_bake.uib import read_uib; from ps2ui_bake import preview; preview.render(read_uib('examples/channel6/build/ui.uib'), screen='probe').save(...)"`
- Re-ran both asset commands with `OUT` substituted per `tools/check-site-assets.py`'s own substitution rule and diffed the result against the committed PNG with `filecmp.cmp(..., shallow=False)`.
- `grep -n "^ifdef" runtime/sample/Makefile` to enumerate every guarded flag.
- `grep -n "make -C runtime/sample" .github/workflows/hw.yml` to read the exact CI build line for each named ELF.

No ps2dev toolchain and no console or emulator exist in this session, so
nothing about what an ELF draws on hardware was reproduced here. Every such
claim is `code-only`, sourced from `docs/bringup.md`'s own hardware log and
`docs/bench-runbook.md`, which this page consolidates rather than re-derives.
`_facts/runtime/deploying.md` does not exist yet (that page is unwritten), so
the "what has actually been verified" framing in this page's brief is drawn
directly from `docs/bringup.md`'s hardware log instead, per this run's
top-level instructions.

| id | fact | source | verified by | status |
|---|---|---|---|---|
| bringup.steps | Ten ordered bring-up steps, each isolating one subsystem before the next is meaningful. Build flag, expected picture and failure reading per step are in `## bringup.steps` below. | docs/bringup.md:114-1343 | table below, cross-checked line by line against docs/bench-runbook.md | code-only |
| bringup.step4.no-bench | Step 4 (`TEX0.TFX`) has no ELF and no bench slot. gsKit hardcodes `TFX = 0` (MODULATE) at every `GS_SETREG_TEX0` site and declares no per-texture TFX field, so tinting has run on every ELF the project has built. | docs/bringup.md:677-716 ("SETTLED BY SOURCE. No bench slot, no ELF, nothing to look at.") | code-only: no console or ps2dev container in this session to re-derive the gsKit header fact independently | code-only |
| bringup.bench-scope | The hardware log records a console or CI-emulator reading for steps 1, 2, 3, 5, 6, 6b, 7, 9 and 10, every one a pass. Step 8 is void, panel-limited. Step 4 carries no reading at all, by design, not as an omission. | docs/bringup.md:18-35 (Hardware log table) | read directly against the table; `_facts/runtime/deploying.md` does not exist yet and this run's instructions say not to read anything for that page, so this row cites docs/bringup.md instead of the brief's suggested deploying.md citation | code-only |
| flags.exist | Every build flag this page names (`MINIMAL`, `PROBE`, `PROBE6`, `STATIC`, `SCREEN`, `LINEAR_CLUT`, `NO_ALPHA`) is declared in `runtime/sample/Makefile` and compiles under the host syntax-check pass. | runtime/sample/Makefile:16-253 | `make -C runtime syntax-check` printed `ok - sample compiles: -DPS2UI_SAMPLE_MINIMAL`, `...PROBE`, `...PROBE6`, `...STATIC`, `...SCREEN`, and `ok - runtime compiles: -DPS2UI_CLUT_PERMUTE=0`, `ok - runtime compiles: -DPS2UI_PRIMALPHA_OFF`; exit 0, no other line failed | verified |
| build.commands | The `make -C runtime/sample` invocation this page gives for each step matches the CI `hw` workflow's own build of that step's ELF (`minimal.elf`, `probe.elf`, `conform.elf`, `conform-linear.elf`, `conform-noalpha.elf`, `probe6.elf`, `probe6-linear.elf`, `testcard.elf`, `ps2ui_sample.elf`). | .github/workflows/hw.yml:239-393 | grepped the workflow for every `make -C runtime/sample` line that names one of those nine `EE_BIN`s | verified |
| probe.cells | The probe screen's seven labelled cells (ALPHA, RADIUS, TYPE, CLIP, IMAGE, ASPECT, FLEX) map to bring-up steps 2, 6, {3, 4, 5}, 7, {3, 5}, 10, and none (FLEX is layout geometry sanity, not a numbered step). | docs/bringup.md:89-99 ("Probe cells to bring-up steps"); examples/channel6/README.md:236-256 ("Reading the probe screen") | the two tables were compared cell by cell; they agree on every cell they both name | verified |
| selftest.testcard | `tools/make_testcard.py --self-test` passes: the wedge is three distinct sizes, finest first, starting at 1px; seven textured quads (three wedge, four corners) are all drawn 1:1; four edge rules are four distinct colours; the step-8 interlace pair differs only in height. | tools/make_testcard.py:180-294 | ran in this session: 19 `ok -` lines, `PASS: 0 failure(s)` | verified |
| selftest.read-testcard | `tools/read_testcard.py --self-test` passes: a correct card reads every rung CRISP; a card whose checkers were mushed to grey reads MUSH, not CRISP; one mushed rung still fails while coarser rungs read patterned; a frame that is not the card reads VOID. | tools/read_testcard.py:169-220 | ran in this session: 5 `ok -` lines, `PASS (0 failure(s))` | verified |
| assets.probe | `assets/runtime/first-boot/probe.png` is the previewer's render of `examples/channel6/build/ui.uib`'s probe screen, the frame every conform.elf reading in this page is compared against. | packages/baker/ps2ui_bake/preview.py | rendered in this session; re-running the recorded command into a scratch path reproduced the committed file byte-for-byte | verified |
| assets.testcard | `assets/runtime/first-boot/testcard.png` is `tools/make_testcard.py`'s own `--preview` output: the resolution wedge, the four edge rules, the four corner checkers and the step-8 interlace pair. | tools/make_testcard.py:297-311 | rendered in this session; re-running the recorded command into a scratch path reproduced the committed file byte-for-byte | verified |

## bringup.steps

Ten rows. `build` is the `make -C runtime/sample` flag(s); several steps
reuse the previous step's ELF, named. Status is `code-only` throughout this
column, since reading the resulting screen needs a console or emulator this
session does not have.

| step | build | hardware/CI reading | source |
|---|---|---|---|
| 1 boot and clear | `MINIMAL=1` | pass, SCPH-50000 | docs/bringup.md:20, :114-141 |
| 2 solid quads, alpha blend | `PROBE=1` | pass (v3), SCPH-50000; Play! confirms geometry, gets per-sprite alpha wrong | docs/bringup.md:21-24, :151-372 |
| 3 CLUT / CSM1 | `STATIC=1 SCREEN=probe UIB=../../examples/channel6/build/ui.uib` (`conform.elf`); A/B with `LINEAR_CLUT=1` (`conform-linear.elf`) | pass, aligned build, SCPH-50000; Play! ground-truth diff passes for the first time | docs/bringup.md:26-27, :30-31, :477-676 |
| 4 text tinting, `TEX0.TFX` | none; settled by source | not run; no bench slot exists for this step | docs/bringup.md:677-716 |
| 5 modulate colour domain | reuses step 3's `conform.elf` | pass, aligned build (grouped with 3/3c/7), SCPH-50000 | docs/bringup.md:30, :822-834 |
| 6 texel and pixel centres | `python3 tools/make_testcard.py testcard.uib --preview expected.png` then `STATIC=1 EE_BIN=testcard.elf UIB=testcard.uib` (`testcard.elf`); `PROBE6=1` (`probe6.elf`) for the 6b column-fault localiser | pass via the faint row, SCPH-50000 (step 6); pass, rebuilt v3, SCPH-50000 (step 6b) | docs/bringup.md:32, :34, :836-1141 |
| 7 scissor nesting | reuses step 3's `conform.elf` | pass, aligned build (grouped with 3/3c/5), SCPH-50000 | docs/bringup.md:30, :1142-1182 |
| 8 interlace | reuses step 6's `testcard.elf` | void, panel-limited (motion-adaptive deinterlacer weaves the fields) | docs/bringup.md:33, :1184-1231 |
| 9 VRAM pressure | `STATIC=1` (default `UIB`, `ps2ui_sample.elf`) | pass, SCPH-50000, full memcard UI | docs/bringup.md:35, :1233-1290 |
| 10 display aspect | reuses step 3's `conform.elf`, probe-aspect cell | pass, SCPH-50000, 4:3 pillarboxed correctly | docs/bringup.md:25, :1292-1343 |
