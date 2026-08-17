/* Host-side checks for the real ps2ui.c, compiled -Werror against the
 * gsKit stub and run over a real baked blob (the memcard example).
 *
 * usage: test_runtime <ui.uib>
 */

#include "../ps2ui.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int checks = 0, failures = 0;

#define CHECK(cond, name) do { \
    checks++; \
    if (cond) { printf("ok %d - %s\n", checks, name); } \
    else { failures++; printf("not ok %d - %s\n", checks, name); } \
} while (0)

static void *slurp(const char *path, size_t *out_len)
{
    FILE *fh = fopen(path, "rb");
    void *buf;
    long len;
    if (!fh) { perror(path); exit(2); }
    fseek(fh, 0, SEEK_END);
    len = ftell(fh);
    fseek(fh, 0, SEEK_SET);
    buf = malloc((size_t)len);
    if (fread(buf, 1, (size_t)len, fh) != (size_t)len) { perror(path); exit(2); }
    fclose(fh);
    *out_len = (size_t)len;
    return buf;
}

static int render_and_count(ps2ui_ctx *ctx, GSGLOBAL *gs)
{
    stub_reset();
    ps2ui_render(ctx, gs);
    return g_stub.n_prims;
}

int main(int argc, char **argv)
{
    size_t len;
    void *blob;
    ps2ui_ctx ctx;
    GSGLOBAL gs;
    int i;

    if (argc != 2) { fprintf(stderr, "usage: %s <ui.uib>\n", argv[0]); return 2; }
    blob = slurp(argv[1], &len);
    memset(&gs, 0, sizeof gs);
    gs.Width = 640; gs.Height = 448;

    /* ---- struct layout matches the on-disk format ---- */
    CHECK(sizeof(ps2ui_header) == 48, "header struct is 48 bytes");
    CHECK(sizeof(ps2ui_tex_entry) == 16, "tex entry struct is 16 bytes");
    CHECK(sizeof(ps2ui_clut_entry) == 8, "clut entry struct is 8 bytes");
    CHECK(sizeof(ps2ui_cmd) == 32, "cmd struct is 32 bytes");
    CHECK(sizeof(ps2ui_focus_node) == 24, "focus node struct is 24 bytes");

    /* ---- loader ---- */
    CHECK(ps2ui_load(&ctx, blob, len) == PS2UI_OK, "load real blob");
    CHECK(ctx.hdr->canvas_w == 640 && ctx.hdr->canvas_h == 448, "canvas is 640x448");
    CHECK(ctx.hdr->n_cmd > 0, "blob has commands");
    CHECK(ctx.hdr->n_focus == 9, "memcard example has 9 focusables");
    CHECK(ctx.focus != PS2UI_NONE, "initial focus set");
    CHECK(strcmp(ps2ui_focus_name(&ctx), "nav-games") == 0, "autofocus lands on nav-games");

    /* Corrupt copies must be rejected. */
    {
        ps2ui_ctx bad;
        uint8_t *dup = malloc(len);
        memcpy(dup, blob, len);
        dup[0] ^= 0xFF;
        CHECK(ps2ui_load(&bad, dup, len) == PS2UI_ERR_MAGIC, "bad magic rejected");
        memcpy(dup, blob, len);
        CHECK(ps2ui_load(&bad, dup, 40) == PS2UI_ERR_TRUNCATED, "truncated header rejected");
        CHECK(ps2ui_load(&bad, dup, len / 2) == PS2UI_ERR_TRUNCATED, "truncated body rejected");
        memcpy(dup, blob, len);
        ((ps2ui_header *)dup)->version = 99;
        CHECK(ps2ui_load(&bad, dup, len) == PS2UI_ERR_VERSION, "wrong version rejected");
        free(dup);
    }

    /* ---- CSM1 permutation mirrors the baker ---- */
    CHECK(ps2ui_clut_csm1(0) == 0 && ps2ui_clut_csm1(7) == 7, "csm1 fixes 0..7");
    CHECK(ps2ui_clut_csm1(8) == 16 && ps2ui_clut_csm1(16) == 8, "csm1 swaps 8 <-> 16");
    CHECK(ps2ui_clut_csm1(0x1F) == 0x1F, "csm1 fixes 24..31");
    for (i = 0; i < 256; i++)
        if (ps2ui_clut_csm1(ps2ui_clut_csm1((uint32_t)i)) != (uint32_t)i)
            break;
    CHECK(i == 256, "csm1 is an involution over 0..255");

    /* ---- upload ---- */
    CHECK(ps2ui_upload(&ctx, &gs) == 0, "textures fit in 4 MB VRAM");
    CHECK(g_stub.n_uploads == (int)ctx.hdr->n_tex, "every texture uploaded once");

    /* ---- render: focus filtering ---- */
    {
        int base = render_and_count(&ctx, &gs);
        int per_state[16];
        int all_equal = 1, any_diff_content = 0, s;
        CHECK(base > 0, "initial state draws primitives");
        CHECK(base <= (int)ctx.hdr->n_cmd, "state filter draws a subset of records");

        for (s = 0; s < (int)ctx.hdr->n_focus && s < 16; s++) {
            uint16_t saved = ctx.focus;
            ctx.focus = (uint16_t)s;
            per_state[s] = render_and_count(&ctx, &gs);
            ctx.focus = saved;
        }
        for (s = 1; s < (int)ctx.hdr->n_focus && s < 16; s++)
            if (per_state[s] != per_state[0]) all_equal = 0;
        /* :focus is a paint-only delta — identical draw-call cost. */
        CHECK(all_equal, "every focus state costs the same draw calls");

        /* But the content differs between two states. */
        {
            u64 sig0 = 0, sig1 = 0;
            int k;
            ctx.focus = 0;
            stub_reset(); ps2ui_render(&ctx, &gs);
            for (k = 0; k < g_stub.n_prims; k++) sig0 ^= g_stub.prims[k].color * (u64)(k + 1);
            ctx.focus = 1;
            stub_reset(); ps2ui_render(&ctx, &gs);
            for (k = 0; k < g_stub.n_prims; k++) sig1 ^= g_stub.prims[k].color * (u64)(k + 1);
            ctx.focus = ctx.hdr->initial_focus;
            any_diff_content = sig0 != sig1;
        }
        CHECK(any_diff_content, "focus state changes what is drawn");
    }

    /* ---- modulate color domain (backlog B1) ----
     * TEXQUADs draw with TEX MODULATE where 0x80 is identity; a channel
     * above 0x80 means the baker leaked a full-range color and hardware
     * would render it overbright. Solid QUADs are flat-shaded and may
     * use the full 0..255 RGB range. */
    {
        uint32_t k;
        int domain_ok = 1;
        for (k = 0; k < ctx.hdr->n_cmd; k++) {
            const ps2ui_cmd *c = &ctx.cmd[k];
            if (c->op == PS2UI_OP_TEXQUAD
                && (c->r > 0x80 || c->g > 0x80 || c->b > 0x80 || c->a > 0x80)) {
                domain_ok = 0;
                break;
            }
            if (c->op == PS2UI_OP_QUAD && c->a > 0x80) {
                domain_ok = 0;
                break;
            }
        }
        CHECK(domain_ok, "texquad colors in the 0x80 modulate domain");
    }

    /* ---- render: geometry stays on canvas ---- */
    {
        int k, in_bounds = 1;
        stub_reset();
        ps2ui_render(&ctx, &gs);
        for (k = 0; k < g_stub.n_prims; k++) {
            const stub_prim *p = &g_stub.prims[k];
            if (p->x1 < 0 || p->y1 < 0 || p->x2 > 640 || p->y2 > 448
                || p->x2 < p->x1 || p->y2 < p->y1) { in_bounds = 0; break; }
        }
        CHECK(in_bounds, "all primitives inside the canvas");
        CHECK(g_stub.last_scissor == GS_SETREG_SCISSOR(0, 639, 0, 447),
              "scissor restored to full canvas after replay");
    }

    /* ---- focus graph walk (memcard example geometry) ---- */
    CHECK(ps2ui_move(&ctx, PS2UI_RIGHT) == 1, "right from nav-games moves");
    CHECK(strcmp(ps2ui_focus_name(&ctx), "tile-ico") == 0, "lands on tile-ico");
    CHECK(ps2ui_move(&ctx, PS2UI_RIGHT) == 1
          && strcmp(ps2ui_focus_name(&ctx), "tile-sotc") == 0, "right again: tile-sotc");
    CHECK(ps2ui_move(&ctx, PS2UI_DOWN) == 1
          && strcmp(ps2ui_focus_name(&ctx), "tile-ffx") == 0, "down: tile-ffx");
    CHECK(ps2ui_move(&ctx, PS2UI_DOWN) == 0, "down off the grid edge stays put");
    CHECK(ps2ui_move(&ctx, PS2UI_LEFT) == 1 && ps2ui_move(&ctx, PS2UI_LEFT) == 1
          && strcmp(ps2ui_focus_name(&ctx), "nav-settings") == 0,
          "left twice reaches the nav column");
    CHECK(ps2ui_move(&ctx, PS2UI_LEFT) == 0, "left off the nav column stays put");

    printf("1..%d\n", checks);
    printf("%s: %d checks, %d failure(s)\n", failures ? "FAIL" : "PASS", checks, failures);
    free(blob);
    return failures ? 1 : 0;
}
