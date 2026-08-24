/* Host-side checks for the real ps2ui.c, compiled -Werror against the
 * gsKit stub and run over a real baked blob (the memcard example).
 *
 * usage: test_runtime <ui.uib>
 */

#include "../ps2ui.h"
/* The recording ledger the assertions read. Under the old stub this
 * arrived implicitly through ps2ui.h's host branch; ps2ui.h now has a
 * single include block for both targets, so the test names its own
 * dependency. */
#include "../stub/gskit_stub.h"
/* The step 6 probe's pattern bits, so the suite pins the aperiodicity
 * the instrument's verdicts rest on -- against the exact constant the
 * console draws, not a description of it. */
#include "../sample/probe6_pattern.h"
#include "../sample/cover_pattern.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int checks = 0, failures = 0;

#define CHECK(cond, name) do { \
    checks++; \
    if (cond) { printf("ok %d - %s\n", checks, name); } \
    else { failures++; printf("not ok %d - %s\n", checks, name); } \
} while (0)

/* Load with an arena sized for the blob (v6 resource model).
 *
 * Deliberately leaks: these are one-shot fixtures in a test binary,
 * and the arena must outlive the context it backs -- freeing it at the
 * end of a helper would hand the caller a context pointing into freed
 * memory, which is the exact lifetime mistake the arena contract
 * warns about, reproduced inside the test suite.
 *
 * Never passes NULL: a rejected blob reports arena_size() == 0, and
 * the point of these calls is to prove the blob was refused for the
 * reason named rather than for want of an arena. */
/* Re-stamp the CRC of a deliberately mutated blob.
 *
 * Without this every "corrupt one field and load" check returns
 * PS2UI_ERR_CRC instead of the error it was written to prove -- green
 * for the wrong reason, and silent about the field it meant to test.
 * The file's CRC is computed with the crc32 field read as zero, so
 * zeroing it and hashing the whole file reproduces the same value. */
static void recrc(void *blob, size_t len)
{
    ps2ui_header *h = (ps2ui_header *)blob;
    h->crc32 = 0;
    h->crc32 = ps2ui_crc32(blob, len);
}

static int load_arena(ps2ui_ctx *c, const void *blob, size_t len)
{
    size_t need = ps2ui_arena_size(blob, len);
    void *a;
    if (need < 64) need = 64;
    a = malloc(need);          /* malloc is >= 16-aligned on every host
                                * this suite runs on; the align check
                                * below has its own dedicated fixture */
    return ps2ui_load(c, blob, len, a, need);
}

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

    /* "I have what I need", never "the caller passed exactly what I
     * expected": an == here once skipped eighteen checks in silence
     * when a fixture was added. */
    if (argc < 2) {
        fprintf(stderr,
                "usage: %s <ui.uib> [list.uib] [streamed.uib] "
                "[wide.uib] [huge.uib]\n", argv[0]);
        return 2;
    }
    blob = slurp(argv[1], &len);
    memset(&gs, 0, sizeof gs);
    /* Start VRAM where a real console starts it: past the display
     * buffers, never at zero. This is not cosmetic. The REAL gsKit
     * headers define GSKIT_ALLOC_ERROR as 0x00 -- so an allocation
     * that lands at address 0 is indistinguishable from a failed one,
     * and a test GS with CurrentPointer 0 makes its own first
     * successful alloc read as an error. The hand-written stub this
     * suite used to compile against had invented 0xFFFFFFFF for the
     * error value, which hid that landmine; the vendored headers
     * surfaced it on their first build. Real programs never see it
     * because gsKit_init_screen allocates the framebuffers first.
     *
     * This stands in for what init_screen allocates FOR THE SAMPLE'S
     * OWN SETTINGS, not a generic layout: main.c sets ZBuffering OFF
     * (strict back-to-front paint order), and gsInit.c:347 allocates
     * the Z buffer only when it is ON -- so the sample's console
     * reserves exactly two CT32 display buffers and no Z. Review
     * caught the first version of this line adding a phantom 16-bit Z,
     * which made the test's free-VRAM number match neither the sample
     * nor the baker's budget. The SYSBUFFER rounding is written out
     * even though 640x448 CT32 lands on a page boundary anyway, so the
     * expression stays true at a resolution where it does not. */
    gs.CurrentPointer =
        2u * ((640u * 448u * 4u + 8191u) & ~8191u);   /* = 2293760 */
    gs.Width = 640; gs.Height = 448;

    /* ---- struct layout matches the on-disk format ---- */
    CHECK(sizeof(ps2ui_header) == 76, "header struct is 76 bytes");
    CHECK(sizeof(ps2ui_screen_entry) == 24, "screen entry struct is 24 bytes");
    CHECK(sizeof(ps2ui_font_entry) == 24, "font entry struct is 24 bytes");
    CHECK(sizeof(ps2ui_glyph) == 20, "glyph struct is 20 bytes");
    CHECK(sizeof(ps2ui_kern) == 12, "kern struct is 12 bytes");
    CHECK(sizeof(ps2ui_slot_entry) == 32, "slot entry struct is 32 bytes");
    CHECK(sizeof(ps2ui_tex_entry) == 20, "tex entry struct is 20 bytes (v6: kind + name_off)");
    CHECK(sizeof(ps2ui_clut_entry) == 8, "clut entry struct is 8 bytes");
    CHECK(sizeof(ps2ui_cmd) == 32, "cmd struct is 32 bytes");
    CHECK(sizeof(ps2ui_focus_node) == 24, "focus node struct is 24 bytes");

    u32 vram_before, vram_used;

    /* ---- loader ---- */
    CHECK(load_arena(&ctx, blob, len) == PS2UI_OK, "load real blob");
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
        CHECK(load_arena(&bad, dup, len) == PS2UI_ERR_MAGIC, "bad magic rejected");
        memcpy(dup, blob, len);
        CHECK(load_arena(&bad, dup, 40) == PS2UI_ERR_TRUNCATED, "truncated header rejected");
        CHECK(load_arena(&bad, dup, len / 2) == PS2UI_ERR_TRUNCATED, "truncated body rejected");
        memcpy(dup, blob, len);
        ((ps2ui_header *)dup)->version = 99;
        CHECK(load_arena(&bad, dup, len) == PS2UI_ERR_VERSION, "wrong version rejected");
        memcpy(dup, blob, len);
        dup[len / 2] ^= 0xFF; /* one flipped bit in the body */
        CHECK(load_arena(&bad, dup, len) == PS2UI_ERR_CRC, "corrupt body fails crc");
        memcpy(dup, blob, len);
        ((ps2ui_header *)dup)->feature_flags |= 0x8000;
        CHECK(load_arena(&bad, dup, len) == PS2UI_ERR_FEATURES,
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

    /* ---- the step 6 probe's pattern is an instrument, not a picture ----
     *
     * The previous pattern was a periodic checker, and the periodicity
     * voided the instrument: a TBW fault shifts each row's texels by a
     * multiple of 64, every multiple of 64 was a multiple of the
     * checker's period, and the one fault class the wide-atlas column
     * existed for rendered as a clean column. These pins are what make
     * the replacement's verdicts mean something; a constant that fails
     * them is a picture. Each pin was falsified: the old checker
     * (0xAAAA...) goes red on the shift pin at s=2 and on the share
     * pin; an all-ones half (0xFFFFFFFF00000000) goes red on the
     * transitions pin. */
    {
        /* Every 16-cell window disagrees with its own image at every
         * cell shift 1..31 in at least 4 of 16 cells: no whole-cell
         * texel shift -- 64 (a TBW unit) and the 4..12-texel DMA
         * truncation class included -- can render as alignment. */
        int s, w, ok_shift = 1, ok_trans = 1, on_cells = 0;
        for (s = 1; s < 32 && ok_shift; s++)
            for (w = 0; w + 16 + s <= P6_PAT_CELLS; w++) {
                int c, d = 0;
                for (c = 0; c < 16; c++)
                    if (p6_bar((w + c) * P6_CELL) !=
                        p6_bar((w + c + s) * P6_CELL))
                        d++;
                if (d < 4) { ok_shift = 0; break; }
            }
        CHECK(ok_shift,
              "probe6 pattern: every 16-cell window breaks every cell shift 1..31");
        /* Sub-cell shifts move bar EDGES, so every window must carry
         * enough transitions to read a 1px offset at the seam. */
        for (w = 0; w + 16 <= P6_PAT_CELLS; w++) {
            int c, t = 0;
            for (c = 1; c < 16; c++)
                if (p6_bar((w + c) * P6_CELL) != p6_bar((w + c - 1) * P6_CELL))
                    t++;
            if (t < 5) { ok_trans = 0; break; }
        }
        CHECK(ok_trans,
              "probe6 pattern: every 16-cell window has 5+ bar transitions");
        /* Column G's verdict is an AREA flip: a wrong CLUT convention
         * exchanges the two colours, so the ON share must sit far
         * enough off 50% for the exchange to move the capture's colour
         * fingerprint. A balanced pattern makes G unreadable. */
        for (w = 0; w < P6_PAT_CELLS; w++)
            on_cells += p6_bar(w * P6_CELL);
        CHECK(on_cells >= 36 && on_cells <= 44,
              "probe6 pattern: ON share is off-balance (36..44 of 64) for the G flip");
        /* The stripe is the V axis: forced ON across every bar. */
        for (w = 0; w < P6_PAT_CELLS; w++)
            if (!p6_bar(w * P6_CELL))
                break;
        CHECK(w < P6_PAT_CELLS && p6_on(w * P6_CELL, P6_STRIPE_Y0) == 1
                  && p6_on(w * P6_CELL, P6_STRIPE_Y0 + P6_STRIPE_H) == 0,
              "probe6 pattern: stripe rows force ON over an OFF bar, and end");
    }

    /* ---- upload ---- */
    vram_before = gs.CurrentPointer;
    /* The manager does not move CurrentPointer (its blocks live above
     * it), so "what the blob costs" is computed the way the preflight
     * computes it rather than read back from an allocator cursor. Kept
     * in sync with ps2ui_upload by construction: same size function,
     * same per-texture terms. */
    {
        uint32_t k;
        vram_used = 0;
        for (k = 0; k < ctx.hdr->n_tex; k++) {
            const ps2ui_tex_entry *t = &ctx.tex[k];
            vram_used += gsKit_texture_size(t->width, t->height,
                t->format == PS2UI_TEXFMT_PSMCT32 ? GS_PSM_CT32 : GS_PSM_T8);
            if (t->format == PS2UI_TEXFMT_PSMT8)
                vram_used += gsKit_texture_size(16, 16, GS_PSM_CT32);
        }
        CHECK(vram_used > 0, "the blob costs a nonzero amount of VRAM to state a budget against");
    }
    CHECK(ps2ui_upload(&ctx, &gs) == 0, "textures fit in 4 MB VRAM");
    /* What the blob's textures actually cost. Step 9's starved cases at
     * the end of this file size themselves from this rather than from a
     * hardcoded budget: a constant tuned to today's example is a check
     * that goes red when someone shrinks an asset by six percent, for a
     * reason that has nothing to do with what they changed. */
    CHECK(gs.CurrentPointer == vram_before,
          "upload no longer moves CurrentPointer: residency belongs to the manager, "
          "and a vram_alloc here would reset its block list");
    CHECK(g_stub.n_uploads == (int)ctx.hdr->n_tex, "every texture uploaded once");

    /* The EE writes back lazily and the GIF reads main memory, so any
     * buffer the CPU touched before an upload has to be flushed or the
     * GS reads what was there before. permute_clut builds every CLUT
     * with ordinary stores immediately before the transfer, which puts
     * the whole palette in dirty cache lines -- and glyph coverage IS
     * the palette's alpha, so a stale one turns text to noise while
     * leaving geometry untouched.
     *
     * gsKit happens to cover this today with a whole-cache
     * FlushCache(0) inside gsKit_texture_send, so these calls are
     * hardening: they scope the writeback to the buffers ps2ui owns
     * instead of leaning on that implementation detail, matching what
     * gsKit_TexManager_bind does with SyncDCache. A host cache is
     * coherent, so this cannot be caught by rendering: the stub
     * records the calls instead and the upload checks coverage. */
    CHECK(g_stub.n_uploads_unflushed == 0,
          "every upload is preceded by a writeback of its pixels and its CLUT");
    CHECK(g_stub.n_flushes > 0,
          "and flushes were actually recorded, so the check above had something to check");

    /* ---- gsKit_texture_size is the console's own arithmetic ---- */
    /* The preflight's safety argument is "the sum mirrors the manager's
     * appetite exactly", and that is only true if this function returns
     * what the console's does. The stub's page-rounded approximation
     * agreed on every power-of-two case and diverged on the rest --
     * including 8 KB UNDER on a 320x32 T8 strip, the unsafe direction:
     * a host-certified preflight that under-counts walks the console
     * into _blockAlloc's no-exit loop. Review computed this table from
     * gsKit's real block math; the suite now links that real function
     * (vendored source, compiled with -DF_gsKit_texture_size) and these
     * rows pin it against silent drift of the vendored file. */
    {
        static const struct { int w, h, psm; u32 want; } sz[] = {
            {  16,  16, GS_PSM_CT32,    1024 },  /* every CLUT's csize   */
            { 256, 128, GS_PSM_T8,     32768 },  /* channel-6 atlas      */
            { 128, 128, GS_PSM_T8,     16384 },
            {  64,  64, GS_PSM_CT32,   16384 },
            { 640, 448, GS_PSM_CT32, 1146880 },  /* a framebuffer        */
            {   8,   8, GS_PSM_CT32,     256 },  /* smallest block       */
            {  24,  24, GS_PSM_CT32,    4096 },
            { 320,  32, GS_PSM_T8,     24576 },  /* the under-count case */
        };
        /* sizeof-derived bound and one CHECK per row, both from review:
         * the first version hardcoded `< 8`, and a ninth row with an
         * impossible expectation left the suite green -- the quietest
         * possible failure, since adding a case is exactly the
         * maintenance action this table invites. And a bare boolean
         * over the table turns a red pin into a manual bisect; a named
         * row is the bisect already done. */
        size_t k3;
        char szmsg[96];
        for (k3 = 0; k3 < sizeof sz / sizeof *sz; k3++) {
            u32 got = gsKit_texture_size(sz[k3].w, sz[k3].h, sz[k3].psm);
            snprintf(szmsg, sizeof szmsg,
                     "gsKit_texture_size(%dx%d psm%d) = %u, the console's block math (got %u)",
                     sz[k3].w, sz[k3].h, sz[k3].psm, (unsigned)sz[k3].want, (unsigned)got);
            CHECK(got == sz[k3].want, szmsg);
        }
    }

    /* ---- render: the heal is bounded by the budget ---- */
    /* Review of the migration found that the render-time re-bind is a
     * second entry into _blockAlloc's no-exit eviction loop: a host
     * gsKit_vram_alloc after our upload shrinks the manager's region
     * AND drops residency, and if the footprint no longer fits, the
     * "healing" bind at the next draw never returns -- a hang with no
     * error path, at frame time. ps2ui_render therefore re-checks the
     * fit before any textured draw and skips them all when it fails,
     * reporting stats.vram_lost. This test IS that scenario: allocate
     * the region out from under an uploaded context, render, and
     * require zero binds, zero transfers, no textured prims, and the
     * stat -- while untextured quads still draw, because a bad frame
     * beats a dead console. */
    {
        GSGLOBAL shrunk = gs;
        int before_transfers, before_binds, k, any_tex = 0, any_quad = 0;
        u32 grab = 4u * 1024u * 1024u - shrunk.CurrentPointer - 256u;
        CHECK(gsKit_vram_alloc(&shrunk, grab, GSKIT_ALLOC_USERBUFFER)
                  != GSKIT_ALLOC_ERROR,
              "a host allocation can legally take nearly all remaining VRAM");
        before_transfers = g_stub.n_transfers;
        before_binds = g_stub.n_binds;
        stub_reset_keep_tm();
        ps2ui_render(&ctx, &shrunk);
        CHECK(ctx.stats.vram_lost == 1,
              "render reports vram_lost when the uploaded footprint no longer fits");
        CHECK(g_stub.n_binds == before_binds && g_stub.n_transfers == before_transfers,
              "and calls bind zero times, because a bind that cannot fit never returns");
        for (k = 0; k < g_stub.n_prims; k++) {
            if (g_stub.prims[k].tex) any_tex = 1; else any_quad = 1;
        }
        CHECK(!any_tex, "no textured primitive was submitted this frame");
        CHECK(any_quad, "while untextured quads still drew: a bad frame, not a dead console");
        /* Back on the original gs the fit still holds and nothing sticks. */
        stub_reset();
        ps2ui_render(&ctx, &gs);
        CHECK(ctx.stats.vram_lost == 0, "and the stat clears on a budget that fits");
    }

    /* ---- render: an out-of-contract render after a refused upload ---- */
    /* ps2ui_load memsets the context, so on the refusal path vram_need
     * is 0 and the fit half of the guard is vacuously true. A caller
     * that ignores upload's -1 and renders anyway must still hit the
     * guard -- otherwise it binds zero-filled GSTEXTUREs (Mem NULL)
     * into the transfer path, which is the exact misbehaving-host
     * shape the guard exists for. Review probed this hole before the
     * uploaded check existed: all three assertions failed. */
    {
        ps2ui_ctx rc2;
        GSGLOBAL starved2 = gs;
        int before_binds, k2, any_tex2 = 0, any_quad2 = 0;
        starved2.CurrentPointer = 4u * 1024u * 1024u - 16u;
        memset(&rc2, 0, sizeof rc2);
        if (load_arena(&rc2, blob, len) == PS2UI_OK
            && ps2ui_upload(&rc2, &starved2) != 0) {
            stub_reset_keep_tm();
            before_binds = g_stub.n_binds;
            ps2ui_render(&rc2, &starved2);
            CHECK(rc2.stats.vram_lost == 1,
                  "a render after a REFUSED upload reports vram_lost rather than binding");
            CHECK(g_stub.n_binds == before_binds,
                  "and binds nothing: the GSTEXTUREs were never filled in");
            for (k2 = 0; k2 < g_stub.n_prims; k2++) {
                if (g_stub.prims[k2].tex) any_tex2 = 1; else any_quad2 = 1;
            }
            CHECK(!any_tex2, "no textured primitive from an un-uploaded context");
            CHECK(any_quad2, "while its untextured quads still draw");
        } else {
            CHECK(0, "refused-upload fixture failed to set up");
        }
    }

    /* ---- render: binds per draw, so residency heals ---- */
    /* The property is not "textures are resident after upload" -- that
     * passes trivially. It is "a texture that LOSES residency between
     * frames gets it back at the next draw", which is what protects
     * ps2ui inside a host that also uses the TexManager, or that calls
     * gsKit_vram_alloc after our upload and thereby resets the block
     * list. Invalidate everything the way that reset would, render,
     * and require the frame's draws to have re-transferred. Rendering
     * that never binds passes every other check in this file, which is
     * exactly why this one exists -- it was added after measuring that
     * deleting the render-time binds turned nothing red. */
    {
        uint32_t k;
        int before;
        for (k = 0; k < ctx.hdr->n_tex; k++)
            gsKit_TexManager_invalidate(&gs, &ctx.gs_tex[k]);
        before = g_stub.n_transfers;
        ps2ui_render(&ctx, &gs);
        CHECK(g_stub.n_transfers > before,
              "a draw after invalidation re-transfers: render binds per draw rather "
              "than trusting upload-time residency");
        {
            int all_drawn_resident = 1;
            for (k = 0; k < (uint32_t)g_stub.n_prims; k = k + 1) {
                const stub_prim *pr = &g_stub.prims[k];
                if (pr->tex && pr->tex->Vram == 0) all_drawn_resident = 0;
            }
            CHECK(all_drawn_resident,
                  "and no primitive this frame sampled a texture the manager considers absent");
        }
    }

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
        CHECK(load_arena(&mis, base + 8, len) == PS2UI_ERR_ALIGN,
              "a blob at a non-16-aligned address is refused with PS2UI_ERR_ALIGN");
        memcpy(base, blob, len);
        CHECK(load_arena(&mis, base, len) == PS2UI_OK,
              "and the identical bytes load once the address is aligned, so it was the address");
        free(shifted);
    }

    /* ---- the arena (v6 resource model) ----
     *
     * The context is sized by the blob now, so the numbers below are
     * the contract: ps2ui_arena_size tells the caller what to hand
     * over, and load must accept exactly that and refuse one byte
     * less. A helper that over-allocates would make every one of these
     * pass without the arithmetic being right, which is the whole
     * failure mode this section exists to prevent. */
    {
        size_t need = ps2ui_arena_size(blob, len);
        uint8_t *raw = malloc(need + 64);
        /* 16-align by hand: the misalignment check below needs a base
         * it can deliberately shift off, and malloc's own alignment is
         * not something to assert against. */
        uint8_t *a16 = raw + (16 - (((uintptr_t)raw) & 15u));
        ps2ui_ctx ac;

        CHECK(need > 0, "arena_size reports a requirement for a real blob");

        /* Independently recomputed from the header, the way scan_glyph
         * checks the binary search: two implementations that agree is
         * evidence, one compared against itself is not. The first
         * version of this section did exactly that -- it asserted
         * load(need) passes and load(need-1) fails, both sides sourced
         * from arena_size, so arena_size could over-report by any
         * amount and the pair stayed green. Verified: adding 1 to
         * L->total goes red here and nowhere else. */
        {
            const ps2ui_header *h = (const ps2ui_header *)blob;
            const ps2ui_slot_entry *sl =
                (const ps2ui_slot_entry *)((const uint8_t *)blob + h->off_slot);
            size_t want = 0;
            uint32_t q;
            want += (size_t)h->n_clut * 256 * 4;          /* permuted CLUTs */
            want += (size_t)h->n_tex * sizeof(GSTEXTURE); /* gs_tex         */
            want += (size_t)h->n_slot * sizeof(uint32_t); /* slot_off       */
            want += ((size_t)(h->n_focus + 31) / 32) * sizeof(uint32_t);
            want += (size_t)h->n_screen * sizeof(uint16_t);
            for (q = 0; q < h->n_slot; q++)
                want += (size_t)sl[q].capacity + 1;       /* slot text      */
            want += h->n_slot;                            /* slot_is_set    */
            CHECK(need == want,
                  "arena_size matches an independent carve of the same header");
        }
        CHECK(ps2ui_arena_size(blob, 8) == 0,
              "arena_size refuses a blob too short to hold a header");
        {
            uint8_t junk[128];
            memset(junk, 0xAB, sizeof junk);
            CHECK(ps2ui_arena_size(junk, sizeof junk) == 0,
                  "arena_size refuses a bad magic rather than sizing from garbage");
        }

        /* Exact fit accepted, one byte short refused. This pair is the
         * fence: it fails if the layout drifts from the size function
         * in EITHER direction, which a single generous allocation
         * could never show. */
        CHECK(ps2ui_load(&ac, blob, len, a16, need) == PS2UI_OK,
              "load accepts an arena of exactly arena_size bytes");
        CHECK(ps2ui_load(&ac, blob, len, a16, need - 1) == PS2UI_ERR_ARENA,
              "load refuses an arena one byte short, so the size is exact");
        CHECK(ps2ui_load(&ac, blob, len, NULL, need) == PS2UI_ERR_ARENA,
              "load refuses a NULL arena");
        CHECK(ps2ui_load(&ac, blob, len, a16 + 8, need) == PS2UI_ERR_ALIGN,
              "load refuses a misaligned arena: the CLUT region is a DMA source");

        /* A refused blob must not have written to the arena. The
         * caller may reuse that buffer for the next attempt, and a
         * half-carved arena behind a returned error is the kind of
         * thing that only shows up as corruption three loads later. */
        {
            ps2ui_ctx bc;
            uint8_t *dup = malloc(len);
            size_t k;
            int untouched = 1;
            memcpy(dup, blob, len);
            ((ps2ui_header *)dup)->version = 99;
            memset(a16, 0xC7, need);
            CHECK(ps2ui_load(&bc, dup, len, a16, need) == PS2UI_ERR_VERSION,
                  "a stale-version blob is still refused with an arena in hand");
            for (k = 0; k < need; k++)
                if (a16[k] != 0xC7) { untouched = 0; break; }
            CHECK(untouched,
                  "a refused blob leaves the arena untouched, so it can be reused");
            free(dup);
        }
        free(raw);
    }

    /* ---- the arena is per-context, which the static pool was not ----
     *
     * The CLUT staging buffers used to be one file-scope array shared
     * by every context in the process. Two UIs loaded at once (a shell
     * and a module, the case Phase 1 is built toward) would have
     * silently overwritten each other's palettes -- gsKit keeps the
     * Clut POINTER, so the damage lands at the next bind, arbitrarily
     * far from the upload that caused it. Two contexts, two arenas,
     * and the pointers must not collide. */
    {
        ps2ui_ctx c1, c2;
        size_t need = ps2ui_arena_size(blob, len);
        void *a1 = malloc(need), *a2 = malloc(need);
        int ok1 = ps2ui_load(&c1, blob, len, a1, need);
        int ok2 = ps2ui_load(&c2, blob, len, a2, need);
        CHECK(ok1 == PS2UI_OK && ok2 == PS2UI_OK, "two contexts load side by side");
        if (ok1 == PS2UI_OK && ok2 == PS2UI_OK) {
            CHECK(c1.clut_pool != c2.clut_pool,
                  "each context stages its CLUTs in its own arena, not a shared static");
            CHECK(c1.slot_text != c2.slot_text && c1.gs_tex != c2.gs_tex,
                  "and the same holds for slot text and the texture array");
        }
        /* a1/a2 deliberately leaked: the contexts point into them. */
    }

    /* ---- one permuted CLUT per palette, shared by its textures ----
     *
     * Measured on this blob: 8 PSMT8 textures, 1 CLUT. Per-texture
     * buffers cost 8 KiB for 1 KiB of distinct palette, on the arena's
     * dominant term. Textures naming the same CLUT must therefore land
     * on the same staging buffer -- and textures naming different
     * CLUTs must not. */
    {
        uint32_t t, first = PS2UI_NONE;
        int shared_ok = 1, distinct_ok = 1;
        for (t = 0; t < ctx.hdr->n_tex; t++) {
            if (ctx.tex[t].format != PS2UI_TEXFMT_PSMT8) continue;
            if (first == PS2UI_NONE) { first = t; continue; }
            if (ctx.tex[t].clut == ctx.tex[first].clut) {
                if (ctx.gs_tex[t].Clut != ctx.gs_tex[first].Clut) shared_ok = 0;
            } else {
                if (ctx.gs_tex[t].Clut == ctx.gs_tex[first].Clut) distinct_ok = 0;
            }
        }
        CHECK(first != PS2UI_NONE, "the blob has an indexed texture to check");
        CHECK(shared_ok, "textures sharing a CLUT index share one permuted buffer");
        CHECK(distinct_ok, "textures with different CLUT indices do not");
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

        /* Per-slot buffers, not one BUFSZ-sized row each (v6 §2).
         *
         * The storage moved from slot_text[16][96] to capacity+1 bytes
         * per slot, packed end to end in the arena. Truncation at the
         * declared capacity is not the new risk -- the old code already
         * did that -- the new risk is a neighbour: an off-by-one in
         * slot_off, or a write of capacity+1 bytes, lands in the NEXT
         * slot's text rather than in slack that used to absorb it.
         *
         * This blob's capacities differ (count=15, save-0=31), which is
         * what makes the pair meaningful: a single global buffer size
         * cannot produce two different truncation points. */
        {
            const char *long_a =
                "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA";
            uint32_t ia = find_slot(&ctx, "count");
            uint32_t ib = find_slot(&ctx, "save-0");
            CHECK(ia != PS2UI_NONE && ib != PS2UI_NONE
                  && ctx.slots[ia].capacity != ctx.slots[ib].capacity,
                  "the fixture has two slots with different capacities");
            ps2ui_slot_set(&ctx, "count", long_a);
            CHECK(strlen(ps2ui_slot_get(&ctx, "count")) == ctx.slots[ia].capacity,
                  "a slot truncates at its own declared capacity");
            ps2ui_slot_set(&ctx, "save-0", long_a);
            CHECK(strlen(ps2ui_slot_get(&ctx, "save-0")) == ctx.slots[ib].capacity,
                  "and a slot with a different capacity truncates at that one");
            /* The neighbour check: filling one to the brim must not
             * have moved the other's terminator or content. */
            CHECK(strlen(ps2ui_slot_get(&ctx, "count")) == ctx.slots[ia].capacity,
                  "filling one slot to capacity leaves its neighbour intact");
            {
                uint32_t q;
                int packed_ok = 1;
                size_t expect = 0;
                for (q = 0; q < ctx.hdr->n_slot; q++) {
                    if (ctx.slot_off[q] != expect) packed_ok = 0;
                    expect += (size_t)ctx.slots[q].capacity + 1;
                }
                CHECK(packed_ok,
                      "slot buffers are packed at capacity+1 with no gaps");
            }
            ps2ui_slot_set(&ctx, "count", NULL);
            ps2ui_slot_set(&ctx, "save-0", NULL);
        }
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

        /* The #16 review debt: unknown-name and hidden both returned 0,
         * so an app could not tell a typo from a hidden node -- and the
         * typo is the one the caller can fix. Now distinct. */
        CHECK(ps2ui_visible_get(&ctx, "no-such-node") == PS2UI_VISIBLE_UNKNOWN,
              "visible_get reports an unknown name distinctly from hidden");
        CHECK(ps2ui_visible_get(&ctx, "no-such-node") != 0,
              "and that value is not the one hidden uses");
        /* Every focus node the blob declares can be hidden: the bits are
         * sized from n_focus, so the old past-the-ceiling silent failure
         * has no index left to happen at. */
        {
            uint16_t q;
            int all_ok = 1;
            for (q = 0; q < ctx.hdr->n_focus; q++) {
                const char *nm =
                    (const char *)(ctx.blob + ctx.focus_nodes[q].name_off);
                /* Scoped to the current screen by design, so only this
                 * screen's nodes are addressable by name here. */
                if (ps2ui_visible_get(&ctx, nm) == PS2UI_VISIBLE_UNKNOWN)
                    continue;
                if (ps2ui_visible_set(&ctx, nm, 0) != 1) all_ok = 0;
                if (ps2ui_visible_get(&ctx, nm) != 0) all_ok = 0;
                ps2ui_visible_set(&ctx, nm, 1);
            }
            CHECK(all_ok, "every focus node on this screen can be hidden and shown");
        }
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

    /* ---- the streaming bench's fallback cover pattern ---------------
     * The bench ELF generates this on the EE when no drive is present,
     * and tools/make_cover_raw.py generates it on the host for the
     * reference PNG. If they diverge, a sitting compares a console
     * photo against a picture of something else. Pinned as a CRC in
     * the header both sides include, and checked from both: this is
     * the C half, packages/baker/tests the Python half. */
    {
        static unsigned char cov[64 * 64 * 4];
        int flat = 0, k;
        cover_fill(cov, 0, 64, 64);
        CHECK(ps2ui_crc32(cov, sizeof cov) == COVER_PATTERN_CRC_0_64x64,
              "the C cover pattern matches the CRC the header pins, which "
              "the Python generator is checked against too");
        /* A flat cover cannot tell "the texels arrived" from "a stale
         * VRAM block is being drawn", which is the whole reading of
         * bench step S1.
         *
         * The first version of this compared every texel against
         * cov[0] -- which is the white BORDER, so the first interior
         * texel satisfied it no matter what the interior looked like.
         * Review collapsed the checker to a uniform interior: the CRC
         * pin fired and this stayed green. A border-plus-flat cover
         * has exactly two distinct values and passed a check written
         * to reject exactly that.
         *
         * Counted properly now, which is the property the Python
         * self-test asserts, so "the C suite asserts it again" is
         * true rather than nearly true. */
        {
            unsigned char seen[8][4];
            int n_seen = 0, j;
            for (k = 0; k + 3 < (int)sizeof cov; k += 4) {
                for (j = 0; j < n_seen; j++)
                    if (memcmp(seen[j], cov + k, 4) == 0) break;
                if (j == n_seen && n_seen < 8)
                    memcpy(seen[n_seen++], cov + k, 4);
            }
            CHECK(n_seen > 2,
                  "and carries more than two distinct texels, so a border "
                  "around a flat fill cannot pass for it");
            flat = n_seen > 2;
        }
        /* And varies on BOTH axes. Three distinct values could still
         * be horizontal stripes, which is a shape stale VRAM plausibly
         * takes -- a framebuffer row or a texture at the wrong stride
         * both stripe. A checker cannot be mistaken for either. */
        {
            /* Scanned BELOW AND RIGHT of the corner block, not from the
             * first interior texel. Falsifying this with horizontal
             * stripes left it green: the white corner block sits
             * against the stripes and supplies horizontal variation on
             * its own, so the check was reading the block rather than
             * the pattern. Same class of mistake as the one review
             * found, one level down, found by falsifying the fix. */
            int x, y, vx = 0, vy = 0, lo = COVER_EDGE + 8 + 1;
            for (y = lo; y < 64 - COVER_EDGE; y++) {
                for (x = lo; x < 64 - COVER_EDGE; x++) {
                    const unsigned char *c = cov + ((y * 64) + x) * 4;
                    if (memcmp(c, c - 4, 4) != 0) vx = 1;
                    if (memcmp(c, c - 64 * 4, 4) != 0) vy = 1;
                }
            }
            CHECK(vx && vy,
                  "and varies on both axes clear of the corner block, so it "
                  "cannot be mistaken for a framebuffer row or a texture "
                  "read at the wrong stride");
        }
        (void)flat;
        CHECK(cov[3] == 0x80,
              "and its alpha is in the GS domain: 0xFF would ask for about "
              "twice the coverage it has");
        {
            /* At 2x2 every texel is border, so both indices come out
             * identical and this said nothing -- I wrote it with a
             * `|| 1` to make it pass, which is worse than not having
             * it. At a real cover size the hues differ, and "which
             * cover is on screen" is a question the bench asks. */
            static unsigned char other[64 * 64 * 4];
            cover_fill(other, 1, 64, 64);
            CHECK(memcmp(cov, other, sizeof cov) != 0,
                  "and two indices differ, so a swapped cover is visible");
        }
    }

    /* ---- composition: two screens in one frame (design v6 4) --------
     *
     * ps2ui_render never clears, so `screen_set + render` twice in one
     * frame composites the second over the first. That is the dialog
     * and modal technique an OPL-class environment needs, and until
     * this block it worked by ACCIDENT: undocumented, untested, found
     * by experiment. The first refactor that adds a clear to render
     * deletes it silently, and the symptom is on a television.
     *
     * Everything here is asserted against the two screens' own solo
     * counts rather than against literals, so the fences survive the
     * example's markup changing. */
    {
        int solo_a, solo_b, composed, after_a;
        const char *focus_a, *focus_b;
        uint32_t stats_a, stats_b;

        CHECK(ps2ui_screen_set(&ctx, "library") == 1, "composition: base screen exists");
        solo_a = render_and_count(&ctx, &gs);
        stats_a = ctx.stats.prims;
        focus_a = ps2ui_focus_name(&ctx);

        CHECK(ps2ui_screen_set(&ctx, "saves") == 1, "and the overlay screen exists");
        solo_b = render_and_count(&ctx, &gs);
        stats_b = ctx.stats.prims;
        CHECK(solo_a > 0 && solo_b > 0,
              "both screens draw something on their own, or the sum below is vacuous");

        /* One frame: base, then overlay, with no reset between them --
         * which is precisely what a caller does and what a clear would
         * break. */
        stub_reset();
        ps2ui_screen_set(&ctx, "library");
        ps2ui_render(&ctx, &gs);
        ps2ui_screen_set(&ctx, "saves");
        ps2ui_render(&ctx, &gs);
        composed = g_stub.n_prims;
        CHECK(composed == solo_a + solo_b,
              "compositing two screens draws the sum: render adds to the frame, "
              "it does not own it");
        /* The guarantee itself, not a consequence of it. The sum above
         * would survive a clear being added to render -- a clear costs
         * no primitives -- and a clear is precisely the refactor the
         * design doc names as the one that deletes this feature. So it
         * is asserted directly: the stub counts gsKit_clear and
         * gsKit_vram_clear, and render must call neither. */
        CHECK(g_stub.n_clears == 0,
              "and render issued no clear, which is the guarantee the sum "
              "above only depends on");
        /* The other half of the same idea, and the one review caught
         * undefended. gsKit_TexManager_nextFrame is the residency
         * ageing tick and it belongs to the CALLER's frame loop, once,
         * after the flip. A render that took it over would make the
         * overlay age the base's textures, so an open dialog
         * re-uploads the base's atlases every frame -- and unlike a
         * clear, which anyone sees the instant they look at a
         * composited frame, that shows up only as frame time. The stub
         * already had nextFrame as a bare no-op, so a render calling
         * it linked fine and asserted nothing. */
        CHECK(g_stub.n_frame_ticks == 0,
              "and issued no residency ageing tick: nextFrame is the frame "
              "loop's, once per frame, or the overlay ages the base");

        /* The anti-leak half, and it took two attempts to make it real.
         *
         * The first version re-rendered the overlay alone and checked
         * the count was unchanged. That cannot fail: the stub records
         * every primitive regardless of scissor, so no clip state can
         * move a prim count in this suite -- deleting render's
         * end-of-frame scissor restore left it green. What the stub
         * CAN see is the register, so that is what is asserted.
         *
         * Two things worth being straight about. It is delivered by
         * two mechanisms, not one: a balanced blob's last POP already
         * re-applies stack[0], so the explicit restore at the end of
         * render is belt to those braces and deleting either alone
         * leaves this green. It fires when both go.
         *
         * The redundancy is structurally untestable, not merely
         * untested (review's point, and sharper than the first version
         * of this comment): the baker refuses to write an unbalanced
         * blob and render refuses the pops of pushes it refused, so no
         * blob the loader accepts can distinguish the two mechanisms.
         * That is a reason to keep both and say so, not a reason to
         * hunt for a fixture that separates them.
         *
         * It also overlaps the single-render check further up, which
         * asserts the same register after one replay -- kept anyway,
         * because "the next drawer inherits the whole screen" is part
         * of THIS contract and a reader of the composite block should
         * not have to know the other check exists to find it stated.
         *
         * It matters for compositing specifically: an app drawing its
         * own geometry after ps2ui_render -- which is the whole point
         * of a runtime that composites -- must not inherit a scissor
         * clipped to some panel deep inside the last screen. */
        CHECK(g_stub.last_scissor
                  == GS_SETREG_SCISSOR(0, ctx.hdr->canvas_w - 1,
                                       0, ctx.hdr->canvas_h - 1),
              "a composited frame leaves the scissor at full canvas, so the "
              "next drawer inherits the whole screen and not the last clip");
        CHECK(render_and_count(&ctx, &gs) == solo_b,
              "and the overlay alone still costs what it did before: render "
              "is idempotent, it does not consume the screen it drew");

        /* Per render, not per frame. ps2ui_render memsets stats at the
         * top of every call, so after a composite the counters describe
         * the LAST render only -- not the frame. Asserted rather than
         * left as a surprise: a caller summing frame cost has to read
         * them between renders, and finding that out from a wrong
         * number on a television is the expensive way. */
        CHECK(ctx.stats.prims == stats_b && stats_b != (uint32_t)composed,
              "stats describe one render, not the composited frame");
        CHECK(stats_a == (uint32_t)solo_a, "and each render's own stats are its own");

        /* Input goes to the last screen_set, which is the overlay if
         * you drew it last -- so a modal owns the D-pad for free, and
         * dismissing it is one screen_set back. */
        focus_b = ps2ui_focus_name(&ctx);
        CHECK(focus_b != NULL && focus_a != NULL && strcmp(focus_a, focus_b) != 0,
              "the two screens focus different nodes, or the routing check "
              "below cannot tell them apart");
        /* focus_set is screen-scoped, so it doubles as the question
         * "is this name addressable from where input currently is". */
        CHECK(ps2ui_focus_set(&ctx, focus_b) == 1,
              "after the composite, input resolves inside the overlay: the last "
              "screen_set owns the D-pad");
        CHECK(ps2ui_focus_set(&ctx, focus_a) == 0,
              "and the base's focused node is not reachable from it, so the "
              "overlay is not merely drawn on top -- it has input scope");
        CHECK(ps2ui_screen_set(&ctx, "library") == 1
              && strcmp(ps2ui_focus_name(&ctx), focus_a) == 0,
              "and dismissing restores the base's focus where the user left it");
        after_a = render_and_count(&ctx, &gs);
        CHECK(after_a == solo_a, "and the base draws what it always did");

        /* Residency is per FRAME, not per render. gsKit_TexManager_nextFrame
         * is the ageing tick and the sample calls it once after
         * sync_flip, so two composited renders share one residency
         * generation: the second must not re-transfer what the first
         * bound. If it did, an overlay would cost a full re-upload of
         * the base's atlases every frame it was open. */
        {
            int t0, b0;
            /* Frame 1 warms both screens. The first draft of this
             * checked that the OVERLAY render transferred nothing the
             * base had made resident, and it failed -- correctly. The
             * overlay's own atlases had never been bound in that
             * frame, so transferring them is first use, not eviction.
             * The property worth pinning is steady state: a composited
             * frame that runs again costs no pixels. */
            stub_reset_keep_tm();
            ps2ui_screen_set(&ctx, "library");
            ps2ui_render(&ctx, &gs);
            ps2ui_screen_set(&ctx, "saves");
            ps2ui_render(&ctx, &gs);

            /* Deltas, not absolutes: stub_reset_keep_tm zeroes the
             * per-frame counters and deliberately leaves n_transfers
             * and n_binds cumulative, because residency is the thing
             * that survives a frame boundary. */
            t0 = g_stub.n_transfers;
            b0 = g_stub.n_binds;
            stub_reset_keep_tm();          /* next frame, VRAM untouched */
            ps2ui_screen_set(&ctx, "library");
            ps2ui_render(&ctx, &gs);
            ps2ui_screen_set(&ctx, "saves");
            ps2ui_render(&ctx, &gs);
            CHECK(g_stub.n_transfers == t0,
                  "a composited frame in steady state transfers no pixels: two "
                  "renders share one residency generation, so an open overlay "
                  "does not re-upload the base's atlases every frame");
            CHECK(g_stub.n_binds > b0,
                  "while still binding, so the zero above is a residency hit "
                  "and not an absence of textures");
            /* WHAT THIS DOES NOT PROVE. The stub leaves gsKit's
             * eviction heuristic unmodelled on purpose -- ps2ui_upload
             * preflights the whole blob, so eviction is unreachable,
             * and modelling the weight function here would certify a
             * guess. So this fences "nothing on the composite path
             * invalidates or resets residency", which is the half a
             * refactor can break. Whether the real manager keeps both
             * screens resident under pressure is a console question,
             * and the Phase 1 bench sitting is where it gets asked. */
        }
        /* Visibility across a composite. The bits are indexed by
         * GLOBAL focus index, but a name resolves through
         * focus_index_by_name, which searches only the current
         * screen's range -- so "hide this" is unambiguous even when
         * two screens use the same name, and hiding on the overlay
         * cannot reach into the base. The ordering rule that falls out
         * of it is the one an app has to know: set visibility on the
         * screen that owns the node, which is the screen you are about
         * to render anyway. */
        {
            int base_hidden, base_shown;
            ps2ui_screen_set(&ctx, "library");
            base_shown = render_and_count(&ctx, &gs);
            CHECK(ps2ui_visible_set(&ctx, focus_a, 0) == 1,
                  "a node on the base can be hidden while the base is current");
            base_hidden = render_and_count(&ctx, &gs);
            CHECK(base_hidden < base_shown,
                  "and hiding it costs the base primitives, or the check "
                  "below cannot tell a scope failure from a no-op");

            ps2ui_screen_set(&ctx, "saves");
            CHECK(ps2ui_visible_set(&ctx, focus_a, 1) == 0,
                  "that same name is not settable from the overlay: visibility "
                  "resolves in the current screen, so an overlay cannot reach "
                  "into the base by naming one of its nodes");
            CHECK(render_and_count(&ctx, &gs) == solo_b,
                  "and the overlay is unaffected by the base's hidden bit");

            ps2ui_screen_set(&ctx, "library");
            CHECK(render_and_count(&ctx, &gs) == base_hidden,
                  "while the base kept it: visibility survives a screen "
                  "round trip rather than being frame state");
            CHECK(ps2ui_visible_set(&ctx, focus_a, 1) == 1
                  && render_and_count(&ctx, &gs) == base_shown,
                  "and restoring it restores the frame exactly");
        }
        ps2ui_screen_set(&ctx, "library");
    }

    /* ---- lists and visibility against a real data-repeat blob ----
     * The memcard example cannot test this: its tiles are named after
     * games, so a list prefix matches nothing and every assertion below
     * would pass vacuously. This fixture bakes row-0..row-3 with one
     * slot each. */
    /* `> 2`, not `== 3`: an exact match silently skipped this whole
     * section the moment a THIRD fixture was added to the command
     * line, taking 18 checks with it and leaving the suite green and
     * smaller. A guard on argument count must say "I have what I
     * need", never "the caller passed exactly what I expected". */
    if (argc > 2) {
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
        int loaded = load_arena(&lc, lblob, llen);
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

        /* (a) nothing fits: the preflight refuses before any bind. */
        starved = gs;
        starved.CurrentPointer = 4u * 1024u * 1024u - 16u;
        memset(&sc, 0, sizeof sc);
        if (load_arena(&sc, blob, len) == PS2UI_OK) {
            CHECK(ps2ui_upload(&sc, &starved) != 0,
                  "upload reports failure when VRAM is exhausted, so "
                  "step 9's expected 0 is a result and not a constant");
            CHECK(sc.uploaded == 0,
                  "and leaves the context not-uploaded, so a caller "
                  "cannot render through a half-built texture table");
        } else {
            CHECK(0, "starved-upload fixture failed to load");
        }

        /* (b) a budget that the OLD path would have exhausted PARTWAY
         * -- enough for some textures, not all. Under the manager this
         * case no longer exists as a runtime state, and that is the
         * point: gsKit_TexManager_bind cannot report exhaustion (its
         * allocator loops forever evicting when nothing can ever fit),
         * so ps2ui_upload preflights the whole budget and refuses
         * BEFORE the first transfer. The old test asserted "uploaded
         * some but not all (7 of 19)"; the property worth keeping is
         * stronger: a budget that cannot hold everything uploads
         * NOTHING, so there is no half-built texture table for a
         * caller to render through and no console hang inside gsKit
         * for the operator to photograph. */
        starved = gs;
        starved.CurrentPointer = 4u * 1024u * 1024u - vram_used / 2u;
        memset(&sc, 0, sizeof sc);
        if (load_arena(&sc, blob, len) == PS2UI_OK) {
            int rc;
            int before = g_stub.n_uploads;
            rc = ps2ui_upload(&sc, &starved);
            CHECK(rc != 0, "upload refuses a budget that holds some textures but "
                           "not all of them");
            snprintf(partway, sizeof partway,
                     "and transfers nothing at all (%d transfers) -- all-or-nothing, "
                     "because bind cannot fail and a partial table cannot render",
                     g_stub.n_uploads - before);
            CHECK(g_stub.n_uploads == before, partway);
            CHECK(sc.uploaded == 0,
                  "and still leaves it not-uploaded");
        } else {
            CHECK(0, "partway-starved fixture failed to load");
        }
    }

    /* ---- streamed texture slots (v6 §3) ----
     *
     * The fixture carries a named baked texture, a named streamed one,
     * and an anonymous baked one, so the name lookup has to tell the
     * kinds apart rather than just find a string. */
    if (argc > 3) {
        size_t slen;
        void *sblob = slurp(argv[3], &slen);
        ps2ui_ctx sc;
        size_t need = ps2ui_arena_size(sblob, slen);
        void *sarena = malloc(need ? need : 64);
        int rc = ps2ui_load(&sc, sblob, slen, sarena, need ? need : 64);
        CHECK(rc == PS2UI_OK, "the streamed fixture loads");
        if (rc == PS2UI_OK) {
            /* 16-aligned because it is about to become a DMA source;
             * the refusal of an unaligned one is checked below with a
             * deliberately shifted pointer. */
            static uint8_t cover[256] __attribute__((aligned(16)));
            static uint8_t cover2[256] __attribute__((aligned(16)));
            GSGLOBAL sgs = gs;
            uint32_t ci = PS2UI_NONE, k;
            int before, after;

            for (k = 0; k < sc.hdr->n_tex; k++)
                if (sc.tex[k].kind == PS2UI_TEXKIND_STREAMED) ci = k;
            CHECK(ci != PS2UI_NONE, "the fixture declares a streamed texture");
            CHECK((sc.hdr->feature_flags & PS2UI_FEAT_STREAMED_TEX) != 0,
                  "and says so in the header, so a reader that cannot "
                  "stream refuses the file");

            /* The loader's own refusals for a malformed v6 blob. Each
             * one is a property the runtime relies on later and cannot
             * afford to re-check per frame. */
            {
                ps2ui_ctx bc;
                uint8_t *dup = malloc(slen);
                void *ba = malloc(need ? need : 64);
                ps2ui_tex_entry *bt;
                size_t tof = ((const ps2ui_header *)sblob)->off_tex
                             + (size_t)ci * sizeof(ps2ui_tex_entry);

                memcpy(dup, sblob, slen);
                bt = (ps2ui_tex_entry *)(dup + tof);
                bt->kind = 7;                       /* neither kind */
                recrc(dup, slen);
                CHECK(ps2ui_load(&bc, dup, slen, ba, need)
                          == PS2UI_ERR_BOUNDS,
                      "a texture with an unknown kind is refused");

                memcpy(dup, sblob, slen);
                bt = (ps2ui_tex_entry *)(dup + tof);
                bt->data_len = 0;
                recrc(dup, slen);
                CHECK(ps2ui_load(&bc, dup, slen, ba, need)
                          == PS2UI_ERR_BOUNDS,
                      "a streamed texture reserving nothing is refused");

                memcpy(dup, sblob, slen);
                bt = (ps2ui_tex_entry *)(dup + tof);
                bt->name_off = PS2UI_NAME_NONE;
                recrc(dup, slen);
                CHECK(ps2ui_load(&bc, dup, slen, ba, need)
                          == PS2UI_ERR_BOUNDS,
                      "an unnamed streamed texture is refused: nothing "
                      "could ever fill it");

                /* The fixture carries a font pointing at the baked
                 * atlas, so this check has something to be wrong
                 * about: the slot pen binds a font's texture without
                 * checking for texels, which a streamed atlas would
                 * not have. */
                memcpy(dup, sblob, slen);
                CHECK(sc.hdr->n_font > 0, "the fixture has a font to repoint");
                {
                    ps2ui_font_entry *bf = (ps2ui_font_entry *)
                        (dup + ((const ps2ui_header *)sblob)->off_font);
                    bf->tex = (uint16_t)ci;
                    recrc(dup, slen);
                    CHECK(ps2ui_load(&bc, dup, slen, ba, need)
                              == PS2UI_ERR_BOUNDS,
                          "a font pointing at a streamed texture is refused");
                }

                memcpy(dup, sblob, slen);
                ((ps2ui_header *)dup)->feature_flags &= (uint16_t)~PS2UI_FEAT_STREAMED_TEX;
                recrc(dup, slen);
                CHECK(ps2ui_load(&bc, dup, slen, ba, need)
                          == PS2UI_ERR_FEATURES,
                      "a blob carrying a streamed texture without declaring "
                      "the feature bit is refused, not quietly drawn empty");
                free(dup);
                free(ba);
            }

            /* Rejections first, while the slot is still empty. */
            CHECK(ps2ui_tex_set(&sc, &sgs, "nope", cover, 256)
                      == PS2UI_ERR_NOT_STREAMED,
                  "tex_set rejects an unknown name");
            CHECK(ps2ui_tex_set(&sc, &sgs, "logo", cover, 64)
                      == PS2UI_ERR_NOT_STREAMED,
                  "tex_set refuses a BAKED texture: its texels are the "
                  "blob's, not the caller's to replace");
            CHECK(ps2ui_tex_set(&sc, &sgs, "cover", cover, 255)
                      == PS2UI_ERR_SIZE,
                  "tex_set refuses a payload one byte short of the reservation");
            CHECK(ps2ui_tex_set(&sc, &sgs, "cover", cover, 257)
                      == PS2UI_ERR_SIZE,
                  "and one byte long: a mismatch means the caller and the "
                  "bake disagree about the geometry");
            CHECK(ps2ui_tex_set(&sc, &sgs, "cover", cover + 8, 256)
                      == PS2UI_ERR_ALIGN,
                  "tex_set refuses a misaligned buffer: a DMA source "
                  "truncates silently below 16 bytes");

            /* An unfilled slot must draw nothing rather than DMA from a
             * null source -- and must not take the rest of the frame
             * with it. */
            CHECK(ps2ui_upload(&sc, &sgs) == 0,
                  "upload succeeds with a streamed slot still empty");
            CHECK(sc.gs_tex[ci].Mem == NULL,
                  "and leaves that slot with no source, rather than "
                  "pointing it at the blob");
            stub_reset_keep_tm();
            ps2ui_render(&sc, &sgs);
            before = g_stub.n_prims;
            CHECK(sc.stats.tex_unfilled == 1,
                  "an unfilled streamed slot is skipped and counted");
            CHECK(before >= 1,
                  "and the baked quad in the same frame still draws");

            /* Now fill it. */
            memset(cover, 0x5A, sizeof cover);
            CHECK(ps2ui_tex_set(&sc, &sgs, "cover", cover, 256) == PS2UI_OK,
                  "tex_set accepts the exact reservation");
            CHECK(sc.gs_tex[ci].Mem == (u32 *)(void *)cover,
                  "and points the slot at the caller's buffer -- nothing "
                  "is copied, the same contract the blob already has");
            {
                int flushed = 0, q;
                for (q = 0; q < g_stub.n_flushes; q++)
                    if (g_stub.flushes[q].start == (const void *)cover
                        && g_stub.flushes[q].end
                           == (const void *)(cover + 256))
                        flushed = 1;
                CHECK(flushed,
                      "tex_set writes the caller's texels back from cache: "
                      "the CPU wrote them and the GIF does not see that cache");
            }
            stub_reset_keep_tm();
            ps2ui_render(&sc, &sgs);
            after = g_stub.n_prims;
            CHECK(after == before + 1,
                  "the filled slot draws, so the frame gains exactly one prim");
            CHECK(sc.stats.tex_unfilled == 0,
                  "and nothing is counted unfilled any more");

            /* Swapping texels is what scrolling a list does. The
             * manager may hold the slot resident from the last set, in
             * which case a bind without invalidation would draw the OLD
             * cover out of VRAM and never look at the new pointer. */
            {
                int inv_before = g_stub.n_invalidates;
                memset(cover2, 0xA5, sizeof cover2);
                CHECK(ps2ui_tex_set(&sc, &sgs, "cover", cover2, 256) == PS2UI_OK,
                      "a second tex_set swaps the texels");
                CHECK(sc.gs_tex[ci].Mem == (u32 *)(void *)cover2,
                      "and repoints the slot");
                CHECK(g_stub.n_invalidates > inv_before,
                      "and invalidates residency, or the next bind would "
                      "draw the previous cover out of VRAM");
            }
        }
        free(sblob);
        /* sarena deliberately leaked: sc points into it. */
    }

    /* ---- the table ceilings, and what replaced them (PLAN 6.3) ---- */
    if (argc > 4) {
        size_t wlen;
        void *wblob = slurp(argv[4], &wlen);
        const ps2ui_header *wh = (const ps2ui_header *)wblob;
        ps2ui_ctx wc;
        size_t need;
        void *warena;
        int wrc;

        /* Past 16 slots, 32 textures and 8 screens -- the three numbers
         * ps2ui.h used to reject a blob for. The counts are read from
         * the fixture rather than hardcoded here, so a generator that
         * quietly shrinks cannot leave this passing on a blob that no
         * longer tests anything. */
        CHECK(wh->n_slot > 16 && wh->n_tex > 32 && wh->n_screen > 8,
              "the wide fixture is actually past all three old ceilings");

        need = ps2ui_arena_size(wblob, wlen);
        CHECK(need > 0, "and the arena for it can be computed");
        warena = malloc(need);
        wrc = ps2ui_load(&wc, wblob, wlen, warena, need);
        CHECK(wrc == PS2UI_OK, "a blob past every old ceiling loads");

        /* The checks below all dereference wc. Guarded so a regression
         * reports the line above rather than dying here -- a segfault
         * is a failure, but it is a failure that says nothing about
         * which property broke. Not a silent skip: the guard's own
         * condition is the check immediately preceding it, so if these
         * do not run, something red says why. */
        if (wrc == PS2UI_OK) {
            /* Addressable, not merely counted. A ceiling removed from
             * the header and left standing in the slot table would
             * load and then fail here. */
            char last[16], scr[16];
            CHECK(ps2ui_slot_set(&wc, "s0", "first") == 1,
                  "slot 0 is settable");
            sprintf(last, "s%u", (unsigned)(wh->n_slot - 1));
            CHECK(ps2ui_slot_set(&wc, last, "past the old ceiling") == 1,
                  "and so is the last slot, well past 16");
            CHECK(strcmp(ps2ui_slot_get(&wc, last), "past the old ceiling") == 0,
                  "and it reads back what was written");
            sprintf(scr, "screen%u", (unsigned)(wh->n_screen - 1));
            CHECK(ps2ui_screen_set(&wc, scr) == 1,
                  "the last screen is reachable, well past 8");
            /* Every slot's text region is distinct. The carve hands
             * each one its own offset; if two shared, writing the last
             * would disturb the first, and a linear region is exactly
             * where an off-by-one in the offset walk shows up. */
            CHECK(strcmp(ps2ui_slot_get(&wc, "s0"), "first") == 0,
                  "and writing the last slot did not disturb the first");
        }
        free(wblob);
        /* warena deliberately leaked: wc points into it. */
    }

    if (argc > 5) {
        size_t hlen;
        void *hblob = slurp(argv[5], &hlen);
        const ps2ui_header *hh = (const ps2ui_header *)hblob;
        ps2ui_ctx hc;
        uint64_t expect_text = 0;
        uint32_t k;
        size_t got;
        {
            const ps2ui_slot_entry *sl =
                (const ps2ui_slot_entry *)((const uint8_t *)hblob + hh->off_slot);
            for (k = 0; k < hh->n_slot; k++)
                expect_text += (uint64_t)sl[k].capacity + 1;
        }
        CHECK(expect_text > 0xFFFFFFFFull - 0x10000ull,
              "the huge fixture demands enough slot text to matter "
              "(a smaller one would prove nothing about a 32-bit total)");

        got = ps2ui_arena_size(hblob, hlen);
        /* On this 64-bit host the total is representable, so the
         * question is whether it was computed at full width or wrapped
         * on the way. A wrapped answer is small; the true one is not.
         * On the EE this same blob is refused -- see test-narrow, which
         * is the only place that path is reachable here. */
        if (sizeof(size_t) > 4) {
            CHECK((uint64_t)got > expect_text,
                  "arena_size reports the true multi-gigabyte total "
                  "rather than a wrapped one");
        } else {
            CHECK(got == 0, "a 32-bit host refuses the carve outright");
        }
        {
            /* Whatever the width, the runtime must not carve a small
             * arena for it. This is the failure the ceilings used to
             * prevent by accident. */
            static uint8_t small[4096]
                __attribute__((aligned(PS2UI_ARENA_ALIGN)));
            int rc;
            size_t j, dirty = 0;
            memset(small, 0xCD, sizeof small);
            rc = ps2ui_load(&hc, hblob, hlen, small, sizeof small);
            CHECK(rc == PS2UI_ERR_ARENA || rc == PS2UI_ERR_TOO_MANY,
                  "and refuses to load it into a 4 KiB arena");
            /* Refused means untouched: the carve happens strictly
             * after the size comparison, so a caller who passed too
             * little still owns whatever was in that buffer. Moving
             * the memset in ps2ui_load one block earlier breaks this
             * and nothing else, which is the point of asserting it. */
            for (j = 0; j < sizeof small; j++)
                if (small[j] != 0xCD) dirty++;
            CHECK(dirty == 0, "and writes nothing into the arena it refused");
        }
        free(hblob);
    }

report:
    printf("1..%d\n", checks);
    printf("%s: %d checks, %d failure(s)\n", failures ? "FAIL" : "PASS", checks, failures);
    free(blob);
    return failures ? 1 : 0;
}
