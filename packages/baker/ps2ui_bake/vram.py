"""VRAM accounting (backlog B8).

The GS has exactly 4 MiB of VRAM, allocated in 8 KiB pages whose pixel
geometry depends on the format: a PSMCT32 page holds 64x32 texels, a
PSMT8 page 128x64. gsKit allocates page-granular, so a texture's true
footprint is its page-rounded size — a 256x40 PSMT8 atlas costs a full
2x1 pages even though its raw bytes are small.

The baker knows every texture it emits, which means an over-budget UI
can and should fail at bake time with a breakdown, not at upload time
on the console with a bare GSKIT_ALLOC_ERROR.
"""

from . import gs

VRAM_TOTAL = 4 * 1024 * 1024
PAGE_BYTES = 8192

# Page pixel geometry per PSM (width, height in texels).
_PAGE_DIMS = {
    gs.PSMCT32: (64, 32),
    gs.PSMT8: (128, 64),
}


def page_rounded_size(width: int, height: int, fmt: int) -> int:
    """Page-granular VRAM footprint of a texture, in bytes. Mirrors the
    geometry gsKit's allocator commits pages against."""
    pw, ph = _PAGE_DIMS[fmt]
    pages_x = -(-width // pw)
    pages_y = -(-height // ph)
    return pages_x * pages_y * PAGE_BYTES


def clut_size() -> int:
    """A 256-entry PSMCT32 CLUT uploads as a 16x16 CT32 block: one page."""
    return PAGE_BYTES


def framebuffer_size(width: int, height: int) -> int:
    """One PSMCT32 display/draw buffer at the given resolution."""
    return page_rounded_size(width, height, gs.PSMCT32)


def default_budget(canvas_w: int, canvas_h: int) -> int:
    """Conservative texture budget: total VRAM minus THREE framebuffer-
    sized reservations at the canvas resolution.

    Deliberately more cautious than what this tree's own sample
    reserves, and honest about it: the sample runs ZBuffering OFF, so
    its console holds exactly two CT32 display buffers (gsKit only
    allocates Z when ZBuffering is ON) -- but a host that turns Z on
    with a 32-bit PSMZ needs the third buffer, and a bake-time default
    must hold for the heaviest host it claims to support, not the
    lightest. An earlier version of this docstring called this "the
    layout a stock gsKit sample allocates", which was false in both
    directions at once. Callers who know their real layout override
    via --vram-budget; the runtime preflight then re-checks the true
    remaining VRAM on the console itself at upload time."""
    fb = framebuffer_size(canvas_w, canvas_h)
    return VRAM_TOTAL - 3 * fb


# A CLUT's texels: 256 entries of PSMCT32. It occupies a whole 8 KiB
# page regardless (F-043), which is exactly the kind of gap the line
# below reports rather than hides.
CLUT_PAYLOAD = 256 * 4


def report(textures, cluts, canvas_w: int, canvas_h: int, budget: int = None):
    """Compute the footprint. Returns (lines, total_bytes, budget, ok);
    lines is a printable per-texture breakdown."""
    if budget is None:
        budget = default_budget(canvas_w, canvas_h)
    lines = []
    total = 0
    payload_total = 0
    for i, t in enumerate(textures):
        size = page_rounded_size(t.width, t.height, t.fmt)
        total += size
        fmt_name = "PSMT8" if t.fmt == gs.PSMT8 else "PSMCT32"
        # A streamed slot carries no texels, so "0 B raw" would read as
        # free when it is a full reservation -- the VRAM is spent
        # whether or not the app ever fills it. Say which it is.
        #
        # Both numbers, and labelled, because they are the two counts
        # the v6 model deliberately separates and an integrator needs
        # the SMALLER one: `payload` is exactly the `len` argument
        # ps2ui_tex_set demands (it compares against data_len and
        # returns PS2UI_ERR_SIZE on any other value), while `in pages`
        # is what the allocator commits. Printing only the page figure
        # put the wrong one of the two on the only line the bake says
        # about a slot.
        streamed = bool(getattr(t, "kind", 0))
        payload = t.reservation if streamed else len(t.data)
        payload_total += payload
        lines.append(
            f"  tex[{i:2d}] {fmt_name:8s} {t.width:4d}x{t.height:<4d} "
            f"{'streamed' if streamed else 'baked':8s} "
            f"{payload:8d} B payload -> {size:7d} B in pages"
        )
    for i, _c in enumerate(cluts):
        size = clut_size()
        total += size
        payload_total += CLUT_PAYLOAD
        lines.append(f"  clut[{i}] PSMCT32  256 entries        -> {size:7d} B in pages")
    fb = framebuffer_size(canvas_w, canvas_h)
    lines.append(
        f"  framebuffers assumed: 2x draw/display + 1x Z @ {canvas_w}x{canvas_h} "
        f"= {3 * fb} B"
    )
    # THE COLUMN ABOVE HAS NEVER BEEN ADDED UP, and the difference is
    # the whole of what P3c has left to argue with. Its frame-rate case
    # is closed [F-037, F-042]: the GS is at 5.6% and no content shape
    # F-038 named revives it. What survives is footprint -- page-aware
    # packing to reduce TBP switches and make streamed reservations
    # exact -- and that case has to be made on bytes. Printing the two
    # totals side by side is the cheapest possible version of making
    # it, on every bake rather than once in a document.
    #
    # WHAT THIS IS NOT: a claim that the gap is recoverable. It is the
    # size of the prize, not the prize. How much a packer could
    # actually reclaim depends on the GS's texture-base granularity and
    # on what gsKit's allocator will do with it, neither of which this
    # tree has verified -- so the number is reported and not spent.
    waste = total - payload_total
    lines.append(
        f"  payload {payload_total} B -> {total} B in pages: "
        f"{waste} B ({100 * waste // max(total, 1)}%) is page-rounding, "
        f"which is what P3c would have to reclaim"
    )
    lines.append(
        f"  textures {total} B of {budget} B budget "
        f"({100 * total // max(budget, 1)}%)"
    )
    return lines, total, budget, total <= budget
