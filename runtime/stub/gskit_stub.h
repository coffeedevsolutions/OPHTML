/* A stub of the slice of gsKit that ps2ui.c and the sample use, for
 * host-side tests and `make syntax-check`.
 *
 * The point is not to emulate the GS — the Python previewer does the
 * visual verification. The stub exists so the real ps2ui.c compiles
 * -Werror against the same call signatures gsKit publishes, and so the
 * test can count and bound-check every primitive the runtime would
 * send. GSTEXTURE mirrors gsKit's own struct field for field -- in
 * particular it has no Function member, because gsKit has none, and a
 * stub that invented one would let the host suite certify a struct
 * shape the console does not have. */
#ifndef GSKIT_STUB_H
#define GSKIT_STUB_H

#include <stdint.h>

typedef uint8_t  u8;
typedef uint32_t u32;
typedef uint64_t u64;

#define GS_PSM_CT32 0x00
#define GS_PSM_T8   0x13
#define GS_PSMZ_16S 0x0A

#define GS_SETTING_OFF 0
#define GS_SETTING_ON  1
#define GS_ONESHOT     0
#define GS_PERSISTENT  1

#define GS_FILTER_NEAREST 0
#define GS_FILTER_LINEAR  1

#define GSKIT_ALLOC_USERBUFFER 1
#define GSKIT_ALLOC_ERROR      0xFFFFFFFFu

#define GS_SETREG_RGBAQ(r, g, b, a, q) \
    ((u64)(r) | ((u64)(g) << 8) | ((u64)(b) << 16) | ((u64)(a) << 24) | ((u64)(q) << 32))
#define GS_SETREG_SCISSOR(x0, x1, y0, y1) \
    ((u64)(x0) | ((u64)(x1) << 16) | ((u64)(y0) << 32) | ((u64)(y1) << 48))

/* Field for field with gsKit's struct gsTexture, in its order. The
 * order does not matter to a host build, but the MEMBERSHIP does: this
 * struct is the only model of gsKit anything in this tree can test
 * against, so a member missing here is a member no test can notice
 * going unwritten. TBW was missing, and it was never being set. */
typedef struct GSTEXTURE {
    u32  Width, Height;
    u8   PSM, ClutPSM;
    u32  TBW;
    u32 *Mem;
    u32 *Clut;
    u32  Vram, VramClut;
    u32  Filter;
    u8   ClutStorageMode;
    u8   Delayed;
} GSTEXTURE;

/* ps2sdk's cache writeback, modelled because ps2ui must call it and a
 * missing call is invisible on a host with a coherent cache. The EE
 * has a write-back D-cache and the GS reads main memory over DMA, so
 * CPU-written texture or CLUT bytes that are still in cache do not
 * exist as far as the GS is concerned. */
void SyncDCache(void *start, void *end);

typedef struct GSGLOBAL {
    int Width, Height;
    u32 CurrentPointer; /* fake VRAM allocator cursor */
    /* Set by the sample during init. Declared so main.c type-checks on
     * the host; nothing here reads them. */
    int PSM, PSMZ, DoubleBuffering, ZBuffering, PrimAlphaEnable;
    /* The blend state the probe now sets explicitly. Real gsKit has
     * these; until the v3 probe nothing in this tree ever wrote them,
     * which is precisely the bug they exist to rule out. */
    u64 PrimAlpha;
    unsigned char PABE;
} GSGLOBAL;

/* ALPHA register: Cv = (A - B) * C >> 7 + D. A/B/D select 0=Cs 1=Cd 2=0;
 * C selects 0=As 1=Ad 2=FIX. Mirrors gsKit's packing, values unused by a
 * syntax check but the arity has to match. */
#define GS_SETREG_ALPHA(A, B, C, D, FIX) \
    (((u64)(A) << 0) | ((u64)(B) << 2) | ((u64)(C) << 4) | \
     ((u64)(D) << 6) | ((u64)(FIX) << 32))

#define GS_ATEST_OFF 0x03
#define GS_ATEST_ON  0x04
void gsKit_set_test(GSGLOBAL *gs, unsigned char preset);
/* Setting gs->PrimAlpha does NOT emit the register -- this call does.
 * Probe v3 assigned the field, changed nothing, and that silence was
 * the clue. */
void gsKit_set_primalpha(GSGLOBAL *gs, u64 alpha_mode, unsigned char per_pixel);
extern u64 stub_prim_alpha;
extern unsigned char stub_prim_alpha_set;

/* ---- stub bookkeeping the test asserts against ---- */

typedef struct stub_prim {
    int   textured;
    float x1, y1, x2, y2;
    float u1, v1, u2, v2;
    u64   color;
    const GSTEXTURE *tex;
} stub_prim;

#define STUB_MAX_PRIMS 4096

#define STUB_MAX_FLUSHES 64

/* One recorded SyncDCache range. The host has a coherent cache, so a
 * missing writeback changes nothing here and everything on a console:
 * recording the calls is the only way a host test can see them. */
typedef struct stub_flush {
    const void *start, *end;
} stub_flush;

typedef struct stub_state {
    stub_prim prims[STUB_MAX_PRIMS];
    int n_prims;
    int n_uploads;
    int n_scissor_sets;
    u64 last_scissor;
    u32 vram_allocated;
    stub_flush flushes[STUB_MAX_FLUSHES];
    int n_flushes;
    /* TexManager model state. bound[] parallels prims/uploads: which
     * GSTEXTUREs the manager considers resident, and where. */
    const GSTEXTURE *bound[64];
    u32 bound_vram[64];
    int n_bound;
    u32 tm_cursor;      /* next free byte; 0 = not yet based on gs */
    int n_binds;        /* every bind call, resident or not */
    int n_transfers;    /* pixel transfers only; the "uploaded once" count */
    /* Uploads whose pixel data or CLUT was not fully covered by a
     * preceding writeback. Any value but zero is a console bug. */
    int n_uploads_unflushed;
} stub_state;

extern stub_state g_stub;

void stub_reset(void);

u32  gsKit_vram_alloc(GSGLOBAL *gs, u32 size, u32 type);
/* The texture manager slice ps2ui uses. The stub mirrors
 * gsTexManager.c's observable behaviour: bind allocates residency for
 * an unseen texture, transfers when Vram/VramClut are 0, does the
 * per-buffer SyncDCache before each transfer (:270, :279), and never
 * reports failure -- the real _blockAlloc spins forever on exhaustion,
 * which is exactly why ps2ui_upload preflights the budget. Eviction is
 * deliberately not modelled: the preflight makes it unreachable for
 * ps2ui's own textures, and a stub that pretended to model gsKit's
 * weight heuristic would certify guesses. */
unsigned int gsKit_TexManager_bind(GSGLOBAL *gs, GSTEXTURE *tex);
void gsKit_TexManager_invalidate(GSGLOBAL *gs, GSTEXTURE *tex);
void gsKit_TexManager_nextFrame(GSGLOBAL *gs);
u32  gsKit_texture_size(u32 width, u32 height, u32 psm);
/* Used only by the sample; the runtime never inits or flips. */
GSGLOBAL *gsKit_init_global(void);
void gsKit_init_screen(GSGLOBAL *gs);
void gsKit_mode_switch(GSGLOBAL *gs, int mode);
void gsKit_queue_exec(GSGLOBAL *gs);
void gsKit_sync_flip(GSGLOBAL *gs);
void gsKit_clear(GSGLOBAL *gs, u64 color);

void gsKit_texture_upload(GSGLOBAL *gs, GSTEXTURE *tex);
void gsKit_set_scissor(GSGLOBAL *gs, u64 scissor);
void gsKit_prim_sprite(GSGLOBAL *gs, float x1, float y1, float x2, float y2,
                       int z, u64 color);
void gsKit_prim_sprite_texture(GSGLOBAL *gs, GSTEXTURE *tex,
                               float x1, float y1, float u1, float v1,
                               float x2, float y2, float u2, float v2,
                               int z, u64 color);

#endif /* GSKIT_STUB_H */
