#include "gskit_stub.h"

#include <string.h>

stub_state g_stub;

void stub_reset(void)
{
    memset(&g_stub, 0, sizeof g_stub);
}

u32 gsKit_texture_size(u32 width, u32 height, u32 psm)
{
    /* Close enough for the fake allocator: bytes, page-rounded. */
    u32 bpp = (psm == GS_PSM_T8) ? 1 : 4;
    u32 size = width * height * bpp;
    return (size + 8191u) & ~8191u;
}

u32 gsKit_vram_alloc(GSGLOBAL *gs, u32 size, u32 type)
{
    u32 at = gs->CurrentPointer;
    (void)type;
    if (at + size > 4u * 1024u * 1024u) /* the GS really has 4 MB */
        return GSKIT_ALLOC_ERROR;
    gs->CurrentPointer += size;
    g_stub.vram_allocated = gs->CurrentPointer;
    return at;
}

void gsKit_texture_upload(GSGLOBAL *gs, GSTEXTURE *tex)
{
    (void)gs; (void)tex;
    g_stub.n_uploads++;
}

void gsKit_set_scissor(GSGLOBAL *gs, u64 scissor)
{
    (void)gs;
    g_stub.n_scissor_sets++;
    g_stub.last_scissor = scissor;
}

static void record(int textured, const GSTEXTURE *tex,
                   float x1, float y1, float x2, float y2,
                   float u1, float v1, float u2, float v2, u64 color)
{
    stub_prim *p;
    if (g_stub.n_prims >= STUB_MAX_PRIMS)
        return;
    p = &g_stub.prims[g_stub.n_prims++];
    p->textured = textured;
    p->tex = tex;
    p->x1 = x1; p->y1 = y1; p->x2 = x2; p->y2 = y2;
    p->u1 = u1; p->v1 = v1; p->u2 = u2; p->v2 = v2;
    p->color = color;
}

void gsKit_prim_sprite(GSGLOBAL *gs, float x1, float y1, float x2, float y2,
                       int z, u64 color)
{
    (void)gs; (void)z;
    record(0, 0, x1, y1, x2, y2, 0, 0, 0, 0, color);
}

void gsKit_prim_sprite_texture(GSGLOBAL *gs, GSTEXTURE *tex,
                               float x1, float y1, float u1, float v1,
                               float x2, float y2, float u2, float v2,
                               int z, u64 color)
{
    (void)gs; (void)z;
    record(1, tex, x1, y1, x2, y2, u1, v1, u2, v2, color);
}
