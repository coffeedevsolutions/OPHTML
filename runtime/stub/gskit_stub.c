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

void SyncDCache(void *start, void *end)
{
    if (g_stub.n_flushes < STUB_MAX_FLUSHES) {
        g_stub.flushes[g_stub.n_flushes].start = start;
        g_stub.flushes[g_stub.n_flushes].end   = end;
        g_stub.n_flushes++;
    }
}

/* Is [p, p+len) entirely inside one range already written back? A
 * partial flush is not a flush: the GS reads the whole buffer. */
static int stub_flushed(const void *p, size_t len)
{
    const unsigned char *a = (const unsigned char *)p;
    int i;
    for (i = 0; i < g_stub.n_flushes; i++) {
        const unsigned char *s = (const unsigned char *)g_stub.flushes[i].start;
        const unsigned char *e = (const unsigned char *)g_stub.flushes[i].end;
        if (a >= s && a + len <= e)
            return 1;
    }
    return 0;
}

/* gsKit_texture_upload's first act, mirrored from gsMisc.c. It
 * OVERWRITES whatever the caller put in TBW, which is why ps2ui does
 * not set it: doing so is dead code, and a stub that let a caller's
 * value survive would make dead code look load-bearing. Note the T8
 * alignment is 128, not 64 -- ceil(width/64) is not what gsKit
 * computes for an indexed texture. */
static void stub_setup_tbw(GSTEXTURE *tex)
{
    u32 align = (tex->PSM == GS_PSM_T8) ? 128u : 64u;
    u32 w = (tex->Width + align - 1u) & ~(align - 1u);
    tex->TBW = (w / 64u) ? (w / 64u) : 1u;
}

void gsKit_texture_upload(GSGLOBAL *gs, GSTEXTURE *tex)
{
    stub_setup_tbw(tex);
    /* Mirrors what gsKit's DMA actually reads: the pixel bytes, and
     * for an indexed texture the 16x16 CT32 palette beside them. */
    size_t texels = (size_t)tex->Width * tex->Height;
    size_t bytes  = (tex->PSM == GS_PSM_T8) ? texels : texels * 4;
    (void)gs;
    if (!stub_flushed(tex->Mem, bytes))
        g_stub.n_uploads_unflushed++;
    else if (tex->Clut && !stub_flushed(tex->Clut, 16 * 16 * 4))
        g_stub.n_uploads_unflushed++;
    g_stub.n_uploads++;
}

/* The manager slice, mirrored from gsTexManager.c so the fences that
 * used to watch gsKit_texture_upload watch this path instead:
 *
 *   - an unseen texture gets residency at the block cursor and its
 *     Vram/VramClut zeroed, exactly like _blockAlloc + the reset in
 *     bind (gsTexManager.c:249-257)
 *   - Vram == 0 means transfer: setup_tbw, SyncDCache over the pixel
 *     bytes, then the send -- the send is modelled as the flush ledger
 *     coverage check plus n_transfers, which keeps the "uploaded once"
 *     and "flushed before DMA" assertions alive
 *   - VramClut == 0 on an indexed texture likewise for the palette
 *     (:277-284)
 *   - a resident re-bind transfers nothing, which is what makes
 *     per-draw binding in ps2ui_render free to assert against
 *
 * Never fails, because the real one never fails -- it hangs, which is
 * why ps2ui_upload preflights. Eviction unmodelled on purpose: the
 * preflight makes it unreachable, and modelling gsKit's weight
 * heuristic here would certify a guess. */
unsigned int gsKit_TexManager_bind(GSGLOBAL *gs, GSTEXTURE *tex)
{
    size_t texels = (size_t)tex->Width * tex->Height;
    size_t bytes  = (tex->PSM == GS_PSM_T8) ? texels : texels * 4;
    u32 tsize = gsKit_texture_size(tex->Width, tex->Height, tex->PSM);
    u32 csize = tex->Clut ? gsKit_texture_size(16, 16, GS_PSM_CT32) : 0;
    unsigned int transferred = 0;
    int i, seen = -1;

    if (g_stub.tm_cursor == 0)
        g_stub.tm_cursor = gs->CurrentPointer ? gs->CurrentPointer : 16;

    g_stub.n_binds++;
    for (i = 0; i < g_stub.n_bound; i++)
        if (g_stub.bound[i] == tex) { seen = i; break; }
    if (seen < 0 && g_stub.n_bound < 64) {
        seen = g_stub.n_bound++;
        g_stub.bound[seen] = tex;
        g_stub.bound_vram[seen] = g_stub.tm_cursor;
        g_stub.tm_cursor += tsize + csize;
        tex->Vram = 0;
        tex->VramClut = 0;
    }

    if (tex->Vram == 0) {
        tex->Vram = g_stub.bound_vram[seen];
        stub_setup_tbw(tex);
        SyncDCache(tex->Mem, (u8 *)tex->Mem + tsize);
        if (!stub_flushed(tex->Mem, bytes))
            g_stub.n_uploads_unflushed++;
        g_stub.n_transfers++;
        g_stub.n_uploads++;   /* the "uploaded once" ledger, unchanged */
        transferred = 1;
    }
    if (tex->Clut && tex->VramClut == 0) {
        tex->VramClut = g_stub.bound_vram[seen] + tsize;
        SyncDCache(tex->Clut, (u8 *)tex->Clut + csize);
        if (!stub_flushed(tex->Clut, 16 * 16 * 4))
            g_stub.n_uploads_unflushed++;
        transferred = 1;
    }
    return transferred;
}

void gsKit_TexManager_invalidate(GSGLOBAL *gs, GSTEXTURE *tex)
{
    (void)gs;
    tex->Vram = 0;
    tex->VramClut = 0;
}

void gsKit_TexManager_nextFrame(GSGLOBAL *gs)
{
    (void)gs;
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

void gsKit_set_test(GSGLOBAL *gs, unsigned char preset)
{
    (void)gs; (void)preset;
}

/* The host stub records the blend mode so a test can assert the
 * runtime asserts it. Inheriting this value silently is the bug that
 * cost a bench session; leaving it unobservable here would let it
 * come back. */
u64 stub_prim_alpha = 0;
unsigned char stub_prim_alpha_set = 0;

void gsKit_set_primalpha(GSGLOBAL *gs, u64 alpha_mode, unsigned char per_pixel)
{
    (void)gs; (void)per_pixel;
    stub_prim_alpha = alpha_mode;
    stub_prim_alpha_set = 1;
}
