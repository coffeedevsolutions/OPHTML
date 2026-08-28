/* A windowed list: N titles, W visible rows, one selection.
 *
 * This is the mechanism Phase 2's exit gate names -- "streaming covers
 * while scrolling a windowed library" -- and the least-tested thing in
 * the project, because slot text and streamed textures have each been
 * exercised alone and never together under motion.
 *
 * It lives in the EXAMPLE, not the runtime, and that placement is the
 * point: ps2ui has no list widget and should not grow one. A list is
 * an app's data model plus a loop that rebinds slots; the runtime's
 * job is to make rebinding cheap and bounded. If this file needed
 * something ps2ui cannot do, that would be a foundation gap worth
 * filing. It did not.
 *
 * Pure C89, no PS2 headers, no allocation: the host suite runs the
 * same code the ELF does rather than a paraphrase of it.
 *
 * THE COST THIS MAKES VISIBLE. Reservations are per ROW, not per item
 * -- the blob declares nine 28x28 slots called row-0-art .. row-8-art,
 * and they are fixed. So scrolling by a single row does not expose one
 * new cover: every visible row now shows a different title, and all
 * nine reservations need refilling. That is 9 x 3136 = 28,224 bytes of
 * upload per scroll step, and at field rate it is the dominant cost of
 * moving. Phase 3's answer is probably to rotate which reservation a
 * row draws from rather than re-upload; this file exists partly to
 * make that number measurable before anyone optimises it.
 */
#ifndef OPLENV_WINDOW_H
#define OPLENV_WINDOW_H

typedef struct {
    int n_items;   /* titles in the library                        */
    int n_rows;    /* visible rows; the blob's reservation count    */
    int top;       /* absolute index drawn in row 0                 */
    int sel;       /* absolute index of the selection               */
} oplenv_window;

/* A window over `n_items`, showing `n_rows`, selection at the top.
 * n_rows is clamped to at least 1 so a caller cannot build a window
 * that divides by zero later; n_items may legitimately be 0. */
static void oplenv_window_init(oplenv_window *w, int n_items, int n_rows)
{
    w->n_items = n_items < 0 ? 0 : n_items;
    w->n_rows  = n_rows  < 1 ? 1 : n_rows;
    w->top = 0;
    w->sel = 0;
}

/* The largest legal `top`: the last full window, or 0 when the list is
 * shorter than the window. Never negative, which is the case a naive
 * n_items - n_rows gets wrong. */
static int oplenv_window_max_top(const oplenv_window *w)
{
    int m = w->n_items - w->n_rows;
    return m < 0 ? 0 : m;
}

/* Move the selection by `delta` and scroll only as far as it takes to
 * keep it visible -- the behaviour a list is expected to have, and the
 * one that makes scrolling rare relative to moving.
 *
 * Returns 1 if `top` changed, which is the caller's signal to refill
 * the covers. Returns 0 when the selection moved within the window and
 * nothing needs uploading, which is the common case and the reason
 * this returns anything at all. */
static int oplenv_window_move(oplenv_window *w, int delta)
{
    int was = w->top;
    if (w->n_items == 0)
        return 0;
    w->sel += delta;
    if (w->sel < 0)             w->sel = 0;
    if (w->sel >= w->n_items)   w->sel = w->n_items - 1;

    if (w->sel < w->top)                 w->top = w->sel;
    if (w->sel >= w->top + w->n_rows)    w->top = w->sel - w->n_rows + 1;

    /* Clamp after, not instead: a window whose list shrank under it
     * can be past the end with a selection that is still legal. */
    if (w->top > oplenv_window_max_top(w)) w->top = oplenv_window_max_top(w);
    if (w->top < 0) w->top = 0;
    return w->top != was;
}

/* The absolute item index drawn in visible row `row`, or -1 when the
 * row is past the end of a list shorter than the window. Rows past the
 * end are real: a 4-title library still draws nine rows, and the app
 * has to blank the other five rather than show stale text. */
static int oplenv_window_row_item(const oplenv_window *w, int row)
{
    int idx;
    if (row < 0 || row >= w->n_rows)
        return -1;
    idx = w->top + row;
    return idx < w->n_items ? idx : -1;
}

/* Which visible row holds the selection, or -1 if none does. */
static int oplenv_window_sel_row(const oplenv_window *w)
{
    int r = w->sel - w->top;
    return (r >= 0 && r < w->n_rows) ? r : -1;
}

#endif /* OPLENV_WINDOW_H */
