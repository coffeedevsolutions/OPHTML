---
id: runtime/integrating
title: Integrating the runtime
description: Vendor ps2ui.c and ps2ui.h into a project, cross-compile them against gsKit, and run the host checks that exist.
section: runtime
order: 40
version: 0.10.0
sources: [packages/baker/ps2ui_bake/vendor.py, packages/baker/setup.py, packages/baker/tests/test_vendor.py, packages/baker/README.md, tools/check-runtime-shipped.py, runtime/Makefile, runtime/ps2ui.c, runtime/ps2ui.h, runtime/sample/Makefile, runtime/sample/main.c, runtime/vendor/README.md, .github/workflows/hw.yml, README.md, CONTRIBUTING.md, CHANGELOG.md, BACKLOG.md]
---

# Integrating the runtime

## What it is

The console half of OPHTML is two C files, `ps2ui.c` and `ps2ui.h`. Add
them to a ps2sdk and gsKit project, include the header, and link the baked
blob in beside them. Nothing else from this repository is compiled.

`ps2ui vendor-runtime` writes the pair into a directory out of the package
that is installed, so the console half needs no clone. The runtime that
lands is the one matching the baker that wrote the blob.

Compiling it is a cross-compile. The PlayStation 2 is a MIPS target and
never the build host, so the host compiler cannot produce the object.

## Minimal example

Write the pair into a project, from the directory above it.

```sh
$ ps2ui vendor-runtime src/
wrote src/ps2ui.c
wrote src/ps2ui.h
runtime source: /home/user/OPHTML/runtime (this checkout)

Compile these with your project against gsKit. The PS2 is a MIPS target, so this needs a cross-toolchain -- you cannot build it with the compiler your machine came with. The ps2dev image carries both:

    docker run --rm -v "$PWD:/work" -w /work ghcr.io/ps2dev/ps2dev make

It ships gsKit at $PS2DEV/gsKit but does NOT put it on the include path, so your Makefile needs these three lines or ps2ui.c will not find <gsKit.h>:

    EE_CFLAGS  += -I$(PS2DEV)/gsKit/include -I$(PS2SDK)/ports/include
    EE_LIBS     = -lgskit -ldmakit
    EE_LDFLAGS += -L$(PS2DEV)/gsKit/lib -L$(PS2SDK)/ports/lib

A complete worked Makefile, and a `main.c` that drives this runtime:
https://github.com/coffeedevsolutions/OPHTML/tree/main/runtime/sample

`ps2ui check` validates the blob. The path onto a console:
https://github.com/coffeedevsolutions/OPHTML/blob/main/docs/deploying.md
```

The command exited 0. `ls src/` then printed those two names and nothing
else.

Put the three lines it names into the project Makefile. Without them the
compile stops at `ps2ui.c`'s `#include <gsKit.h>`.

```make
EE_CFLAGS  += -I$(PS2DEV)/gsKit/include -I$(PS2SDK)/ports/include
EE_LIBS     = -lgskit -ldmakit
EE_LDFLAGS += -L$(PS2DEV)/gsKit/lib -L$(PS2SDK)/ports/lib
```

Build inside the toolchain image, with the line printed above.

```sh
docker run --rm -v "$PWD:/work" -w /work ghcr.io/ps2dev/ps2dev make
```

Turn the blob into an object with `$(PS2SDK)/bin/bin2c`, the way
[runtime/sample/Makefile](repo:runtime/sample/Makefile#L269) does, then
drive the context from the app. The calls are on
[the frame loop](page:runtime/frame-loop#what-it-is).

The pair stands on its own. `ps2ui.c` from the run above compiled under
`-std=c99 -Wall -Wextra -Werror` against gsKit's headers. No other source
from this repository was on the command line.

## Reference table

`ps2ui vendor-runtime` takes one positional and two flags. The subcommand
sits under [ps2ui](page:cli/ps2ui#vendor-runtime).

| option | effect |
|---|---|
| `dest` | Directory to write into. Defaults to `.`. Created when absent. |
| `--force` | Takes this toolchain's copy of every file that differs. Files already identical are left alone. |
| `--starter` | Also writes a `main.c` and a `Makefile` that build to an ELF as they stand. |

`runtime/sample/` is a worked ps2sdk Makefile for the same two files. Its
flags select a build arm. `requires` is enforced by a `$(error)`, not by a
comment.

| flag | builds | requires |
|---|---|---|
| `STATIC=1` | Holds the baked initial focus instead of cycling it | nothing |
| `MINIMAL=1` | Clear, hold, exit, and no blob | nothing |
| `PROBE=1` | Four solid-fill primitive cases, and no blob | nothing |
| `PROBE6=1` | Seven columns over a bar pattern | nothing |
| `TELEMETRY=1` | A once-a-second stats line on stdout | nothing |
| `PROGRESSIVE=1` | 480p output instead of 480i | a display that syncs at 480p |
| `LADDER=1` | The height ladder, twelve rungs, three arms each | nothing |
| `LADDER2=1` | The second ladder instrument | nothing |
| `SCREEN=<name>` | Opens on that screen rather than screen 0 | a screen of that name in the blob |
| `COVERS=1` | Four streamed 128x128 slots filled from `mass:` | `UIB=../../fixtures/bench-stream/build/bench.uib` |
| `USB=1` | Embeds the IOP mass-storage modules | `COVERS=1` |
| `LINEAR_CLUT=1` | Uploads CLUTs unpermuted | nothing |
| `NO_SYNC=1` | Drops the cache writeback from `ps2ui_tex_set` | nothing |
| `NO_ALPHA=1` | Asserts `PrimAlphaEnable` OFF in `ps2ui_render` | nothing |
| `OPLENV=1` | The opl-env driver | nothing |
| `FILL=1` | Full-screen blending over the UI | `OPLENV=1` |
| `FILL_N=<n>` | Sweeps the fill sprite count | `FILL=1` |
| `EE=1` | Renders the whole UI N extra times | `OPLENV=1` |
| `EE_N=<n>` | Sweeps the extra passes | `EE=1` |
| `CLEAR_OPAQUE=1` | The driver's own clear, unblended | `OPLENV=1` |
| `OPLENV_SCREEN=<name>` | Renders one named opl-env screen | `OPLENV=1`, and not `THEME_CYCLE` |
| `CYCLE=1` | Walks all six screens in one boot | `OPLENV=1`, and not `OPLENV_SCREEN`, `COMPOSE` or `THEME_CYCLE` |
| `CYCLE_EVERY=<n>` | Frames per screen | `CYCLE=1` |
| `COMPOSE=1` | Layers two screens in one frame | `OPLENV=1`, and not `OPLENV_SCREEN` or `THEME_CYCLE` |
| `THEME_CYCLE=1` | Switches tint row on a timer | `OPLENV=1`, and not `OPLENV_SCREEN`, `CYCLE` or `COMPOSE` |

`MINIMAL=1` and `PROBE=1` are the first two instruments in
[first boot](page:runtime/first-boot#before-you-start). `EE_BIN=<name>` renames
the ELF and `UIB=<path>` chooses the blob. Neither is guarded.

The tree carries five host targets and no others. Run them from the
repository root.

| target | runs | printed in this session |
|---|---|---|
| `test` | `syntax-check`, `timing-check`, `test-narrow`, then the runtime suite over five blobs | 465 lines, exit 0 |
| `syntax-check` | 27 compiles of `sample/main.c` and `ps2ui.c`, one per build arm | 27 `ok -` lines |
| `timing-check` | `tools/check-timing-probe.py`, a source-level ordering check | 13 `ok -` lines |
| `test-narrow` | `ps2ui.c` compiled against a 32-bit arena limit, over two blobs | `PASS: 5 checks, 0 failure(s)` |
| `clean` | `rm -rf build` | not run |

The tails of the run:

```sh
$ make -C runtime test
...
ok - sample compiles: -DPS2UI_OPLENV_CYCLE_EVERY=300
...
./build/test_narrow ../examples/memcard/build/ui.uib build/huge.uib
...
1..5
PASS: 5 checks, 0 failure(s)
./build/test_runtime ../examples/memcard/build/ui.uib build/list.uib build/streamed.uib build/wide.uib build/huge.uib
...
1..410
PASS: 410 checks, 0 failure(s)
```

The suite is also the check a contribution runs. See
[contributing](page:project/contributing).

## Starting from nothing

`ps2ui.c` and `ps2ui.h` go into a project you already have. If you do
not have one, `--starter` writes the project too:

```sh
ps2ui vendor-runtime --starter src/
```

That is four files rather than two: `ps2ui.c`, `ps2ui.h`, a `main.c`
that drives the runtime, and a `Makefile` producing `ps2ui_app.elf`.
Bake into `src/`, or copy a blob to `src/build/ui.uib`, and build. The
Makefile defaults `UIB` to `build/ui.uib`, which is where `ps2ui build`
writes one, so the default layout needs no flag:

```sh
cd src
docker run --rm -v "$PWD:/work" -w /work ghcr.io/ps2dev/ps2dev make
```

A blob kept elsewhere under `src/` is `make UIB=<path>`. Somewhere
outside it needs a second `-v` too, since the command above mounts only
this directory.

**This is the whole console half without a clone**, which is what
Phase 4's exit gate asks for: a stranger with npm, pip and a TTF
reaching a console. [Deploying](page:runtime/deploying) then applies
unchanged from `src/`. What does not carry over is the reference
material above and on [first boot](page:runtime/first-boot):
`runtime/sample/`, `tools/make_testcard.py` and the channel-6 blob are
checkout-only, and the bring-up steps read them as instruments rather
than as examples. Nor does the status-colour table on either page: it
is `runtime/sample/main.c`'s, and the starter paints navy `#000080`
where that one paints magenta.

`main.c` is yours to edit. Read the comment at the top before deleting
anything: it says which parts have been proved on hardware and which
have only been compiled.

## Behaviour

### Where the files come from

The command reads two candidate directories and says which one answered.
A checkout that carries both files answers as `this checkout`. An install
answers as `the installed package`, from package data staged into the
wheel at build time. The label is printed on every run, so a stale copy
is visible rather than guessed at.

Both can exist at once, because building a checkout leaves the staged copy
on disk. When they disagree the command refuses and names both paths.

A wheel carries the pair. `python3 tools/check-runtime-shipped.py` builds
one, opens it, installs it into a throwaway venv and vendors from outside
any checkout.

```sh
$ python3 tools/check-runtime-shipped.py
ok - built one wheel: ophtml-0.10.0-py3-none-any.whl
ok - the wheel carries ps2ui_bake/runtime/ps2ui.c
...
ok - `ps2ui vendor-runtime` runs from an installed wheel
ok - and it read them from the installed package, not a fallback
ok - ps2ui.c landed byte-identical to runtime/ps2ui.c
ok - ps2ui.h landed byte-identical to runtime/ps2ui.h
```

### Drift in the destination

Every file is classified before any file is written. An unchanged file
reports `already up to date` and stays put.

```sh
$ ps2ui vendor-runtime src/
ps2ui.c, ps2ui.h already up to date.
runtime source: /home/user/OPHTML/runtime (this checkout)
```

A file that differs stops the whole command. Nothing is written, not even
a file that was absent. `ps2ui.c` includes `ps2ui.h` and is written against
its structs, so a half-written pair compiles against the wrong
declarations.

```sh
$ ps2ui vendor-runtime src/
ps2ui: ps2ui.h in src/ differs from the runtime this toolchain ships, so nothing was written.
  Writing the rest would leave you compiling a mixed pair -- ps2ui.c includes ps2ui.h and is written against its structs, and a version check will not catch it: the format is pledged frozen at v7, so PS2UI_VERSION no longer moves when the runtime does.
  Pass --force to take this toolchain's copy, or move your edited file aside first.
```

`PS2UI_VERSION` is the blob format version, frozen at 7. It answers whether
a blob and a runtime agree, and says nothing about whether two copies of
the runtime do. One package shipping both halves is what holds those
together.

Pass `--force` to take the toolchain's copy.

```sh
$ ps2ui vendor-runtime src/ --force
wrote src/ps2ui.h
ps2ui.c already up to date.
runtime source: /home/user/OPHTML/runtime (this checkout)
...
```

The toolchain notes print only when a file was written. The up-to-date run
above stopped after its two lines.

### The cross toolchain

New in 0.6.0. The command prints the toolchain it needs rather than the
two files alone. CI compiles the ELF in the same image,
`ghcr.io/ps2dev/ps2dev:latest`. That tag stays unpinned on purpose, so a
gsKit change shows up as a red job.

`runtime/vendor/gsKit/` holds verbatim public headers from ps2dev/gsKit at
commit `43122eb96289167975b56caa45beb71eb8684fa2`. They are host-only. The
console build takes the same headers from PS2SDK, and only the host
Makefile puts `vendor/` on an include path. One gsKit source file is
compiled for the host, `gsTexture.c` with `-DF_gsKit_texture_size`, which
yields the block-based texture-size arithmetic the VRAM preflight depends
on.

### What the host targets prove

`syntax-check` compiles every build arm with `-S` rather than
`-fsyntax-only`. A compiler emits unused-function warnings during code
generation, which `-fsyntax-only` never reaches. A probe asks whether the
compiler accepts `-fno-integrated-as` and adds it when it does. Clang then
reaches the same 27 compiles that gcc does.

```sh
$ make -C runtime syntax-check CC=clang
...
ok - sample compiles: -DPS2UI_OPLENV_CYCLE_EVERY=300
```

Struct shape and prototypes are checked against gsKit's real declarations,
so a divergence is a compile error. Three classes stay console-only:
drawing behaviour, EE type widths and `printf` formats, and whether PS2SDK
permits an API at all. The last one has already cost a build. A shim for
`fioOpen` made the host green for functions the newlib port rejects at the
header. An ELF that had never compiled for a target passed every local
suite.

## Limits and errors

| limit | what happens |
|---|---|
| A drifted file in `dest` | Nothing is written, including the absent file, and the exit code is 1. Pass `--force` or move the edited file aside. |
| Two complete sources that disagree | The command refuses and names both paths. Rebuild `packages/baker` or delete the staged directory. |
| Neither source present | The command reports a packaging bug and names the sdist workaround. |
| No Makefile is vendored | `dest` receives two C files. The build rules are the reader's, or copied from `runtime/sample/`. |
| A target outside the table above | The five are all there are. `make` stops with `No rule to make target` and exits 2. |
| An older-gsKit build arm | There is none. gsKit declares no per-texture TFX field, so the runtime sets none and there is nothing to select between. |
| A pairing flag without its arm | `make` stops at a `$(error)` and exits 2 before any recipe runs. All thirteen guards were exercised in this session. |
| `syntax-check` and PS2SDK | It answers C-language questions only. `hw.yml`'s `elf` job is the arbiter for anything touching PS2SDK. |

Build-time switches on the runtime itself, and what each one changes, are
on [errors and constants](page:runtime/errors-and-constants#build-time-switches).

## Related pages

- [ps2ui](page:cli/ps2ui#vendor-runtime) for the subcommand and its exit codes.
- [The frame loop](page:runtime/frame-loop#what-it-is) for the calls once the pair compiles.
- [C API reference](page:runtime/api-reference#function-tables-by-group) for every public function.
- [First boot](page:runtime/first-boot#before-you-start) for `MINIMAL=1`, `PROBE=1` and what each colour means.
- [Deploying](page:runtime/deploying#what-it-is) for the path from an ELF onto hardware.
- [Contributing](page:project/contributing) for the checks a change runs.
