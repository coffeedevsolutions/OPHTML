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

/* Say which arm was taken, in the build log.
 *
 * The autoselect above is silent, and its two outcomes differ in what
 * reaches a screen: the fallback renders text and nine-patches DECAL,
 * untinted, on a toolchain nobody inspected. A build that quietly chose
 * it looks exactly like a build that chose MODULATE until a console is
 * in front of you -- which is the shape of check this project keeps
 * digging out of itself. Reporting costs one line and makes the ELF's
 * provenance readable from CI. */
#if !defined(PS2UI_HOST_TEST)
#if PS2UI_GSKIT_HAS_FUNCTION
#pragma message "ps2ui: GSTEXTURE::Function present - text uses GS_TFX_MODULATE"
#else
#pragma message "ps2ui: GSTEXTURE::Function ABSENT - text renders untinted (DECAL fallback)"
#endif
#endif

/* The autoselect above keys off the MACRO to decide whether the FIELD
 * exists, and those are two different facts. A toolchain can ship the
 * field without the GS_TFX_* names -- and the ps2dev container does not
 * define GS_TFX_MODULATE at all, so every ELF this project has ever
 * built took the fallback silently.
 *
 * Forcing PS2UI_GSKIT_HAS_FUNCTION=1 on such a toolchain used to fail
 * to compile for want of a name, which made the two facts impossible to
 * separate by experiment. The value is not a gsKit invention to look
 * up: TEX0.TFX is a GS register field and 0 is MODULATE, straight from
 * the hardware manual. Supplying it here decouples "can I set the
 * field" from "is the macro spelled". */
#if PS2UI_GSKIT_HAS_FUNCTION && !defined(GS_TFX_MODULATE)
#define GS_TFX_MODULATE 0   /* TEX0.TFX: 0=MODULATE 1=DECAL 2=HIGHLIGHT */
#endif

/* ---- on-disk layout (little-endian, matches packages/baker/uib.py) ---- */

#define PS2UI_MAGIC   0x31424955u /* "UIB1" */
#define PS2UI_VERSION 5

/* Feature bits. Unknown bits in a file are a load error — a blob that
 * needs a capability this runtime lacks must fail loudly, not render
 * subtly wrong. */
#define PS2UI_FEAT_DYNAMIC_TEXT (1u << 0)
#define PS2UI_FEAT_KERNING      (1u << 1)
#define PS2UI_FEAT_SLOT_SPACING (1u << 2)
#define PS2UI_FEAT_KNOWN     (PS2UI_FEAT_DYNAMIC_TEXT | PS2UI_FEAT_KERNING | PS2UI_FEAT_SLOT_SPACING)

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
    /* The aspect the panel shows the framebuffer at, as an exact ratio.
     * The GS framebuffer is not square-pixel here even at 4:3, and PS2
     * widescreen is anamorphic: the same 640x448 grid stretched. Your
     * app sets the video mode; this says what the UI was authored for
     * so a mismatch is detectable rather than merely ugly. */
    uint16_t display_aspect_num, display_aspect_den;
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
    uint16_t kern_count;         /* 0 unless PS2UI_FEAT_KERNING        */
    uint16_t pad0;
    uint32_t kerns_off;          /* ps2ui_kern[] in blob, pair-sorted  */
} ps2ui_font_entry;

/* One ordered pair's adjustment, already resolved to pixels at this
 * font's size: the EE is not going to divide by 1000 per glyph pair.
 * Pairs that round to zero are not stored, so a UI whose text is too
 * small to kern carries no table at all. */
typedef struct ps2ui_kern {
    uint32_t prev, cur;          /* the ordered codepoint pair         */
    int16_t  amount;             /* px, negative in almost every case  */
    uint16_t pad0;
} ps2ui_kern;

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
    /* Was pad (always zero) until feature bit 2: CSS letter-spacing in
     * px, applied by the pen at every glyph junction alongside the
     * kern. Zero means what the zeros always meant. */
    int16_t  letter_spacing;
} ps2ui_slot_entry;

typedef enum ps2ui_dir { PS2UI_UP, PS2UI_DOWN, PS2UI_LEFT, PS2UI_RIGHT } ps2ui_dir;

/* ---------------------------------- context ---------------------------- */

#define PS2UI_MAX_SCISSOR_DEPTH 8
#define PS2UI_MAX_TEXTURES      32
#define PS2UI_MAX_SLOTS         16
#define PS2UI_SLOT_BUFSZ        96  /* bytes incl. NUL, per slot */
#define PS2UI_MAX_SCREENS       8
/* Longest row focus name a list can build: prefix + index + NUL. Only
 * a stack buffer in ps2ui_list_move, not a table bound, so it costs
 * nothing to a UI that never uses a list. */
#define PS2UI_LIST_NAME_MAX     64
/* Focus nodes whose visibility can be toggled at runtime (backlog F21),
 * one bit each. Not a load-time cap: a blob with more focusables loads
 * and renders fine, it just cannot hide the ones past this index, and
 * ps2ui_visible_set says so by returning 0. Sized to match the
 * data-repeat ceiling, since a long list is what needs this. */
#define PS2UI_MAX_HIDEABLE      256

/* Per-frame render telemetry, reset at the top of every ps2ui_render
 * and complete when it returns. Counters only: the runtime does no
 * timing (the EE cycle counter is the app's to read, and host tests
 * have no EE) and no I/O (where a log goes — UDP, USB, screen, PCSX2's
 * console capture — is the app's decision, same split as slot data).
 * The cost is one increment per command record walked plus one per
 * primitive drawn -- proportional to the frame, not to the API. */
typedef struct ps2ui_stats {
    uint32_t cmds;             /* command records walked                */
    uint32_t prims;            /* primitives actually submitted to gsKit */
    uint32_t skipped_hidden;   /* command records skipped by runtime
                                * visibility -- records only; a hidden
                                * row's suppressed slot shows up in
                                * slots_hidden, not here               */
    uint32_t slot_glyphs;      /* glyph quads composed by the slot pen  */
    uint32_t slots_hidden;     /* slots suppressed by runtime visibility */
    uint32_t scissor_overflow; /* SCISSOR_PUSHes refused for want of
                                * stack; nonzero means a blob deeper
                                * than PS2UI_MAX_SCISSOR_DEPTH slipped
                                * past the baker somehow               */
} ps2ui_stats;

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
    /* Runtime visibility, one bit per focus node, 0 = shown. Zeroed by
     * ps2ui_load, so a blob that never calls the API behaves exactly as
     * before and pays 32 bytes of context. */
    uint32_t  hidden[(PS2UI_MAX_HIDEABLE + 31) / 32];
    /* Filled by ps2ui_render; see ps2ui_stats. */
    ps2ui_stats stats;
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
 * Returns 1 on success, 0 if the *current screen* has no node with that
 * name. Scoped to the screen deliberately: names are only unique within
 * one, and data-repeat makes two screens each using row-{i} a natural
 * thing to write rather than an accident. Use this to restore focus
 * after a screen swap or to implement shortcuts. */
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

/* Pixel aspect ratio the blob was authored for, x1000 to stay integral
 * (933 = 4:3 at 640x448, 1244 = 16:9). Above 1000 means pixels draw
 * wider than tall. Useful for asserting your video setup matches the
 * blob; ps2ui itself draws in framebuffer pixels regardless. */
uint32_t ps2ui_pixel_aspect_x1000(const ps2ui_ctx *ctx);

/* -------------------------------------------------------- visibility */

/* Hide or show a focusable subtree at runtime (backlog F21).
 *
 * `display: none` is compile-time: it deletes the box before layout, so
 * the geometry closes up around it. This is the other thing, and the
 * only one a fixed command list can offer — the row keeps its space and
 * stops being painted. Nothing reflows, because nothing can.
 *
 * The unit is a focus node, because that is the only grouping the
 * command list already carries. In practice that is the same unit you
 * want: a list row, a button, a panel the app can turn off. Text inside
 * the subtree goes with it, slots included.
 *
 * A hidden node is also skipped by ps2ui_move, so the D-pad cannot land
 * on something invisible. That is the half an app reimplementing this
 * with blank strings does not get.
 *
 * Scoped to the current screen, like ps2ui_focus_set: hiding "row-2"
 * must not blank another screen's identically-named row.
 *
 * Returns 1 on success, 0 if the current screen has no node with that
 * name or its index is past PS2UI_MAX_HIDEABLE. Note the index is
 * global, so with several screens the later ones eat into the same
 * ceiling. */
int ps2ui_visible_set(ps2ui_ctx *ctx, const char *name, int visible);

/* 1 if shown (the default), 0 if hidden or unknown. */
int ps2ui_visible_get(const ps2ui_ctx *ctx, const char *name);

/* Show every node again. Cheap enough to call on a screen change. */
void ps2ui_visible_reset(ps2ui_ctx *ctx);

/* ------------------------------------------------------- list window */

/* Scrolling over more items than the blob has rows (backlog F6).
 *
 * A `data-repeat` template bakes a fixed number of rows. A launcher has
 * a variable number of things to show. This is the arithmetic between
 * the two, and it lives here because every app gets the same edge cases
 * wrong: a selection that walks off the end, a count smaller than the
 * rows, an empty list, and keeping the selection on screen while the
 * window moves under it.
 *
 * ps2ui owns the indices and where focus sits. The app owns the data:
 * after any move, fill row r from item (top + r) with ps2ui_slot_set,
 * and blank the rows past the end.
 *
 * No blob support is involved. A list is a view over rows that are
 * already baked, so this needs no format version and costs nothing to
 * a UI that does not use it. */
typedef struct {
    const char *prefix; /* focus-name prefix; row r is "<prefix>r" */
    uint16_t rows;      /* baked rows, from the data-repeat count */
    uint16_t count;     /* items the app has */
    uint16_t top;       /* item index shown in row 0 */
    uint16_t sel;       /* selected item index */
} ps2ui_list;

/* Bind a list to `rows` baked rows whose focus names are prefix+index
 * ("row-" gives row-0, row-1, ...). Starts empty; call
 * ps2ui_list_set_count next. */
void ps2ui_list_init(ps2ui_list *list, const char *prefix, uint16_t rows);

/* Tell the list how many items exist. Clamps the selection and the
 * window into range, so shrinking a list under a selection sitting past
 * the new end lands somewhere valid rather than off the end — and moves
 * focus with it. Takes ctx for that reason: an index that moved without
 * the highlight following is how the accept button ends up firing on a
 * row the user cannot see selected. Pass NULL to move indices only. */
void ps2ui_list_set_count(ps2ui_ctx *ctx, ps2ui_list *list, uint16_t count);

/* Move the selection by `delta` items (-1 up, +1 down, +/-rows for a
 * page). Clamps at both ends — a list does not wrap, because walking
 * off the end of a hundred saves and arriving at the top is disorienting
 * in a way a six-tile grid never is. Scrolls the window to keep the
 * selection visible, moves focus to the row the selection now occupies,
 * and returns 1 if anything changed. */
int ps2ui_list_move(ps2ui_ctx *ctx, ps2ui_list *list, int delta);

/* Select an absolute item index, scrolling to it. Returns 1 if
 * anything changed. Out-of-range indices clamp. */
int ps2ui_list_select(ps2ui_ctx *ctx, ps2ui_list *list, uint16_t item);

/* The item index displayed in row `row`, or -1 when that row is past
 * the end of the data and should be blanked. This is the loop the app
 * runs after every move to refill the slots. */
int ps2ui_list_item_at(const ps2ui_list *list, uint16_t row);

/* Which baked row the selection currently occupies (0..rows-1), or -1
 * for an empty list. */
int ps2ui_list_selected_row(const ps2ui_list *list);

/* Hide the rows past the end of the data and show the rest.
 * Blanking a row's text leaves its panel and border drawn, which reads
 * as an empty row rather than as no row; this is what makes a short list
 * look short. Call it after set_count and after any move. Needs the row
 * focus names to match the list's prefix. */
void ps2ui_list_apply_visibility(ps2ui_ctx *ctx, const ps2ui_list *list);

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
