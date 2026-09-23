# Host build of the console's portable half. The PS2 build is
# console/Makefile, which needs the ps2dev toolchain; this needs a C
# compiler and nothing else.
#
#   make -C console/tests test

CC     ?= cc
CFLAGS ?= -std=c99 -Wall -Wextra -Werror -O2

test: build/test_library
	./build/test_library

build/test_library: test_library.c ../library.c ../library.h ../scan.c ../scan.h ../mock_library.h
	mkdir -p build
	$(CC) $(CFLAGS) -o $@ test_library.c ../library.c ../scan.c

clean:
	rm -rf build

.PHONY: test clean
