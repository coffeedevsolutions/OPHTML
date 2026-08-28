/* The height ladder: which quad heights lose their last texel row.
 *
 * IT HAS BEEN READ, AND ONE OF ITS THREE ARMS TURNED OUT NOT TO ASK A
 * QUESTION. SCPH-50000, bench sitting 3:
 *
 *   height     1  2  3  4  5  6  7  8  9 10 11 12
 *   A raw UVs  y  y  .  y  .  .  .  y  .  .  .  .
 *   B untex    y  y  y  y  y  y  y  y  y  y  y  y
 *   C +0.5     y  y  y  y  y  y  y  y  y  y  y  y
 *
 * WHAT A AND B ESTABLISH, and this part is solid. Raw integer UVs lose
 * the last texel row at every height that is NOT a power of two -- and
 * the powers of two are exactly the heights whose reciprocal is exact
 * in binary, which points at a reciprocal in the GS's per-scanline UV
 * step. B keeps every row with no texture unit in its path at all, so
 * neither the rasteriser nor the display is losing it. The fault is
 * real, it is in texture sampling, and an exact interpolator does not
 * have it: the host previewer and Play! both render every row.
 *
 * WHY ARM C ANSWERS NOTHING. ladder_texel ignores x and returns the
 * same dark value for every row but the last. So a bias that shifts
 * sampling down by a whole texel is INVISIBLE on rows 0..14 -- they
 * are identical -- and on the last row it reads texel 16, which clamps
 * back to 15 and lights up anyway. Arm C shows a bright bottom line
 * whether the bias corrects the sampling or merely shifts it. It
 * cannot fail, so its passing means nothing.
 *
 * That was not caught until the +0.5 bias was built on this reading
 * and the emulator gate rejected it: with the bias, Play! renders
 * `Library` as `Liibrarny` and the frame diff scores 17.34 against a
 * healthy 4.8. An exact interpolator samples u0+i+1 with the bias --
 * every glyph loses its leftmost column -- which is precisely what
 * docs/bringup.md has argued since before any of this, correctly, for
 * renderers that interpolate exactly. The GS is not one of them, and
 * the correction it needs is still unknown.
 *
 * WHAT LADDER V2 HAS TO DO: give the texture per-row AND per-column
 * detail, so a one-texel shift is distinguishable from a lost row
 * rather than hidden by uniformity and clamping; sweep bias MAGNITUDE
 * (0, 1/16, 1/8, 1/2 -- the GS's UV register carries 4 fractional
 * bits, and a bias below half a texel does not move an exact sampler
 * off its texel at all); and sweep WIDTH as well as height, because
 * every arm here is 128 wide, a power of two, so the U axis was never
 * asked anything either.
 *
 * The card below is kept exactly as it was read. Arm C stays, wrong
 * question and all, because the next version has to be checked against
 * what this one actually showed.
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
