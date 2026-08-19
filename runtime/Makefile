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

test: build/test_runtime $(LIST_UIB)
	./build/test_runtime $(UIB) $(LIST_UIB)

$(LIST_UIB): tests/fixture/list.html tests/fixture/list.css
	@mkdir -p build
	node ../packages/layout/bin/ps2ui-layout.js \
		tests/fixture/list.html tests/fixture/list.css -o build/list.json
	PYTHONPATH=../packages/baker python3 -m ps2ui_bake build/list.json -o $@

# The same objects again with the old-gsKit fallback, proving the
# -DPS2UI_GSKIT_HAS_FUNCTION=0 path also builds clean.
test-compat: build/test_runtime_compat $(LIST_UIB)
	./build/test_runtime_compat $(UIB) $(LIST_UIB)

build/test_runtime: ps2ui.c stub/gskit_stub.c tests/test_runtime.c ps2ui.h stub/gskit_stub.h
	@mkdir -p build
	$(CC) $(CFLAGS) -DPS2UI_HOST_TEST -Istub ps2ui.c stub/gskit_stub.c tests/test_runtime.c -o $@

build/test_runtime_compat: ps2ui.c stub/gskit_stub.c tests/test_runtime.c ps2ui.h stub/gskit_stub.h
	@mkdir -p build
	$(CC) $(CFLAGS) -DPS2UI_HOST_TEST -DPS2UI_GSKIT_HAS_FUNCTION=0 -Istub \
		ps2ui.c stub/gskit_stub.c tests/test_runtime.c -o $@

clean:
	rm -rf build

.PHONY: test test-compat clean
