#!/usr/bin/env python3
"""Turn art into texels a PS2 can DMA, for the Phase 1 streaming bench.

`ps2ui_tex_set` takes DECODED texels and copies nothing -- the pointer
becomes the slot's DMA source. There is no image decoder on the EE and
ps2ui does not want one: the app owns device I/O and decoding, which is
the same split the slot text API has. So art is converted here, on the
host, and the console reads a file that is already a texture.

Output is a bare `.raw`: exactly width * height * 4 bytes of PSMCT32,
row-major, no header. Bare on purpose. The ELF reads it straight into a
16-aligned buffer and hands that buffer to ps2ui_tex_set, so anything
in front of the texels would have to be stripped by a copy -- and the
whole argument for the zero-copy contract is that no copy happens. The
ELF checks the file's SIZE instead, which is the same guarantee a
header would have given and costs nothing at runtime.

THE ALPHA TRAP, which is the reason this file exists rather than a one
line PIL call. The GS treats 0x80 as fully opaque, not 0xFF: the blend
this runtime asserts every frame is

    Cv = (Cs - Cd) * As >> 7 + Cd

so an opaque pixel written as 255 asks the GS for roughly twice the
coverage it has, and composites about 2x overbright against whatever is
underneath. Every alpha here goes through the same css_alpha_to_gs the
baker uses, so a streamed cover and a baked one land in one domain.
This is backlog B1 arriving on a new path; converting art with a plain
`img.tobytes("raw", "RGBA")` would reintroduce it.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "packages", "baker"))

from ps2ui_bake.rounding import css_alpha_to_gs        # noqa: E402


def encode(pixels) -> bytes:
    """(r, g, b, a255) in CSS domain -> PSMCT32 bytes."""
    out = bytearray()
    for r, g, b, a in pixels:
        out += bytes((r, g, b, css_alpha_to_gs(a)))
    return bytes(out)


def convert(path: str, w: int, h: int) -> bytes:
    from PIL import Image
    img = Image.open(path).convert("RGBA")
    if img.size != (w, h):
        # Cover-fit then centre-crop, so a 4:3 box art does not come out
        # squashed. The reservation is one fixed size and the blob has
        # already told the runtime that number; the picture bends, not
        # the geometry.
        sw, sh = img.size
        scale = max(w / sw, h / sh)
        img = img.resize((max(1, round(sw * scale)), max(1, round(sh * scale))),
                         Image.LANCZOS)
        left = (img.width - w) // 2
        top = (img.height - h) // 2
        img = img.crop((left, top, left + w, top + h))
    return encode(img.getdata())


def synthetic(index: int, w: int, h: int) -> bytes:
    """A cover with no art behind it, for a bench with no drive.

    Deliberately NOT a flat fill or a smooth gradient. Both fail the
    same way a bad instrument always fails here: a flat fill looks
    identical whether the texels arrived or a stale VRAM block is being
    drawn, and a gradient hides a half-texel shift. This draws a coarse
    checker in two per-index hues with a one-texel border and a solid
    corner block, so "which cover is this" and "did it arrive intact"
    are both readable from a photograph at arm's length.
    """
    hues = [(220, 90, 70), (70, 170, 220), (240, 200, 80), (150, 220, 120),
            (210, 120, 220), (120, 200, 200)]
    fg = hues[index % len(hues)]
    bg = tuple(c // 3 for c in fg)
    # Scaled, not fixed. A fixed 16-texel cell made an 8x8 cover come
    # out entirely border -- a flat white fill, identical for every
    # index, which is precisely the "cannot tell texels-arrived from
    # stale-VRAM" failure the self-test below exists to catch. It did.
    cell = max(2, min(16, w // 8, h // 8))
    edge = 2
    px = []
    for y in range(h):
        for x in range(w):
            if x < edge or y < edge or x >= w - edge or y >= h - edge:
                c = (255, 255, 255)          # border: any crop shows
            elif x < edge + cell and y < edge + cell:
                c = (255, 255, 255)          # corner block: orientation
            else:
                c = fg if ((x // cell) + (y // cell)) % 2 else bg
            px.append((c[0], c[1], c[2], 255))
    return encode(px)


def self_test() -> int:
    ok = True

    def check(cond, name):
        nonlocal ok
        print(("ok - " if cond else "not ok - ") + name)
        if not cond:
            ok = False

    raw = synthetic(0, 8, 8)
    check(len(raw) == 8 * 8 * 4, "a cover is exactly w * h * 4 bytes")

    # The trap this file exists for. Opaque must reach the GS as 0x80.
    alphas = set(raw[3::4])
    check(alphas == {0x80},
          "opaque alpha lands in the GS domain (0x80), not 255 -- 255 would "
          "ask for ~2x coverage and composite overbright")

    # Two indices must be distinguishable, or "which cover drew" is not
    # a question the bench can answer.
    check(synthetic(0, 8, 8) != synthetic(1, 8, 8),
          "two synthetic covers differ, so a swap is visible")

    # Not a flat fill: a flat cover cannot tell texels-arrived from
    # stale-VRAM, which is the whole reading of bench step S1.
    body = [raw[i:i + 4] for i in range(0, len(raw), 4)]
    check(len(set(map(bytes, body))) > 2,
          "and carries more than two distinct texels, so a stale block "
          "cannot pass for it")

    # Determinism: the ELF's fallback generates the same pattern on the
    # EE, and a reading that compares them needs both sides fixed.
    check(synthetic(2, 16, 16) == synthetic(2, 16, 16),
          "generation is deterministic");

    # Size is the only integrity check the ELF gets, so it has to bite.
    check(len(synthetic(0, 128, 128)) == 65536,
          "128x128 is 65536 bytes, which is what the blob reserves")

    print("1..6")
    print(("PASS" if ok else "FAIL") + ": make_cover_raw self-test")
    return 0 if ok else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("images", nargs="*", help="source art, in slot order")
    ap.add_argument("-o", "--out-dir", default="covers",
                    help="directory to write cover0.raw.. into")
    ap.add_argument("--size", default="128x128",
                    help="reserved slot size, WxH (must match the blob)")
    ap.add_argument("--count", type=int, default=4,
                    help="how many covers to write (pads with synthetic)")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args(argv)

    if args.self_test:
        return self_test()

    w, h = (int(v) for v in args.size.lower().split("x"))
    os.makedirs(args.out_dir, exist_ok=True)
    for i in range(args.count):
        if i < len(args.images):
            data = convert(args.images[i], w, h)
            src = os.path.basename(args.images[i])
        else:
            data = synthetic(i, w, h)
            src = "synthetic"
        path = os.path.join(args.out_dir, f"cover{i}.raw")
        with open(path, "wb") as fh:
            fh.write(data)
        print(f"make_cover_raw: {path}  {w}x{h}  {len(data)} B  <- {src}",
              file=sys.stderr)
    print(f"make_cover_raw: copy {args.out_dir}/ to the drive as "
          f"ps2ui/ (so the ELF finds mass:/ps2ui/cover0.raw)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
