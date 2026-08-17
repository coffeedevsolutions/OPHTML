/* ps2ui runtime implementation. C99, no allocation, no libc beyond
 * string.h/stddef.h. See ps2ui.h for the contract. */

#include "ps2ui.h"

#include <string.h>

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
    if (ctx->hdr->n_tex > PS2UI_MAX_TEXTURES)
        return PS2UI_ERR_TOO_MANY;

    {
        const ps2ui_header *h = ctx->hdr;
        uint64_t need_tex   = (uint64_t)h->off_tex   + (uint64_t)h->n_tex   * sizeof(ps2ui_tex_entry);
        uint64_t need_clut  = (uint64_t)h->off_clut  + (uint64_t)h->n_clut  * sizeof(ps2ui_clut_entry);
        uint64_t need_cmd   = (uint64_t)h->off_cmd   + (uint64_t)h->n_cmd   * sizeof(ps2ui_cmd);
        uint64_t need_focus = (uint64_t)h->off_focus + (uint64_t)h->n_focus * sizeof(ps2ui_focus_node);
        uint64_t need_blob  = (uint64_t)h->off_blob  + h->blob_len;
        if (need_tex > size || need_clut > size || need_cmd > size
            || need_focus > size || need_blob > size)
            return PS2UI_ERR_TRUNCATED;
    }

    ctx->tex         = (const ps2ui_tex_entry *)(ctx->data + ctx->hdr->off_tex);
    ctx->clut        = (const ps2ui_clut_entry *)(ctx->data + ctx->hdr->off_clut);
    ctx->cmd         = (const ps2ui_cmd *)(ctx->data + ctx->hdr->off_cmd);
    ctx->focus_nodes = (const ps2ui_focus_node *)(ctx->data + ctx->hdr->off_focus);
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

    ctx->focus = ctx->hdr->initial_focus;
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

/* CLUTs are stored linearly in the file (readable by any tool); the GS
 * wants CSM1 storage order on upload. Permute into `out` (256*4 bytes). */
static void permute_clut(const uint8_t *linear, uint16_t ncolors, uint8_t *out)
{
    uint32_t i;
    memset(out, 0, 256 * 4);
    for (i = 0; i < ncolors && i < 256; i++) {
        uint32_t j = ps2ui_clut_csm1(i);
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
#if PS2UI_GSKIT_HAS_FUNCTION
        /* Modulate: texel x vertex color, so one white glyph atlas
         * serves every text color. Older gsKit lacks the field; the
         * fallback renders text untinted (see docs/architecture.md). */
        g->Function = GS_TFX_MODULATE;
#endif
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
    uint32_t i;

    stack[0].x0 = 0;
    stack[0].y0 = 0;
    stack[0].x1 = ctx->hdr->canvas_w;
    stack[0].y1 = ctx->hdr->canvas_h;
    apply_scissor(gs, &stack[0]);

    for (i = 0; i < ctx->hdr->n_cmd; i++) {
        const ps2ui_cmd *c = &ctx->cmd[i];

        if (c->op == PS2UI_OP_SCISSOR_PUSH) {
            scissor_rect r, *top = &stack[depth];
            if (depth + 1 >= PS2UI_MAX_SCISSOR_DEPTH)
                continue; /* baker never emits this deep; fail soft */
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
            if (depth > 0)
                depth--;
            apply_scissor(gs, &stack[depth]);
            continue;
        }
        if (!cmd_visible(c, ctx->focus))
            continue;

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
    /* The baker guarantees balance; restore full-canvas scissor anyway
     * so a malformed blob cannot poison the next frame. */
    apply_scissor(gs, &stack[0]);
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
    if (next == PS2UI_NONE || next == ctx->focus)
        return 0;
    ctx->focus = next;
    return 1;
}

const char *ps2ui_focus_name(const ps2ui_ctx *ctx)
{
    if (ctx->focus == PS2UI_NONE || ctx->focus >= ctx->hdr->n_focus)
        return NULL;
    return (const char *)(ctx->blob + ctx->focus_nodes[ctx->focus].name_off);
}
