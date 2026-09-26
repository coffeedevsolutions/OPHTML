# facts: runtime/deploying

Session commands, all run from the repository root.

- `python3 tools/check-deploying.py`: 23 `ok -` lines, exit 0.
- `make -C runtime syntax-check`: 27 `ok -` lines, exit 0 (restates parent
  `integrate.syntax-check.variants`).
- `grep -n "gsKit_clear(" runtime/sample/main.c` and a second grep
  restricted to the four numeric-literal calls the checker itself matches.
- `grep -n "MINIMAL\|STATIC\|SCREEN\|UIB\s*[?:]\?=" runtime/sample/Makefile`.
- `grep -n -i "play\|pcsx2" .github/workflows/hw.yml`.
- `ls examples/channel6/build/ examples/memcard/build/`: both blobs present
  from the pre-built environment.

No console, no ps2dev container and no emulator binary exist in this
session. Every claim about what a step or a card device does on real
hardware is `code-only`, sourced from `docs/deploying.md` and the parent
facts files, and is out of scope to re-derive per this page's brief (the
hardware log is `project/internals`).

Parent facts reused without restatement: `bringup.steps`, `bringup.bench-scope`,
`build.commands`, `flags.exist` (`runtime/first-boot.md`);
`integrate.make.flags`, `integrate.vendor.behaviour`, `integrate.toolchain`
(`runtime/integrating.md`); `stream.deploy.usb`, `stream.host-format.why-bare`
(`runtime/streaming-art.md`). No parent fact was found wrong; no disputes.

| id | fact | source | verified by | status |
|---|---|---|---|---|
| deploy.paths | The baked `.uib` is compiled into the ELF by `bin2c` at build time. `ps2ui_sample.elf` needs no data file beside it and touches no filesystem at runtime, except streamed textures, which read from `mass:/ps2ui/` and need USB. | docs/deploying.md:28-39; runtime/sample/Makefile:8, runtime/sample/Makefile:269-270 (restates parent `integrate.make.blob`) | code-only: `bin2c` is not on this host. Restated from docs/deploying.md and the parent fact it cites | code-only |
| deploy.paths.table | Four onboard paths from an ELF to a running console: memory card on a multi-channel device, an ordinary memory card, USB, and OPL's apps list. Steps and markers are in the reference table below. | docs/deploying.md:116-203 | read directly against the document; restated, not copied | code-only |
| deploy.status-fills | `runtime/sample/main.c` clears the whole screen to exactly four non-background colours: `#4080c0` (minimal.elf passed), `#800000` (`ps2ui_load` failed), `#808000` (`ps2ui_upload` failed), `#ff00ff` (`ps2ui_screen_set` found no screen of that name). `#0a0e1a` is the UI's own canvas background, not a status, and is excluded by name in the checker. | runtime/sample/main.c:1519 (`0x40,0x80,0xc0`), runtime/sample/main.c:1678 (`0x80,0x00,0x00`), runtime/sample/main.c:1570, 1609, 1639, 1686, 1867 (`0x80,0x80,0x00`), runtime/sample/main.c:2634 (`0xff,0x00,0xff`); tools/check-deploying.py:44-51 (`NOT_A_STATUS`) | `python3 tools/check-deploying.py` printed `ok - every status fill runtime/sample/main.c writes is named in both tables (4)` and the four `#<hex> is a gsKit_clear literal` lines, exit 0. **Seven of the eight members were exactly 28 lines low**, each landing on a call or a comment while the `gsKit_clear` it meant sat 28 lines further down; 1519 is right because the 28 inserted lines sit between it and the rest, the same shape as `data-keep` in `html.attributes`. Four of the seven were written as a colon and a number separated by slashes rather than commas -- 1542, 1581, 1611, 1658, 1839, spelled here without their colons for the reason `changelog.mapping` gives, that nothing can tell an example of a banned shape from a use of it -- and were invisible to both readers, because `FACTS_CITE`'s tail wants commas and `BARE_CONT` excluded a preceding `/`. They are a comma list now and the lookbehind no longer excludes `/`. Re-derived by reading every `gsKit_clear` in the file: `0x40,0x80,0xc0` at 1519, `0x80,0x00,0x00` at 1678, `0x80,0x80,0x00` at 1570, 1609, 1639, 1686 and 1867, `0xff,0x00,0xff` at 2634. Found by review of #163 | verified |
| deploy.status-fills.dark-floor | Every status fill sits at or above Rec. 601 luma 30, so none can be confused with a dead console at black. The darkest, `#800000`, is luma 38. | tools/check-deploying.py:53-58, tools/check-deploying.py:168-175 | `python3 tools/check-deploying.py` printed `ok - #800000 is clear of black (luma 38)` and the same for the other three, exit 0 | verified |
| deploy.status-fills.agree | `docs/deploying.md` and `docs/bringup.md` name the same four fills in the same order, so the two documents cannot drift into naming a different status set. | tools/check-deploying.py:128-134 | `python3 tools/check-deploying.py` printed `ok - docs/deploying.md and docs/bringup.md name the same 4 status fills, in the same order` | verified |
| deploy.flags | `MINIMAL`, `STATIC`, `SCREEN` and `UIB` are real `make -C runtime/sample` variables. `MINIMAL=1` and `SCREEN=probe` compile clean under the host syntax-check pass; `UIB` is not itself an `ifdef` guard, it is assigned unconditionally and defaults to `../../examples/memcard/build/ui.uib`. | runtime/sample/Makefile:16-17, runtime/sample/Makefile:30-31, runtime/sample/Makefile:46-52, runtime/sample/Makefile:256 | `python3 tools/check-deploying.py` printed `ok` for all four flags being real in the Makefile; `make -C runtime syntax-check` printed `ok - sample compiles: -DPS2UI_SAMPLE_MINIMAL` and `ok - sample compiles: -DPS2UI_SAMPLE_SCREEN`, exit 0. Restates parent `integrate.make.flags` for the two it also lists | verified |
| deploy.emulators | Play! runs the sample ELF headlessly in CI on every push and the frame is image-diffed against the previewer's render, needing no BIOS. PCSX2's software renderer is the closest practice stand-in short of a console; this project's own CI and bench facts do not cover it. | docs/deploying.md:43-59; .github/workflows/hw.yml:10-18, .github/workflows/hw.yml:676-745 (Play! job, pinned version and SHA-256) | `.github/workflows/hw.yml` grepped for `play`/`pcsx2`: an `emulator job` section pins `PLAY_VERSION`/`PLAY_SHA256` and downloads it from purei.org; a comment at line 18 names `docs/bringup.md` as holding "the local PCSX2 procedure". No emulator binary exists in this session to run either | code-only |
| deploy.markers | `docs/deploying.md`'s legend is two markers: `[bench]` (run on the project's own hardware, in `bringup.md`) and `[practice]` (standard PS2 homebrew procedure this project has not itself run). The memory-card, USB-launch-path-as-procedure, OPL and autoboot sections carry `[practice]`; the SCPH-50000-from-USB-under-FreeMcBoot path in "Get it onto the console" carries `[bench]`. | docs/deploying.md:13-24, docs/deploying.md:116-274 | read directly against the document; the marker on each subsection was checked by hand against the legend table | code-only |
| deploy.usb.streamed | A UI that fills texture slots at runtime with `ps2ui_tex_set` needs USB attached, because those bytes come from `mass:/ps2ui/` and are not compiled into the ELF. Restates parent `stream.deploy.usb`. | docs/deploying.md:36-39; runtime/sample/main.c:1346, runtime/sample/main.c:1362-1366 | code-only, same as the parent fact: the read path is `PS2UI_SAMPLE_USB`-only and needs a console with a drive | code-only |

## follow-up

- `runtime/sample/Makefile:50` says a screen name absent from the blob
  "holds solid blue rather than falling back to screen 0." The code it
  describes, `runtime/sample/main.c:2606`, clears to magenta
  (`0xff,0x00,0xff`), and the comment immediately above that call
  (`main.c:2590-2601`) explains at length why blue was rejected in favour
  of magenta. The Makefile comment was not updated when the fill changed.
  This is a stale in-repository comment, distinct from the drift rows
  ARCHITECTURE.md already lists (none of D1-D14 touch this line), and is a
  fix for a separate change, not for this page.
