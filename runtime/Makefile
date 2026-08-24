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

test: syntax-check build/test_runtime $(LIST_UIB)
	./build/test_runtime $(UIB) $(LIST_UIB)

# The sample is the bring-up instrument -- the ELF that goes on a
# memory card -- and until this target existed nothing but the ps2dev
# container in CI ever compiled main.c. A change to it was a
# push-and-hope, and the telemetry build duly shipped `asm volatile`,
# which -std=c99 rejects, with every local suite green. Same flags the
# console build uses; -fsyntax-only because the host has no EE.
SAMPLE_VARIANTS = "" -DPS2UI_SAMPLE_STATIC -DPS2UI_SAMPLE_MINIMAL -DPS2UI_SAMPLE_PROBE -DPS2UI_SAMPLE_PROBE6 -DPS2UI_SAMPLE_TELEMETRY

syntax-check:
	@for v in $(SAMPLE_VARIANTS); do \
		$(CC) -std=c99 -Wall -Werror -fsyntax-only $$v \
			-Istub -Ivendor/gsKit -Ivendor/host-shim -I. sample/main.c || exit 1; \
		echo "ok - sample compiles: $$v"; \
	done
# Separately, because the quoting a stringised screen name needs does
# not survive `for v in $(SAMPLE_VARIANTS)`: the shell strips one layer
# at expansion and the compiler would be handed a bare identifier.
# Paired with STATIC, which is how CI builds conform.elf.
	@$(CC) -std=c99 -Wall -Werror -fsyntax-only \
		-DPS2UI_SAMPLE_STATIC -DPS2UI_SAMPLE_SCREEN='"probe"' \
		-Istub -Ivendor/gsKit -Ivendor/host-shim -I. sample/main.c
	@echo "ok - sample compiles: -DPS2UI_SAMPLE_SCREEN"
# The linear-CLUT arm of step 3's A/B lives in ps2ui.c, not main.c, so
# it needs its own line: the loop above only ever compiles the sample.
	@$(CC) -std=c99 -Wall -Werror -fsyntax-only \
		-DPS2UI_CLUT_PERMUTE=0 -Istub -Ivendor/gsKit -Ivendor/host-shim -I. ps2ui.c
	@echo "ok - runtime compiles: -DPS2UI_CLUT_PERMUTE=0"
# Step 4b's reference arm, likewise in ps2ui.c rather than main.c.
	@$(CC) -std=c99 -Wall -Werror -fsyntax-only \
		-DPS2UI_PRIMALPHA_OFF -Istub -Ivendor/gsKit -Ivendor/host-shim -I. ps2ui.c
	@echo "ok - runtime compiles: -DPS2UI_PRIMALPHA_OFF"

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

build/test_runtime: ps2ui.c stub/gskit_stub.c tests/test_runtime.c ps2ui.h stub/gskit_stub.h
	@mkdir -p build
	$(CC) $(CFLAGS) -Istub -Ivendor/gsKit -Ivendor/host-shim ps2ui.c stub/gskit_stub.c tests/test_runtime.c -o $@

clean:
	rm -rf build

.PHONY: test syntax-check clean
