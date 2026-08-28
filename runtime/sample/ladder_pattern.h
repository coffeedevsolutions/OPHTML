/* The height ladder: which quad heights lose their last texel row.
 *
 * IT HAS BEEN READ. SCPH-50000, bench sitting 3:
 *
 *   height     1  2  3  4  5  6  7  8  9 10 11 12
 *   A raw UVs  y  y  .  y  .  .  .  y  .  .  .  .
 *   B untex    y  y  y  y  y  y  y  y  y  y  y  y
 *   C +0.5     y  y  y  y  y  y  y  y  y  y  y  y
 *
 * B keeps every row, so the rasteriser and the display are innocent.
 * C keeps every row, so the +0.5 bias is the fix -- it now ships as
 * PS2UI_TEXEL_BIAS in ps2ui.c. A's survivors are exactly the powers
 * of two, which are exactly the heights whose reciprocal is exact in
 * binary; see the constant's comment for what that suggests and for
 * how much of it is hypothesis.
 *
 * The card is kept, unchanged, as a regression instrument: arm A is
 * deliberately still the UNBIASED path, so a future sitting can boot
 * this and see the fault reproduce beside its fix. Do not "update"
 * arm A to match what ps2ui now ships -- that would delete the only
 * on-console evidence the bias does anything.
 *
 * The text below is the design as written before the reading, kept
 * because it says what each outcome would have meant.
 *
 * WHAT THE BENCH ESTABLISHED. On a SCPH-50000, capitals lose exactly
 * one screen row -- E reads as F, L as I, 2 as ?. Measured against the
 * blob: the lost row is the LAST row of an 11-texel-tall quad, and a
 * ONE-texel-tall quad at a neighbouring row renders perfectly. Both
 * sample the same atlas, neither is near its edge, and the blob has no
 * scissors at all. The host previewer and the Play! emulator both draw
 * the same GIF stream with every row present.
 *
 * That killed the two hypotheses the first write-up carried. "The last
 * row of every quad is lost" cannot be it: a one-row quad's only row
 * IS its last, and it survives. "The panel erases thin horizontal
 * strokes" cannot be it either: the hyphen IS a thin isolated
 * horizontal stroke, and a display that ate those would eat it first.
 *
 * Both bars measure ONE texel out of the atlas -- the size-15 face
 * inks E as [8,2,2,2,2,8,2,2,2,2,8] and the hyphen as [5] -- so the
 * finding states with thickness removed as a variable rather than
 * relied on, and this is the form the whole card rests on:
 *
 *   TWO HORIZONTAL STROKES OF IDENTICAL THICKNESS, ONE TEXEL, DIFFER
 *   ONLY IN THE HEIGHT OF THE QUAD CARRYING THEM. THE ONE IN A 1-ROW
 *   QUAD RENDERS; THE ONE AT THE BOTTOM OF AN 11-ROW QUAD DOES NOT.
 *
 * Nothing else is left in the frame, and quad height is exactly what
 * the ladder sweeps.
 *
 * What is left has to treat a tall quad differently from a short one,
 * which is a sampling or rasterisation property rather than anything a
 * deinterlacer or a scaler does. This card finds where the boundary
 * is, and which stage owns it.
 *
 * THREE ARMS PER HEIGHT, and the reading is one question asked three
 * ways: IS THE BRIGHT BOTTOM LINE THERE?
 *
 *   A  textured, raw integer UVs      -- what ps2ui ships today
 *   B  h stacked 1px untextured quads -- rasterisation with no texture
 *                                        unit involved at all
 *   C  textured, UVs biased by +0.5   -- the standing candidate fix,
 *                                        which bringup.md has carried
 *                                        as unsettled since step 6
 *
 * Every arm's last row is the SAME atlas row, because each height
 * samples [ROWS - h, ROWS) rather than [0, h). So "the bright line is
 * missing" means one thing in every column and does not need a
 * different reading per height -- the mistake that made the first
 * probe6 unreadable was exactly this kind of per-column reinterpretation.
 *
 * READING IT. A shows the line at every height and the fault is not
 * where this card looks. A loses it above some height while B keeps it
 * -- texture sampling, and the height it starts at is the signature. A
 * and B both lose it -- rasterisation or the display, and the renderer
 * is off the hook. C keeps it where A loses it -- the +0.5 bias is the
 * fix and it has just been demonstrated rather than argued.
 */
#ifndef PS2UI_LADDER_PATTERN_H
#define PS2UI_LADDER_PATTERN_H

#define LADDER_ROWS      16   /* texture height; row 15 is the bright one */
#define LADDER_W        128   /* texture and block width, drawn 1:1       */
#define LADDER_MAX_H     12   /* tallest rung; capitals are 11            */
#define LADDER_PITCH     30   /* vertical spacing between rungs           */
#define LADDER_TOP       24
#define LADDER_TICK_X    24
#define LADDER_ARM_A_X  116
#define LADDER_ARM_B_X  288
#define LADDER_ARM_C_X  460

/* The one row that answers the question, and the only bright row in
 * the texture. Every rung samples up to and including it. */
#define LADDER_BRIGHT_ROW (LADDER_ROWS - 1)

/* Rung i (0-based) draws at height i+1. Screen y of its top. */
static int ladder_y(int i) { return LADDER_TOP + i * LADDER_PITCH; }
static int ladder_h(int i) { return i + 1; }

/* The atlas rows a rung samples: [v0, LADDER_ROWS). Anchored at the
 * BOTTOM of the texture so every rung's last row is the bright one. */
static int ladder_v0(int i) { return LADDER_ROWS - ladder_h(i); }

/* One texel of the ladder texture, PSMCT32 with alpha in the GS
 * domain. Dark body, one bright row at the bottom -- present or
 * absent is a judgement a phone at arm's length can make, which a
 * gradient or a per-row hue ramp is not. */
static void ladder_texel(int x, int y, unsigned char out[4])
{
    (void)x;
    if (y == LADDER_BRIGHT_ROW) {
        out[0] = 255; out[1] = 236; out[2] = 150;
    } else {
        out[0] = 44; out[1] = 54; out[2] = 96;
    }
    out[3] = 0x80;
}

static void ladder_fill(unsigned char *dst, int w, int h)
{
    int x, y;
    for (y = 0; y < h; y++)
        for (x = 0; x < w; x++)
            ladder_texel(x, y, dst + ((y * w) + x) * 4);
}

#endif /* PS2UI_LADDER_PATTERN_H */
