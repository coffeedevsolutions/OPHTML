"""Shared numeric rules.

Two hosts compute pixel positions: Node (layout) and Python (baking).
They must agree bit-for-bit, and Python's round() rounds half to even
(round(2.5) == 2), which JavaScript's Math.round does not. Both sides
therefore use the same explicit floor(x + 0.5).
"""

import math


def round_half_up(x: float) -> int:
    """floor(x + 0.5) — identical to Math.round for non-negative x and
    to the layout package's roundHalfUp for all x."""
    return math.floor(x + 0.5)


def glyph_advance_px(units: int, size: int) -> int:
    """The rounding rule from docs/architecture.md. Layout's text.js
    implements the identical expression; test_metrics_agree proves it."""
    return round_half_up(units * size / 1000)


def css_alpha_to_gs(a255: int) -> int:
    """CSS alpha (0..255) -> GS alpha (0..128), converted exactly once.

    The GS blend unit treats 0x80 as 1.0 and values above as >1
    (used for additive overbright, never by this compiler). Mapping
    0xFF -> 0x80 here is the difference between correct translucency
    and the classic 'everything is half transparent' PS2 bug.
    """
    if not 0 <= a255 <= 255:
        raise ValueError(f"alpha {a255} outside 0..255")
    return round_half_up(a255 * 128 / 255)


def gs_alpha_to_css(a128: int) -> int:
    """Inverse mapping, used only by the previewer."""
    if not 0 <= a128 <= 128:
        raise ValueError(f"GS alpha {a128} outside 0..128")
    return min(255, round_half_up(a128 * 255 / 128))
