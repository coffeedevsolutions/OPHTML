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
 *   PS2UI_CLUT_PERMUTE        0 uploads CLUTs unpermuted (step 3's A/B arm)
 */
#ifndef PS2UI_H
#define PS2UI_H

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/* One include block for both targets, deliberately: the console gets
 * PS2SDK's real headers, the host test build gets the SAME gsKit
 * headers vendored under runtime/vendor/ plus a two-file shim for the
 * PS2SDK ones. There is no hand-written model of gsKit left to
 * diverge -- the model that existed shipped an invented GSTEXTURE
 * member and a missing one in a single day, with every host check
 * green both times. A struct-shape or prototype divergence is now a
 * compile error on the host, not a bench session. */
#include <gsKit.h>
#include <kernel.h>   /* SyncDCache */

/* ---- on-disk layout (little-endian, matches packages/baker/uib.py) ---- */

#define PS2UI_MAGIC   0x31424955u /* "UIB1" */
#define PS2UI_VERSION 6

/* Feature bits. Unknown bits in a file are a load error — a blob that
 * needs a capability this runtime lacks must fail loudly, not render
 * subtly wrong. */
#define PS2UI_FEAT_DYNAMIC_TEXT (1u << 0)
#define PS2UI_FEAT_KERNING      (1u << 1)
#define PS2UI_FEAT_SLOT_SPACING (1u << 2)
/* The blob declares at least one streamed texture, so a reader that
 * cannot fill one must refuse the file rather than draw a slot that
 * never receives texels. */
#define PS2UI_FEAT_STREAMED_TEX (1u << 3)
#define PS2UI_FEAT_KNOWN     (PS2UI_FEAT_DYNAMIC_TEXT | PS2UI_FEAT_KERNING \
                              | PS2UI_FEAT_SLOT_SPACING | PS2UI_FEAT_STREAMED_TEX)

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

/* How a texture's texels arrive.
 *
 * BAKED is every texture that has ever existed in this format: bytes in
 * the blob, DMA'd in place from the caller's file. STREAMED is a slot
 * the app fills at runtime -- cover art off a disc, HDD or network,
 * which cannot be baked because nothing at bake time knows what it is.
 * A streamed entry carries geometry and a reservation and NO texel
 * data; ps2ui_tex_set points it at the caller's buffer. */
#define PS2UI_TEXKIND_BAKED    0
#define PS2UI_TEXKIND_STREAMED 1

typedef struct ps2ui_tex_entry {
    uint8_t  format, kind;    /* kind: PS2UI_TEXKIND_*                  */
    uint16_t width, height;
    uint16_t clut;            /* CLUT index or PS2UI_NONE               */
    /* BAKED: where the texels are. STREAMED: data_off is unused and
     * data_len is the exact payload ps2ui_tex_set will demand, so the
     * app is told the number rather than deriving it and getting the
     * padding wrong. */
    uint32_t data_off, data_len;
    /* NUL-terminated name in the blob, or PS2UI_NAME_NONE. Streamed
     * slots need one to be addressable; baked textures are anonymous
     * unless the author named them. */
    uint32_t name_off;
} ps2ui_tex_entry;

/* A texture with no name. Not 0: offset 0 is a legitimate blob offset,
 * and the first string written to a blob lands there. */
#define PS2UI_NAME_NONE 0xFFFFFFFFu

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

/* Real storage, and the only remaining fixed-size thing in the
 * runtime: ps2ui_render keeps a scissor stack of this depth, so a
 * blob nesting `overflow: hidden` deeper than this draws the inner
 * subtree under the outer clip. The bake refuses it rather than
 * letting that arrive on a television. caps.py parses this value.
 *
 * PS2UI_MAX_TEXTURES, PS2UI_MAX_SLOTS and PS2UI_MAX_SCREENS used to
 * sit here as "validation limits". They are gone. Once the context
 * stopped being sized by them (v6, the arena) they bounded nothing
 * the blob's own size did not already bound, and 16 slots was a real
 * obstacle to a real UI -- the UC-3 scoping fixture measures 28 on one
 * screen. What a corrupt count must not do is decide an allocation,
 * and that guarantee now lives where the allocation is computed: see
 * arena_compute in ps2ui.c, which refuses arithmetic it cannot do
 * rather than wrapping it. */
#define PS2UI_MAX_SCISSOR_DEPTH 8
/* Longest row focus name a list can build: prefix + index + NUL. Only
 * a stack buffer in ps2ui_list_move, not a table bound, so it costs
 * nothing to a UI that never uses a list. */
#define PS2UI_LIST_NAME_MAX     64

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
    uint32_t tex_unfilled;     /* textured draws skipped because their
                                * streamed slot has no texels yet -- the
                                * ordinary state of a row that just
                                * scrolled in, not an error            */
    uint32_t vram_lost;        /* 1 when this frame skipped every
                                * textured draw because the host shrank
                                * VRAM below the uploaded footprint --
                                * see the guard in ps2ui_render        */
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

    /* Everything below points into the caller's arena, carved by
     * ps2ui_load in descending alignment order (see arena_layout in
     * ps2ui.c). The arena must outlive the context: the CLUT region is
     * a DMA source that gsKit re-reads whenever the TexManager re-binds
     * an evicted texture, which is render time, not upload time. */
    /* Per-screen focus memory: switching back restores where you were. */
    uint16_t  *screen_focus;         /* n_screen */
    GSTEXTURE *gs_tex;               /* n_tex */
    /* Permuted CLUTs, 1 KiB per PSMT8-with-palette texture, 16-aligned
     * (DMA source). Replaces the 32 KiB ceiling-sized static pool. */
    uint8_t   *clut_pool;
    int       uploaded;
    /* Runtime slot text. Each slot owns capacity+1 bytes at
     * slot_text + slot_off[i] -- the capacity the baker declared for
     * it, not a global buffer size. slot_is_set distinguishes "never
     * set" (draw the baked placeholder) from "set to an empty string"
     * (draw nothing). Caller-free storage keeps the no-allocation rule. */
    char      *slot_text;            /* sum of (capacity + 1) */
    uint32_t  *slot_off;             /* n_slot */
    uint8_t   *slot_is_set;          /* n_slot */
    /* Runtime visibility, one bit per focus node, 0 = shown, sized from
     * n_focus -- so "focusable past the hideable ceiling" is a case
     * that no longer exists rather than one reported better. */
    uint32_t  *hidden;               /* (n_focus + 31) / 32 words */
    /* The budget ps2ui_upload preflighted. ps2ui_render re-checks the
     * fit against it before any textured draw: gsKit_TexManager_bind
     * cannot report exhaustion (its allocator spins forever), so a
     * host that shrank VRAM after upload must be caught by arithmetic,
     * not by binding. Meaningful only while `uploaded` is set. */
    uint32_t  vram_need;
    /* Filled by ps2ui_render; see ps2ui_stats. */
    ps2ui_stats stats;
} ps2ui_ctx;

/* Errors returned by ps2ui_load. */
#define PS2UI_OK              0
#define PS2UI_ERR_TRUNCATED  -1
#define PS2UI_ERR_MAGIC      -2
#define PS2UI_ERR_VERSION    -3
#define PS2UI_ERR_BOUNDS     -4
/* The blob's counts are legal but the arena they add up to does not
 * fit this machine's address space. It stopped meaning "past a number
 * ps2ui.h picked" when the table ceilings went away. */
#define PS2UI_ERR_TOO_MANY   -5
#define PS2UI_ERR_CRC        -6
#define PS2UI_ERR_FEATURES   -7
#define PS2UI_ERR_ALIGN      -8  /* texture bytes or arena not 16-aligned */
#define PS2UI_ERR_ARENA      -9  /* arena smaller than ps2ui_arena_size() */
#define PS2UI_ERR_NOT_STREAMED -10 /* tex_set on a baked or unknown slot  */
#define PS2UI_ERR_SIZE       -11 /* tex_set payload is not the reservation */

/* The arena's required alignment. The CLUT region at its start is a
 * DMA source, and DMA source addresses truncate silently below qword
 * alignment -- the exact fault class bringup.md 3c records. */
#define PS2UI_ARENA_ALIGN    16

/* Bytes of scratch this blob needs. Reads the header and table counts
 * (and the slot/texture tables they locate) but does not validate the
 * blob and does not touch the GS. Returns 0 if the header is
 * unreadable or the tables do not fit in `size`, which is also the
 * answer for "do not bother calling load". */
size_t ps2ui_arena_size(const void *data, size_t size);

/* Validate a blob and point the context into it. The blob must stay
 * alive and unmoved for the context's lifetime; nothing is copied.
 * The arena must be at least ps2ui_arena_size() bytes and
 * PS2UI_ARENA_ALIGN-aligned; the context points into it, so its
 * lifetime is the caller's and must cover every render, not just this
 * call. A blob that fails validation never touches the arena. */
int ps2ui_load(ps2ui_ctx *ctx, const void *data, size_t size,
               void *arena, size_t arena_size);

/* The CSM1 index permutation (swap bit 3 and bit 4). Exposed for tests;
 * mirrors clut_csm1_order in packages/baker/ps2ui_bake/gs.py. */
uint32_t ps2ui_clut_csm1(uint32_t index);

/* Allocate VRAM and upload every texture + permuted CLUT.
 *
 * Streamed slots are preflighted here like any other texture -- their
 * VRAM is part of the budget from the start -- but nothing is
 * transferred for them until ps2ui_tex_set names their texels. A
 * streamed slot that is never set draws nothing rather than DMAing
 * from a null source. */
int ps2ui_upload(ps2ui_ctx *ctx, GSGLOBAL *gs);

/* Point a streamed texture slot at the caller's texels.
 *
 * `len` must equal the entry's reservation exactly: a partial upload
 * is worse than none, because it draws convincingly wrong instead of
 * failing. ps2ui-bake prints the number on the slot's VRAM row --
 * `28000 B payload`, the smaller of the two figures there; the larger
 * one is the page-rounded VRAM the allocator commits and passing it
 * here is PS2UI_ERR_SIZE. This comment used to add "and the mismatch
 * error says which number was expected", which it does not: the
 * return is a bare code. An accessor that answers it from the blob is
 * the right fix and belongs with the rest of the v6 API work, not
 * here; until then the bake output is where the number lives.
 *
 * NOTHING IS COPIED, which is the same contract the blob already has.
 * `texels` becomes this slot's DMA source, so it must stay alive and
 * unmoved for as long as the slot can be drawn -- gsKit re-reads it
 * whenever the texture manager re-binds an evicted texture, which is
 * render time, not this call. It must also be 16-aligned, because a
 * DMA source address truncates silently below qword alignment.
 *
 * The design that preceded this had ps2ui stage a copy in the arena.
 * Measured against the case it exists for -- a library scrolling
 * 128x128 covers -- that is 576 KiB of duplicate texels for nine
 * visible rows, and ps2ui already points GSTEXTURE::Mem straight into
 * the caller's blob for every baked texture. One lifetime rule for
 * both kinds beats two, and the app already owns the decoded bytes.
 *
 * Returns PS2UI_OK, PS2UI_ERR_NOT_STREAMED (no such name, or the name
 * is a baked texture), PS2UI_ERR_SIZE, or PS2UI_ERR_ALIGN. Safe to
 * call before ps2ui_upload; safe to call again to swap the texels,
 * which is what scrolling a list does. */
int ps2ui_tex_set(ps2ui_ctx *ctx, GSGLOBAL *gs, const char *name,
                  const void *texels, size_t len);

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
 * name. The old "index past the hideable ceiling" failure is gone: the
 * visibility bits are sized from the blob's own n_focus, so every node
 * a blob declares can be hidden. */
int ps2ui_visible_set(ps2ui_ctx *ctx, const char *name, int visible);

/* 1 if shown (the default), 0 if hidden, PS2UI_VISIBLE_UNKNOWN if the
 * current screen has no node with that name.
 *
 * The three used to collapse into 0 (the #16 review's finding), so an
 * app could not tell "hidden" from "you typed the name wrong" -- and
 * the typo is the one a caller can fix. A third value rather than an
 * out-parameter because every other query in this header returns its
 * answer, and -1 cannot be confused with a visibility. */
#define PS2UI_VISIBLE_UNKNOWN (-1)
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
