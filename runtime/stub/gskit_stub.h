/* The recording half of the host test double.
 *
 * TYPES AND PROTOTYPES COME FROM THE REAL GSKIT HEADERS (vendored
 * under runtime/vendor/gsKit, verbatim from ps2dev/gsKit@43122eb).
 * This file adds only what gsKit does not have: the ledger the tests
 * assert against, and the reset helpers. The hand-written model this
 * replaces shipped two struct-shape bugs in one day -- an invented
 * GSTEXTURE::Function and a missing GSTEXTURE::TBW -- and every host
 * check stayed green both times, because the stub was the only gsKit
 * the checks could see. Nothing here may re-declare a gsKit type.
 *
 * The point is still not to emulate the GS -- the Python previewer
 * does the visual verification. gskit_stub.c gives the real prototypes
 * recording bodies so the tests can count and bound-check every
 * primitive, flush, and bind the runtime would send. */
#ifndef GSKIT_STUB_H
#define GSKIT_STUB_H

#include <gsKit.h>
#include <kernel.h>

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
    int n_invalidates;  /* residency dropped by hand -- what tex_set does
                         * so a swapped buffer is actually re-read */
    int n_transfers;    /* pixel transfers only; the "uploaded once" count */
    /* Uploads whose pixel data or CLUT was not fully covered by a
     * preceding writeback. Any value but zero is a console bug. */
    int n_uploads_unflushed;
} stub_state;

extern stub_state g_stub;

void stub_reset(void);
void stub_reset_keep_tm(void);

#endif /* GSKIT_STUB_H */
