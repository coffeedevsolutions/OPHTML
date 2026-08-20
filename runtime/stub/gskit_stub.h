/* A stub of the slice of gsKit that ps2ui.c and the sample use, for
 * host-side tests and `make syntax-check`.
 *
 * The point is not to emulate the GS — the Python previewer does the
 * visual verification. The stub exists so the real ps2ui.c compiles
 * -Werror against the same call signatures gsKit publishes, and so the
 * test can count and bound-check every primitive the runtime would
 * send. Signatures follow gsKit as of 2024 (GSTEXTURE::Function
 * present; build with -DPS2UI_GSKIT_HAS_FUNCTION=0 to mimic older
 * releases). */
#ifndef GSKIT_STUB_H
#define GSKIT_STUB_H

#include <stdint.h>

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

#define GS_TFX_MODULATE 0
#define GS_TFX_DECAL    1

#define GSKIT_ALLOC_USERBUFFER 1
#define GSKIT_ALLOC_ERROR      0xFFFFFFFFu

#define GS_SETREG_RGBAQ(r, g, b, a, q) \
    ((u64)(r) | ((u64)(g) << 8) | ((u64)(b) << 16) | ((u64)(a) << 24) | ((u64)(q) << 32))
#define GS_SETREG_SCISSOR(x0, x1, y0, y1) \
    ((u64)(x0) | ((u64)(x1) << 16) | ((u64)(y0) << 32) | ((u64)(y1) << 48))

typedef struct GSTEXTURE {
    u32  Width, Height;
    u32  PSM, ClutPSM;
    u32 *Mem;
    u32 *Clut;
    u32  Vram, VramClut;
    u32  Filter;
    u32  Function; /* recent gsKit only — the whole reason the stub tracks it */
} GSTEXTURE;

typedef struct GSGLOBAL {
    int Width, Height;
    u32 CurrentPointer; /* fake VRAM allocator cursor */
    /* Set by the sample during init. Declared so main.c type-checks on
     * the host; nothing here reads them. */
    int PSM, PSMZ, DoubleBuffering, ZBuffering, PrimAlphaEnable;
} GSGLOBAL;

/* ---- stub bookkeeping the test asserts against ---- */

typedef struct stub_prim {
    int   textured;
    float x1, y1, x2, y2;
    float u1, v1, u2, v2;
    u64   color;
    const GSTEXTURE *tex;
} stub_prim;

#define STUB_MAX_PRIMS 4096

typedef struct stub_state {
    stub_prim prims[STUB_MAX_PRIMS];
    int n_prims;
    int n_uploads;
    int n_scissor_sets;
    u64 last_scissor;
    u32 vram_allocated;
} stub_state;

extern stub_state g_stub;

void stub_reset(void);

u32  gsKit_vram_alloc(GSGLOBAL *gs, u32 size, u32 type);
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
