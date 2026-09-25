/* libFuzzer harness for the .uib loader (BACKLOG S2).
 *
 * WHY. ps2ui_load bounds-checks every table, and until now that rested
 * on review plus the hand-built fixtures in test_runtime.c and
 * test_narrow.c. A blob is a file somebody else wrote: the console
 * launcher loads whatever theme.uib it finds on a drive, so a crafted
 * or truncated blob reaches this code on a real console, where an
 * out-of-bounds read is a hang or a crash with nothing on screen.
 *
 * WHAT IT DRIVES. Everything a program does with a blob it did not
 * write, in the order it does it:
 *   1. ps2ui_arena_size, on raw bytes;
 *   2. ps2ui_load into an arena of exactly that size;
 *   and, only for a blob that loaded,
 *   3. ps2ui_upload and ps2ui_render against the recording gsKit stub;
 *   4. every screen, both directions of focus movement, every theme,
 *      every slot written at and past its capacity, every focus node
 *      hidden and shown, the list window over the rows a console theme
 *      uses, and a render after each group.
 * The blob is copied into a buffer of exactly its size, so ASan sees a
 * read one byte past the end, and its CRC is rewritten (below).
 *
 * WHAT IT DOES NOT. ps2ui_tex_set and ps2ui_clut_set take caller
 * texels, not blob bytes, and are not driven here. Rendering is checked
 * for memory safety, not for what it draws: the previewer and the
 * emulator job own that.
 *
 * Build and run: `make -C runtime fuzz` (needs clang with libFuzzer).
 * CI runs a short pass; `make -C runtime fuzz FUZZ_TIME=3600` is the
 * long one. */
#include <stddef.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

#include "../ps2ui.h"
#include "../stub/gskit_stub.h"

/* Past this an arena is not a theme, and allocating it only measures
 * the host's malloc. The largest blob this repository builds needs well
 * under a megabyte; ps2ui_arena_size itself is tested on the huge
 * fixture in test_narrow.c. */
#define FUZZ_ARENA_MAX (64u << 20)

static void render(ps2ui_ctx *ctx, GSGLOBAL *gs)
{
    stub_reset_keep_tm();
    ps2ui_render(ctx, gs);
}

static void exercise(ps2ui_ctx *ctx, GSGLOBAL *gs)
{
    static const ps2ui_dir dirs[] = {
        PS2UI_UP, PS2UI_DOWN, PS2UI_LEFT, PS2UI_RIGHT
    };
    static const char *const prefixes[] = { "game-", "row-" };
    char text[300];
    uint32_t i;
    unsigned t;
    int d, k;

    if (ps2ui_upload(ctx, gs) != 0)
        return;
    render(ctx, gs);

    for (i = 0; i < ctx->hdr->n_screen; i++) {
        const char *name = (const char *)(ctx->blob +
                                          ctx->screen_table[i].name_off);
        ps2ui_screen_set(ctx, name);
        render(ctx, gs);
        for (k = 0; k < 3; k++)
            for (d = 0; d < 4; d++)
                ps2ui_move(ctx, dirs[d]);
        (void)ps2ui_focus_name(ctx);
        (void)ps2ui_screen_name(ctx);
        render(ctx, gs);
    }

    for (t = 0; t <= ctx->hdr->n_theme; t++) {
        ps2ui_theme_set(ctx, t);
        render(ctx, gs);
    }

    /* Every slot, at a length past any capacity this repository writes,
     * so the truncation path runs as well as the copy. */
    memset(text, 'W', sizeof text - 1);
    text[sizeof text - 1] = '\0';
    for (i = 0; i < ctx->hdr->n_slot; i++) {
        const char *name = (const char *)(ctx->blob + ctx->slots[i].name_off);
        ps2ui_slot_set(ctx, name, text);
        (void)ps2ui_slot_get(ctx, name);
    }
    render(ctx, gs);

    for (i = 0; i < ctx->hdr->n_focus; i++) {
        const char *name = (const char *)(ctx->blob +
                                          ctx->focus_nodes[i].name_off);
        ps2ui_visible_set(ctx, name, (int)(i & 1));
        (void)ps2ui_visible_get(ctx, name);
        ps2ui_focus_set(ctx, name);
    }
    ps2ui_offset_set(ctx, -3, 5);
    render(ctx, gs);
    ps2ui_visible_reset(ctx);

    for (k = 0; k < 2; k++) {
        ps2ui_list list;
        ps2ui_list_init(&list, prefixes[k], 10);
        ps2ui_list_set_count(ctx, &list, 37);
        ps2ui_list_move(ctx, &list, 12);
        ps2ui_list_move(ctx, &list, -40);
        ps2ui_list_select(ctx, &list, 36);
        (void)ps2ui_list_item_at(&list, 3);
        (void)ps2ui_list_selected_row(&list);
        ps2ui_list_apply_visibility(ctx, &list);
        render(ctx, gs);
    }
}

int LLVMFuzzerTestOneInput(const uint8_t *data, size_t size)
{
    ps2ui_ctx ctx;
    GSGLOBAL gs;
    uint8_t *blob;
    void *arena;
    size_t need, alloc;

    blob = malloc(size ? size : 1);
    if (blob == NULL)
        return 0;
    memcpy(blob, data, size);

    /* A hostile blob carries a valid CRC: anyone can compute one. So the
     * harness rewrites it, which is what lets a mutation get past the
     * CRC check and into the validation that matters. The check itself
     * is covered by test_runtime.c. */
    if (size >= sizeof(ps2ui_header)) {
        uint32_t crc;
        memset(blob + offsetof(ps2ui_header, crc32), 0, 4);
        crc = ps2ui_crc32(blob, size);
        memcpy(blob + offsetof(ps2ui_header, crc32), &crc, 4);
    }

    /* ps2ui_load runs whatever ps2ui_arena_size says, so its own
     * refusals (magic, version, alignment, no screens) are reached too:
     * the first version of this harness returned early on a zero size
     * and never ran them. A zero size gets a token arena, which a blob
     * that loads would have to overrun. The last input byte decides
     * whether a real size is passed exactly or one byte short, so the
     * arena check runs as well. */
    need = ps2ui_arena_size(blob, size);
    if (need > FUZZ_ARENA_MAX) {
        free(blob);
        return 0;
    }
    alloc = need ? need : 64;
    arena = aligned_alloc(PS2UI_ARENA_ALIGN,
                          (alloc + PS2UI_ARENA_ALIGN - 1) &
                          ~(size_t)(PS2UI_ARENA_ALIGN - 1));
    if (arena == NULL) {
        free(blob);
        return 0;
    }
    if (need && size && (data[size - 1] & 1u))
        alloc = need - 1;

    /* The console's VRAM, as test_runtime.c sets it up: two CT32
     * display buffers at 640x448, no Z. */
    memset(&gs, 0, sizeof gs);
    gs.CurrentPointer = 2u * ((640u * 448u * 4u + 8191u) & ~8191u);
    gs.Width = 640;
    gs.Height = 448;
    stub_reset();

    memset(&ctx, 0, sizeof ctx);
    if (ps2ui_load(&ctx, blob, size, arena, alloc) == PS2UI_OK)
        exercise(&ctx, &gs);

    free(arena);
    free(blob);
    return 0;
}
