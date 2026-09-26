# Host-side test build. The PS2 build is a source drop: add ps2ui.c to
# your ps2sdk/gsKit project and include ps2ui.h (see README).

CC      ?= cc
CFLAGS  ?= -std=c99 -Wall -Wextra -Werror -O2
UIB     ?= ../examples/memcard/build/ui.uib
# A data-repeat blob whose focus names are row-0..row-3 with one slot
# each. The memcard example cannot stand in: its tiles are named after
# games, so a list prefix never matches and the list/visibility checks
# would assert nothing. Built here rather than committed so it tracks
# the compiler it is testing.
LIST_UIB = build/list.uib
# The streamed-texture fixture (v6 §3). Built straight from write_uib
# rather than through HTML: authoring a streamed slot from markup is a
# separate change, and the runtime half needs a blob first.
STREAM_UIB = build/streamed.uib
# Blobs past the table ceilings that used to exist (PLAN 6.3). wide is
# a realistic OPL-class shape; huge is the largest arena a legal header
# can demand, which is the one the arithmetic has to survive.
WIDE_UIB = build/wide.uib
HUGE_UIB = build/huge.uib

test: syntax-check timing-check build/test_runtime $(LIST_UIB) $(STREAM_UIB) $(WIDE_UIB) test-narrow
	./build/test_runtime $(UIB) $(LIST_UIB) $(STREAM_UIB) $(WIDE_UIB) $(HUGE_UIB)

# The sample is the bring-up instrument -- the ELF that goes on a
# memory card -- and until this target existed nothing but the ps2dev
# container in CI ever compiled main.c. A change to it was a
# push-and-hope, and the telemetry build duly shipped `asm volatile`,
# which -std=c99 rejects, with every local suite green. Same flags the
# console build uses; -fsyntax-only because the host has no EE.
#
# WHAT THIS TARGET DOES NOT VOUCH FOR. It catches C-language errors.
# It does not know whether a PS2SDK API exists, or is permitted --
# vendor/host-shim only describes the ones it declares. The streaming
# bench compiled clean here against a shim for fio/fileXio, an API the
# newlib port rejects at the header, so covers.elf had never built for
# a target while this said ok. hw.yml's elf job is the arbiter for
# anything touching PS2SDK; see runtime/vendor/README.md.
SAMPLE_VARIANTS = "" -DPS2UI_SAMPLE_STATIC -DPS2UI_SAMPLE_MINIMAL -DPS2UI_SAMPLE_PROBE -DPS2UI_SAMPLE_PROBE6 -DPS2UI_SAMPLE_TELEMETRY -DPS2UI_SAMPLE_COVERS -DPS2UI_SAMPLE_PROGRESSIVE -DPS2UI_SAMPLE_LADDER -DPS2UI_SAMPLE_LADDER2 -DPS2UI_SAMPLE_OPLENV

# `-S`, NOT `-fsyntax-only`, and NOT `-c`.
#
# GCC emits -Wunused-function and friends during CODE GENERATION, which
# -fsyntax-only never reaches -- so for the life of this target the host
# check was structurally blind to a whole warning class the ps2dev
# toolchain treats as fatal. It cost a red `elf` job on a static helper
# that the host suite called and the ELF did not. The target's name was
# honest; the reliance placed on it was not.
#
# `-c` would be the obvious upgrade and does not work: main.c carries
# MIPS inline asm (mfc0) that an x86 assembler cannot encode, which is
# why -fsyntax-only was chosen in the first place. `-S` generates code
# and stops before the assembler, so the warnings appear and the asm is
# never encoded. Verified by injecting an unused static: -fsyntax-only
# passes it, -S rejects it.
#
# AND THAT PARAGRAPH IS WHY THIS TARGET FAILED ON CLANG FOR ITS WHOLE
# LIFE. `-S` stops before the assembler in GCC. Clang parses inline asm
# with its INTEGRATED assembler during -S, so `mfc0 %0, $9` is rejected
# against an x86 host before any of the above applies:
#
#     sample/main.c:110:26: error: invalid instruction mnemonic 'mfc0'
#
# Reverting to -fsyntax-only is the obvious fix and is wrong -- it is
# the fix this comment already refuses, and taking it would trade a
# compiler nobody ran for the warning class that cost the red `elf`
# job. HOST_NOASM asks the compiler whether it can be told to emit the
# asm text without parsing it, which is what GCC does unconditionally
# and clang does under -fno-integrated-as. Both then generate code, so
# -Wunused-function still fires under both.
#
# PROBED BY FEATURE, NOT BY NAME. Matching "clang" in $(CC) --version
# gets the cross-compilers and the wrappers wrong, and says nothing
# about a compiler neither of us has heard of. Asking whether the flag
# is accepted is the question that actually matters, and a compiler
# that does not need it answers empty.
#
# AND HOST_NOASM IS ABOUT THE ASSEMBLER, WHICH IS NOT THE ONLY HALF.
# It stops clang PARSING `mfc0`; the frontend still reads the operand
# constraint, and on arm64 a u32 in an "=r" slot is a 32-bit value in a
# 64-bit register. Apple clang raises -Wasm-operand-widths and suggests
# `%w0` -- correct for AArch64, wrong for the MIPS instruction written
# there -- and -Werror made it fatal, so `make -C runtime test` could
# not finish on any Mac. Found by registry run 35164624418, the first
# run that ever got this far on macOS, and reproduced here by
# cross-targeting: `clang --target=aarch64-linux-gnu` prints the
# runner's diagnostic word for word while the same command on x86_64
# exits 0, which is why ci.yml's clang arm never saw it.
#
# The fix is in main.c, not here: the asm is guarded on __mips__ with a
# host definition beside it, so no flag suppresses a correct
# diagnostic and the callers stay -Wall -Werror checked.
HOST_NOASM := $(shell $(CC) -fno-integrated-as -S -o /dev/null -x c /dev/null >/dev/null 2>&1 \
	&& echo -fno-integrated-as)

# `ps2ui vendor-runtime --starter` hands this out, written against
# ps2ui.h, and ps2ui.h is what moves. syntax-check compiles it.
STARTER := ../packages/baker/ps2ui_bake/starter/main.c

syntax-check:
	@for v in $(SAMPLE_VARIANTS); do \
		$(CC) -std=c99 -Wall -Werror -S $(HOST_NOASM) -o /dev/null $$v \
			-Istub -Ivendor/gsKit -Ivendor/host-shim -I. sample/main.c || exit 1; \
		echo "ok - sample compiles: $$v"; \
	done
# Separately, because the quoting a stringised screen name needs does
# not survive `for v in $(SAMPLE_VARIANTS)`: the shell strips one layer
# at expansion and the compiler would be handed a bare identifier.
# Paired with STATIC, which is how CI builds conform.elf.
	@$(CC) -std=c99 -Wall -Werror -S $(HOST_NOASM) -o /dev/null \
		-DPS2UI_SAMPLE_STATIC -DPS2UI_SAMPLE_SCREEN='"probe"' \
		-Istub -Ivendor/gsKit -Ivendor/host-shim -I. sample/main.c
	@echo "ok - sample compiles: -DPS2UI_SAMPLE_SCREEN"
# THE STARTER, which lives in the Python package rather than here.
#
# `ps2ui vendor-runtime --starter` hands somebody a main.c written
# against THIS header, and the header is what moves. Compiled here
# because this is the target that already knows how to build a
# gsKit-facing file on a host with no PS2 toolchain, and because the
# alternative is finding out in the elf job -- or, worse, finding out
# from somebody who installed the package.
#
# NOPAD only, and the reason is the one runtime/vendor/README.md gives
# for the USB path: libpad.h, loadfile.h and sifrpc.h do not exist on
# the host, and after the fileio.h episode this tree does not write a
# shim to pretend otherwise. The pad build is compiled by the elf job
# in the ps2dev container, which is the arbiter for that path.
	@$(CC) -std=c99 -Wall -Werror -S $(HOST_NOASM) -o /dev/null \
		-DPS2UI_STARTER_NOPAD \
		-Istub -Ivendor/gsKit -Ivendor/host-shim -I. $(STARTER)
	@echo "ok - starter compiles: -DPS2UI_STARTER_NOPAD"
# The stringised screen name, separately, for the quoting reason the
# sample's own SCREEN line gives right above.
	@$(CC) -std=c99 -Wall -Werror -S $(HOST_NOASM) -o /dev/null \
		-DPS2UI_STARTER_NOPAD -DPS2UI_STARTER_SCREEN='"probe"' \
		-Istub -Ivendor/gsKit -Ivendor/host-shim -I. $(STARTER)
	@echo "ok - starter compiles: -DPS2UI_STARTER_SCREEN"
# THE HOST SHIM IS LOAD-BEARING ON A PLATFORM THIS NEVER RUNS ON, so
# assert it here where it does. vendor/gsKit/src/gsTexture.c is
# verbatim upstream and includes <malloc.h>, which Linux has and macOS
# does not; vendor/host-shim/malloc.h forwards to <stdlib.h> so both
# resolve. Delete that shim and every ubuntu job stays green -- checked
# by deleting it: 410 checks, rc=0, the include falling through to
# /usr/include/malloc.h. The only thing that would have noticed is a
# weekly macOS job, so the fix was one shim away from being unfenced
# on every gate that actually blocks a PR.
#
# -H prints the include tree, so this asserts WHICH header was opened
# rather than that the compile worked. That is the distinction: on
# Linux the compile works either way.
	@$(CC) -std=c99 -O2 -fsyntax-only -DF_gsKit_texture_size \
		-Ivendor/gsKit -Ivendor/host-shim -H \
		vendor/gsKit/src/gsTexture.c 2>&1 \
		| grep -q 'vendor/host-shim/malloc\.h' \
		|| { echo "not ok - gsTexture.c did not open vendor/host-shim/malloc.h."; \
		     echo "  It fell through to the system header, which macOS has not."; \
		     exit 1; }
	@echo "ok - gsTexture.c resolves <malloc.h> through the host shim"
# The step 6 probe's falsification arm pairs two defines the loop
# above never combines: column G branches on PS2UI_CLUT_PERMUTE inside
# the PROBE6 block, so this is the only line that compiles that branch.
	@$(CC) -std=c99 -Wall -Werror -fsyntax-only \
		-DPS2UI_SAMPLE_PROBE6 -DPS2UI_CLUT_PERMUTE=0 \
		-Istub -Ivendor/gsKit -Ivendor/host-shim -I. sample/main.c
	@echo "ok - sample compiles: -DPS2UI_SAMPLE_PROBE6 -DPS2UI_CLUT_PERMUTE=0"
# The linear-CLUT arm of step 3's A/B lives in ps2ui.c, not main.c, so
# it needs its own line: the loop above only ever compiles the sample.
	@$(CC) -std=c99 -Wall -Werror -fsyntax-only \
		-DPS2UI_CLUT_PERMUTE=0 -Istub -Ivendor/gsKit -Ivendor/host-shim -I. ps2ui.c
	@echo "ok - runtime compiles: -DPS2UI_CLUT_PERMUTE=0"
# Step 4b's reference arm, likewise in ps2ui.c rather than main.c.
	@$(CC) -std=c99 -Wall -Werror -fsyntax-only \
		-DPS2UI_PRIMALPHA_OFF -Istub -Ivendor/gsKit -Ivendor/host-shim -I. ps2ui.c
	@echo "ok - runtime compiles: -DPS2UI_PRIMALPHA_OFF"
# The streaming bench's falsification arm, also in ps2ui.c: tex_set
# without the cache writeback. Compiled here so the arm cannot rot --
# it is the ELF that says what a live cache fault looks like, and an
# arm that stopped building would be discovered at a bench.
	@$(CC) -std=c99 -Wall -Werror -fsyntax-only \
		-DPS2UI_SKIP_SYNCDCACHE -Istub -Ivendor/gsKit -Ivendor/host-shim -I. ps2ui.c
	@echo "ok - runtime compiles: -DPS2UI_SKIP_SYNCDCACHE"
# P3a's falsification arm pairs two defines the loop above never
# combines, same reason as PROBE6's. It matters more than most: the arm
# is what makes the GS number a measurement rather than a hope, and an
# arm that quietly stopped building would be discovered at a bench with
# the console already on.
	@$(CC) -std=c99 -Wall -Werror -S $(HOST_NOASM) -o /dev/null \
		-DPS2UI_SAMPLE_OPLENV -DPS2UI_OPLENV_FILL \
		-Istub -Ivendor/gsKit -Ivendor/host-shim -I. sample/main.c
	@echo "ok - sample compiles: -DPS2UI_SAMPLE_OPLENV -DPS2UI_OPLENV_FILL"
# And one sweep point, so -DPS2UI_OPLENV_FILL_N is not a define only the
# ps2dev toolchain ever sees. The code path is identical, which is why
# this is close to noise -- but that is exactly the argument that would
# have left OPLENV+FILL out of this list too.
	@$(CC) -std=c99 -Wall -Werror -S $(HOST_NOASM) -o /dev/null \
		-DPS2UI_SAMPLE_OPLENV -DPS2UI_OPLENV_FILL -DPS2UI_OPLENV_FILL_N=16 \
		-Istub -Ivendor/gsKit -Ivendor/host-shim -I. sample/main.c
	@echo "ok - sample compiles: -DPS2UI_OPLENV_FILL_N=16"
# The EE arm and one of its sweep points, for the same reason: it is the
# instrument P3d's gate now rests on [F-042], and an arm discovered
# broken at a bench is an arm discovered with the console already on.
	@$(CC) -std=c99 -Wall -Werror -S $(HOST_NOASM) -o /dev/null \
		-DPS2UI_SAMPLE_OPLENV -DPS2UI_OPLENV_EE \
		-Istub -Ivendor/gsKit -Ivendor/host-shim -I. sample/main.c
	@echo "ok - sample compiles: -DPS2UI_SAMPLE_OPLENV -DPS2UI_OPLENV_EE"
	@$(CC) -std=c99 -Wall -Werror -S $(HOST_NOASM) -o /dev/null \
		-DPS2UI_SAMPLE_OPLENV -DPS2UI_OPLENV_EE -DPS2UI_OPLENV_EE_N=4 \
		-Istub -Ivendor/gsKit -Ivendor/host-shim -I. sample/main.c
	@echo "ok - sample compiles: -DPS2UI_OPLENV_EE_N=4"
# Both arms at once must NOT be a silent combination: fill multiplies GS
# work and this multiplies both, so a build carrying both measures
# neither cleanly. It still has to compile, because the flags are
# independent and someone will try it.
	@$(CC) -std=c99 -Wall -Werror -S $(HOST_NOASM) -o /dev/null \
		-DPS2UI_SAMPLE_OPLENV -DPS2UI_OPLENV_EE -DPS2UI_OPLENV_FILL \
		-Istub -Ivendor/gsKit -Ivendor/host-shim -I. sample/main.c
	@echo "ok - sample compiles: both arms together (measures neither cleanly)"
# AND THE THREE OPLENV ARMS THIS LIST STILL DID NOT HAVE. FILL and EE
# were here from the start; CLEAR_OPAQUE, THEME_CYCLE and SCREEN were
# added to hw.yml later and never joined, so three build arms CI
# compiles had no host check at all. P3d's screen arm duly shipped a
# red `elf` job: trading `up` off the readout left last_upload written
# four times and read nowhere, which is -Wunused-but-set-variable and
# fatal under -Werror. The rule the list needs is not "add the flags
# you thought of" but "every arm hw.yml builds appears here, or says
# in writing why it cannot", so a new arm in the workflow is a new
# line here.
#
# ONE ARM TAKES THE SECOND CLAUSE, and only one: USB. It is excluded
# on purpose and the reason is at sample/Makefile's `ifdef USB` --
# sifrpc.h and friends do not exist on the host, and this tree does
# not shim them after the fileio.h episode. `elf` is its arbiter.
# Everything else hw.yml builds is above or in SAMPLE_VARIANTS;
# checked by diffing the workflows' make invocations against this
# list, which is worth mechanising the day a third exception appears.
	@$(CC) -std=c99 -Wall -Werror -S $(HOST_NOASM) -o /dev/null \
		-DPS2UI_SAMPLE_OPLENV -DPS2UI_OPLENV_CLEAR_OPAQUE \
		-Istub -Ivendor/gsKit -Ivendor/host-shim -I. sample/main.c
	@echo "ok - sample compiles: -DPS2UI_OPLENV_CLEAR_OPAQUE"
	@$(CC) -std=c99 -Wall -Werror -S $(HOST_NOASM) -o /dev/null \
		-DPS2UI_SAMPLE_OPLENV -DPS2UI_OPLENV_THEME_CYCLE \
		-Istub -Ivendor/gsKit -Ivendor/host-shim -I. sample/main.c
	@echo "ok - sample compiles: -DPS2UI_OPLENV_THEME_CYCLE"
# Quoted separately for the reason SAMPLE_SCREEN is: a stringised name
# does not survive a `for v in` expansion.
	@$(CC) -std=c99 -Wall -Werror -S $(HOST_NOASM) -o /dev/null \
		-DPS2UI_SAMPLE_OPLENV -DPS2UI_OPLENV_SCREEN='"confirm"' \
		-Istub -Ivendor/gsKit -Ivendor/host-shim -I. sample/main.c
	@echo "ok - sample compiles: -DPS2UI_OPLENV_SCREEN"
	@$(CC) -std=c99 -Wall -Werror -S $(HOST_NOASM) -o /dev/null \
		-DPS2UI_SAMPLE_OPLENV -DPS2UI_OPLENV_COMPOSE \
		-Istub -Ivendor/gsKit -Ivendor/host-shim -I. sample/main.c
	@echo "ok - sample compiles: -DPS2UI_OPLENV_COMPOSE"
	@$(CC) -std=c99 -Wall -Werror -S $(HOST_NOASM) -o /dev/null \
		-DPS2UI_SAMPLE_OPLENV -DPS2UI_OPLENV_CYCLE \
		-Istub -Ivendor/gsKit -Ivendor/host-shim -I. sample/main.c
	@echo "ok - sample compiles: -DPS2UI_OPLENV_CYCLE"
	@$(CC) -std=c99 -Wall -Werror -S $(HOST_NOASM) -o /dev/null \
		-DPS2UI_SAMPLE_OPLENV -DPS2UI_OPLENV_CYCLE \
		-DPS2UI_OPLENV_CYCLE_EVERY=300 \
		-Istub -Ivendor/gsKit -Ivendor/host-shim -I. sample/main.c
	@echo "ok - sample compiles: -DPS2UI_OPLENV_CYCLE_EVERY=300"

# Source-level, because the property it guards is an ORDERING and the
# compiler has no opinion about it: the opl-env driver's frame timer
# has to stop counting before gsKit_sync_flip blocks on vsync. Through
# HW #260 it did not, and the field period it printed instead was
# stable, plausible and photographed. See tools/check-timing-probe.py.
#
# Deliberately not folded into syntax-check: that target runs inside
# the ps2dev container in hw.yml, which has no python3, and moving a
# python step in there is a mistake this repo has already made once.
timing-check:
	@python3 ../tools/check-timing-probe.py


# The fixture exists so the runtime tests track the compiler that
# produced their blob, which only holds if a compiler change rebuilds
# it. Without these prerequisites a format change leaves a stale blob
# that the loader then rejects -- and the tests crash on it rather than
# say so.
LAYOUT_SRC = $(wildcard ../packages/layout/src/*.js)
BAKER_SRC  = $(wildcard ../packages/baker/ps2ui_bake/*.py)
METRICS    = $(wildcard ../fonts/*.metrics.json)

$(LIST_UIB): tests/fixture/list.html tests/fixture/list.css \
             $(LAYOUT_SRC) $(BAKER_SRC) $(METRICS)
	@mkdir -p build
	node ../packages/layout/bin/ps2ui-layout.js \
		tests/fixture/list.html tests/fixture/list.css -o build/list.json
	PYTHONPATH=../packages/baker python3 -m ps2ui_bake build/list.json -o $@

$(STREAM_UIB): tests/fixture/make_streamed.py $(BAKER_SRC)
	@mkdir -p build
	python3 tests/fixture/make_streamed.py $@

# One recipe, two outputs: the generator writes both in a single pass
# and huge.uib is ~3 MB, so nothing is gained by building it twice.
$(WIDE_UIB) $(HUGE_UIB): tests/fixture/make_wide.py $(BAKER_SRC)
	@mkdir -p build
	python3 tests/fixture/make_wide.py $(WIDE_UIB) $(HUGE_UIB)

# The EE is 32-bit MIPS; this suite runs on a 64-bit host and the CI
# image has no 32-bit libc to link a -m32 build against. So the arena
# guard -- which only fires when a blob's carve exceeds the target's
# address width -- is unreachable in the ordinary build. This one
# compiles ps2ui.c against a 32-bit limit and feeds it the same blobs:
# huge.uib must be refused, and the ordinary blob must still load, or
# the guard is refusing everything rather than the right thing.
test-narrow: build/test_narrow $(HUGE_UIB) $(UIB)
	./build/test_narrow $(UIB) $(HUGE_UIB)

build/test_narrow: ps2ui.c tests/test_narrow.c ps2ui.h stub/gskit_stub.c \
                   build/gsKit_texture_size.o
	@mkdir -p build
	$(CC) $(CFLAGS) -DPS2UI_ARENA_LIMIT=0xFFFFFFFFull \
		-Istub -Ivendor/gsKit -Ivendor/host-shim \
		ps2ui.c stub/gskit_stub.c tests/test_narrow.c \
		build/gsKit_texture_size.o -o $@

# gsKit's real texture-size arithmetic, selectively compiled from the
# vendored source: gsKit guards every function with a per-function F_*
# macro, so defining exactly one yields exactly one function. It is the
# one gsKit function whose VALUE (not just shape) the runtime's
# preflight safety argument depends on.
#
# Compiled without -Wall -Wextra -Werror because the file is verbatim
# upstream and not ours to edit. What that actually waives, measured
# rather than left silent: two -Wsign-compare (u32 Width vs int in the
# unused static gsKit_set_tw_th) and one -Wunused-parameter (in
# gsInline.h's heap helper). Nothing in the compiled function itself.
build/gsKit_texture_size.o: vendor/gsKit/src/gsTexture.c
	@mkdir -p build
	$(CC) -std=c99 -O2 -c -DF_gsKit_texture_size \
		-Ivendor/gsKit -Ivendor/host-shim $< -o $@

# Every header the test includes, or an edit to one of them does not
# rebuild and the suite reports the PREVIOUS binary's result --
# which is how a falsification pass first read as "the check does
# not fire" when the check was fine and make had simply not run.
build/test_runtime: ps2ui.c stub/gskit_stub.c tests/test_runtime.c ps2ui.h \
                    stub/gskit_stub.h sample/probe6_pattern.h \
                    sample/cover_pattern.h sample/ladder_pattern.h sample/ladder2_pattern.h \
                    ../examples/opl-env/window.h \
                    build/gsKit_texture_size.o
	@mkdir -p build
	$(CC) $(CFLAGS) -Istub -Ivendor/gsKit -Ivendor/host-shim ps2ui.c stub/gskit_stub.c tests/test_runtime.c build/gsKit_texture_size.o -o $@

# S2: libFuzzer over ps2ui_load and everything a program does with a
# blob that loaded (tests/fuzz_load.c says what, and what not). Needs
# clang with its libFuzzer runtime: Ubuntu's libclang-rt-18-dev.
#
# The seeds are every blob this Makefile and the examples build, so a
# mutation starts from a real layout rather than from nothing. Run
# after `make test` and the examples' build.sh; a missing seed is
# skipped, and the target fails only when there is none at all.
#
# `make fuzz` is CI's short pass. `make fuzz FUZZ_TIME=3600` is a long
# one, and keeps what it finds in build/fuzz-corpus for the next run.
# FUZZ_ARGS goes to libFuzzer as-is: ci.yml passes -seed=1, so its pass
# walks the same inputs every run instead of a new random walk that
# could surface an old bug on an unrelated pull request (review of #182).
FUZZ_CC   ?= clang
FUZZ_TIME ?= 60
FUZZ_ARGS ?=
FUZZ_SEEDS = $(LIST_UIB) $(STREAM_UIB) $(WIDE_UIB) \
             $(wildcard ../examples/*/build/*.uib) \
             $(wildcard ../fixtures/*/build/*.uib)

build/fuzz_load: ps2ui.c ps2ui.h stub/gskit_stub.c stub/gskit_stub.h \
                 tests/fuzz_load.c build/gsKit_texture_size.o
	@mkdir -p build
	$(FUZZ_CC) -std=c11 -g -O1 -Wall -Wextra -Werror \
		-fsanitize=fuzzer,address,undefined -fno-sanitize-recover=undefined \
		-Istub -Ivendor/gsKit -Ivendor/host-shim \
		ps2ui.c stub/gskit_stub.c tests/fuzz_load.c \
		build/gsKit_texture_size.o -o $@

fuzz: build/fuzz_load
	@mkdir -p build/fuzz-corpus build/fuzz-seeds build/fuzz-crashes
	@n=0; for f in $(FUZZ_SEEDS); do \
		if [ -f "$$f" ]; then \
			cp "$$f" "build/fuzz-seeds/$$(echo "$$f" | tr '/.' '__')"; n=$$((n+1)); \
		fi; \
	done; \
	if [ $$n -eq 0 ]; then echo "fuzz: no seed blobs; run make test and the examples' build.sh first" >&2; exit 1; fi; \
	echo "fuzz: $$n seed blob(s), $(FUZZ_TIME) s"
	./build/fuzz_load build/fuzz-corpus build/fuzz-seeds \
		-max_total_time=$(FUZZ_TIME) -max_len=262144 \
		-artifact_prefix=build/fuzz-crashes/ -print_final_stats=1 $(FUZZ_ARGS)

clean:
	rm -rf build

.PHONY: test test-narrow syntax-check timing-check clean fuzz
