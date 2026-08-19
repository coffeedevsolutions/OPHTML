"""The scissor model, in one place.

`ps2ui_render` intersects each SCISSOR_PUSH with the enclosing rect
rather than replacing it, and pops back to the parent. Three consumers
need to replay exactly that: the baker (to drop geometry that cannot
draw), the previewer (to composite the same pixels the console does),
and ps2ui-check (to report geometry that survived).

They used to carry two copies of it, already differing by one term. A
validator whose job is to confirm the baker is worth rather less when
it shares the *bug* by coincidence and not the *model* by construction,
so the model lives here and both import it. What stays independent is
what matters: the baker decides what to emit, this decides what could
draw, and the runtime is the only real oracle for either.
"""

from .quads import OP_SCISSOR_POP, OP_SCISSOR_PUSH, OP_QUAD, OP_TEXQUAD


def intersect(clip, x, y, w, h):
    """A SCISSOR_PUSH against the enclosing rect."""
    cx, cy, cw, ch = clip
    x0, y0 = max(cx, x), max(cy, y)
    x1, y1 = min(cx + cw, x + w), min(cy + ch, y + h)
    return (x0, y0, max(0, x1 - x0), max(0, y1 - y0))


def can_draw(rec, clip):
    """Could this draw record produce a pixel under `clip`?"""
    cx, cy, cw, ch = clip
    if cw <= 0 or ch <= 0:
        # Nested scissors that do not overlap. The edge tests below
        # cannot see this: a quad straddling x == cx passes all four.
        return False
    if rec.w <= 0 or rec.h <= 0:
        return False
    return not (rec.x + rec.w <= cx or rec.y + rec.h <= cy
                or rec.x >= cx + cw or rec.y >= cy + ch)


def dead_indices(records, first, count, canvas_w, canvas_h):
    """Indices into `records` of draw records that cannot draw.

    Scissor records are never reported: balance is a contract the
    runtime relies on, and a push whose rect is empty still has to be
    popped.
    """
    clip = [(0, 0, canvas_w, canvas_h)]
    dead = []
    for i in range(first, first + count):
        rec = records[i]
        if rec.op == OP_SCISSOR_PUSH:
            clip.append(intersect(clip[-1], rec.x, rec.y, rec.w, rec.h))
        elif rec.op == OP_SCISSOR_POP:
            if len(clip) > 1:
                clip.pop()
        elif rec.op in (OP_QUAD, OP_TEXQUAD):
            if not can_draw(rec, clip[-1]):
                dead.append(i)
    return dead
