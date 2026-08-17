"""Graphics Synthesizer pixel formats.

Only what the compiler emits:

    PSMCT32  32-bit RGBA, alpha already in the GS 0..128 domain.
    PSMT8    8-bit indexed with a 256-entry PSMCT32 CLUT.

CLUTs are stored *linearly* in the .uib. Real CSM1 uploads want the
infamous bit-3/bit-4 swap of the index (blocks of 8 swapped within
each 32), which the runtime applies at upload time — keeping the file
format readable by tools that know nothing about the GS. clut_csm1_order
exists here only so tests and the previewer can prove the permutation
round-trips.
"""

from .rounding import css_alpha_to_gs

PSMT8 = 0
PSMCT32 = 1


def pack_rgba_gs(r: int, g: int, b: int, a255: int) -> bytes:
    """One PSMCT32 texel from CSS-domain channels. Alpha crosses into
    the GS domain here and nowhere else."""
    return bytes((r, g, b, css_alpha_to_gs(a255)))


def encode_psmct32(pixels) -> bytes:
    """pixels: iterable of (r, g, b, a255) in CSS domain, row-major."""
    out = bytearray()
    for r, g, b, a in pixels:
        out += pack_rgba_gs(r, g, b, a)
    return bytes(out)


def encode_psmt8(indices) -> bytes:
    return bytes(indices)


def coverage_clut(color=(255, 255, 255)) -> bytes:
    """256-entry CLUT for glyph atlases: index i = `color` at coverage
    i/255. Stored linearly (see module docstring)."""
    out = bytearray()
    r, g, b = color
    for i in range(256):
        out += pack_rgba_gs(r, g, b, i)
    return bytes(out)


def clut_csm1_order(i: int) -> int:
    """Index permutation the GS applies to CSM1 CLUT storage: within
    each 32-entry block, entries 8..15 and 16..23 swap. Equivalent to
    swapping bit 3 and bit 4 of the index."""
    b3 = (i >> 3) & 1
    b4 = (i >> 4) & 1
    return (i & ~0b11000) | (b3 << 4) | (b4 << 3)


def permute_clut_csm1(linear: bytes) -> bytes:
    """Reorder a linear 256-entry PSMCT32 CLUT into CSM1 storage order.
    The C runtime mirrors this in ps2ui_clut_csm1(); test_uib checks the
    two agree on a known pattern."""
    assert len(linear) == 256 * 4
    out = bytearray(len(linear))
    for i in range(256):
        j = clut_csm1_order(i)
        out[j * 4:j * 4 + 4] = linear[i * 4:i * 4 + 4]
    return bytes(out)
