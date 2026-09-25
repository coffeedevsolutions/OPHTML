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

# The same suite under ASan and UBSan, fatal on the first report. This
# code parses bytes off somebody's drive -- file names, ISO9660 records,
# SYSTEM.CNF -- so the sanitizer build is the version of the test worth
# running every time, not once by hand. A separate binary, because a
# plain `test` build of build/test_library would otherwise look up to
# date and skip the rebuild.
SANITIZE = -std=c99 -Wall -Wextra -Werror -O1 -g \
           -fsanitize=address,undefined -fno-sanitize-recover=all

test-sanitize: build/test_library_san
	./build/test_library_san

build/test_library_san: test_library.c ../library.c ../library.h ../scan.c ../scan.h ../mock_library.h
	mkdir -p build
	$(CC) $(SANITIZE) -o $@ test_library.c ../library.c ../scan.c

clean:
	rm -rf build

.PHONY: test test-sanitize clean
