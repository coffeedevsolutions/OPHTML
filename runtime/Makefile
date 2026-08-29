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
syntax-check:
	@for v in $(SAMPLE_VARIANTS); do \
		$(CC) -std=c99 -Wall -Werror -S -o /dev/null $$v \
			-Istub -Ivendor/gsKit -Ivendor/host-shim -I. sample/main.c || exit 1; \
		echo "ok - sample compiles: $$v"; \
	done
# Separately, because the quoting a stringised screen name needs does
# not survive `for v in $(SAMPLE_VARIANTS)`: the shell strips one layer
# at expansion and the compiler would be handed a bare identifier.
# Paired with STATIC, which is how CI builds conform.elf.
	@$(CC) -std=c99 -Wall -Werror -S -o /dev/null \
		-DPS2UI_SAMPLE_STATIC -DPS2UI_SAMPLE_SCREEN='"probe"' \
		-Istub -Ivendor/gsKit -Ivendor/host-shim -I. sample/main.c
	@echo "ok - sample compiles: -DPS2UI_SAMPLE_SCREEN"
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
	@$(CC) -std=c99 -Wall -Werror -S -o /dev/null \
		-DPS2UI_SAMPLE_OPLENV -DPS2UI_OPLENV_FILL \
		-Istub -Ivendor/gsKit -Ivendor/host-shim -I. sample/main.c
	@echo "ok - sample compiles: -DPS2UI_SAMPLE_OPLENV -DPS2UI_OPLENV_FILL"

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

clean:
	rm -rf build

.PHONY: test test-narrow syntax-check timing-check clean
