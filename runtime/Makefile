# Host-side test build. The PS2 build is a source drop: add ps2ui.c to
# your ps2sdk/gsKit project and include ps2ui.h (see README).

CC      ?= cc
CFLAGS  ?= -std=c99 -Wall -Wextra -Werror -O2
UIB     ?= ../examples/memcard/build/ui.uib

test: build/test_runtime
	./build/test_runtime $(UIB)

# The same objects again with the old-gsKit fallback, proving the
# -DPS2UI_GSKIT_HAS_FUNCTION=0 path also builds clean.
test-compat: build/test_runtime_compat
	./build/test_runtime_compat $(UIB)

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
