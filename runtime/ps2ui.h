/* ps2ui runtime — .uib loader and gsKit replay.
 *
 * The console side of the toolchain. It does four things and nothing
 * else: validate a baked blob, upload textures (applying the CSM1 CLUT
 * permutation), replay the command list filtered by focus state, and
 * walk the precomputed D-pad graph. No parsing, no layout, no
 * rasterization, no allocation beyond the caller-provided blob and one
 * GSTEXTURE array.
 *
 * Build-time switches:
 *   PS2UI_HOST_TEST           compile against runtime/stub/ instead of gsKit
 *   PS2UI_GSKIT_HAS_FUNCTION  0 for older gsKit without GSTEXTURE::Function;
 *                             text renders untinted (white) in that case
 */
#ifndef PS2UI_H
#define PS2UI_H

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#ifdef PS2UI_HOST_TEST
#include "gskit_stub.h"
#else
#include <gsKit.h>
#include <gsToolkit.h>
#endif

/* GSTEXTURE::Function (per-texture TFX) arrived in gsKit together with
 * the GS_TFX_* macros, so their presence is the detection signal: on an
 * older gsKit this autoselects the fallback, which renders text and
 * nine-patches untinted (DECAL) instead of failing the build. Define
 * PS2UI_GSKIT_HAS_FUNCTION yourself to override the detection either
 * way. First thing to eyeball on hardware — docs/bringup.md step 4. */
#ifndef PS2UI_GSKIT_HAS_FUNCTION
#ifdef GS_TFX_MODULATE
#define PS2UI_GSKIT_HAS_FUNCTION 1
#else
#define PS2UI_GSKIT_HAS_FUNCTION 0
#endif
#endif

/* ---- on-disk layout (little-endian, matches packages/baker/uib.py) ---- */

#define PS2UI_MAGIC   0x31424955u /* "UIB1" */
#define PS2UI_VERSION 3

/* Feature bits. Unknown bits in a file are a load error — a blob that
 * needs a capability this runtime lacks must fail loudly, not render
 * subtly wrong. */
#define PS2UI_FEAT_DYNAMIC_TEXT (1u << 0)
#define PS2UI_FEAT_KNOWN        PS2UI_FEAT_DYNAMIC_TEXT

#define PS2UI_OP_QUAD          0
#define PS2UI_OP_TEXQUAD       1
#define PS2UI_OP_SCISSOR_PUSH  2
#define PS2UI_OP_SCISSOR_POP   3

#define PS2UI_STATE_ALWAYS     0
#define PS2UI_STATE_UNFOCUSED  1
#define PS2UI_STATE_FOCUSED    2

#define PS2UI_TEXFMT_PSMT8     0
#define PS2UI_TEXFMT_PSMCT32   1

#define PS2UI_NONE 0xFFFFu

typedef struct ps2ui_header {
    uint32_t magic;
    uint16_t version, feature_flags;
    uint16_t canvas_w, canvas_h;
    uint16_t n_tex, n_clut;
    uint32_t n_cmd;
    uint16_t n_focus, initial_focus;
    uint32_t off_tex, off_clut, off_cmd, off_focus, off_blob, blob_len;
    uint32_t crc32;              /* whole file, this field zeroed */
    uint16_t n_font, n_slot;
    uint32_t off_font, off_slot;
    uint16_t n_screen, pad0;
    uint32_t off_screen;
} ps2ui_header;

/* A screen is a contiguous slice of the command, focus and slot
 * tables; textures, CLUTs and fonts are shared. Focus indices are
 * global, and a screen's D-pad graph links only within its range. */
typedef struct ps2ui_screen_entry {
    uint32_t name_off;           /* NUL-terminated UTF-8 in blob */
    uint32_t cmd_first, cmd_count;
    uint16_t focus_first, focus_count;
    uint16_t slot_first, slot_count;
    uint16_t initial_focus;      /* global index or PS2UI_NONE */
    uint8_t  pad0[2];
} ps2ui_screen_entry;

typedef struct ps2ui_tex_entry {
    uint8_t  format, pad0;
    uint16_t width, height;
    uint16_t clut;            /* CLUT index or PS2UI_NONE */
    uint32_t data_off, data_len; /* relative to blob */
} ps2ui_tex_entry;

typedef struct ps2ui_clut_entry {
    uint16_t ncolors, pad0;
    uint32_t data_off;
} ps2ui_clut_entry;

typedef struct ps2ui_cmd {
    uint8_t  op, state;
    uint16_t focus;           /* focus index or PS2UI_NONE */
    int16_t  x, y;
    uint16_t w, h;
    uint8_t  r, g, b, a;      /* a already in the GS 0..128 domain */
    uint16_t tex;             /* texture index or PS2UI_NONE */
    uint16_t u0, v0, u1, v1;  /* texel rect */
    uint8_t  pad0[6];
} ps2ui_cmd;

typedef struct ps2ui_focus_node {
    uint16_t id;
    uint16_t up, down, left, right; /* focus indices or PS2UI_NONE */
    uint16_t pad0;
    uint32_t name_off;              /* NUL-terminated UTF-8 in blob */
    int16_t  x, y;
    uint16_t w, h;
} ps2ui_focus_node;

/* ---- dynamic text (feature bit 0) ---- */

typedef struct ps2ui_font_entry {
    uint16_t tex;                /* PSMT8 atlas texture index          */
    uint16_t size, weight;
    uint16_t ascent;             /* px, from the metrics JSON          */
    uint16_t line_height;
    uint16_t glyph_count;
    uint32_t glyphs_off;         /* ps2ui_glyph[] in blob, cp-sorted   */
} ps2ui_font_entry;

typedef struct ps2ui_glyph {
    uint32_t codepoint;
    uint16_t u, v, w, h;
    int16_t  bearing_x, bearing_y; /* from pen x / line-box top        */
    uint16_t advance;
    uint16_t pad0;
} ps2ui_glyph;

#define PS2UI_SLOT_ALIGN_LEFT   0
#define PS2UI_SLOT_ALIGN_CENTER 1
#define PS2UI_SLOT_ALIGN_RIGHT  2
#define PS2UI_SLOT_FLAG_ELLIPSIS 1

typedef struct ps2ui_slot_entry {
    uint32_t name_off, placeholder_off; /* NUL-terminated in blob      */
    int16_t  x, text_y;          /* content-left px, glyph-box top px  */
    uint16_t w;                  /* content width px                   */
    uint16_t font;               /* font table index                   */
    uint8_t  align, flags;
    uint16_t capacity;           /* max bytes of runtime text          */
    uint16_t focus;              /* focus index or PS2UI_NONE          */
    uint8_t  color_base[4];      /* modulate domain, like every TEXQUAD */
    uint8_t  color_focus[4];
    uint8_t  pad0[2];
} ps2ui_slot_entry;

typedef enum ps2ui_dir { PS2UI_UP, PS2UI_DOWN, PS2UI_LEFT, PS2UI_RIGHT } ps2ui_dir;

/* ---------------------------------- context ---------------------------- */

#define PS2UI_MAX_SCISSOR_DEPTH 8
#define PS2UI_MAX_TEXTURES      32
#define PS2UI_MAX_SLOTS         16
#define PS2UI_SLOT_BUFSZ        96  /* bytes incl. NUL, per slot */
#define PS2UI_MAX_SCREENS       8

typedef struct ps2ui_ctx {
    const uint8_t         *data;     /* the whole .uib, caller-owned      */
    size_t                 size;
    const ps2ui_header    *hdr;
    const ps2ui_tex_entry *tex;
    const ps2ui_clut_entry*clut;
    const ps2ui_cmd       *cmd;
    const ps2ui_focus_node*focus_nodes;
    const uint8_t         *blob;

    const ps2ui_font_entry *fonts;
    const ps2ui_slot_entry *slots;
    const ps2ui_screen_entry *screen_table;

    uint16_t  screen;                /* current screen index */
    uint16_t  focus;                 /* current focus index or PS2UI_NONE */
    /* Per-screen focus memory: switching back restores where you were. */
    uint16_t  screen_focus[PS2UI_MAX_SCREENS];
    GSTEXTURE gs_tex[PS2UI_MAX_TEXTURES];
    int       uploaded;
    /* Runtime slot text. slot_is_set distinguishes "never set" (draw
     * the baked placeholder) from "set to an empty string" (draw
     * nothing). Caller-free storage keeps the no-allocation rule. */
    char      slot_text[PS2UI_MAX_SLOTS][PS2UI_SLOT_BUFSZ];
    uint8_t   slot_is_set[PS2UI_MAX_SLOTS];
} ps2ui_ctx;

/* Errors returned by ps2ui_load. */
#define PS2UI_OK              0
#define PS2UI_ERR_TRUNCATED  -1
#define PS2UI_ERR_MAGIC      -2
#define PS2UI_ERR_VERSION    -3
#define PS2UI_ERR_BOUNDS     -4
#define PS2UI_ERR_TOO_MANY   -5
#define PS2UI_ERR_CRC        -6
#define PS2UI_ERR_FEATURES   -7

/* Validate a blob and point the context into it. The blob must stay
 * alive and unmoved for the context's lifetime; nothing is copied. */
int ps2ui_load(ps2ui_ctx *ctx, const void *data, size_t size);

/* The CSM1 index permutation (swap bit 3 and bit 4). Exposed for tests;
 * mirrors clut_csm1_order in packages/baker/ps2ui_bake/gs.py. */
uint32_t ps2ui_clut_csm1(uint32_t index);

/* Allocate VRAM and upload every texture + permuted CLUT. */
int ps2ui_upload(ps2ui_ctx *ctx, GSGLOBAL *gs);

/* Replay one frame's command list for the current focus state. */
void ps2ui_render(ps2ui_ctx *ctx, GSGLOBAL *gs);

/* D-pad move. Returns 1 when focus changed. */
int ps2ui_move(ps2ui_ctx *ctx, ps2ui_dir dir);

/* Name of the focused node ("tile-okami"), or NULL. */
const char *ps2ui_focus_name(const ps2ui_ctx *ctx);

/* Set focus by node name (the id/name attribute from the HTML).
 * Returns 1 on success, 0 if no node has that name. Use this to
 * restore focus after a screen swap or to implement shortcuts. */
int ps2ui_focus_set(ps2ui_ctx *ctx, const char *name);

/* Set a dynamic-text slot's current string (UTF-8; copied, truncated
 * at the slot's baked capacity without splitting a character). NULL
 * reverts to the baked placeholder; "" blanks the slot.
 * Returns 1 on success, 0 if no slot has that name.
 * The runtime lays the glyphs out per frame from the baked glyph
 * table: advance walk + optional ellipsis, no wrapping, no allocation. */
int ps2ui_slot_set(ps2ui_ctx *ctx, const char *name, const char *text);

/* Current string of a slot (runtime text, else placeholder), or NULL. */
const char *ps2ui_slot_get(const ps2ui_ctx *ctx, const char *name);

/* Switch to a named screen. Remembers the current screen's focus and
 * restores the target's remembered focus (else its baked initial).
 * Returns 1 on success, 0 if no screen has that name. */
int ps2ui_screen_set(ps2ui_ctx *ctx, const char *name);

/* Name of the current screen ("library"), never NULL after load. */
const char *ps2ui_screen_name(const ps2ui_ctx *ctx);

/* CRC-32 (IEEE, reflected) used by the .uib integrity check; exposed
 * for tests. */
uint32_t ps2ui_crc32(const void *data, size_t len);

/* Activation convention: ps2ui owns *where* focus is, the app owns
 * *what happens* — on your accept button, switch on
 * ps2ui_focus_name(ctx). There is deliberately no callback table in
 * the blob; game logic does not belong in a UI file. */

#ifdef __cplusplus
}
#endif
#endif /* PS2UI_H */
