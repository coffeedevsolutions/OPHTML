/* Ladder v2: how big a UV bias the GS needs, and whether it shifts.
 *
 * IT HAS BEEN READ. SCPH-50000, sitting 4:
 *
 *   bias    last texel ROW          last texel COLUMN
 *   0       lost unless h is 2^n    ALWAYS lost (100 is not 2^n)
 *   1/16    present at every h      present
 *   1/8     present at every h      present
 *   1/2     present at every h      present
 *
 * BOTH AXES FAIL, INDEPENDENTLY, EACH ON ITS OWN SPAN -- the finding
 * this card was built for and v1 could not have produced. The clincher
 * is column 1 at h=4 and h=8: those rungs keep their bottom row (4 and
 * 8 are powers of two) and still lose their right column (100 is not).
 *
 * THE POSITIVE CONTROL DID NOT FIRE, AND THAT WAS A DESIGN FLAW HERE,
 * not a fault in the reading. Arm 1/2 was required to show SHIFTED on
 * the reasoning that half a texel shifts an exact sampler -- but the
 * GS is not an exact sampler, which is the thing under test, so the
 * control was circular. What saved the reading is the red row: a shift
 * replaces it with a second yellow, and it stayed red in every biased
 * column. The card could see a shift; there was none to see.
 *
 * Recorded rather than corrected, because the next card that needs a
 * positive control has to pick one that does not assume its own
 * conclusion, and this is the worked example of getting that wrong.
 *
 * ps2ui ships 1/16 (see PS2UI_TEXEL_BIAS): it fixes both axes on the
 * console and is below the half-texel tipping point, so it is a no-op
 * on the previewer and on Play!, where 1/2 scored 17.34 against a
 * healthy 4.8.
 *
 * WHY THERE IS A V2. Ladder v1 established two things and could not
 * establish a third. Raw integer UVs lose a quad's last texel row at
 * every height that is not a power of two; the same rungs drawn
 * untextured keep every row. So the fault is real and it is in texture
 * sampling. But v1's third arm asked whether a +0.5 bias fixes it, and
 * that arm COULD NOT FAIL: its texture was uniform dark on every row
 * but the last, so a bias that merely shifted sampling down a whole
 * texel was invisible on the body, and on the last row it read texel
 * 16, clamped back to 15, and lit up anyway. A bright bottom line
 * appeared whether the bias corrected the sampling or ruined it.
 *
 * It had ruined it. The +0.5 build made Play! render `Library` as
 * `Liibrarny` and scored 17.34 on a frame diff whose healthy band is
 * 4.8. On an exact interpolator a half-texel bias moves every pixel
 * one texel past its target -- which docs/bringup.md had argued
 * correctly for years, without knowing the GS is not exact.
 *
 * SO THE TEXTURE HERE HAS DETAIL WHERE V1 HAD NONE, and the whole
 * design follows from making a shift impossible to mistake for a fix:
 *
 *   row 15 (last)   YELLOW      the row the fault eats
 *   row 14          RED         so "shifted" and "correct" differ
 *   rows 0..13      dark navy   the body
 *   column 99       CYAN        on body rows only -- the U axis
 *
 * READ EACH BLOCK AS THREE QUESTIONS:
 *
 *   yellow bottom row, RED directly above it   -> sampling is CORRECT
 *   yellow bottom row, NO red (or two yellows) -> sampling is SHIFTED
 *   RED bottom row, no yellow                  -> last row is LOST
 *
 * That third state is what v1 called "the line is missing", and it now
 * has a positive signature rather than an absence. The second state is
 * what v1 could not see at all.
 *
 * THE CYAN RIGHT EDGE IS THE U AXIS, which v1 never asked about: every
 * v1 arm was 128 wide, a power of two, so the one span that cannot
 * trigger the fault. Here the sampled sub-rect is 100 wide. If U
 * sampling is correct the block's rightmost body column is cyan; if it
 * is shifted, column 99 is never sampled and the cyan disappears.
 * Needs h >= 3 to be visible, since rows 14 and 15 span the full
 * width. (The GS texture stays 128x16 because TEX0 sizes are powers of
 * two; 100 is a sub-rect of it, exactly as every glyph is.)
 *
 * FOUR ARMS SWEEP THE BIAS MAGNITUDE, not its presence -- v1's mistake
 * was treating "bias" as a boolean:
 *
 *   0      what ps2ui ships. NEGATIVE CONTROL: must show LOST at every
 *          height that is not a power of two, or the card is not
 *          reproducing the fault and nothing else on it can be trusted
 *   1/16   the GS's UV register carries four fractional bits, so this
 *          is the smallest bias it can express
 *   1/8    the next one up
 *   1/2    POSITIVE CONTROL: known to shift on an exact interpolator,
 *          so it must show SHIFTED here. If it does not, this card
 *          cannot see a shift and its other columns mean nothing --
 *          which is precisely the check v1 lacked
 *
 * Any bias below 1/2 leaves an exact sampler on the same texel, since
 * floor(u + b + i + 0.5) == u + i for b < 0.5. So a winning column at
 * 1/16 or 1/8 would fix the console without moving the emulator at
 * all, and that is the outcome this card exists to look for.
 */
#ifndef PS2UI_LADDER2_PATTERN_H
#define PS2UI_LADDER2_PATTERN_H

#define L2_TEX_W     128   /* GS texture: power of two, as TEX0 requires */
#define L2_TEX_H      16
#define L2_W         100   /* SAMPLED width -- deliberately not a power  */
                           /* of two, so the U axis is asked something   */
#define L2_MAX_H      12   /* tallest rung; capitals are 11              */
#define L2_PITCH      32
#define L2_TOP        30
#define L2_TICK_X      8
#define L2_N_ARMS      4
#define L2_ARM_X0     40
#define L2_ARM_PITCH 150

/* The three texels that carry the reading. */
#define L2_ROW_LAST  (L2_TEX_H - 1)   /* 15, yellow */
#define L2_ROW_PREV  (L2_TEX_H - 2)   /* 14, red    */
#define L2_COL_LAST  (L2_W - 1)       /* 99, cyan on body rows          */

/* Rung i draws at height i+1, sampling [v0, L2_TEX_H) so that every
 * rung's last texel row is the SAME one -- v1's one good idea, kept:
 * it means "the bottom is wrong" reads identically in every column and
 * needs no per-height reinterpretation. */
static int ladder2_y(int i)  { return L2_TOP + i * L2_PITCH; }
static int ladder2_h(int i)  { return i + 1; }
static int ladder2_v0(int i) { return L2_TEX_H - ladder2_h(i); }

static int ladder2_arm_x(int a) { return L2_ARM_X0 + a * L2_ARM_PITCH; }

/* Sixteenths, so the values are exact in binary and in the GS's 12.4
 * UV register alike -- a bias the hardware cannot represent would be a
 * column testing something other than what it claims. */
static float ladder2_bias(int a)
{
    static const float b[L2_N_ARMS] = { 0.0f, 1.0f / 16.0f,
                                        1.0f / 8.0f, 1.0f / 2.0f };
    return b[a];
}

static void ladder2_texel(int x, int y, unsigned char out[4])
{
    if (y == L2_ROW_LAST) {          /* yellow: the row under test    */
        out[0] = 255; out[1] = 236; out[2] = 150;
    } else if (y == L2_ROW_PREV) {   /* red: makes a shift visible    */
        out[0] = 232; out[1] =  76; out[2] =  76;
    } else if (x == L2_COL_LAST) {   /* cyan: the U axis, on the body */
        out[0] =  90; out[1] = 220; out[2] = 220;
    } else {                         /* dark navy body                */
        out[0] =  44; out[1] =  54; out[2] =  96;
    }
    out[3] = 0x80;
}

static void ladder2_fill(unsigned char *dst, int w, int h)
{
    int x, y;
    for (y = 0; y < h; y++)
        for (x = 0; x < w; x++)
            ladder2_texel(x, y, dst + ((y * w) + x) * 4);
}

#endif /* PS2UI_LADDER2_PATTERN_H */
