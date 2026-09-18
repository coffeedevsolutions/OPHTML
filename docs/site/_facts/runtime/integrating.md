# facts: runtime/integrating

Session commands behind the rows below. Every one was run in this session.

- `ps2ui vendor-runtime src/` into an empty scratch directory, then a second
  time unchanged, then again after appending a line to `src/ps2ui.h`, then
  `ps2ui vendor-runtime src/ --force`. All four outputs are on the page.
- `ps2ui vendor-runtime mixed/` into a directory holding a hand-written
  `ps2ui.c` and no `ps2ui.h`: exit 1, and `ls mixed/` afterwards printed
  `ps2ui.c` alone.
- `python3 tools/check-runtime-shipped.py` from the repository root: 13 `ok -`
  lines, exit 0. It cleaned up after itself; `packages/baker/ps2ui_bake/runtime`
  does not exist afterwards.
- `make -C runtime test`: 465 lines, exit 0. Line 1 enters, lines 2-28 are
  syntax-check, 29-41 timing-check, 42-49 test-narrow, 50-464 test_runtime.
- `make -C runtime syntax-check CC=clang`: the same 27 `ok -` lines, exit 0.
- `make -C runtime test-compat`: `No rule to make target 'test-compat'`, exit 2.
- `make -C runtime/sample <flags> -n` for thirteen flag combinations, each
  stopping at its `$(error)`, exit 2, nothing written under `runtime/sample`.
- `cc -std=c99 -Wall -Wextra -Werror -fsyntax-only -Istub -Ivendor/gsKit
  -Ivendor/host-shim -I<scratch>/src <scratch>/src/ps2ui.c` from `runtime/`,
  exit 0.
- `grep -n Function runtime/vendor/gsKit/*.h`: no match.
- `grep -rn PS2UI_GSKIT_HAS_FUNCTION .`: three hits outside `docs/site`, all
  prose, none in a C or Makefile source.
- `grep -n 'vendor/' runtime/sample/Makefile`: one comment, no compile flag.

No docker was run: this session has no container runtime, so every claim about
the `ghcr.io/ps2dev/ps2dev` image is quoted from the tool's own output or from
the workflow, and is marked `code-only`.

Line numbers were re-located by symbol in this session.

| id | fact | source | verified by | status |
|---|---|---|---|---|
| integrate.vendor.behaviour | `ps2ui vendor-runtime [dest] [--force] [--starter]` classifies every shipped file before writing any of them, then prints one `wrote <dest>/<name>` per file written, `<names> already up to date.` for byte-identical ones, and `runtime source: <dir> (<label>)` always. | packages/baker/ps2ui_bake/vendor.py:188-223 | the four scratch runs: run 1 printed two `wrote` lines, run 2 printed `ps2ui.c, ps2ui.h already up to date.`, run 3 refused, `--force` printed `wrote src/ps2ui.h` and `ps2ui.c already up to date.` Restates parent `cli.ps2ui.vendor-runtime` | verified |
| integrate.vendor.two-files | Without `--starter` the command writes exactly `ps2ui.c` and `ps2ui.h`. `FILES` is a literal pair, not a glob, and `setup.py`'s `SHIPPED` is the same pair. `--starter` adds `STARTER_FILES`, a second literal pair. | vendor.py:43-46; packages/baker/setup.py:74 | `ls src/` after the first run printed those two names and nothing else; `ShippedListTest.test_setup_py_and_vendor_agree` in packages/baker/tests/test_vendor.py:225 reads the literal back out of setup.py | verified |
| integrate.vendor.starter | `--starter` also writes `main.c` and a `Makefile` that build to `ps2ui_app.elf` as they stand, so a reader who installed from the registries reaches a console without a clone. The two starter files behave differently from the runtime pair: an existing one is never replaced without `--force` and never stops the command, because a `main.c` that differs from this one is the expected end state rather than a fault. | packages/baker/ps2ui_bake/vendor.py:59 (`STARTER_FILES`); vendor.py:240-250; vendor.py `_write_starter` docstring | measured this session from an installed package: `ps2ui vendor-runtime --starter /tmp/st` printed `wrote` for all four of `ps2ui.c`, `ps2ui.h`, `main.c`, `Makefile`; `ls` showed exactly those four; the closing message gave the `ghcr.io/ps2dev/ps2dev make UIB=build/ui.uib` line and `ps2ui vendor-runtime --help` listed `[--force] [--starter] [dest]`. Restates parent fact `integrate.vendor.two-files` for the without-`--starter` case | verified |
| integrate.vendor.source-label | `find_source()` returns the repository `runtime/` labelled `this checkout` when that directory holds both files, and the package's staged `ps2ui_bake/runtime/` labelled `the installed package` otherwise. Two complete copies that disagree refuse the command. | vendor.py:79-129, 131-146 | every scratch run printed `runtime source: /home/user/OPHTML/runtime (this checkout)`; `check-runtime-shipped.py` printed `ok - and it read them from the installed package, not a fallback` for the wheel install; test_vendor.py:72-155 covers all five resolutions | verified |
| integrate.vendor.all-or-nothing | A target file that differs from the shipped runtime stops the whole command. Nothing is written, including the file that was absent, and the exit code is 1. | vendor.py:188-210 | `ps2ui vendor-runtime mixed/` with a hand-written `ps2ui.c` and no `ps2ui.h`: the refusal named `ps2ui.c`, exit 1, and `ls mixed/` printed `ps2ui.c` alone; test_vendor.py:181-197 asserts the same | verified |
| integrate.vendor.force | `--force` overwrites every drifted file and leaves identical ones alone. | vendor.py:212-216 | after the edited header, `ps2ui vendor-runtime src/ --force` printed `wrote src/ps2ui.h` and `ps2ui.c already up to date.`, exit 0; `diff -q src/ps2ui.h runtime/ps2ui.h` was silent | verified |
| integrate.vendor.notes-when-written | The docker line, the three Makefile lines and the two links print only when the run wrote a file. A run with nothing to do returns after the source line. | vendor.py:225-226 (`if not absent and not (args.force and drifted): return 0`) | run 2 printed two lines and stopped; run 1 and the `--force` run printed the full notes | verified |
| integrate.vendor.exit | Exit 0 when files are written and when everything is already up to date. Exit 1 on a drift refusal, on two disagreeing sources, and when neither source exists. | vendor.py:198, 131-160; parent fact `cli.ps2ui.exit-codes` | runs 1, 2 and `--force` exited 0; run 3 and the `mixed/` run exited 1 | verified |
| integrate.vendor.compiles | The two vendored files compile on their own against gsKit's declarations, with no other file from the repository. | runtime/ps2ui.c; runtime/ps2ui.h | `cc -std=c99 -Wall -Wextra -Werror -fsyntax-only -Istub -Ivendor/gsKit -Ivendor/host-shim -I<scratch>/src <scratch>/src/ps2ui.c` from `runtime/`, exit 0, no diagnostics | verified |
| integrate.vendor.wheel | A built wheel and sdist carry `ps2ui_bake/runtime/ps2ui.c` and `ps2ui.h` byte-identical to `runtime/`, and `ps2ui vendor-runtime` run from that wheel outside a checkout reads them from the installed package. | tools/check-runtime-shipped.py:64-200; packages/baker/setup.py:74-110 | `python3 tools/check-runtime-shipped.py` printed 13 `ok -` lines, exit 0 | verified |
| integrate.version | `PS2UI_VERSION` is the frozen `.uib` format version, 7. Baker and runtime match because one package ships both halves, not because the macro moves. | runtime/ps2ui.h:37; vendor.py:15-24, 169-186 | restates parent `constants.version.frozen` and parent `api.constants.version`; README.md:172 says the macro is what stops baker and runtime drifting (D12) | contradicts-readme |
| integrate.toolchain | The PS2 is a MIPS target. `vendor-runtime` prints one cross-compile line, `docker run --rm -v "$PWD:/work" -w /work ghcr.io/ps2dev/ps2dev make`, and three Makefile lines: `EE_CFLAGS  += -I$(PS2DEV)/gsKit/include -I$(PS2SDK)/ports/include`, `EE_LIBS     = -lgskit -ldmakit`, `EE_LDFLAGS += -L$(PS2DEV)/gsKit/lib -L$(PS2SDK)/ports/lib`. | vendor.py:237-252 | the run-1 and `--force` outputs pasted on the page; packages/baker/README.md:36-47 carries the same four lines | verified |
| integrate.toolchain.gskit-not-on-path | The ps2dev image ships gsKit at `$PS2DEV/gsKit` and does not put it on the include path, so `ps2ui.c` cannot find `<gsKit.h>` without the three lines. | vendor.py:245-248; runtime/sample/Makefile:11-13, :254 | code-only: no container runtime in this session, so the image's include path was not inspected. The sample Makefile carries the same three lines and `.github/workflows/hw.yml:163` builds it inside that image | code-only |
| integrate.gskit-pin | `runtime/vendor/gsKit/` holds verbatim public headers from ps2dev/gsKit at commit `43122eb96289167975b56caa45beb71eb8684fa2`, under the Academic Free License 2.0. The ps2dev container CI compiles in is `ghcr.io/ps2dev/ps2dev:latest` and is deliberately unpinned. | runtime/vendor/README.md:3-7; .github/workflows/hw.yml:47-49, :163 | code-only for the commit hash: nothing in the tree re-fetches upstream to compare. The pin's tripwire is the eight `gsKit_texture_size` values in runtime/tests/test_runtime.c, which `make -C runtime test` exercises (PASS: 410 checks) | code-only |
| integrate.gskit.no-tfx | gsKit declares no per-texture TFX field, so `ps2ui.c` sets no `TEX0.TFX` and there is no second gsKit build arm to select between. | runtime/ps2ui.c:607-614; BACKLOG.md:373 (F28); .github/workflows/hw.yml:188-235 | `grep -n Function runtime/vendor/gsKit/*.h` matched nothing at the pinned headers; the container probe in hw.yml watches upstream for the same member and reports without gating | verified |
| integrate.gskit.host-only | The vendored headers are host-only. Only the host Makefile puts `vendor/` on the include path; the console build takes the same headers from PS2SDK. | runtime/vendor/README.md:18-20; runtime/Makefile:104 versus runtime/sample/Makefile:13 | `grep -n 'vendor/' runtime/sample/Makefile` matches one comment at :230 and no compile flag; every `syntax-check` line carries `-Ivendor/gsKit -Ivendor/host-shim` | verified |
| integrate.gskit.texture-size | One gsKit source file is compiled for the host suite, `vendor/gsKit/src/gsTexture.c`, with `-DF_gsKit_texture_size` alone, which yields exactly that function. It is the gsKit value the VRAM preflight depends on. | runtime/Makefile:284-287; runtime/vendor/README.md:25-32 | `make -C runtime test` builds `build/gsKit_texture_size.o` and links it into both test binaries; PASS: 410 and PASS: 5 | verified |
| integrate.test-targets | `runtime/Makefile` declares five targets: `test`, `test-narrow`, `syntax-check`, `timing-check`, `clean`. `test` depends on the other three checks. There is no `test-compat` target and no `PS2UI_GSKIT_HAS_FUNCTION` macro anywhere in the tree. | runtime/Makefile:23, :81, :209, :246, :285, :288 | `make -C runtime test` exit 0; `make -C runtime test-compat` printed `make: *** No rule to make target 'test-compat'.  Stop.`, exit 2; `grep -rn PS2UI_GSKIT_HAS_FUNCTION` over the tree matches no C or Makefile source, only prose: README.md:675, examples/channel6/ui/channel6.css:466 and BACKLOG.md:373. CONTRIBUTING.md:16 tells a contributor to run the missing target (D1, BACKLOG.md F28) | contradicts-readme |
| integrate.test.output | `make -C runtime test` prints 27 `ok -` compile lines, then 13 `ok -` timing lines, then `PASS: 5 checks, 0 failure(s)` from `test_narrow`, then `PASS: 410 checks, 0 failure(s)` from `test_runtime`. | runtime/Makefile:23-24, :209-210, :246-247 | the run in this session, 465 lines, exit 0; parent facts `api.functions.count` and `errors.table` cite the same two PASS lines | verified |
| integrate.syntax-check.variants | `SAMPLE_VARIANTS` holds 11 entries, the first empty. Sixteen further compile lines follow it, so `syntax-check` is 27 compiles: 23 with `-S`, 4 with `-fsyntax-only`. Three of the four compile `ps2ui.c` rather than the sample. | runtime/Makefile:40, :81-198 | the 27 pasted `ok -` lines; the flag split read off Makefile lines 83, 91, 98, 104, 108, 115, 123, 131, 138, 142, 150, 172, 176, 182, 186, 190, 194 | verified |
| integrate.syntax-check.dash-s | The target uses `-S`, not `-fsyntax-only`, because GCC emits `-Wunused-function` during code generation. `HOST_NOASM` probes whether the compiler accepts `-fno-integrated-as` and adds it when it does, which is what stops clang's integrated assembler rejecting the sample's MIPS `mfc0`. That is the assembler and not the frontend: clang still reads the operand constraint, and on arm64 it raises `-Wasm-operand-widths`, which `-Werror` made fatal until the asm was guarded on `__mips__` in main.c. | runtime/Makefile:42-96 | `make -C runtime syntax-check CC=clang` printed 30 `ok -` lines, exit 0 (27 when this row was written; the starter added rows since) | verified |
| integrate.host-tests.scope | The host suite proves struct shape and prototypes against gsKit's real declarations. It does not prove GS behaviour, EE type widths and printf formats, or whether PS2SDK permits an API at all. `hw.yml`'s `elf` job is the arbiter for anything touching PS2SDK. | runtime/vendor/README.md:34-84; runtime/Makefile:33-39 | code-only: the negative claim is about what the host cannot reach, and neither a console nor the ps2dev container is in this session. The documented evidence is the deleted `host-shim/fileio.h`, which made `syntax-check` green for an API newlib rejects at the header | code-only |
| integrate.make.flags | The sample Makefile's flags are in the table under `## integrate.make.flags`. Each sets one `-D` on `EE_CFLAGS`; `USB` also adds `irx_table.o` to `EE_OBJS` and `-lpatches` to `EE_LIBS`. | runtime/sample/Makefile:8-13, :16-253 | the guarded combinations below were run; the rest is read in source, since building any of them needs the ps2dev toolchain | code-only |
| integrate.make.pairing | Thirteen `$(error)` guards. Seven arms refuse to build without `OPLENV=1`: `FILL`, `EE`, `CLEAR_OPAQUE`, `OPLENV_SCREEN`, `CYCLE`, `COMPOSE`, `THEME_CYCLE`. Six pairs are exclusive: `OPLENV_SCREEN` with `THEME_CYCLE`; `CYCLE` with `OPLENV_SCREEN`, `COMPOSE` or `THEME_CYCLE`; `COMPOSE` with `OPLENV_SCREEN` or `THEME_CYCLE`. | runtime/sample/Makefile:82, :102, :121, :132, :135, :147, :150, :153, :156, :171, :174, :177, :187 | `make -C runtime/sample <flags> -n` for all thirteen combinations: each stopped at its `$(error)` with exit 2, before the `$(PS2SDK)` includes and before any recipe ran. `git status --porcelain runtime/sample` was empty afterwards | verified |
| integrate.make.blob | The sample links the blob in as C. `ui_uib.c` comes from `$(PS2SDK)/bin/bin2c $(UIB)`, `UIB` defaults to `../../examples/memcard/build/ui.uib`, and the ELF is `EE_BIN`, default `ps2ui_sample.elf`. | runtime/sample/Makefile:8, :256, :269-270 | code-only: `bin2c` and the two PS2SDK makefile includes are not on this host | code-only |
| integrate.make.copies-runtime | The sample copies `../ps2ui.c` and `../ps2ui.h` next to `main.c` so PS2SDK's implicit `%.o` rule builds them with its full include set. `objclean` removes the copies and the object files without removing the ELF. | runtime/sample/Makefile:260-267, :286-292 | code-only: the rule fires only under the ps2dev toolchain, which is not in this session | code-only |

## integrate.make.flags

`flag` is what a person writes on the `make` command line. Source:
runtime/sample/Makefile:16-253.

| flag | builds | requires |
|---|---|---|
| `STATIC=1` | `-DPS2UI_SAMPLE_STATIC`: holds the baked initial focus instead of cycling it | nothing |
| `MINIMAL=1` | `-DPS2UI_SAMPLE_MINIMAL`: bring-up step 1, clear and hold and exit | nothing |
| `PROBE=1` | `-DPS2UI_SAMPLE_PROBE`: bring-up step 2, four solid-fill cases, no blob | nothing |
| `PROBE6=1` | `-DPS2UI_SAMPLE_PROBE6`: bring-up step 6b, seven columns over a bar pattern | nothing |
| `TELEMETRY=1` | `-DPS2UI_SAMPLE_TELEMETRY`: the once-a-second stats line on stdout | nothing |
| `PROGRESSIVE=1` | `-DPS2UI_SAMPLE_PROGRESSIVE`: 480p output instead of 480i | a display that syncs at 480p |
| `LADDER=1` | `-DPS2UI_SAMPLE_LADDER`: the height ladder, twelve rungs, three arms each | nothing |
| `LADDER2=1` | `-DPS2UI_SAMPLE_LADDER2`: the second ladder instrument | nothing |
| `SCREEN=<name>` | `-DPS2UI_SAMPLE_SCREEN='"<name>"'`: opens on that screen rather than screen 0 | a screen of that name in the blob |
| `COVERS=1` | `-DPS2UI_SAMPLE_COVERS`: the streaming bench, four 128x128 streamed slots | `UIB=../../fixtures/bench-stream/build/bench.uib` |
| `USB=1` | `-DPS2UI_SAMPLE_USB`, plus `irx_table.o` and `-lpatches`: embeds the IOP mass-storage modules | `COVERS=1`; excluded from `syntax-check` |
| `LINEAR_CLUT=1` | `-DPS2UI_CLUT_PERMUTE=0`: uploads CLUTs unpermuted | nothing |
| `NO_SYNC=1` | `-DPS2UI_SKIP_SYNCDCACHE`: drops the cache writeback from `ps2ui_tex_set` | nothing |
| `NO_ALPHA=1` | `-DPS2UI_PRIMALPHA_OFF`: `ps2ui_render` asserts `PrimAlphaEnable` OFF | nothing |
| `OPLENV=1` | `-DPS2UI_SAMPLE_OPLENV`: the opl-env driver | nothing |
| `FILL=1` | `-DPS2UI_OPLENV_FILL`: the fill arm, full-screen blending over the UI | `OPLENV=1` |
| `FILL_N=<n>` | `-DPS2UI_OPLENV_FILL_N=<n>`: sweeps the sprite count | `FILL=1` |
| `EE=1` | `-DPS2UI_OPLENV_EE`: renders the whole UI N extra times | `OPLENV=1` |
| `EE_N=<n>` | `-DPS2UI_OPLENV_EE_N=<n>`: sweeps the extra passes | `EE=1` |
| `CLEAR_OPAQUE=1` | `-DPS2UI_OPLENV_CLEAR_OPAQUE`: the driver's own clear, unblended | `OPLENV=1` |
| `OPLENV_SCREEN=<name>` | `-DPS2UI_OPLENV_SCREEN='"<name>"'`: renders one named opl-env screen | `OPLENV=1`; excludes `THEME_CYCLE` |
| `CYCLE=1` | `-DPS2UI_OPLENV_CYCLE`: walks all six screens in one boot | `OPLENV=1`; excludes `OPLENV_SCREEN`, `COMPOSE`, `THEME_CYCLE` |
| `CYCLE_EVERY=<n>` | `-DPS2UI_OPLENV_CYCLE_EVERY=<n>`: frames per screen | `CYCLE=1` |
| `COMPOSE=1` | `-DPS2UI_OPLENV_COMPOSE`: layers two screens in one frame | `OPLENV=1`; excludes `OPLENV_SCREEN`, `THEME_CYCLE` |
| `THEME_CYCLE=1` | `-DPS2UI_OPLENV_THEME_CYCLE`: switches tint row on a timer | `OPLENV=1`; excludes `OPLENV_SCREEN`, `CYCLE`, `COMPOSE` |

`EE_BIN=<name>` renames the ELF and `UIB=<path>` chooses the blob; neither is
guarded (runtime/sample/Makefile:8, :256).

## integrate.test-targets

Source: runtime/Makefile:23, :81, :209, :246, :285, :288. Verified by the
`make -C runtime test` run above.

| target | runs | output in this session |
|---|---|---|
| `test` | `syntax-check`, `timing-check`, `test-narrow`, then `test_runtime` over five blobs | 465 lines, exit 0 |
| `syntax-check` | 27 compiles of `sample/main.c` and `ps2ui.c` across every build arm | 27 `ok -` lines |
| `timing-check` | `python3 ../tools/check-timing-probe.py`, a source-level ordering check | 13 `ok -` lines |
| `test-narrow` | `ps2ui.c` compiled with `-DPS2UI_ARENA_LIMIT=0xFFFFFFFFull`, over two blobs | `PASS: 5 checks, 0 failure(s)` |
| `clean` | `rm -rf build` | not run |

## follow-up

- `runtime/Makefile:23` lists `test-narrow` last among `test`'s prerequisites,
  so its 5 checks print before the 410 of `test_runtime`. Nothing documents that
  ordering, and a reader who stops at the first `PASS:` line reads the narrow
  suite's count as the whole suite's.
- `packages/baker/ps2ui_bake/vendor.py:242` prints the docker line with `make`
  as the command, but the file the reader has just been handed is two C sources
  with no Makefile beside them. The notes link `runtime/sample/` for the
  Makefile; the line above them would run `make` in a directory that has none.
