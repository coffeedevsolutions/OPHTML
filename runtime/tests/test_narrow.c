/* The arena arithmetic at the EE's address width.
 *
 * ps2ui.c is compiled here with -DPS2UI_ARENA_LIMIT=0xFFFFFFFF, which
 * is what a 32-bit size_t can hold and therefore what the console
 * actually has. The ordinary suite cannot reach this: it runs 64-bit,
 * where every carve a legal header can demand is representable, and
 * the CI image has no 32-bit libc to link a -m32 build against.
 *
 * Two checks, and the second is what stops the first from being
 * satisfied by a guard that refuses everything:
 *
 *   huge.uib  -- 65535 slots at capacity 65535, so the carve totals
 *                just past 4 GiB. Must be refused, at both entry
 *                points, without carving anything.
 *   ui.uib    -- the real example blob. Must still load, at the same
 *                narrow width, with a real arena.
 *
 * Kept out of test_runtime.c deliberately. That binary is built once
 * at the host's width and shares one ps2ui.o; a per-file limit
 * override cannot be expressed there without compiling the runtime
 * twice into one link. */

#include "../ps2ui.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int checks, failures;

#define CHECK(cond, name)                                            \
    do {                                                             \
        checks++;                                                    \
        if (cond) { printf("ok %d - %s\n", checks, (name)); }        \
        else { failures++; printf("not ok %d - %s\n", checks, (name)); } \
    } while (0)

static void *slurp(const char *path, size_t *len)
{
    FILE *f = fopen(path, "rb");
    void *p;
    long n;
    if (!f) { fprintf(stderr, "cannot open %s\n", path); exit(2); }
    fseek(f, 0, SEEK_END); n = ftell(f); fseek(f, 0, SEEK_SET);
    p = malloc((size_t)n);
    if (fread(p, 1, (size_t)n, f) != (size_t)n) { fprintf(stderr, "short read\n"); exit(2); }
    fclose(f);
    *len = (size_t)n;
    return p;
}

int main(int argc, char **argv)
{
    size_t ulen, hlen, need;
    void *ublob, *hblob, *arena;
    ps2ui_ctx ctx;

    if (argc < 3) {
        fprintf(stderr, "usage: %s <ui.uib> <huge.uib>\n", argv[0]);
        return 2;
    }
    ublob = slurp(argv[1], &ulen);
    hblob = slurp(argv[2], &hlen);

    /* The blob is well formed. It is not corrupt, not truncated, not a
     * wrong version -- every count in it is legal for the format. It
     * simply asks for more arena than a 32-bit machine can address,
     * which is a thing a header is allowed to say and the runtime is
     * not allowed to wrap on. */
    CHECK(ps2ui_arena_size(hblob, hlen) == 0,
          "a carve past the target's address width is reported as 0, "
          "not as a wrapped small number");
    {
        static uint8_t small[65536] __attribute__((aligned(PS2UI_ARENA_ALIGN)));
        CHECK(ps2ui_load(&ctx, hblob, hlen, small, sizeof small)
              == PS2UI_ERR_TOO_MANY,
              "and ps2ui_load refuses it by name rather than carving");
        /* "A refused load leaves the arena untouched" belongs with this
         * one and is NOT asserted here: at this host's real width the
         * refusal happens on the ERR_ARENA path whether or not the
         * guard exists, so the check could not fail and would be
         * decoration. It lives in test_runtime.c, against an ordinary
         * blob and a too-small arena, where reordering the carve does
         * break it. */
    }

    /* The other half of the argument. Everything above passes just as
     * well if the guard rejects every blob it is shown. */
    need = ps2ui_arena_size(ublob, ulen);
    CHECK(need > 0, "an ordinary blob still gets an arena at this width");
    arena = malloc(need);
    CHECK(ps2ui_load(&ctx, ublob, ulen, arena, need) == PS2UI_OK,
          "and still loads");
    CHECK(ps2ui_screen_name(&ctx) != NULL, "and is usable afterwards");

    printf("1..%d\n", checks);
    printf("%s: %d checks, %d failure(s)\n",
           failures ? "FAIL" : "PASS", checks, failures);
    return failures ? 1 : 0;
}
