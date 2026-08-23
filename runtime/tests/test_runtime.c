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

/* Linear-scan lookups used to check the runtime's binary searches.
 * Deliberately a different algorithm over the same bytes: two
 * implementations that agree is evidence, one implementation compared
 * against itself is not. */
static const ps2ui_glyph *scan_glyph(const ps2ui_ctx *c,
                                     const ps2ui_font_entry *f, uint32_t cp)
{
    const ps2ui_glyph *g = (const ps2ui_glyph *)(c->blob + f->glyphs_off);
    uint32_t i;
    for (i = 0; i < f->glyph_count; i++)
        if (g[i].codepoint == cp) return &g[i];
    return cp == '?' ? 0 : scan_glyph(c, f, '?');
}

static uint32_t find_slot(const ps2ui_ctx *c, const char *name)
{
    uint32_t i;
    for (i = 0; i < c->hdr->n_slot; i++)
        if (strcmp((const char *)(c->blob + c->slots[i].name_off), name) == 0)
            return i;
    return PS2UI_NONE;
}

static int scan_kern(const ps2ui_ctx *c, const ps2ui_font_entry *f,
                     uint32_t prev, uint32_t cp)
{
    const ps2ui_kern *k = (const ps2ui_kern *)(c->blob + f->kerns_off);
    uint32_t i;
    for (i = 0; i < f->kern_count; i++)
        if (k[i].prev == prev && k[i].cur == cp) return k[i].amount;
    return 0;
}

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

    if (argc < 2 || argc > 3) {
        fprintf(stderr, "usage: %s <ui.uib> [list.uib]\n", argv[0]);
        return 2;
    }
    blob = slurp(argv[1], &len);
    memset(&gs, 0, sizeof gs);
    gs.Width = 640; gs.Height = 448;

    /* ---- struct layout matches the on-disk format ---- */
    CHECK(sizeof(ps2ui_header) == 76, "header struct is 76 bytes");
    CHECK(sizeof(ps2ui_screen_entry) == 24, "screen entry struct is 24 bytes");
    CHECK(sizeof(ps2ui_font_entry) == 24, "font entry struct is 24 bytes");
    CHECK(sizeof(ps2ui_glyph) == 20, "glyph struct is 20 bytes");
    CHECK(sizeof(ps2ui_kern) == 12, "kern struct is 12 bytes");
    CHECK(sizeof(ps2ui_slot_entry) == 32, "slot entry struct is 32 bytes");
    CHECK(sizeof(ps2ui_tex_entry) == 16, "tex entry struct is 16 bytes");
    CHECK(sizeof(ps2ui_clut_entry) == 8, "clut entry struct is 8 bytes");
    CHECK(sizeof(ps2ui_cmd) == 32, "cmd struct is 32 bytes");
    CHECK(sizeof(ps2ui_focus_node) == 24, "focus node struct is 24 bytes");

    u32 vram_before, vram_used;

    /* ---- loader ---- */
    CHECK(ps2ui_load(&ctx, blob, len) == PS2UI_OK, "load real blob");
    CHECK(ctx.hdr->canvas_w == 640 && ctx.hdr->canvas_h == 448, "canvas is 640x448");
    CHECK(ctx.hdr->n_cmd > 0, "blob has commands");
    CHECK(ctx.hdr->n_screen == 2, "memcard example has 2 screens");
    CHECK(ctx.screen_table[0].focus_count == 9, "library screen has 9 focusables");
    CHECK(ctx.hdr->n_focus == 16, "16 focusables across both screens");
    CHECK(strcmp(ps2ui_screen_name(&ctx), "library") == 0, "boots into the library screen");
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
        memcpy(dup, blob, len);
        dup[len / 2] ^= 0xFF; /* one flipped bit in the body */
        CHECK(ps2ui_load(&bad, dup, len) == PS2UI_ERR_CRC, "corrupt body fails crc");
        memcpy(dup, blob, len);
        ((ps2ui_header *)dup)->feature_flags |= 0x8000;
        CHECK(ps2ui_load(&bad, dup, len) == PS2UI_ERR_FEATURES,
              "unknown feature bits rejected");
        free(dup);
    }

    /* ---- crc32 matches zlib's definition ---- */
    CHECK(ps2ui_crc32("123456789", 9) == 0xCBF43926u, "crc32 check vector");

    /* ---- CSM1 permutation mirrors the baker ---- */
    CHECK(ps2ui_clut_csm1(0) == 0 && ps2ui_clut_csm1(7) == 7, "csm1 fixes 0..7");
    CHECK(ps2ui_clut_csm1(8) == 16 && ps2ui_clut_csm1(16) == 8, "csm1 swaps 8 <-> 16");
    CHECK(ps2ui_clut_csm1(0x1F) == 0x1F, "csm1 fixes 24..31");
    for (i = 0; i < 256; i++)
        if (ps2ui_clut_csm1(ps2ui_clut_csm1((uint32_t)i)) != (uint32_t)i)
            break;
    CHECK(i == 256, "csm1 is an involution over 0..255");

    /* ---- upload ---- */
    vram_before = gs.CurrentPointer;
    CHECK(ps2ui_upload(&ctx, &gs) == 0, "textures fit in 4 MB VRAM");
    /* What the blob's textures actually cost. Step 9's starved cases at
     * the end of this file size themselves from this rather than from a
     * hardcoded budget: a constant tuned to today's example is a check
     * that goes red when someone shrinks an asset by six percent, for a
     * reason that has nothing to do with what they changed. */
    vram_used = gs.CurrentPointer - vram_before;
    CHECK(g_stub.n_uploads == (int)ctx.hdr->n_tex, "every texture uploaded once");

    /* The EE writes back lazily and the GIF reads main memory, so any
     * buffer the CPU touched before an upload has to be flushed or the
     * GS reads what was there before. permute_clut builds every CLUT
     * with ordinary stores immediately before the transfer, which puts
     * the whole palette in dirty cache lines -- and glyph coverage IS
     * the palette's alpha, so a stale one turns text to noise while
     * leaving geometry untouched.
     *
     * gsKit_texture_upload does not flush. gsKit_TexManager_bind does,
     * and Open-PS2-Loader uses that path for the same reason. A host
     * cache is coherent, so this cannot be caught by rendering: the
     * stub records the calls instead and the upload checks coverage. */
    CHECK(g_stub.n_uploads_unflushed == 0,
          "every upload is preceded by a writeback of its pixels and its CLUT");
    CHECK(g_stub.n_flushes > 0,
          "and flushes were actually recorded, so the check above had something to check");

    /* ---- load: DMA alignment guard ---- */
    /* The GIF DMA reads texture bytes in place and its source address
     * must be qword aligned. The baker aligns everything relative to
     * the file; the base address is the embedding host's to get wrong
     * -- bin2c output, a heap buffer, a memcard read. +8 keeps every
     * struct overlay legal (all fields are 4-aligned) while breaking
     * the one property DMA needs, so the load must refuse for the
     * right reason and not by accident of a torn header. */
    {
        ps2ui_ctx mis;
        uint8_t *shifted = malloc(len + 32);   /* room for align pad (<=16) plus the +8 shift */
        size_t pad = 16 - (((uintptr_t)shifted) & 15u);
        uint8_t *base = shifted + pad;      /* 16-aligned */
        memcpy(base + 8, blob, len);
        CHECK(ps2ui_load(&mis, base + 8, len) == PS2UI_ERR_ALIGN,
              "a blob at a non-16-aligned address is refused with PS2UI_ERR_ALIGN");
        memcpy(base, blob, len);
        CHECK(ps2ui_load(&mis, base, len) == PS2UI_OK,
              "and the identical bytes load once the address is aligned, so it was the address");
        free(shifted);
    }

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

    /* ---- render: the blend equation is asserted, not inherited ----
     *
     * gsKit's default ALPHA is GS_BLEND_BACK2FRONT, which decodes to
     * A=Cd B=Cs C=As D=Cs -- the operands swapped -- so the effective
     * coverage is (128 - As). Every blended quad ran with its alpha
     * inverted, and a quad the format calls fully opaque composited to
     * pure background. It took a console to find, because nothing in
     * the host toolchain models GS state. This is the fence. */
    {
        u64 want = GS_SETREG_ALPHA(0, 1, 0, 1, 0);
        stub_prim_alpha = 0;
        stub_prim_alpha_set = 0;
        ps2ui_render(&ctx, &gs);
        CHECK(stub_prim_alpha_set, "render sets the GS blend mode rather than inheriting it");
        CHECK(stub_prim_alpha == want, "and sets it to (Cs - Cd) * As >> 7 + Cd");
    }

    /* ---- render: PrimAlphaEnable, which is TEX0.TCC as well ---- */
    /* gsKit passes gsGlobal->PrimAlphaEnable as TEX0.TCC at every one
     * of its GS_SETREG_TEX0 sites, and reads it per draw. TCC=0 means
     * "this texture has no alpha channel", and glyph coverage IS the
     * alpha channel -- so a host that leaves the field off turns every
     * glyph into a filled box while untextured quads, which emit no
     * TEX0, keep rendering perfectly. Same class as the inverted blend
     * above: global GS state the format depends on and the runtime did
     * not own. Starting from OFF is what makes this test able to fail;
     * the sample always sets it ON first, so a version that only
     * checked the field after a default render would pass without the
     * assignment existing. */
    {
        gs.PrimAlphaEnable = GS_SETTING_OFF;
        ps2ui_render(&ctx, &gs);
        CHECK(gs.PrimAlphaEnable == GS_SETTING_ON,
              "render turns PrimAlphaEnable on, so TEX0.TCC keeps the atlas alpha a host left off");
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

    /* ---- focus API (F10) ---- */
    CHECK(ps2ui_focus_set(&ctx, "tile-okami") == 1
          && strcmp(ps2ui_focus_name(&ctx), "tile-okami") == 0,
          "focus_set jumps by name");
    CHECK(ps2ui_focus_set(&ctx, "no-such-node") == 0, "focus_set rejects unknown names");

    /* ---- dynamic text (F2): the example's "count" slot ---- */
    CHECK((ctx.hdr->feature_flags & PS2UI_FEAT_DYNAMIC_TEXT) != 0,
          "example blob carries the dynamic-text feature bit");
    CHECK(ctx.hdr->n_slot == 6 && ctx.hdr->n_font >= 1, "six slots across screens");
    CHECK(ctx.screen_table[0].slot_count == 1, "library screen owns one slot");
    CHECK(strcmp(ps2ui_slot_get(&ctx, "count"), "6 titles") == 0,
          "unset slot serves its placeholder");
    {
        int with_placeholder, with_text, with_short;
        with_placeholder = render_and_count(&ctx, &gs);
        CHECK(ps2ui_slot_set(&ctx, "count", "42 titles") == 1, "slot_set by name");
        CHECK(strcmp(ps2ui_slot_get(&ctx, "count"), "42 titles") == 0,
              "slot_get returns runtime text");
        with_text = render_and_count(&ctx, &gs);
        /* "42 titles" has one more inked glyph than "6 titles". */
        CHECK(with_text == with_placeholder + 1, "runtime text changes glyph count");
        ps2ui_slot_set(&ctx, "count", "7");
        with_short = render_and_count(&ctx, &gs);
        CHECK(with_short < with_placeholder, "short text draws fewer glyphs");
        CHECK(ps2ui_slot_set(&ctx, "nope", "x") == 0, "slot_set rejects unknown names");
        ps2ui_slot_set(&ctx, "count", NULL);
        CHECK(strcmp(ps2ui_slot_get(&ctx, "count"), "6 titles") == 0,
              "NULL reverts to placeholder");

        /* B12: "" blanks the slot instead of reverting. */
        ps2ui_slot_set(&ctx, "count", "");
        CHECK(strcmp(ps2ui_slot_get(&ctx, "count"), "") == 0,
              "empty string blanks a slot");
        {
            int blank_prims = render_and_count(&ctx, &gs);
            ps2ui_slot_set(&ctx, "count", NULL);
            CHECK(blank_prims < render_and_count(&ctx, &gs),
                  "a blanked slot draws no glyphs");
        }

        /* F9: the pen kerns, and it kerns by the table in the blob.
         *
         * Expected positions are computed here by a LINEAR scan of the
         * same tables the runtime binary-searches. Two independent
         * lookups over one table is the point: a bsearch that returns
         * the wrong record, or a pen that forgets to add what it
         * found, disagrees with the scan. Recomputing with the
         * runtime's own helper would assert nothing. */
        {
            uint32_t si = find_slot(&ctx, "count");
            const ps2ui_slot_entry *sl = &ctx.slots[si];
            const ps2ui_font_entry *fe = &ctx.fonts[sl->font];
            const char *probe = "AV Ta To Wa";
            int base_prims, expect_x[32], n_expect = 0, i, ok = 1, kerned = 0;
            int pen = 0;
            uint32_t prev = 0;
            int have_prev = 0;
            const char *p2 = probe;

            CHECK((ctx.hdr->feature_flags & PS2UI_FEAT_KERNING) != 0,
                  "example blob declares the kerning feature bit");
            CHECK(fe->kern_count > 0, "and its font carries kern pairs");

            while (*p2) {
                uint32_t cp = (uint32_t)(unsigned char)*p2++;
                const ps2ui_glyph *g = scan_glyph(&ctx, fe, cp);
                if (!g)
                    continue;
                if (have_prev) {
                    int k = scan_kern(&ctx, fe, prev, cp);
                    if (k) kerned++;
                    pen += k;
                }
                if (g->w > 0)
                    expect_x[n_expect++] = sl->x + pen + g->bearing_x;
                pen += g->advance;
                prev = cp;
                have_prev = 1;
            }
            CHECK(kerned >= 3, "the probe string exercises several pairs");

            /* The prim comparison below reads the slot's glyphs as the
             * tail of the frame, which holds because render_slots runs
             * after the command list and this screen owns exactly one
             * slot. Stated rather than assumed. */
            CHECK(ctx.screen_table[ctx.screen].slot_count == 1
                  && ctx.screen_table[ctx.screen].slot_first == si,
                  "the probed slot is the only one on this screen");

            ps2ui_slot_set(&ctx, "count", "");
            base_prims = render_and_count(&ctx, &gs);
            ps2ui_slot_set(&ctx, "count", probe);
            CHECK(render_and_count(&ctx, &gs) == base_prims + n_expect,
                  "the slot draws one prim per inked glyph");
            for (i = 0; i < n_expect; i++) {
                if ((int)g_stub.prims[base_prims + i].x1 != expect_x[i])
                    ok = 0;
            }
            CHECK(ok, "and lands every glyph on the kerned pen position");

            /* And the kerning is doing something: the same glyphs with
             * the pairs ignored would sit further right. */
            {
                int unkerned = 0;
                const char *p3 = probe;
                while (*p3) {
                    const ps2ui_glyph *g =
                        scan_glyph(&ctx, fe, (uint32_t)(unsigned char)*p3++);
                    if (g) unkerned += g->advance;
                }
                CHECK(pen < unkerned,
                      "a kerned run is narrower than the sum of its advances");
            }
            ps2ui_slot_set(&ctx, "count", NULL);
        }

        /* B11: byte-wise truncation must not split a UTF-8 sequence.
         * The "count" slot has capacity 15; each 'e' with an acute is
         * two bytes, so a naive strncpy would cut the 8th in half and
         * the pen would draw a replacement glyph. */
        ps2ui_slot_set(&ctx, "count", "\u00e9\u00e9\u00e9\u00e9\u00e9\u00e9\u00e9\u00e9");
        {
            const char *got = ps2ui_slot_get(&ctx, "count");
            size_t n = strlen(got), k;
            int trailing_partial = 0;
            for (k = 0; k < n; k++) {
                unsigned char c = (unsigned char)got[k];
                if ((c & 0xE0u) == 0xC0u) {   /* 2-byte lead */
                    if (k + 1 >= n) { trailing_partial = 1; break; }
                    k++;
                }
            }
            CHECK(n <= 15, "truncated at the slot capacity");
            CHECK(n % 2 == 0, "truncation landed on a character boundary");
            CHECK(!trailing_partial, "no split UTF-8 sequence survives");
        }
        ps2ui_slot_set(&ctx, "count", NULL);
    }

    /* ---- display aspect (widescreen support) ---- */
    CHECK(ctx.hdr->display_aspect_num == 4 && ctx.hdr->display_aspect_den == 3,
          "memcard example is authored for 4:3");
    /* 640x448 at 4:3 is PAR 0.9333, not 1.0: the GS framebuffer is not
     * square-pixel even in the ordinary case. */
    CHECK(ps2ui_pixel_aspect_x1000(&ctx) == 933,
          "pixel aspect derives to 933 for 4:3 at 640x448");

    /* ---- multi-screen (F4) ---- */
    {
        int lib_prims, saves_prims;
        ps2ui_focus_set(&ctx, "nav-games");
        lib_prims = render_and_count(&ctx, &gs);
        CHECK(ps2ui_screen_set(&ctx, "saves") == 1, "screen_set switches by name");
        CHECK(strcmp(ps2ui_screen_name(&ctx), "saves") == 0, "current screen renamed");
        CHECK(strcmp(ps2ui_focus_name(&ctx), "nav-saves") == 0,
              "saves screen starts at its autofocus");
        saves_prims = render_and_count(&ctx, &gs);
        CHECK(saves_prims > 0 && saves_prims != lib_prims,
              "screens render different command ranges");
        /* Focus memory: wander on saves, leave, come back. */
        CHECK(ps2ui_focus_set(&ctx, "save-ffx") == 1, "focus a save row");
        CHECK(ps2ui_screen_set(&ctx, "library") == 1, "back to library");
        CHECK(strcmp(ps2ui_focus_name(&ctx), "nav-games") == 0,
              "library remembered its focus");
        CHECK(ps2ui_screen_set(&ctx, "saves") == 1
              && strcmp(ps2ui_focus_name(&ctx), "save-ffx") == 0,
              "saves remembered its focus");
        CHECK(ps2ui_screen_set(&ctx, "settings") == 0, "unknown screen rejected");
        /* Slots are per-screen: the saves counter exists here. */
        CHECK(ps2ui_slot_set(&ctx, "save-count", "12 saves") == 1,
              "saves screen slot settable");
        ps2ui_screen_set(&ctx, "library");
    }

    /* ---- list window (F6) ----
     * Pure index arithmetic, so it needs no blob support and is tested
     * without one. These are the cases an app reimplementing this by
     * hand gets wrong; that is the reason the helper exists. */
    {
        ps2ui_list list;
        int r;

        ps2ui_list_init(&list, "row-", 4);
        CHECK(list.rows == 4 && list.count == 0 && list.top == 0,
              "list starts empty");
        CHECK(ps2ui_list_item_at(&list, 0) == -1,
              "empty list has no item in row 0");
        CHECK(ps2ui_list_selected_row(&list) == -1,
              "empty list has no selected row");
        CHECK(ps2ui_list_move(NULL, &list, 1) == 0,
              "moving in an empty list does nothing");

        /* Fewer items than rows: the tail rows must report -1 so the app
         * blanks them instead of leaving last frame's text. */
        ps2ui_list_set_count(NULL, &list, 2);
        CHECK(ps2ui_list_item_at(&list, 1) == 1
              && ps2ui_list_item_at(&list, 2) == -1,
              "rows past the end of a short list report -1");

        /* More items than rows: the window slides by the minimum needed. */
        ps2ui_list_set_count(NULL, &list, 10);
        CHECK(list.top == 0 && list.sel == 0, "long list starts at the top");
        for (i = 0; i < 3; i++) ps2ui_list_move(NULL, &list, 1);
        CHECK(list.sel == 3 && list.top == 0,
              "selection reaches the last visible row without scrolling");
        ps2ui_list_move(NULL, &list, 1);
        CHECK(list.sel == 4 && list.top == 1,
              "the fifth step scrolls by exactly one row");
        CHECK(ps2ui_list_selected_row(&list) == 3,
              "the selection stays on the bottom row while scrolling");
        CHECK(ps2ui_list_item_at(&list, 0) == 1,
              "row 0 now shows item 1");

        /* Both ends clamp; a list does not wrap. */
        ps2ui_list_move(NULL, &list, 99);
        CHECK(list.sel == 9 && list.top == 6, "moving past the end clamps");
        CHECK(ps2ui_list_item_at(&list, 3) == 9, "the last item is on the last row");
        r = ps2ui_list_move(NULL, &list, 1);
        CHECK(r == 0 && list.sel == 9, "moving down at the end is a no-op");
        ps2ui_list_move(NULL, &list, -99);
        CHECK(list.sel == 0 && list.top == 0, "moving past the start clamps");
        CHECK(ps2ui_list_move(NULL, &list, -1) == 0,
              "moving up at the start is a no-op");

        /* Paging is the same call with a bigger delta. */
        ps2ui_list_move(NULL, &list, (int)list.rows);
        CHECK(list.sel == 4 && list.top == 1, "a page down moves one screenful");

        /* Shrinking the data under a selection that was past the new end
         * must land somewhere valid rather than off it. */
        ps2ui_list_select(NULL, &list, 9);
        ps2ui_list_set_count(NULL, &list, 3);
        CHECK(list.sel == 2 && list.top == 0,
              "shrinking the list pulls the selection and window back in");
        ps2ui_list_set_count(NULL, &list, 0);
        CHECK(list.sel == 0 && list.top == 0 && ps2ui_list_selected_row(&list) == -1,
              "emptying the list resets it");

        /* Focus follows the selection, by the baked row names. */
        {
            ps2ui_list rows;
            ps2ui_list_init(&rows, "save-", 4);
            ps2ui_list_set_count(NULL, &rows, 4);
            /* The memcard example's saves screen has no "save-N" nodes,
             * so this proves the failure path: indices still move, the
             * focus call reports that the prefix does not match. */
            CHECK(ps2ui_list_move(&ctx, &rows, 1) == 1 && rows.sel == 1,
                  "a prefix that matches no node still tracks indices");
        }
    }

    /* ---- runtime visibility (F21) ----
     * Driven against the real memcard blob, because the point is that
     * hiding removes a subtree's commands from the frame and keeps the
     * D-pad off it. */
    {
        int base_prims, hidden_prims;

        ps2ui_screen_set(&ctx, "library");
        ps2ui_focus_set(&ctx, "nav-games");
        base_prims = render_and_count(&ctx, &gs);

        CHECK(ps2ui_visible_get(&ctx, "tile-okami") == 1,
              "everything starts visible");
        CHECK(ps2ui_visible_set(&ctx, "tile-okami", 0) == 1,
              "hiding a known node succeeds");
        CHECK(ps2ui_visible_get(&ctx, "tile-okami") == 0, "and it reads back hidden");
        hidden_prims = render_and_count(&ctx, &gs);
        CHECK(hidden_prims < base_prims,
              "a hidden subtree stops being drawn");

        /* The half that blanking a slot cannot do: keep focus off it. */
        CHECK(ps2ui_focus_set(&ctx, "tile-okami") == 1,
              "focus_set is deliberate and still reaches a hidden node");
        ps2ui_focus_set(&ctx, "nav-games");
        {
            /* Walk right across the tile row; the hidden tile must never
             * be where we land. */
            int landed_on_hidden = 0, steps = 0;
            ps2ui_focus_set(&ctx, "tile-ico");
            while (ps2ui_move(&ctx, PS2UI_RIGHT) && steps++ < 20) {
                const char *nm = ps2ui_focus_name(&ctx);
                if (nm && strcmp(nm, "tile-okami") == 0) landed_on_hidden = 1;
            }
            CHECK(!landed_on_hidden, "the D-pad walks past a hidden node");
        }

        CHECK(ps2ui_visible_set(&ctx, "tile-okami", 1) == 1, "showing it again");
        CHECK(render_and_count(&ctx, &gs) == base_prims,
              "showing restores exactly the original frame");

        CHECK(ps2ui_visible_set(&ctx, "no-such-node", 0) == 0,
              "an unknown name is rejected rather than silently ignored");

        /* Name lookups are scoped to the current screen. The example has
         * nav-games on both screens, and data-repeat makes two screens
         * each using row-{i} the natural thing to write. A blob-global
         * scan would hide the other screen's node and report success. */
        {
            int lib_before, lib_after, saves_before;
            lib_before = render_and_count(&ctx, &gs);
            ps2ui_screen_set(&ctx, "saves");
            saves_before = render_and_count(&ctx, &gs);
            CHECK(ps2ui_visible_set(&ctx, "nav-games", 0) == 1,
                  "the saves screen has its own nav-games");
            CHECK(render_and_count(&ctx, &gs) < saves_before,
                  "and hiding it changes the screen you are looking at");
            ps2ui_screen_set(&ctx, "library");
            lib_after = render_and_count(&ctx, &gs);
            CHECK(lib_after == lib_before,
                  "the other screen's identically-named node is untouched");
            ps2ui_visible_reset(&ctx);
        }

        ps2ui_visible_set(&ctx, "tile-ico", 0);
        ps2ui_visible_reset(&ctx);
        CHECK(ps2ui_visible_get(&ctx, "tile-ico") == 1, "reset shows everything");
        CHECK(render_and_count(&ctx, &gs) == base_prims, "and restores the frame");
    }

    /* ---- render telemetry (ps2ui_stats) ----
     * The stub counts gsKit calls; the runtime counts what it submits.
     * Two independent tallies of the same frame must agree, which is
     * the same discipline as the linear-scan pen checks: a counter
     * compared against itself asserts nothing. */
    {
        int frame1, frame2, shown_slots = 0;
        uint32_t k;
        frame1 = render_and_count(&ctx, &gs);
        CHECK((int)ctx.stats.prims == frame1,
              "stats.prims agrees with the stub's independent count");
        CHECK(ctx.stats.cmds == ctx.screen_table[ctx.screen].cmd_count,
              "stats.cmds is the current screen's record count");
        CHECK(ctx.stats.scissor_overflow == 0,
              "a baked blob never overflows the scissor stack");
        CHECK(ctx.stats.skipped_hidden == 0,
              "nothing hidden, nothing skipped");
        /* Count textured prims in the stub independently. Slot glyphs
         * are a subset of them, so this bounds the counter against a
         * tally the runtime did not produce. */
        for (k = 0; k < (uint32_t)g_stub.n_prims; k++)
            if (g_stub.prims[k].textured) shown_slots++;
        CHECK(ctx.stats.slot_glyphs > 0
              && (int)ctx.stats.slot_glyphs <= shown_slots,
              "slot glyphs are a subset of the stub's textured prims");

        /* Hiding moves records from prims to skipped_hidden, exactly. */
        ps2ui_visible_set(&ctx, "tile-ico", 0);
        frame2 = render_and_count(&ctx, &gs);
        CHECK((int)ctx.stats.prims == frame2,
              "stats.prims still agrees after hiding a node");
        CHECK(ctx.stats.skipped_hidden > 0
              && (int)(ctx.stats.prims + ctx.stats.skipped_hidden)
                 >= frame1,
              "hidden records are counted, not lost");
        ps2ui_visible_reset(&ctx);

        /* Counters are per-frame: two identical renders, identical
         * stats — nothing accumulates across frames. */
        render_and_count(&ctx, &gs);
        k = ctx.stats.prims;
        render_and_count(&ctx, &gs);
        CHECK(ctx.stats.prims == k, "stats reset every frame");
    }

    /* ---- lists and visibility against a real data-repeat blob ----
     * The memcard example cannot test this: its tiles are named after
     * games, so a list prefix matches nothing and every assertion below
     * would pass vacuously. This fixture bakes row-0..row-3 with one
     * slot each. */
    if (argc == 3) {
        size_t llen;
        void *lblob = slurp(argv[2], &llen);
        ps2ui_ctx lc;
        ps2ui_list list;
        int full, one_hidden, row_cost;

        /* Bail rather than fall through: everything below dereferences
         * the loaded context, so a rejected blob segfaults instead of
         * reporting, and a crash names none of the checks that ran. A
         * fixture left stale by a format change is exactly how that
         * happens -- it happened while adding kerning. */
        int loaded = ps2ui_load(&lc, lblob, llen);
        CHECK(loaded == PS2UI_OK, "list fixture loads");
        if (loaded != PS2UI_OK) {
            printf("# ps2ui_load returned %d; skipping the list checks\n",
                   loaded);
            free(lblob);
            goto report;
        }
        ps2ui_upload(&lc, &gs);

        /* Focus really does follow the selection, by baked row name.
         * #14 only ever exercised the failure path. */
        ps2ui_list_init(&list, "row-", 4);
        ps2ui_list_set_count(&lc, &list, 4);
        CHECK(ps2ui_list_move(&lc, &list, 1) == 1
              && strcmp(ps2ui_focus_name(&lc), "row-1") == 0,
              "list_move focuses the row the selection lands on");
        CHECK(ps2ui_list_select(&lc, &list, 3) == 1
              && strcmp(ps2ui_focus_name(&lc), "row-3") == 0,
              "list_select focuses by absolute index");

        /* Hiding a row must take its slot text with it. The header and
         * the README both promise "slots included"; before this was
         * fixed the panel went and the glyphs kept drawing. */
        ps2ui_list_select(&lc, &list, 0);
        full = render_and_count(&lc, &gs);
        ps2ui_visible_set(&lc, "row-1", 0);
        one_hidden = render_and_count(&lc, &gs);
        row_cost = full - one_hidden;
        CHECK(row_cost > 1,
              "hiding a row drops its panel *and* its slot glyphs, not just the panel");
        ps2ui_slot_set(&lc, "row-1-text", "");
        CHECK(render_and_count(&lc, &gs) == one_hidden,
              "blanking an already-hidden row's slot changes nothing further");
        ps2ui_slot_set(&lc, "row-1-text", NULL);
        ps2ui_visible_reset(&lc);
        CHECK(render_and_count(&lc, &gs) == full, "showing restores the frame");

        /* apply_visibility hides exactly the rows past the end. */
        ps2ui_list_set_count(&lc, &list, 2);
        ps2ui_list_apply_visibility(&lc, &list);
        CHECK(ps2ui_visible_get(&lc, "row-1") == 1
              && ps2ui_visible_get(&lc, "row-2") == 0
              && ps2ui_visible_get(&lc, "row-3") == 0,
              "apply_visibility hides only the rows past the end");
        CHECK(render_and_count(&lc, &gs) < full,
              "a short list draws less than a full one");

        /* Focus must not be left on a row that was just hidden. */
        ps2ui_list_init(&list, "row-", 4);
        ps2ui_list_set_count(&lc, &list, 4);
        ps2ui_list_select(&lc, &list, 3);
        ps2ui_list_set_count(&lc, &list, 2);
        ps2ui_list_apply_visibility(&lc, &list);
        CHECK(ps2ui_visible_get(&lc, ps2ui_focus_name(&lc)) == 1,
              "shrinking a list never leaves focus on a hidden row");
        CHECK(strcmp(ps2ui_focus_name(&lc), "row-1") == 0,
              "and focus follows the clamped selection");

        /* Telemetry reconciles exactly on a list-shaped UI, which the
         * memcard blob cannot test: its tiles carry no slots, so
         * hiding one suppresses command records and nothing else. Here
         * a hidden row takes its slot's glyphs with it, and those are
         * counted in slots_hidden rather than vanishing from the
         * arithmetic. */
        {
            uint32_t p0, g0, p1, g1, sh1, hid1;
            ps2ui_visible_reset(&lc);
            ps2ui_list_set_count(&lc, &list, 4);
            ps2ui_list_apply_visibility(&lc, &list);
            render_and_count(&lc, &gs);
            p0 = lc.stats.prims; g0 = lc.stats.slot_glyphs;
            CHECK(g0 > 0 && lc.stats.slots_hidden == 0,
                  "all rows visible: slot glyphs drawn, none suppressed");

            ps2ui_visible_set(&lc, "row-1", 0);
            render_and_count(&lc, &gs);
            p1 = lc.stats.prims; g1 = lc.stats.slot_glyphs;
            sh1 = lc.stats.slots_hidden; hid1 = lc.stats.skipped_hidden;
            CHECK(sh1 == 1, "hiding a row suppresses exactly its one slot");
            CHECK(g1 < g0, "and its glyphs stop being composed");
            /* Every primitive the frame lost is either a skipped
             * command record or a suppressed slot's glyphs. Exact, not
             * >=: this fixture can violate it, which is the point. */
            CHECK(p0 - p1 == hid1 + (g0 - g1),
                  "prims lost = records skipped + slot glyphs suppressed");
            ps2ui_visible_reset(&lc);
        }

        /* Feature bit 2: slot letter-spacing travels with the slot and
         * the pen applies it at every junction, alongside the kern.
         * The fixture's .label carries letter-spacing: 2px so this is
         * exercised for real — with every slot at zero the check below
         * would pass whatever the pen did. Expected positions come from
         * a linear scan, same discipline as the kerning check. */
        {
            const ps2ui_slot_entry *sl = &lc.slots[0];
            const ps2ui_font_entry *fe = &lc.fonts[sl->font];
            const char *probe = "To AV list";
            int expect_x[32], n_expect = 0, base_prims, i, ok = 1;
            int pen = 0;
            uint32_t prev = 0;
            int have_prev = 0;
            const char *p2 = probe;

            CHECK((lc.hdr->feature_flags & PS2UI_FEAT_SLOT_SPACING) != 0,
                  "fixture declares the slot-spacing feature bit");
            CHECK(sl->letter_spacing == 2,
                  "and the slot carries the stylesheet's 2px");

            while (*p2) {
                uint32_t cp = (uint32_t)(unsigned char)*p2++;
                const ps2ui_glyph *g = scan_glyph(&lc, fe, cp);
                if (!g)
                    continue;
                if (have_prev)
                    pen += sl->letter_spacing + scan_kern(&lc, fe, prev, cp);
                if (g->w > 0)
                    expect_x[n_expect++] = sl->x + pen + g->bearing_x;
                pen += g->advance;
                prev = cp;
                have_prev = 1;
            }

            ps2ui_visible_reset(&lc);
            ps2ui_list_set_count(&lc, &list, 4);
            ps2ui_list_apply_visibility(&lc, &list);
            /* Blank every row, then set only row 0, so its glyphs are
             * the frame's tail and the prim indices are predictable. */
            ps2ui_slot_set(&lc, "row-0-text", "");
            ps2ui_slot_set(&lc, "row-1-text", "");
            ps2ui_slot_set(&lc, "row-2-text", "");
            ps2ui_slot_set(&lc, "row-3-text", "");
            base_prims = render_and_count(&lc, &gs);
            ps2ui_slot_set(&lc, "row-3-text", probe);
            CHECK(render_and_count(&lc, &gs) == base_prims + n_expect,
                  "the spaced slot draws one prim per inked glyph");
            /* row-3 is the last slot on the screen, so its glyphs are
             * the frame's tail — but its x differs from slot 0's only
             * by the shared left edge, which is identical per row. */
            for (i = 0; i < n_expect; i++) {
                int got = (int)g_stub.prims[base_prims + i].x1;
                int want = expect_x[i] - sl->x + lc.slots[3].x;
                if (got != want)
                    ok = 0;
            }
            CHECK(ok, "and lands every glyph on the spaced, kerned pen");
        }

        free(lblob);
    }

    /* ---- bring-up step 9: is a non-zero return reachable? ----------
     *
     * Step 9 asks the operator to read ps2ui_upload's return value and
     * expect 0. That is worth nothing unless non-zero is reachable: a
     * function that only ever returns 0 gives the same answer on a
     * console with 4 MB free and on one with none, and the step reads
     * as a pass either way.
     *
     * Last among the CHECKS and immediately before `report:`, which is
     * the property that matters -- not last in the file. It sat after
     * the label, so the one `goto report` fell into it and the bail-out
     * path, whose whole job is to run nothing, ran two loads and two
     * uploads on the way out.
     *
     * clut_pool is file-scope, not
     * per-context, and ps2ui_upload writes a permuted CLUT into it
     * BEFORE the allocation that fails -- so a second live context
     * silently borrows the first one's CLUT storage. Run here, nothing
     * afterwards can read what these contexts leave behind. It was
     * originally placed beside the first upload check, where it was
     * safe only because both contexts loaded the identical blob, an
     * invariant nobody had written down. Worth remembering against the
     * v6 arena work, which moves exactly this storage per-context:
     * this test is not a precedent that two live contexts are fine.
     *
     * The stub models the real ceiling -- gsKit_vram_alloc refuses past
     * 4 MB -- so these fail for the reason a crowded console would.
     * `starved` is a COPY of gs, not a mutation of it -- an earlier
     * version of this comment said "restore it afterwards", describing
     * a hazard the code already sidesteps and reading as an invitation
     * to "fix" it by starving gs directly. Nothing is restored because
     * nothing is disturbed. */
    {
        ps2ui_ctx sc;
        GSGLOBAL starved;
        char partway[128];

        /* (a) nothing fits: the first allocation fails. */
        starved = gs;
        starved.CurrentPointer = 4u * 1024u * 1024u - 16u;
        memset(&sc, 0, sizeof sc);
        if (ps2ui_load(&sc, blob, len) == PS2UI_OK) {
            CHECK(ps2ui_upload(&sc, &starved) != 0,
                  "upload reports failure when VRAM is exhausted, so "
                  "step 9's expected 0 is a result and not a constant");
            CHECK(sc.uploaded == 0,
                  "and leaves the context not-uploaded, so a caller "
                  "cannot render through a half-built texture table");
        } else {
            CHECK(0, "starved-upload fixture failed to load");
        }

        /* (b) exhaustion PARTWAY, which is the case a real console
         * hits: earlier textures allocated and uploaded, a later one
         * refused. Only the first-allocation path was covered, which
         * is the easiest path through the function and the least like
         * the failure anyone will actually meet.
         *
         * The two cases turn out to cover different code, not just
         * different budgets. ps2ui_upload has two ways to refuse -- the
         * texture allocation and, for PSMT8, the CLUT allocation right
         * after it. Case (a) trips the first; (b) at this budget trips
         * the second. Neutralising only one of them leaves the other
         * case green, which is how the pair was measured. */
        starved = gs;
        /* Half of what the blob really needs, so this lands in the
         * middle of the table wherever the example's art goes next.
         * The hardcoded 256 KiB it replaces gave 18 of 19 -- the
         * narrowest partway available, failing on the LAST texture,
         * with about 16 KiB between it and "everything fits". */
        starved.CurrentPointer = 4u * 1024u * 1024u - vram_used / 2u;
        memset(&sc, 0, sizeof sc);
        if (ps2ui_load(&sc, blob, len) == PS2UI_OK) {
            int rc;
            int before = g_stub.n_uploads;
            int got;
            rc = ps2ui_upload(&sc, &starved);
            got = g_stub.n_uploads - before;
            CHECK(rc != 0, "upload reports failure when VRAM runs out "
                           "partway through the texture table");
            /* Without this the case above is indistinguishable from
             * (a): both return non-zero, and a budget that happened to
             * fail on texture 0 would look like partway coverage while
             * exercising the same three lines. */
            snprintf(partway, sizeof partway,
                     "having uploaded some but not all of them "
                     "(%d of %u), which is the case a console meets",
                     got, (unsigned)sc.hdr->n_tex);
            CHECK(got > 0 && got < (int)sc.hdr->n_tex, partway);
            CHECK(sc.uploaded == 0,
                  "and still leaves it not-uploaded, however far it got");
        } else {
            CHECK(0, "partway-starved fixture failed to load");
        }
    }

report:
    printf("1..%d\n", checks);
    printf("%s: %d checks, %d failure(s)\n", failures ? "FAIL" : "PASS", checks, failures);
    free(blob);
    return failures ? 1 : 0;
}
