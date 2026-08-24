"""The v6 arena requirement, computed from a baked blob.

`ps2ui_load` no longer sizes itself from PS2UI_MAX_* ceilings: it carves
one caller-provided block, and the caller has to know how big it is
before running anything. This is the host-side mirror of `arena_compute`
in runtime/ps2ui.c, so `ps2ui-bake` and `ps2ui-check` can print the
number an integrator needs to declare a static buffer.

THE NUMBER IS TARGET-DEPENDENT, which is the only subtle thing here.
The arena holds an array of gsKit's GSTEXTURE, and that struct contains
two pointers (`u32 *Mem`, `u32 *Clut`). On the EE they are 4 bytes; on a
64-bit host they are 8, so the same blob needs a different arena in the
sample ELF than in the host test suite. Reporting one number without
saying which target it belongs to would be wrong roughly half the time,
so both are computed and the console one is the headline -- that is
where the static buffer actually lives.

test_arena_matches_runtime proves this file agrees with the C: two
implementations that agree is evidence, one restating the other's
comments is not.
"""

# GSTEXTURE, from runtime/vendor/gsKit/gsInit.h (u32 Width, u32 Height,
# u8 PSM, u8 ClutPSM, u32 TBW, u32 *Mem, u32 *Clut, u32 Vram,
# u32 VramClut, u32 Filter, u8 ClutStorageMode, u8 Delayed), laid out by
# the ordinary C rules rather than by a remembered total.
_GSTEXTURE_FIELDS = [
    (4, 4), (4, 4),          # Width, Height
    (1, 1), (1, 1),          # PSM, ClutPSM
    (4, 4),                  # TBW
    ("ptr", "ptr"), ("ptr", "ptr"),   # Mem, Clut
    (4, 4), (4, 4), (4, 4),  # Vram, VramClut, Filter
    (1, 1), (1, 1),          # ClutStorageMode, Delayed
]

EE_PTR = 4     # mips64r5900el-ps2-elf: 32-bit pointers
HOST64_PTR = 8


def sizeof_gstexture(ptr_size: int = EE_PTR) -> int:
    off = 0
    align_max = 1
    for size, align in _GSTEXTURE_FIELDS:
        if size == "ptr":
            size = align = ptr_size
        off = (off + align - 1) // align * align
        off += size
        align_max = max(align_max, align)
    return (off + align_max - 1) // align_max * align_max


def arena_size(uib, ptr_size: int = EE_PTR) -> int:
    """Bytes ps2ui_load needs for `uib`, for a target with this pointer
    size. Mirrors arena_compute's regions in the same order."""
    total = 0
    total += len(uib.cluts) * 256 * 4                  # permuted CLUTs
    total += len(uib.textures) * sizeof_gstexture(ptr_size)
    total += len(uib.slots) * 4                        # slot_off[]
    total += ((len(uib.focus) + 31) // 32) * 4         # hidden bits
    total += len(uib.screens) * 2                      # screen_focus[]
    for sl in uib.slots:
        total += sl["capacity"] + 1                    # slot text
    total += len(uib.slots)                            # slot_is_set
    return total


def breakdown(uib, ptr_size: int = EE_PTR) -> list:
    """(region, bytes) pairs, for a report that says where it went."""
    return [
        ("permuted CLUTs", len(uib.cluts) * 256 * 4),
        ("texture handles", len(uib.textures) * sizeof_gstexture(ptr_size)),
        ("slot text", sum(sl["capacity"] + 1 for sl in uib.slots)),
        ("slot offsets", len(uib.slots) * 4),
        ("visibility bits", ((len(uib.focus) + 31) // 32) * 4),
        ("screen focus", len(uib.screens) * 2),
        ("slot set flags", len(uib.slots)),
    ]
