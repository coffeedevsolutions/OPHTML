/* The cover pattern, in the one place both languages read it.
 *
 * The streaming bench needs texels from somewhere. Normally that is
 * mass:/ps2ui/cover*.raw, written by tools/make_cover_raw.py from real
 * art. When the drive is absent the ELF generates the same pattern on
 * the EE instead, so a sitting still produces a reading -- and "the
 * same pattern" has to be true, not asserted, or the fallback picture
 * and the reference PNG diverge and nobody notices.
 *
 * Same reason probe6_pattern.h exists: a property two implementations
 * must share belongs in a file they both include, not in prose.
 *
 * THE PATTERN IS NOT A FLAT FILL OR A GRADIENT, deliberately. A flat
 * cover looks identical whether the texels arrived or a stale VRAM
 * block is being drawn -- which is the exact question step S1 asks. A
 * gradient hides a half-texel shift. This is a coarse checker in a
 * per-index hue, a one-texel white border (any crop shows) and a solid
 * corner block (orientation), all readable from a photograph.
 *
 * Alpha is 0x80, not 0xFF: the GS blend this runtime asserts every
 * frame is Cv = (Cs - Cd) * As >> 7 + Cd, so 0xFF asks for about twice
 * the coverage it has. Backlog B1 on a new path.
 */
#ifndef PS2UI_COVER_PATTERN_H
#define PS2UI_COVER_PATTERN_H

#define COVER_EDGE 2

/* CRC-32 (IEEE reflected, the one ps2ui_crc32 computes) of
 * cover_fill(0, 64, 64). Pinned here and checked from BOTH sides:
 * runtime/tests/test_runtime.c computes it in C, and the baker suite
 * computes it over make_cover_raw.synthetic() in Python. Either
 * implementation drifting turns one of them red. */
#define COVER_PATTERN_CRC_0_64x64 0xfbae5623u

/* Per-index hues. Six is enough for any bench row and keeps "which
 * cover is this" answerable without counting. */
static const unsigned char cover_hue[6][3] = {
    { 220,  90,  70 }, {  70, 170, 220 }, { 240, 200,  80 },
    { 150, 220, 120 }, { 210, 120, 220 }, { 120, 200, 200 },
};

/* One texel, PSMCT32 (r, g, b, a) with a already in the GS domain. */
static void cover_texel(int index, int x, int y, int w, int h,
                        unsigned char out[4])
{
    /* Scaled with the cover, not fixed: a fixed 16-texel cell makes a
     * small cover come out entirely border -- a flat fill, identical
     * for every index, which is the failure this pattern exists to
     * avoid. The Python side's self-test caught exactly that. */
    int cw = w / 8, ch = h / 8, cell;
    const unsigned char *fg = cover_hue[index % 6];
    cell = cw < ch ? cw : ch;
    if (cell > 16) cell = 16;
    if (cell < 2)  cell = 2;

    if (x < COVER_EDGE || y < COVER_EDGE
        || x >= w - COVER_EDGE || y >= h - COVER_EDGE) {
        out[0] = out[1] = out[2] = 255;            /* border */
    } else if (x < COVER_EDGE + cell && y < COVER_EDGE + cell) {
        out[0] = out[1] = out[2] = 255;            /* corner block */
    } else if (((x / cell) + (y / cell)) & 1) {
        out[0] = fg[0]; out[1] = fg[1]; out[2] = fg[2];
    } else {
        out[0] = fg[0] / 3; out[1] = fg[1] / 3; out[2] = fg[2] / 3;
    }
    out[3] = 0x80;
}

/* Fill a whole cover, row-major, exactly w * h * 4 bytes. */
static void cover_fill(unsigned char *dst, int index, int w, int h)
{
    int x, y;
    for (y = 0; y < h; y++)
        for (x = 0; x < w; x++)
            cover_texel(index, x, y, w, h, dst + ((y * w) + x) * 4);
}

/* The bench's phase schedule, here rather than in main.c so it can be
 * tested at all.
 *
 * Its first version lived inline in the frame loop as
 * `(frame / N) % 4`, which fired the FILL case on frame 0 -- so the
 * EMPTY state was overwritten before a single frame reached the
 * television, while the comment beside it claimed a five-second hold.
 * Step S1 came back VOID from a console because of it, and nothing on
 * the host could have said so: main.c is compiled but never linked
 * into a test.
 *
 * Five phases on the first lap, four forever after. EMPTY belongs
 * only at the top: ps2ui_tex_set has no "unset" and should not have
 * one, so once the slots are filled they stay filled. That is why
 * this is not simply `% 5`. */
static unsigned cover_phase_for_frame(unsigned frame, unsigned per_phase)
{
    unsigned phase = frame / per_phase;
    if (phase > 4u)
        phase = 1u + ((phase - 1u) % 4u);
    return phase;
}

/* The label the bench photographs, keyed by the same number the
 * schedule returns.
 *
 * The point is that a photograph labels itself and cannot lie. Before
 * this, the label was written inside each switch case, so the case
 * that fired and the text it printed were two separate claims -- and
 * the defect that made S1 void was exactly a disagreement between
 * them: phase 0 printed nothing and filled instead. Deriving the
 * label from the phase makes that disagreement unrepresentable.
 *
 * The test asserts these strings against the phase numbers, so a
 * re-mapping shows up as a wrong label rather than as a bench sitting
 * that reads the wrong step. */
static const char *cover_phase_name(unsigned phase)
{
    switch (phase) {
    case 0:  return "0 EMPTY: nothing set -- boxes must be blank";
    case 1:  return "1 FILL: four covers via tex_set";
    case 2:  return "2 SWAP: slot 0 now shows cover 3";
    case 3:  return "3 RESTORE: slot 0 shows cover 0 again";
    case 4:  return "4 COMPOSITE: dialog over covers";
    default: return "?? schedule produced a phase with no name";
    }
}

#endif /* PS2UI_COVER_PATTERN_H */
