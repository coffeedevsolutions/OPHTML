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


def report(textures, cluts, canvas_w: int, canvas_h: int, budget: int = None):
    """Compute the footprint. Returns (lines, total_bytes, budget, ok);
    lines is a printable per-texture breakdown."""
    if budget is None:
        budget = default_budget(canvas_w, canvas_h)
    lines = []
    total = 0
    for i, t in enumerate(textures):
        size = page_rounded_size(t.width, t.height, t.fmt)
        total += size
        fmt_name = "PSMT8" if t.fmt == gs.PSMT8 else "PSMCT32"
        lines.append(
            f"  tex[{i:2d}] {fmt_name:8s} {t.width:4d}x{t.height:<4d} "
            f"{len(t.data):7d} B raw -> {size:7d} B in pages"
        )
    for i, _c in enumerate(cluts):
        size = clut_size()
        total += size
        lines.append(f"  clut[{i}] PSMCT32  256 entries        -> {size:7d} B in pages")
    fb = framebuffer_size(canvas_w, canvas_h)
    lines.append(
        f"  framebuffers assumed: 2x draw/display + 1x Z @ {canvas_w}x{canvas_h} "
        f"= {3 * fb} B"
    )
    lines.append(
        f"  textures {total} B of {budget} B budget "
        f"({100 * total // max(budget, 1)}%)"
    )
    return lines, total, budget, total <= budget
