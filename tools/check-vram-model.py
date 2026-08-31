#!/usr/bin/env python3
"""Hold vram.alloc_size() to the gsKit function it is a port of.

WHY THIS EXISTS. vram.py used to state, as established fact, that
"gsKit allocates page-granular, so a texture's true footprint is its
page-rounded size". It is not: the runtime binds through
gsKit_TexManager_bind, which sizes with gsKit_texture_size(), and that
counts 256-byte blocks. An 11x11 PSMT8 patch costs 256 B there against
8192 B under the page model. That claim sat in a docstring beside the
code for four format versions, and a PR then quoted the gap it implied
as a saving P3c could reclaim -- 84% of which the allocator never took.

The fix was a port. A port is a second implementation of someone
else's arithmetic, which is the thing this project keeps finding
wrong, and here the original is IN THE TREE and compiles. So it is
checked rather than trusted, over every size the baker can emit rather
than the handful anyone would think to spot-check.

Skips with a message if there is no C compiler; it is a cross-language
agreement check, not a unit test, and a silent pass would be worse
than an announced skip.
"""
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "packages", "baker"))
VENDOR = os.path.join(ROOT, "runtime", "vendor", "gsKit")

# THE TWO NUMBERINGS ARE NOT THE SAME, and conflating them is how the
# first run of this check reported 22,436 disagreements that were not
# disagreements. The baker's gs.py numbers its own formats PSMT8=0,
# PSMCT32=1; the GS hardware values are GS_PSM_CT32=0 and GS_PSM_T8=19.
# Both are called "psm" everywhere they appear. ps2ui.c:592 does this
# same translation and is the reason the runtime gets it right.
_GS_PSM = {1: 0, 0: 19}          # baker fmt -> GS_PSM_*

DRIVER = r"""
#include <stdio.h>
#include <stdlib.h>
#include "gsKit.h"
u32 gsKit_texture_size(int width, int height, int psm);
int main(void) {
    int w, h, psm;
    while (scanf("%d %d %d", &w, &h, &psm) == 3)
        printf("%u\n", gsKit_texture_size(w, h, psm));
    return 0;
}
"""


def build(tmp):
    cc = os.environ.get("CC", "cc")
    obj = os.path.join(tmp, "gstex.o")
    src = os.path.join(tmp, "driver.c")
    exe = os.path.join(tmp, "driver")
    with open(src, "w") as fh:
        fh.write(DRIVER)
    inc = ["-I" + VENDOR, "-I" + os.path.join(ROOT, "runtime", "vendor", "host-shim")]
    subprocess.run([cc, "-std=c99", "-O2", "-c", "-DF_gsKit_texture_size"]
                   + inc + [os.path.join(VENDOR, "src", "gsTexture.c"), "-o", obj],
                   check=True, capture_output=True)
    subprocess.run([cc, "-std=c99", "-O2"] + inc + [src, obj, "-o", exe],
                   check=True, capture_output=True)
    return exe


def main():
    from ps2ui_bake import gs, vram

    # Every size the baker can emit, not a sample: atlases, coverage
    # patches, CLUTs and streamed reservations all land in here, and
    # the alignment groups switch at 2/4/8 blocks -- boundaries a
    # hand-picked list is exactly what misses.
    cases = []
    for fmt in (gs.PSMCT32, gs.PSMT8):
        for w in list(range(1, 145)) + [160, 192, 200, 256, 320, 512]:
            for h in list(range(1, 145)) + [160, 192, 200, 256, 320, 512]:
                cases.append((w, h, fmt))

    try:
        with tempfile.TemporaryDirectory() as tmp:
            exe = build(tmp)
            stdin = "\n".join("%d %d %d" % (w, h, _GS_PSM[fmt])
                              for w, h, fmt in cases)
            out = subprocess.run([exe], input=stdin, capture_output=True,
                                 text=True, check=True).stdout.split()
    except FileNotFoundError:
        print("ok - SKIPPED: no C compiler, so the port is unchecked here")
        return 0
    except subprocess.CalledProcessError as exc:
        print("not ok - could not build the gsKit reference: %s"
              % (exc.stderr or b"").strip()[:200])
        return 1

    if len(out) != len(cases):
        print("not ok - reference produced %d of %d answers"
              % (len(out), len(cases)))
        return 1

    bad = []
    for (w, h, fmt), ref in zip(cases, out):
        mine = vram.alloc_size(w, h, fmt)
        if mine != int(ref):
            bad.append((w, h, fmt, mine, int(ref)))
    for w, h, fmt, mine, ref in bad[:8]:
        print("not ok - %dx%d psm=%d: port says %d, gsKit says %d"
              % (w, h, fmt, mine, ref))
    if bad:
        print("not ok - %d of %d sizes disagree" % (len(bad), len(cases)))
        return 1
    print("ok - alloc_size agrees with gsKit_texture_size on %d sizes"
          % len(cases))
    # And the two models must actually differ, or the port is checking
    # nothing that matters: the whole point is that the budget figure
    # is not the allocator figure.
    gap = sum(1 for (w, h, fmt) in cases
              if vram.alloc_size(w, h, fmt) != vram.page_rounded_size(w, h, fmt))
    if not gap:
        print("not ok - the two models never differ, so this proves nothing")
        return 1
    print("ok - and differs from the page model on %d of them, which is "
          "why both are reported" % gap)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
