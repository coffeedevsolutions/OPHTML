#!/usr/bin/env python3
"""Read the step 6 probe's column G -- the CLUT-convention verdict.

The CSM1 permutation is an involution, so from inside the renderer
"applied once" (correct) and "applied zero or two times" (wrong) are
unprovable; only a picture says which side of it a build is on. The
emulator gate cannot be that picture: a wrong convention moves the UI
diff by ~0.02 RMSE, inside the gate's tolerance by design (see hw.yml).
Column G is built for exactly that blindness. Its texels use indices 8
and 16 -- the smallest pair the permutation exchanges -- over a pattern
whose ON share is deliberately off 50%, so the wrong convention swaps
the two colours' AREAS:

    right convention  ->  the band is mostly ORANGE
    wrong convention  ->  the band is mostly TEAL

An area share survives any scaling the capture applies, which is what
lets a machine read it. The reference band directly beneath is drawn
with solid sprites -- no palette fetch -- so it is orange-dominant in
BOTH arms; that is the reader's calibration that it is looking at the
right rectangle, and this reader refuses a verdict without it.

Geometry and colours are parsed out of the C sources the console
compiles, never restated here, so a change to the probe moves this
reader with it rather than leaving it reading the wrong rectangle.

  read_probe6.py CAPTURE --expect permuted   gate the shipped arm
  read_probe6.py CAPTURE --expect linear     gate the falsification arm
  read_probe6.py --self-test                 prove the reader can fail
"""
import argparse
import os
import re
import sys

from PIL import Image

TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
MAIN_C = os.path.join(TOOLS_DIR, "..", "runtime", "sample", "main.c")
PATTERN_H = os.path.join(TOOLS_DIR, "..", "runtime", "sample",
                         "probe6_pattern.h")

CANVAS_W, CANVAS_H = 640, 448

# A pixel belongs to a colour when it sits within this Euclidean RGB
# distance of it. Wide enough for llvmpipe plus the trim step's resize
# to blur edges without orphaning interior pixels; the two colours are
# ~190 apart, so the balls cannot overlap.
NEAR = 60.0

# The verdict is a dominance ratio, not a majority: the pattern's ON
# share is ~59% plus the stripe, so the winning colour carries ~63% of
# the band and the losing one ~37%. Requiring a 1.2x lead means a
# genuinely ambiguous band (edge mush, wrong rectangle, a fault this
# reader does not model) refuses a verdict instead of guessing.
DOMINANCE = 1.2

# Below this classified fraction the band is not made of G's two
# colours at all -- wrong rectangle, dead emulator, or the magenta
# that means the probe's own data is corrupt. No verdict.
MIN_CLASSIFIED = 0.5


def _defines(path, names):
    """Pull `#define NAME value` integers out of a C source."""
    got = {}
    text = open(path).read()
    for name in names:
        m = re.search(r"#define\s+%s\s+(0[xX][0-9a-fA-F]+|\d+)" % name, text)
        if not m:
            raise SystemExit("read_probe6: %s not found in %s" % (name, path))
        got[name] = int(m.group(1), 0)
    return got


def geometry():
    g = _defines(MAIN_C, [
        "P6_W", "P6_H", "P6_GAP", "P6_X0", "P6_TOP_Y", "P6_COLS",
        "P6G_ON_R", "P6G_ON_G", "P6G_ON_B",
        "P6G_OFF_R", "P6G_OFF_G", "P6G_OFF_B",
    ])
    gcol = g["P6_COLS"] - 1  # G is the last column
    x0 = g["P6_X0"] + gcol * (g["P6_W"] + g["P6_GAP"])
    return {
        "tex": (x0, g["P6_TOP_Y"], x0 + g["P6_W"], g["P6_TOP_Y"] + g["P6_H"]),
        "ref": (x0, g["P6_TOP_Y"] + g["P6_H"],
                x0 + g["P6_W"], g["P6_TOP_Y"] + 2 * g["P6_H"]),
        "orange": (g["P6G_ON_R"], g["P6G_ON_G"], g["P6G_ON_B"]),
        "teal": (g["P6G_OFF_R"], g["P6G_OFF_G"], g["P6G_OFF_B"]),
    }


def shares(img, box, orange, teal):
    """(orange, teal, other) pixel fractions of the box, scaled to the
    capture's own size so a frame that is not exactly 640x448 still
    reads."""
    w, h = img.size
    sx, sy = w / CANVAS_W, h / CANVAS_H
    x0, y0, x1, y1 = box
    crop = img.crop((round(x0 * sx), round(y0 * sy),
                     round(x1 * sx), round(y1 * sy))).convert("RGB")
    n_or = n_te = n = 0
    for px in crop.getdata():
        n += 1
        do = sum((a - b) ** 2 for a, b in zip(px, orange)) ** 0.5
        dt = sum((a - b) ** 2 for a, b in zip(px, teal)) ** 0.5
        if do < NEAR:
            n_or += 1
        elif dt < NEAR:
            n_te += 1
    return n_or / n, n_te / n, 1.0 - (n_or + n_te) / n


def read(img, geo):
    """-> ('permuted'|'linear'|'void', explanation)"""
    r_or, r_te, _ = shares(img, geo["ref"], geo["orange"], geo["teal"])
    t_or, t_te, t_other = shares(img, geo["tex"], geo["orange"], geo["teal"])
    print("  reference band: %.0f%% orange, %.0f%% teal" %
          (r_or * 100, r_te * 100))
    print("  textured band : %.0f%% orange, %.0f%% teal, %.0f%% other" %
          (t_or * 100, t_te * 100, t_other * 100))
    if r_or + r_te < MIN_CLASSIFIED or not r_or > r_te * DOMINANCE:
        return "void", ("the reference band is not orange-dominant, so this "
                        "is not column G -- wrong rectangle or bad capture, "
                        "and no verdict survives that")
    if t_or + t_te < MIN_CLASSIFIED:
        return "void", ("the textured band is not made of G's colours -- "
                        "dead texture path, magenta (corrupt probe data), "
                        "or bad capture")
    if t_or > t_te * DOMINANCE:
        return "permuted", "the textured band is orange-dominant"
    if t_te > t_or * DOMINANCE:
        return "linear", "the textured band is teal-dominant"
    return "void", "neither colour dominates; the band is ambiguous"


def synth(geo, tex_on, tex_off, ref_on, ref_off,
          tex_frac=0.63, ref_frac=0.63):
    """A capture with the two bands painted at the given colours."""
    img = Image.new("RGB", (CANVAS_W, CANVAS_H), (26, 14, 10))
    for box, on, off, frac in ((geo["tex"], tex_on, tex_off, tex_frac),
                               (geo["ref"], ref_on, ref_off, ref_frac)):
        x0, y0, x1, y1 = box
        split = x0 + round((x1 - x0) * frac)
        for x in range(x0, x1):
            for y in range(y0, y1):
                img.putpixel((x, y), on if x < split else off)
    return img


def self_test():
    geo = geometry()
    o, t = geo["orange"], geo["teal"]
    grey = (100, 100, 100)
    cases = [
        ("correct arm reads permuted", synth(geo, o, t, o, t), "permuted"),
        ("swapped arm reads linear", synth(geo, t, o, o, t), "linear"),
        ("reference not orange voids", synth(geo, o, t, t, o), "void"),
        ("foreign colours void", synth(geo, grey, grey, o, t), "void"),
        ("balanced textured band voids",
         synth(geo, o, t, o, t, tex_frac=0.5), "void"),
    ]
    failures = 0
    for name, img, want in cases:
        got, why = read(img, geo)
        ok = got == want
        failures += not ok
        print("%s - %s (got %s: %s)" % ("ok" if ok else "not ok", name,
                                        got, why))
    print("self-test:", "PASS" if not failures else "FAIL")
    return 1 if failures else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("capture", nargs="?")
    ap.add_argument("--expect", choices=["permuted", "linear"])
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return self_test()
    if not args.capture or not args.expect:
        ap.error("need CAPTURE and --expect (or --self-test)")
    geo = geometry()
    got, why = read(Image.open(args.capture), geo)
    print("read_probe6: %s -- %s (expected %s)" % (got, why, args.expect))
    return 0 if got == args.expect else 1


if __name__ == "__main__":
    sys.exit(main())
