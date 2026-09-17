#!/usr/bin/env python3
"""No two header logos carry the same version in their artwork.

WHY THIS IS NOT IN check-versions.py. That file is ci.yml's first step
precisely because it needs no build and no toolchain -- a disagreement
there means the rest of the run is measuring something that does not
know what it is. This check decodes a PNG, so it needs Pillow, so it
cannot go there without putting an install in front of the cheapest
check in the repository.

WHAT IT CATCHES, AND WHAT IT DOES NOT. `docs/assets/` holds one logo
per release, staged ahead of time, differing by one digit in the
filename and one digit in the artwork. Rule 10b reads the filename,
which is the half a regex can hold; the version rendered into the
pixels is the half it cannot, and staging made that gap wider by
keeping three unreferenced files around to be swapped in months later
by somebody who did not export them.

This asserts that the version line -- a fixed band in every export --
is DISTINCT across the directory. So a duplicated export (`cp` the
0.7.0 file to the 0.8.0 name, the likeliest mis-export) fails, because
the two bands are identical.

It does NOT read the glyphs, so a logo whose artwork says `1.2.3`
collides with nothing and passes. This catches duplication, not
correctness; correctness still needs somebody to open the file, which
is what docs/releasing.md step 5 and docs/assets/README.md both say.

A WHOLE-FILE HASH WOULD NOT DO. It differs on any incidental pixel, so
a re-export carrying the wrong version passes it while failing this;
the two fail on opposite things, and this is the one that matters here.

Proposed in review of the change that staged the logos, deferred to the
cut that first had four of them to compare.
"""

import hashlib
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(ROOT, "docs", "assets")
NAME = re.compile(r"^ophtml-logo-releaseVersion(\d+)-plain-white-darkbg\.png$")

# The band the version line occupies in every export to date. Read off
# the committed files rather than guessed: the text sits at y=481..501
# on a 640-tall canvas, and the margin either side absorbs a re-export
# that moves it by a pixel or two without swallowing the barcode above.
CROP = (360, 475, 930, 508)
SIZE = (1280, 640)


def main():
    try:
        from PIL import Image
    except ImportError:
        print("not ok - check-logo-artwork needs Pillow, which the baker "
              "already requires: python3 -m pip install Pillow")
        return 2

    logos = sorted(n for n in os.listdir(ASSETS) if NAME.match(n))
    if len(logos) < 2:
        print("ok - %d header logo(s); nothing to compare" % len(logos))
        return 0

    bands, fails = {}, []
    for name in logos:
        im = Image.open(os.path.join(ASSETS, name))
        if im.size != SIZE:
            fails.append("not ok - %s is %dx%d, not %dx%d; the crop this "
                         "rule reads is only meaningful at the standard "
                         "size" % ((name,) + im.size + SIZE))
            continue
        digest = hashlib.sha256(
            im.convert("L").crop(CROP).tobytes()).hexdigest()
        bands.setdefault(digest, []).append(name)

    for digest, names in sorted(bands.items()):
        if len(names) > 1:
            fails.append(
                "not ok - these carry an IDENTICAL version line in their "
                "artwork: %s. One of them is a copy of another under a new "
                "name, so its filename promises a version the pixels do not "
                "show. Re-export the wrong one -- docs/releasing.md step 5, "
                "docs/assets/README.md." % ", ".join(names))

    for line in fails:
        print(line)
    if fails:
        print("not ok - %d header logo problem(s)" % len(fails))
        return 1
    print("ok - %d header logos, %d distinct version lines in the artwork"
          % (len(logos), len(bands)))
    print("#    Distinctness only. Nothing here reads the glyphs, so a "
          "logo naming a version no other file uses passes; step 5 says "
          "to open it.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
