"""VRAM accounting (backlog B8).

The GS has exactly 4 MiB of VRAM. This file carries TWO models of what
a texture costs in it, and the difference between them is large:

  page_rounded_size()  8 KiB pages, the BUDGET model. Deliberately
                       pessimistic; what the bake refuses against.
  alloc_size()         256-byte blocks, what gsKit's TexManager
                       actually commits on the path the runtime takes.

THE DOCSTRING HERE USED TO ASSERT THE FIRST WAS THE SECOND -- "gsKit
allocates page-granular, so a texture's true footprint is its
page-rounded size" -- and that is false for this runtime.
`gsKit_vram_alloc` rounds to 8 KiB only for GSKIT_ALLOC_SYSBUFFER, and
ps2ui.c:632 does not call it at all: every texture binds through
gsKit_TexManager_bind, which sizes with gsKit_texture_size(), and that
counts 256-byte blocks after rounding to a sub-page alignment group.
A full page is its LARGEST case, not its unit. An 11x11 PSMT8 patch
costs 256 B there against 8192 B here -- 32x -- and a 256-entry CLUT
costs 1024 B against 8192 B.

KEEPING THE PESSIMISTIC MODEL FOR THE BUDGET IS DELIBERATE: refusing a
blob that would have fitted is the safe direction, and ps2ui_upload's
preflight exists because _blockAlloc hangs rather than failing. What
does not follow is quoting that number as a saving something could
reclaim, which is what this file did for one commit.

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
    """Page-granular VRAM footprint, in bytes: the BUDGET model.

    Not what the allocator commits -- see alloc_size() and the module
    docstring. This is the conservative figure the bake refuses
    against, and it stays conservative on purpose."""
    pw, ph = _PAGE_DIMS[fmt]
    pages_x = -(-width // pw)
    pages_y = -(-height // ph)
    return pages_x * pages_y * PAGE_BYTES


# Block geometry per PSM: (texels per block across, down). Ported from
# gsKit_texture_size in runtime/vendor/gsKit/src/gsTexture.c, whose own
# comment reads "A block is 256 bytes in size".
_BLOCK_DIMS = {
    gs.PSMCT32: (8, 8),
    gs.PSMT8: (16, 16),
}
BLOCK_BYTES = 256


def alloc_size(width: int, height: int, fmt: int) -> int:
    """What gsKit's TexManager commits for a texture, in bytes.

    A port of gsKit_texture_size(), which is the function
    gsKit_TexManager_bind sizes its allocation with -- and therefore
    the only model that describes this runtime's real footprint.
    Blocks are 256 B, then rounded up to an alignment GROUP (1x1, 2x2,
    4x4, or 8x4 blocks); 8x4 is one full page, and it is the largest
    case rather than the unit.

    Checked against the vendored C itself by tools/check-vram-model.py
    rather than trusted: a second implementation of someone else's
    arithmetic is exactly the thing this project keeps finding wrong,
    and here the original is in the tree and compiles."""
    bw, bh = _BLOCK_DIMS[fmt]
    wb = -(-width // bw)
    hb = -(-height // bh)
    # The CT32/CT24/T8 group table. CT16/CT16S/T4 use different ones and
    # are not ported: the baker emits neither, and a wrong answer for a
    # format nobody bakes is worse than no answer.
    if wb <= 2 and hb <= 1:
        wa, ha = 1, 1
    elif wb <= 4 and hb <= 2:
        wa, ha = 2, 2
    elif wb <= 8 and hb <= 4:
        wa, ha = 4, 4
    else:
        wa, ha = 8, 4
    wb = -(-wb // wa) * wa
    hb = -(-hb // ha) * ha
    return wb * hb * BLOCK_BYTES


def alloc_total(textures) -> int:
    """What the runtime's own preflight computes for a texture list.

    A MIRROR OF ps2ui.c's LOOP, not a reinvention of it: that loop is
    `gsKit_texture_size(w, h, psm)` per texture, plus
    `gsKit_texture_size(16, 16, CT32)` -- 1024 B -- for every INDEXED
    one, and its comment states why ("the sum mirrors the manager's
    own appetite exactly"). The result is stored as ctx->vram_need.

    THE CLUT CHARGE IS PER PSMT8 TEXTURE, NOT PER DISTINCT CLUT, which
    is the detail that makes this a mirror rather than a re-derivation:
    textures sharing a palette are each charged for one, because the
    manager appends a CLUT to each texture's own block. Counting
    distinct CLUTs instead would undercount every blob that shares
    one -- which is every blob this baker emits."""
    total = 0
    for t in textures:
        total += alloc_size(t.width, t.height, t.fmt)
        if t.fmt == gs.PSMT8:
            total += alloc_size(16, 16, gs.PSMCT32)
    return total


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
    # THREE NUMBERS, BECAUSE TWO OF THEM WERE BEING CONFLATED.
    #
    # The first version of this line printed payload against the budget
    # figure and called the difference "what P3c would have to
    # reclaim". Most of it is not there to reclaim: the budget model
    # charges 8 KiB pages, and the allocator this runtime actually uses
    # charges 256-byte blocks (see the module docstring). On channel6
    # that gap was 178 KiB, of which 84% is pessimism nothing ever
    # allocated.
    #
    # So: payload is what the texels weigh, `allocator` is what
    # ps2ui_upload's preflight computes and gsKit commits, and
    # `budget-charged` is the conservative figure the bake refuses
    # against. Only the first gap is a prize. The second is headroom
    # the budget is deliberately holding back, and worth seeing for its
    # own sake -- channel6 books half the budget where the allocator
    # takes under a third.
    committed = alloc_total(textures)
    lines.append(
        f"  payload {payload_total} B -> allocator {committed} B "
        f"-> budget-charged {total} B"
    )
    lines.append(
        f"  reclaimable {committed - payload_total} B "
        f"({100 * (committed - payload_total) // max(committed, 1)}% of "
        f"committed) -- the rest of the gap to {total} B is the budget "
        f"model's pessimism, which nothing allocates and P3c cannot reclaim"
    )
    lines.append(
        f"  textures {total} B of {budget} B budget "
        f"({100 * total // max(budget, 1)}%)"
    )
    return lines, total, budget, total <= budget
