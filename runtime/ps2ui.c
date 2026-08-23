/* ps2ui runtime implementation. C99, no allocation, no libc beyond
 * string.h/stddef.h. See ps2ui.h for the contract. */

#include "ps2ui.h"

#include <string.h>

static void render_slots(ps2ui_ctx *ctx, GSGLOBAL *gs);
static uint16_t focus_index_by_name(const ps2ui_ctx *ctx, const char *name);

/* ---------------------------------------------------------------- crc */

/* IEEE reflected CRC-32, table built on first use (static storage, no
 * allocation). Matches Python's zlib.crc32, which writes the field. */
static uint32_t crc_table[256];
static int crc_table_ready = 0;

static void crc_init(void)
{
    uint32_t n, k, c;
    for (n = 0; n < 256; n++) {
        c = n;
        for (k = 0; k < 8; k++)
            c = (c & 1u) ? 0xEDB88320u ^ (c >> 1) : c >> 1;
        crc_table[n] = c;
    }
    crc_table_ready = 1;
}

/* Chaining core: crc is the internal (pre-inverted) state. */
static uint32_t crc_update(uint32_t crc, const uint8_t *p, size_t len)
{
    size_t i;
    for (i = 0; i < len; i++)
        crc = crc_table[(crc ^ p[i]) & 0xFFu] ^ (crc >> 8);
    return crc;
}

uint32_t ps2ui_crc32(const void *data, size_t len)
{
    if (!crc_table_ready)
        crc_init();
    return crc_update(0xFFFFFFFFu, (const uint8_t *)data, len) ^ 0xFFFFFFFFu;
}

/* CRC of the whole file with the header's crc32 field read as zero,
 * computed in three spans so the caller's const buffer stays const. */
static uint32_t crc_file_with_hole(const uint8_t *data, size_t len)
{
    static const uint8_t zeros[4] = { 0, 0, 0, 0 };
    const size_t hole = 48; /* byte offset of ps2ui_header.crc32 */
    uint32_t c;
    if (!crc_table_ready)
        crc_init();
    c = 0xFFFFFFFFu;
    c = crc_update(c, data, hole);
    c = crc_update(c, zeros, 4);
    c = crc_update(c, data + hole + 4, len - hole - 4);
    return c ^ 0xFFFFFFFFu;
}

/* ------------------------------------------------------------- loading */

static int in_blob(const ps2ui_ctx *ctx, uint32_t off, uint32_t len)
{
    return off <= ctx->hdr->blob_len && len <= ctx->hdr->blob_len - off;
}

int ps2ui_load(ps2ui_ctx *ctx, const void *data, size_t size)
{
    uint32_t i;
    memset(ctx, 0, sizeof *ctx);
    if (size < sizeof(ps2ui_header))
        return PS2UI_ERR_TRUNCATED;

    ctx->data = (const uint8_t *)data;
    ctx->size = size;
    ctx->hdr  = (const ps2ui_header *)data;

    if (ctx->hdr->magic != PS2UI_MAGIC)
        return PS2UI_ERR_MAGIC;
    if (ctx->hdr->version != PS2UI_VERSION)
        return PS2UI_ERR_VERSION;
    if (ctx->hdr->feature_flags & ~PS2UI_FEAT_KNOWN)
        return PS2UI_ERR_FEATURES;
    if (ctx->hdr->n_tex > PS2UI_MAX_TEXTURES || ctx->hdr->n_slot > PS2UI_MAX_SLOTS
        || ctx->hdr->n_screen > PS2UI_MAX_SCREENS || ctx->hdr->n_screen == 0)
        return PS2UI_ERR_TOO_MANY;

    {
        const ps2ui_header *h = ctx->hdr;
        uint64_t need_tex   = (uint64_t)h->off_tex   + (uint64_t)h->n_tex   * sizeof(ps2ui_tex_entry);
        uint64_t need_clut  = (uint64_t)h->off_clut  + (uint64_t)h->n_clut  * sizeof(ps2ui_clut_entry);
        uint64_t need_cmd   = (uint64_t)h->off_cmd   + (uint64_t)h->n_cmd   * sizeof(ps2ui_cmd);
        uint64_t need_focus = (uint64_t)h->off_focus + (uint64_t)h->n_focus * sizeof(ps2ui_focus_node);
        uint64_t need_font  = (uint64_t)h->off_font  + (uint64_t)h->n_font  * sizeof(ps2ui_font_entry);
        uint64_t need_slot  = (uint64_t)h->off_slot  + (uint64_t)h->n_slot  * sizeof(ps2ui_slot_entry);
        uint64_t need_scr   = (uint64_t)h->off_screen + (uint64_t)h->n_screen * sizeof(ps2ui_screen_entry);
        uint64_t need_blob  = (uint64_t)h->off_blob  + h->blob_len;
        if (need_tex > size || need_clut > size || need_cmd > size
            || need_focus > size || need_font > size || need_slot > size
            || need_scr > size || need_blob > size)
            return PS2UI_ERR_TRUNCATED;
    }

    if (crc_file_with_hole(ctx->data, size) != ctx->hdr->crc32)
        return PS2UI_ERR_CRC;

    ctx->tex         = (const ps2ui_tex_entry *)(ctx->data + ctx->hdr->off_tex);
    ctx->clut        = (const ps2ui_clut_entry *)(ctx->data + ctx->hdr->off_clut);
    ctx->cmd         = (const ps2ui_cmd *)(ctx->data + ctx->hdr->off_cmd);
    ctx->focus_nodes = (const ps2ui_focus_node *)(ctx->data + ctx->hdr->off_focus);
    ctx->fonts       = (const ps2ui_font_entry *)(ctx->data + ctx->hdr->off_font);
    ctx->slots       = (const ps2ui_slot_entry *)(ctx->data + ctx->hdr->off_slot);
    ctx->screen_table = (const ps2ui_screen_entry *)(ctx->data + ctx->hdr->off_screen);
    ctx->blob        = ctx->data + ctx->hdr->off_blob;

    /* Every cross-reference is checked once here so the render loop can
     * index without branching. */
    for (i = 0; i < ctx->hdr->n_tex; i++) {
        const ps2ui_tex_entry *t = &ctx->tex[i];
        if (!in_blob(ctx, t->data_off, t->data_len))
            return PS2UI_ERR_BOUNDS;
        if (t->clut != PS2UI_NONE && t->clut >= ctx->hdr->n_clut)
            return PS2UI_ERR_BOUNDS;
        if (t->format != PS2UI_TEXFMT_PSMT8 && t->format != PS2UI_TEXFMT_PSMCT32)
            return PS2UI_ERR_BOUNDS;
    }
    for (i = 0; i < ctx->hdr->n_clut; i++) {
        if (!in_blob(ctx, ctx->clut[i].data_off, (uint32_t)ctx->clut[i].ncolors * 4u))
            return PS2UI_ERR_BOUNDS;
    }
    for (i = 0; i < ctx->hdr->n_cmd; i++) {
        const ps2ui_cmd *c = &ctx->cmd[i];
        if (c->op > PS2UI_OP_SCISSOR_POP)
            return PS2UI_ERR_BOUNDS;
        if (c->op == PS2UI_OP_TEXQUAD && c->tex >= ctx->hdr->n_tex)
            return PS2UI_ERR_BOUNDS;
        if (c->focus != PS2UI_NONE && c->focus >= ctx->hdr->n_focus)
            return PS2UI_ERR_BOUNDS;
    }
    for (i = 0; i < ctx->hdr->n_focus; i++) {
        const ps2ui_focus_node *n = &ctx->focus_nodes[i];
        uint16_t dirs[4];
        int d;
        dirs[0] = n->up; dirs[1] = n->down; dirs[2] = n->left; dirs[3] = n->right;
        for (d = 0; d < 4; d++)
            if (dirs[d] != PS2UI_NONE && dirs[d] >= ctx->hdr->n_focus)
                return PS2UI_ERR_BOUNDS;
        if (n->name_off >= ctx->hdr->blob_len)
            return PS2UI_ERR_BOUNDS;
        /* The name must terminate inside the blob. */
        if (!memchr(ctx->blob + n->name_off, 0, ctx->hdr->blob_len - n->name_off))
            return PS2UI_ERR_BOUNDS;
    }

    for (i = 0; i < ctx->hdr->n_font; i++) {
        const ps2ui_font_entry *f = &ctx->fonts[i];
        if (f->tex >= ctx->hdr->n_tex)
            return PS2UI_ERR_BOUNDS;
        if (!in_blob(ctx, f->glyphs_off,
                     (uint32_t)f->glyph_count * (uint32_t)sizeof(ps2ui_glyph)))
            return PS2UI_ERR_BOUNDS;
        if (!in_blob(ctx, f->kerns_off,
                     (uint32_t)f->kern_count * (uint32_t)sizeof(ps2ui_kern)))
            return PS2UI_ERR_BOUNDS;
    }
    for (i = 0; i < ctx->hdr->n_slot; i++) {
        const ps2ui_slot_entry *s = &ctx->slots[i];
        if (s->font >= ctx->hdr->n_font)
            return PS2UI_ERR_BOUNDS;
        if (s->focus != PS2UI_NONE && s->focus >= ctx->hdr->n_focus)
            return PS2UI_ERR_BOUNDS;
        if (s->name_off >= ctx->hdr->blob_len
            || !memchr(ctx->blob + s->name_off, 0, ctx->hdr->blob_len - s->name_off))
            return PS2UI_ERR_BOUNDS;
        if (s->placeholder_off >= ctx->hdr->blob_len
            || !memchr(ctx->blob + s->placeholder_off, 0,
                       ctx->hdr->blob_len - s->placeholder_off))
            return PS2UI_ERR_BOUNDS;
    }

    for (i = 0; i < ctx->hdr->n_screen; i++) {
        const ps2ui_screen_entry *sc = &ctx->screen_table[i];
        if ((uint64_t)sc->cmd_first + sc->cmd_count > ctx->hdr->n_cmd
            || (uint32_t)sc->focus_first + sc->focus_count > ctx->hdr->n_focus
            || (uint32_t)sc->slot_first + sc->slot_count > ctx->hdr->n_slot)
            return PS2UI_ERR_BOUNDS;
        if (sc->initial_focus != PS2UI_NONE
            && sc->initial_focus >= ctx->hdr->n_focus)
            return PS2UI_ERR_BOUNDS;
        if (sc->name_off >= ctx->hdr->blob_len
            || !memchr(ctx->blob + sc->name_off, 0,
                       ctx->hdr->blob_len - sc->name_off))
            return PS2UI_ERR_BOUNDS;
        ctx->screen_focus[i] = sc->initial_focus;
    }

    ctx->screen = 0;
    ctx->focus = ctx->screen_table[0].initial_focus;
    if (ctx->focus != PS2UI_NONE && ctx->focus >= ctx->hdr->n_focus)
        return PS2UI_ERR_BOUNDS;
    return PS2UI_OK;
}

/* --------------------------------------------------------------- CLUT */

uint32_t ps2ui_clut_csm1(uint32_t index)
{
    uint32_t b3 = (index >> 3) & 1u;
    uint32_t b4 = (index >> 4) & 1u;
    return (index & ~0x18u) | (b3 << 4) | (b4 << 3);
}

/* Build with -DPS2UI_CLUT_PERMUTE=0 to upload the CLUT linearly.
 *
 * This exists as a compile-time A/B because the permutation is an
 * INVOLUTION, which makes its two failure modes indistinguishable from
 * the inside: applying it once is correct if the GS un-permutes, and
 * applying it zero or two times is identical to each other. If gsKit --
 * or a particular gsKit version -- already permutes on upload, ps2ui
 * doing it too lands the CLUT in VRAM linear, every index fetches the
 * wrong palette entry in 8-entry bands, and glyph coverage turns to
 * noise. No host test can tell those apart, because the host has no GS.
 *
 * bringup.md step 3 names the symptom and the test: "Toggle the
 * permute_clut call and compare." This is that toggle, so the compare
 * is two ELFs rather than a source edit at a bench. */
#ifndef PS2UI_CLUT_PERMUTE
#define PS2UI_CLUT_PERMUTE 1
#endif

/* CLUTs are stored linearly in the file (readable by any tool); the GS
 * wants CSM1 storage order on upload. Permute into `out` (256*4 bytes). */
static void permute_clut(const uint8_t *linear, uint16_t ncolors, uint8_t *out)
{
    uint32_t i;
    memset(out, 0, 256 * 4);
    for (i = 0; i < ncolors && i < 256; i++) {
#if PS2UI_CLUT_PERMUTE
        uint32_t j = ps2ui_clut_csm1(i);
#else
        uint32_t j = i;
#endif
        memcpy(out + j * 4, linear + i * 4, 4);
    }
}

/* ------------------------------------------------------------- upload */

/* One static CLUT staging buffer per context upload pass. gsKit keeps a
 * pointer to CLUT memory in GSTEXTURE::Clut, so the permuted copies
 * must live as long as the textures do; they go in a static pool sized
 * for the file limit rather than on the stack. */
static uint8_t clut_pool[PS2UI_MAX_TEXTURES][256 * 4] __attribute__((aligned(16)));

int ps2ui_upload(ps2ui_ctx *ctx, GSGLOBAL *gs)
{
    uint32_t i;
    for (i = 0; i < ctx->hdr->n_tex; i++) {
        const ps2ui_tex_entry *t = &ctx->tex[i];
        GSTEXTURE *g = &ctx->gs_tex[i];
        memset(g, 0, sizeof *g);
        g->Width  = t->width;
        g->Height = t->height;
        g->Filter = GS_FILTER_NEAREST; /* baked at exact size; bilinear only blurs */
        /* Nothing sets TEX0.TFX here, and nothing can: gsKit has no
         * per-texture TFX field, and every one of its GS_SETREG_TEX0
         * call sites passes a hardcoded 0 in the tfx position. 0 is
         * MODULATE -- texel x vertex color -- which is exactly what the
         * white glyph atlas needs, so the mode this runtime wants is
         * the mode it already gets. Verified two ways: gsKit source at
         * 43122eb declares no such field, and a compile probe in the
         * ps2dev container fails on `t.Function`. See docs/bringup.md
         * step 4. */
        if (t->format == PS2UI_TEXFMT_PSMCT32) {
            g->PSM = GS_PSM_CT32;
            g->Mem = (u32 *)(const void *)(ctx->blob + t->data_off);
        } else { /* PSMT8 + CLUT */
            const ps2ui_clut_entry *c = &ctx->clut[t->clut];
            g->PSM     = GS_PSM_T8;
            g->ClutPSM = GS_PSM_CT32;
            g->Mem     = (u32 *)(const void *)(ctx->blob + t->data_off);
            permute_clut(ctx->blob + c->data_off, c->ncolors, clut_pool[i]);
            g->Clut = (u32 *)(void *)clut_pool[i];
        }
        g->Vram = gsKit_vram_alloc(gs, gsKit_texture_size(g->Width, g->Height, g->PSM),
                                   GSKIT_ALLOC_USERBUFFER);
        if (g->Vram == GSKIT_ALLOC_ERROR)
            return -1;
        if (t->format == PS2UI_TEXFMT_PSMT8) {
            g->VramClut = gsKit_vram_alloc(gs, gsKit_texture_size(16, 16, GS_PSM_CT32),
                                           GSKIT_ALLOC_USERBUFFER);
            if (g->VramClut == GSKIT_ALLOC_ERROR)
                return -1;
        }
        gsKit_texture_upload(gs, g);
    }
    ctx->uploaded = 1;
    return 0;
}

/* ------------------------------------------------------------- render */

typedef struct scissor_rect { int x0, y0, x1, y1; } scissor_rect;

static void apply_scissor(GSGLOBAL *gs, const scissor_rect *r)
{
    gsKit_set_scissor(gs, GS_SETREG_SCISSOR(r->x0, r->x1 - 1, r->y0, r->y1 - 1));
}

/* Runtime visibility (F21), one bit per focus node. Separate from the
 * baked state machine below: `hidden` answers "should this subtree be
 * painted at all", cmd_visible answers "is this the focused or the
 * unfocused variant". */
static int node_hidden(const ps2ui_ctx *ctx, uint16_t idx)
{
    if (idx == PS2UI_NONE || idx >= PS2UI_MAX_HIDEABLE)
        return 0;
    return (ctx->hidden[idx >> 5] >> (idx & 31u)) & 1u;
}

static int cmd_visible(const ps2ui_cmd *c, uint16_t focus)
{
    int is_focused;
    if (c->state == PS2UI_STATE_ALWAYS)
        return 1;
    is_focused = (c->focus != PS2UI_NONE) && (c->focus == focus);
    return (c->state == PS2UI_STATE_FOCUSED) ? is_focused : !is_focused;
}

void ps2ui_render(ps2ui_ctx *ctx, GSGLOBAL *gs)
{
    scissor_rect stack[PS2UI_MAX_SCISSOR_DEPTH];
    int depth = 0;
    /* Pushes refused for want of stack. Their pops must be refused too:
     * popping a push that never happened leaves the stack one level
     * shallow, and every clip for the rest of the frame is then wrong,
     * not just the ones inside the too-deep subtree. The baker refuses
     * to write a blob this deep, so this is the belt to those braces. */
    int overflow = 0;
    uint32_t i;

    memset(&ctx->stats, 0, sizeof ctx->stats);

    /* Assert the blend this format's alpha domain assumes, every frame,
     * rather than inheriting whatever gsKit_init_screen left:
     *
     *     Cv = (Cs - Cd) * As >> 7 + Cd        A=Cs B=Cd C=As D=Cd
     *
     * Until a SCPH-50000 read the step 2 probe, nothing in this tree
     * had ever written the GS ALPHA register, and gsKit's default is
     * not this. Its default is GS_BLEND_BACK2FRONT, which decodes to
     * A=Cd B=Cs C=As D=Cs -- the operands swapped, so the effective
     * coverage is (128 - As) rather than As. Alpha ran exactly
     * inverted: a quad the .uib calls fully opaque at As=0x80 composited
     * to pure background and disappeared, while a nearly transparent
     * one painted at almost full strength. The probe measured that on
     * six rungs and every one fit 128 - As to within a unit.
     *
     * docs/format-uib.md documents the domain; this is the line that
     * makes the runtime honour it. Set it here, not once at init: the
     * value is global GS state and any other gsKit user in the host
     * program can change it between frames. gsKit_init_screen writes
     * the default straight into GS_ALPHA_1/GS_ALPHA_2 rather than
     * through gsGlobal->PrimAlpha, so a caller cannot pre-empt it by
     * assigning the field either -- here is the only place this fits.
     *
     * The alpha TEST is deliberately NOT asserted alongside it, and the
     * argument above does apply to it: a host that enables ATE between
     * frames would silently discard ps2ui pixels, the same shape of
     * fault found the same expensive way. It is left inherited because
     * gsKit_init_screen defaults ATE off, the probe positively ruled a
     * discard out (column 5's reference drew at the same vertex alpha
     * its test vanished at), and TEST also carries ZTE and ZTST -- so
     * rewriting it per frame through a preset whose full register
     * semantics are not pinned down here would be depending on
     * unverified GS state to fix a bug caused by depending on
     * unverified GS state. If a discard ever does show up, probe step 2
     * still covers it and gsKit_set_test(gs, GS_ATEST_OFF) is the line.
     */
    gsKit_set_primalpha(gs, GS_SETREG_ALPHA(0, 1, 0, 1, 0), 0);

    stack[0].x0 = 0;
    stack[0].y0 = 0;
    stack[0].x1 = ctx->hdr->canvas_w;
    stack[0].y1 = ctx->hdr->canvas_h;
    apply_scissor(gs, &stack[0]);

    {
        const ps2ui_screen_entry *sc = &ctx->screen_table[ctx->screen];
        uint32_t first = sc->cmd_first, endi = sc->cmd_first + sc->cmd_count;
        for (i = first; i < endi; i++) {
        const ps2ui_cmd *c = &ctx->cmd[i];
        ctx->stats.cmds++;

        if (c->op == PS2UI_OP_SCISSOR_PUSH) {
            scissor_rect r, *top = &stack[depth];
            if (depth + 1 >= PS2UI_MAX_SCISSOR_DEPTH) {
                /* Fail soft: the subtree draws under the enclosing clip,
                 * which is larger, so it draws too much rather than
                 * corrupting the frame. */
                overflow++;
                ctx->stats.scissor_overflow++;
                continue;
            }
            r.x0 = c->x > top->x0 ? c->x : top->x0;
            r.y0 = c->y > top->y0 ? c->y : top->y0;
            r.x1 = c->x + c->w < top->x1 ? c->x + c->w : top->x1;
            r.y1 = c->y + c->h < top->y1 ? c->y + c->h : top->y1;
            if (r.x1 < r.x0) r.x1 = r.x0;
            if (r.y1 < r.y0) r.y1 = r.y0;
            stack[++depth] = r;
            apply_scissor(gs, &stack[depth]);
            continue;
        }
        if (c->op == PS2UI_OP_SCISSOR_POP) {
            if (overflow > 0) {
                overflow--;   /* matches a push that was refused */
                continue;
            }
            if (depth > 0)
                depth--;
            apply_scissor(gs, &stack[depth]);
            continue;
        }
        if (!cmd_visible(c, ctx->focus))
            continue;
        if (node_hidden(ctx, c->focus)) {
            ctx->stats.skipped_hidden++;
            continue;
        }

        ctx->stats.prims++;
        if (c->op == PS2UI_OP_QUAD) {
            gsKit_prim_sprite(gs,
                (float)c->x, (float)c->y,
                (float)(c->x + c->w), (float)(c->y + c->h),
                0, GS_SETREG_RGBAQ(c->r, c->g, c->b, c->a, 0x00));
        } else { /* PS2UI_OP_TEXQUAD */
            gsKit_prim_sprite_texture(gs, &ctx->gs_tex[c->tex],
                (float)c->x, (float)c->y, (float)c->u0, (float)c->v0,
                (float)(c->x + c->w), (float)(c->y + c->h),
                (float)c->u1, (float)c->v1,
                0, GS_SETREG_RGBAQ(c->r, c->g, c->b, c->a, 0x00));
        }
        }
    }
    /* The baker guarantees balance; restore full-canvas scissor anyway
     * so a malformed blob cannot poison the next frame. */
    apply_scissor(gs, &stack[0]);

    /* Dynamic text draws after the static list: slots sit visually on
     * panels that the command list painted, and their glyph quads are
     * composed here from the baked glyph tables. */
    if (ctx->hdr->n_slot > 0)
        render_slots(ctx, gs);
}

/* ------------------------------------------------------- dynamic text */

/* Minimal UTF-8 decode: advances *s, returns the codepoint (U+FFFD on
 * malformed input rather than desyncing the stream). */
static uint32_t utf8_next(const char **s)
{
    const uint8_t *p = (const uint8_t *)*s;
    uint32_t cp;
    int extra, i;
    if (p[0] < 0x80) { cp = p[0]; extra = 0; }
    else if ((p[0] & 0xE0) == 0xC0) { cp = p[0] & 0x1Fu; extra = 1; }
    else if ((p[0] & 0xF0) == 0xE0) { cp = p[0] & 0x0Fu; extra = 2; }
    else if ((p[0] & 0xF8) == 0xF0) { cp = p[0] & 0x07u; extra = 3; }
    else { (*s)++; return 0xFFFD; }
    for (i = 1; i <= extra; i++) {
        if ((p[i] & 0xC0) != 0x80) { (*s)++; return 0xFFFD; }
        cp = (cp << 6) | (p[i] & 0x3Fu);
    }
    *s += extra + 1;
    return cp;
}

static const ps2ui_glyph *find_glyph(const ps2ui_ctx *ctx,
                                     const ps2ui_font_entry *font, uint32_t cp)
{
    /* Binary search: the baker writes glyphs codepoint-sorted. */
    const ps2ui_glyph *g = (const ps2ui_glyph *)(ctx->blob + font->glyphs_off);
    uint32_t lo = 0, hi = font->glyph_count;
    while (lo < hi) {
        uint32_t mid = lo + (hi - lo) / 2;
        if (g[mid].codepoint < cp) lo = mid + 1;
        else hi = mid;
    }
    if (lo < font->glyph_count && g[lo].codepoint == cp)
        return &g[lo];
    /* '?' fallback, matching the metrics' missing-glyph convention. */
    if (cp != '?')
        return find_glyph(ctx, font, '?');
    return 0;
}

/* Pixel kern for an ordered pair, or 0 when the pair is not adjusted.
 *
 * The baker resolved every pair to pixels at this font's size and
 * sorted the table by (prev, cur), so this is the same binary search
 * find_glyph does — no division, no metrics, no per-frame arithmetic
 * beyond a lookup. With the feature bit clear the table is empty by
 * construction and the whole thing costs one branch. */
static int find_kern(const ps2ui_ctx *ctx, const ps2ui_font_entry *font,
                     uint32_t prev, uint32_t cp)
{
    const ps2ui_kern *k;
    uint32_t lo = 0, hi = font->kern_count;
    if (hi == 0)
        return 0;
    k = (const ps2ui_kern *)(ctx->blob + font->kerns_off);
    while (lo < hi) {
        uint32_t mid = lo + (hi - lo) / 2;
        if (k[mid].prev < prev || (k[mid].prev == prev && k[mid].cur < cp))
            lo = mid + 1;
        else
            hi = mid;
    }
    if (lo < font->kern_count && k[lo].prev == prev && k[lo].cur == cp)
        return k[lo].amount;
    return 0;
}

#define PS2UI_ELLIPSIS_CP 0x2026u

/* Measure text against the slot width; returns width actually used and
 * writes the byte length to draw (truncated before an ellipsis) into
 * *draw_len and whether the ellipsis is needed into *ellipsize. */
static int slot_measure(const ps2ui_ctx *ctx, const ps2ui_slot_entry *s,
                        const ps2ui_font_entry *font, const char *text,
                        size_t *draw_len, int *ellipsize)
{
    const ps2ui_glyph *ell = find_glyph(ctx, font, PS2UI_ELLIPSIS_CP);
    int ell_w = ell ? ell->advance : 0;
    int w = 0, fit_w = 0;
    uint32_t prev = 0;
    int have_prev = 0;
    size_t fit_len = 0;
    const char *p = text;
    *ellipsize = 0;
    while (*p) {
        uint32_t cp = utf8_next(&p);
        const ps2ui_glyph *g = find_glyph(ctx, font, cp);
        int ell_kern;
        if (!g)
            continue;
        if (have_prev)
            w += s->letter_spacing + find_kern(ctx, font, prev, cp);
        /* The ellipsis joins like any other glyph: spacing plus the
         * kern against whatever the cut leaves last, so its cost
         * depends on where the cut falls and cannot be subtracted from
         * the budget once up front. */
        ell_kern = (s->flags & PS2UI_SLOT_FLAG_ELLIPSIS)
            ? s->letter_spacing + find_kern(ctx, font, cp, PS2UI_ELLIPSIS_CP)
            : 0;
        if ((s->flags & PS2UI_SLOT_FLAG_ELLIPSIS)
            && w + g->advance + ell_kern + ell_w <= s->w) {
            fit_w = w + g->advance + ell_kern;
            fit_len = (size_t)(p - text);
        }
        w += g->advance;
        prev = cp;
        have_prev = 1;
    }
    if (w <= s->w) {
        *draw_len = strlen(text);
        return w;
    }
    if (s->flags & PS2UI_SLOT_FLAG_ELLIPSIS) {
        *ellipsize = 1;
        *draw_len = fit_len;
        return fit_w + ell_w;
    }
    *draw_len = strlen(text); /* clip: draw all, scissor handles excess */
    return w;
}

static const char *slot_current_text(const ps2ui_ctx *ctx, uint32_t index)
{
    /* An explicitly set slot wins even when its text is empty, so an
     * app can blank a row it has no data for (backlog B12). */
    if (index < PS2UI_MAX_SLOTS && ctx->slot_is_set[index])
        return ctx->slot_text[index];
    return (const char *)(ctx->blob + ctx->slots[index].placeholder_off);
}

static void render_slots(ps2ui_ctx *ctx, GSGLOBAL *gs)
{
    const ps2ui_screen_entry *scr = &ctx->screen_table[ctx->screen];
    uint32_t i;
    for (i = scr->slot_first; i < (uint32_t)scr->slot_first + scr->slot_count; i++) {
        const ps2ui_slot_entry *s = &ctx->slots[i];
        const ps2ui_font_entry *font;
        const char *text;
        /* Slots live outside the command list, so the visibility check
         * in the command loop does not reach them. Without this, hiding
         * a row removes its panel and leaves its glyphs floating over
         * the background — worse than not hiding it at all. */
        if (node_hidden(ctx, s->focus)) {
            ctx->stats.slots_hidden++;
            continue;
        }
        font = &ctx->fonts[s->font];
        text = slot_current_text(ctx, i);
        size_t draw_len;
        int ellipsize;
        int width = slot_measure(ctx, s, font, text, &draw_len, &ellipsize);
        int pen, is_focused;
        const uint8_t *col;
        const char *p = text;
        const char *end = text + draw_len;

        pen = s->x;
        if (s->align == PS2UI_SLOT_ALIGN_CENTER && width < s->w)
            pen += (s->w - width) / 2;
        else if (s->align == PS2UI_SLOT_ALIGN_RIGHT && width < s->w)
            pen += s->w - width;

        is_focused = (s->focus != PS2UI_NONE) && (s->focus == ctx->focus);
        col = is_focused ? s->color_focus : s->color_base;

        uint32_t prev = 0;
        int have_prev = 0;
        while (p < end) {
            uint32_t cp = utf8_next(&p);
            const ps2ui_glyph *g = find_glyph(ctx, font, cp);
            if (!g)
                continue;
            /* Same pen as the baker's: spacing + kern, place, advance.
             * Runtime text sits next to baked text on the same screen,
             * so a runtime pen that skipped either would look like a
             * different font. */
            if (have_prev)
                pen += s->letter_spacing + find_kern(ctx, font, prev, cp);
            if (g->w > 0) {
                ctx->stats.prims++;
                ctx->stats.slot_glyphs++;
                gsKit_prim_sprite_texture(gs, &ctx->gs_tex[font->tex],
                    (float)(pen + g->bearing_x), (float)(s->text_y + g->bearing_y),
                    (float)g->u, (float)g->v,
                    (float)(pen + g->bearing_x + g->w),
                    (float)(s->text_y + g->bearing_y + g->h),
                    (float)(g->u + g->w), (float)(g->v + g->h),
                    0, GS_SETREG_RGBAQ(col[0], col[1], col[2], col[3], 0x00));
            }
            pen += g->advance;
            prev = cp;
            have_prev = 1;
        }
        if (ellipsize) {
            const ps2ui_glyph *g = find_glyph(ctx, font, PS2UI_ELLIPSIS_CP);
            if (have_prev)
                pen += s->letter_spacing
                     + find_kern(ctx, font, prev, PS2UI_ELLIPSIS_CP);
            if (g && g->w > 0) {
                ctx->stats.prims++;
                ctx->stats.slot_glyphs++;
                gsKit_prim_sprite_texture(gs, &ctx->gs_tex[font->tex],
                    (float)(pen + g->bearing_x), (float)(s->text_y + g->bearing_y),
                    (float)g->u, (float)g->v,
                    (float)(pen + g->bearing_x + g->w),
                    (float)(s->text_y + g->bearing_y + g->h),
                    (float)(g->u + g->w), (float)(g->v + g->h),
                    0, GS_SETREG_RGBAQ(col[0], col[1], col[2], col[3], 0x00));
            }
        }
    }
}

static uint32_t slot_index_by_name(const ps2ui_ctx *ctx, const char *name)
{
    uint32_t i;
    if (name == NULL)
        return PS2UI_NONE;
    for (i = 0; i < ctx->hdr->n_slot; i++) {
        if (strcmp((const char *)(ctx->blob + ctx->slots[i].name_off), name) == 0)
            return i;
    }
    return PS2UI_NONE;
}

/* Drop a trailing partial UTF-8 sequence left by a byte-wise truncation
 * (backlog B11). Without this, a title cut mid-character decodes as
 * U+FFFD and the pen draws '?' where half a glyph used to be. */
static void utf8_trim_partial(char *s)
{
    size_t n = strlen(s);
    size_t start = n;
    unsigned char lead;
    size_t need;

    while (start > 0 && ((unsigned char)s[start - 1] & 0xC0u) == 0x80u)
        start--;
    if (start == 0)
        return; /* nothing but continuation bytes; leave it to the decoder */
    start--;    /* index of the last sequence's lead byte */

    lead = (unsigned char)s[start];
    if (lead < 0x80u) need = 1;
    else if ((lead & 0xE0u) == 0xC0u) need = 2;
    else if ((lead & 0xF0u) == 0xE0u) need = 3;
    else if ((lead & 0xF8u) == 0xF0u) need = 4;
    else return; /* malformed lead; the decoder substitutes and moves on */

    if (start + need > n)
        s[start] = '\0';
}

int ps2ui_slot_set(ps2ui_ctx *ctx, const char *name, const char *text)
{
    uint32_t i = slot_index_by_name(ctx, name);
    size_t cap;
    if (i == PS2UI_NONE)
        return 0;
    if (text == NULL) {
        /* Revert to the baked placeholder. "" is a different request:
         * it blanks the slot (backlog B12). */
        ctx->slot_text[i][0] = '\0';
        ctx->slot_is_set[i] = 0;
        return 1;
    }
    cap = ctx->slots[i].capacity;
    if (cap >= PS2UI_SLOT_BUFSZ)
        cap = PS2UI_SLOT_BUFSZ - 1;
    strncpy(ctx->slot_text[i], text, cap);
    ctx->slot_text[i][cap] = '\0';
    utf8_trim_partial(ctx->slot_text[i]);
    ctx->slot_is_set[i] = 1;
    return 1;
}

const char *ps2ui_slot_get(const ps2ui_ctx *ctx, const char *name)
{
    uint32_t i = slot_index_by_name(ctx, name);
    if (i == PS2UI_NONE)
        return NULL;
    return slot_current_text(ctx, i);
}

/* ------------------------------------------------------------- screens */

int ps2ui_screen_set(ps2ui_ctx *ctx, const char *name)
{
    uint32_t i;
    if (name == NULL)
        return 0;
    for (i = 0; i < ctx->hdr->n_screen; i++) {
        const char *n = (const char *)(ctx->blob + ctx->screen_table[i].name_off);
        if (strcmp(n, name) == 0) {
            if (i != ctx->screen) {
                ctx->screen_focus[ctx->screen] = ctx->focus;
                ctx->screen = (uint16_t)i;
                ctx->focus = ctx->screen_focus[i];
            }
            return 1;
        }
    }
    return 0;
}

const char *ps2ui_screen_name(const ps2ui_ctx *ctx)
{
    return (const char *)(ctx->blob + ctx->screen_table[ctx->screen].name_off);
}

uint32_t ps2ui_pixel_aspect_x1000(const ps2ui_ctx *ctx)
{
    /* PAR = displayAspect / (w / h), scaled by 1000 with no floats. */
    uint32_t num = ctx->hdr->display_aspect_num;
    uint32_t den = ctx->hdr->display_aspect_den;
    if (den == 0 || ctx->hdr->canvas_w == 0)
        return 1000;
    return (num * (uint32_t)ctx->hdr->canvas_h * 1000u)
         / (den * (uint32_t)ctx->hdr->canvas_w);
}

/* -------------------------------------------------------------- focus */

int ps2ui_move(ps2ui_ctx *ctx, ps2ui_dir dir)
{
    const ps2ui_focus_node *n;
    uint16_t next = PS2UI_NONE;

    if (ctx->focus == PS2UI_NONE || ctx->focus >= ctx->hdr->n_focus)
        return 0;
    n = &ctx->focus_nodes[ctx->focus];
    switch (dir) {
    case PS2UI_UP:    next = n->up;    break;
    case PS2UI_DOWN:  next = n->down;  break;
    case PS2UI_LEFT:  next = n->left;  break;
    case PS2UI_RIGHT: next = n->right; break;
    }
    /* Walk past hidden nodes in the same direction rather than landing
     * on something invisible. Bounded by the node count: a graph with a
     * cycle of hidden nodes must terminate, not spin. */
    {
        uint32_t guard = ctx->hdr->n_focus + 1;
        while (next != PS2UI_NONE && node_hidden(ctx, next) && guard--) {
            const ps2ui_focus_node *h = &ctx->focus_nodes[next];
            uint16_t step = PS2UI_NONE;
            switch (dir) {
            case PS2UI_UP:    step = h->up;    break;
            case PS2UI_DOWN:  step = h->down;  break;
            case PS2UI_LEFT:  step = h->left;  break;
            case PS2UI_RIGHT: step = h->right; break;
            }
            if (step == next) break;
            next = step;
        }
        if (next != PS2UI_NONE && node_hidden(ctx, next))
            return 0;   /* every candidate in this direction is hidden */
    }
    if (next == PS2UI_NONE || next == ctx->focus)
        return 0;
    ctx->focus = next;
    return 1;
}

/* ---------------------------------------------------------- visibility */

/* Scoped to the current screen's focus range, not the whole blob.
 * Names are only unique per screen — the memcard example has nav-games
 * on both — and data-repeat makes two screens each using row-{i} the
 * natural thing to write rather than an accident. A blob-global scan
 * finds the first match anywhere, so hiding "row-2" from screen two
 * would silently blank screen one's and report success.
 *
 * Linear: focus_count is a screenful of widgets, not a database, and
 * this runs on a button press, not per frame. */
static uint16_t focus_index_by_name(const ps2ui_ctx *ctx, const char *name)
{
    const ps2ui_screen_entry *scr;
    uint32_t i, lo, hi;
    if (name == NULL || ctx->screen >= ctx->hdr->n_screen)
        return PS2UI_NONE;
    scr = &ctx->screen_table[ctx->screen];
    lo = scr->focus_first;
    hi = lo + scr->focus_count;
    for (i = lo; i < hi && i < ctx->hdr->n_focus; i++) {
        const char *n = (const char *)(ctx->blob + ctx->focus_nodes[i].name_off);
        if (strcmp(n, name) == 0)
            return (uint16_t)i;
    }
    return PS2UI_NONE;
}

int ps2ui_visible_set(ps2ui_ctx *ctx, const char *name, int visible)
{
    uint16_t idx;
    if (!ctx)
        return 0;
    idx = focus_index_by_name(ctx, name);
    if (idx == PS2UI_NONE || idx >= PS2UI_MAX_HIDEABLE)
        return 0;
    if (visible)
        ctx->hidden[idx >> 5] &= ~(1u << (idx & 31u));
    else
        ctx->hidden[idx >> 5] |= 1u << (idx & 31u);
    return 1;
}

int ps2ui_visible_get(const ps2ui_ctx *ctx, const char *name)
{
    uint16_t idx;
    if (!ctx)
        return 0;
    idx = focus_index_by_name(ctx, name);
    if (idx == PS2UI_NONE)
        return 0;
    return node_hidden(ctx, idx) ? 0 : 1;
}

void ps2ui_visible_reset(ps2ui_ctx *ctx)
{
    if (ctx)
        memset(ctx->hidden, 0, sizeof ctx->hidden);
}

const char *ps2ui_focus_name(const ps2ui_ctx *ctx)
{
    if (ctx->focus == PS2UI_NONE || ctx->focus >= ctx->hdr->n_focus)
        return NULL;
    return (const char *)(ctx->blob + ctx->focus_nodes[ctx->focus].name_off);
}

int ps2ui_focus_set(ps2ui_ctx *ctx, const char *name)
{
    uint16_t idx = focus_index_by_name(ctx, name);
    if (idx == PS2UI_NONE)
        return 0;
    ctx->focus = idx;
    return 1;
}

/* --------------------------------------------------------- list window */

/* Row focus names are built here rather than by the app, so the naming
 * convention lives in exactly one place. No snprintf: the runtime is
 * string.h only, and the index is bounded by PS2UI_MAX_LIST_ROWS. */
static void list_row_name(const ps2ui_list *list, uint16_t row,
                          char *out, size_t cap)
{
    size_t n = 0;
    char digits[6];
    int d = 0;
    unsigned v = row;

    if (list->prefix) {
        while (list->prefix[n] && n + 1 < cap) { out[n] = list->prefix[n]; n++; }
    }
    do { digits[d++] = (char)('0' + (v % 10u)); v /= 10u; } while (v && d < 6);
    while (d > 0 && n + 1 < cap) out[n++] = digits[--d];
    out[n] = '\0';
}

/* Slide the window the minimum distance that puts sel back on screen.
 * Minimum, not centred: a list that recentres on every step makes the
 * whole screen move when the user asked one row to. */
static void list_scroll_into_view(ps2ui_list *list)
{
    if (list->rows == 0 || list->count == 0) { list->top = 0; return; }
    if (list->sel < list->top)
        list->top = list->sel;
    else if ((uint32_t)list->sel >= (uint32_t)list->top + list->rows)
        list->top = (uint16_t)(list->sel - list->rows + 1);

    /* Never leave blank rows above real items when the tail is in view. */
    if (list->count > list->rows) {
        uint16_t max_top = (uint16_t)(list->count - list->rows);
        if (list->top > max_top) list->top = max_top;
    } else {
        list->top = 0;
    }
}

static int list_sync_focus(ps2ui_ctx *ctx, const ps2ui_list *list);

void ps2ui_list_init(ps2ui_list *list, const char *prefix, uint16_t rows)
{
    if (!list) return;
    list->prefix = prefix;
    list->rows = rows;
    list->count = 0;
    list->top = 0;
    list->sel = 0;
}

void ps2ui_list_set_count(ps2ui_ctx *ctx, ps2ui_list *list, uint16_t count)
{
    if (!list) return;
    list->count = count;
    if (count == 0) { list->sel = 0; list->top = 0; return; }
    if (list->sel >= count) list->sel = (uint16_t)(count - 1);
    list_scroll_into_view(list);
    list_sync_focus(ctx, list);
}

int ps2ui_list_item_at(const ps2ui_list *list, uint16_t row)
{
    uint32_t item;
    if (!list || row >= list->rows) return -1;
    item = (uint32_t)list->top + row;
    if (item >= list->count) return -1;
    return (int)item;
}

int ps2ui_list_selected_row(const ps2ui_list *list)
{
    int row;
    if (!list || list->count == 0 || list->rows == 0) return -1;
    row = (int)list->sel - (int)list->top;
    /* Agree with item_at rather than reporting a row that cannot
     * exist: with rows == 0 this used to return sel while item_at(0)
     * correctly returned -1. */
    return (row >= 0 && row < (int)list->rows) ? row : -1;
}

/* Focus follows the selection. Failing to find the row's node is not
 * fatal — the indices are still correct and the app can still fill the
 * slots — but it means the prefix does not match the baked names, which
 * is worth surfacing as a 0 return rather than silently doing nothing. */
static int list_sync_focus(ps2ui_ctx *ctx, const ps2ui_list *list)
{
    char name[PS2UI_LIST_NAME_MAX];
    int row = ps2ui_list_selected_row(list);
    if (!ctx || row < 0) return 0;
    list_row_name(list, (uint16_t)row, name, sizeof name);
    return ps2ui_focus_set(ctx, name);
}

int ps2ui_list_select(ps2ui_ctx *ctx, ps2ui_list *list, uint16_t item)
{
    uint16_t old_sel, old_top;
    if (!list || list->count == 0) return 0;
    old_sel = list->sel;
    old_top = list->top;
    list->sel = item >= list->count ? (uint16_t)(list->count - 1) : item;
    list_scroll_into_view(list);
    list_sync_focus(ctx, list);
    return (list->sel != old_sel || list->top != old_top) ? 1 : 0;
}

int ps2ui_list_move(ps2ui_ctx *ctx, ps2ui_list *list, int delta)
{
    long target;
    if (!list || list->count == 0) return 0;
    target = (long)list->sel + delta;
    if (target < 0) target = 0;
    if (target > (long)list->count - 1) target = (long)list->count - 1;
    return ps2ui_list_select(ctx, list, (uint16_t)target);
}

void ps2ui_list_apply_visibility(ps2ui_ctx *ctx, const ps2ui_list *list)
{
    char name[PS2UI_LIST_NAME_MAX];
    uint16_t r;
    if (!ctx || !list)
        return;
    for (r = 0; r < list->rows; r++) {
        list_row_name(list, r, name, sizeof name);
        ps2ui_visible_set(ctx, name, ps2ui_list_item_at(list, r) >= 0);
    }
}
