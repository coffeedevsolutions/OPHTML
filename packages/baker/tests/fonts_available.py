"""Whether this machine has the fonts, and what to do when it does not.

WHY THIS IS ITS OWN MODULE. It started inside test_baker.py, and then
test_serve.py turned out to need the same answer: its build- and
dev-driving tests hand the CLI a project whose fonts come from
fonts/fonts.json, so they fail on a machine with no DejaVu exactly as
test_baker's did. Copying the helper across would have made two
answers to one question, which is the defect this repository has now
found three times -- the suite's own TTF list against the manifest's,
ttfs() against load_font_manifest, and the two lists fonts.json
replaced. So it is imported, not duplicated.
"""
import os
import sys
import unittest

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..")
FONTS = os.path.join(ROOT, "fonts")
METRICS = os.path.join(FONTS, "default.metrics.json")

sys.path.insert(0, os.path.join(ROOT, "packages", "baker"))


# ONE LIST OF CANDIDATE FONTS, AND IT IS fonts/fonts.json.
#
# This used to be two hardcoded Linux paths while fonts.json carried
# six. Two lists for one job, and the shorter one was the one the test
# suite believed -- so the suite could not find a font on a machine the
# baker itself would have been fine on. The manifest is the thing the
# product reads; the tests read it too, and a path added for a user is
# added for the suite in the same edit.
def _manifest_ttf():
    try:
        from ps2ui_bake.cli import load_font_manifest
        return load_font_manifest(os.path.join(FONTS, "fonts.json"))
    except Exception:
        # Any reason at all: no manifest, no candidate on this machine,
        # a face missing. The caller's question is "can I build an
        # atlas", and every one of those answers it "no".
        return None


_MANIFEST = _manifest_ttf()
TTF = _MANIFEST["regular"]["ttf"] if _MANIFEST else None


# A MISSING FONT IS A SKIP, NOT AN ERROR, AND NOT A DECORATOR.
#
# With no TTF this suite used to report `errors=22` across seven
# classes -- a stranger's first `python3 -m unittest discover`, on any
# machine without DejaVu at one of two Linux paths, after they had done
# everything the tutorial asked. Four `skipIf(TTF is None)` sites
# existed and seven classes needed one.
#
# Decorating the other fifteen methods was the obvious fix and is the
# worse one, twice over. Class-level guards would skip 25 tests that do
# not touch a font and pass without one; method-level guards are
# fifteen things to remember, and the sixteenth test to reach for a
# font gets an error again. So the guard lives where the font is
# actually fetched: raising SkipTest from inside a test body is a skip,
# so every present and future path to a font is covered by the fetch
# rather than by a habit.
def require_ttf():
    if TTF is None:
        _no_fonts("no DejaVu Sans on this machine")
    return TTF


# ...AND WHERE IT MUST NOT BE QUIET, IT IS NOT.
#
# The same tripwire and the same wording as PS2UI_REQUIRE_CROSSCHECK
# and PS2UI_REQUIRE_EXAMPLES. A skip is the right answer on a stranger's
# laptop and the wrong one in CI, where the fonts are installed on
# purpose: 22 silent skips there would mean the kerning tables, the
# cross-language pen agreement and the slot spacing all stopped being
# checked, with the run still green. CI sets this, so a skip that
# should be impossible is a failure that names itself.
def _no_fonts(why):
    if os.environ.get("PS2UI_REQUIRE_FONTS") == "1":
        raise AssertionError(
            "PS2UI_REQUIRE_FONTS=1 but %s. This environment is supposed to "
            "have the fonts fonts/fonts.json names, so this is a broken "
            "environment rather than a test to skip." % why)
    raise unittest.SkipTest(
        "%s. fonts/fonts.json lists the paths that are looked in; install "
        "DejaVu Sans or add yours to that file." % why)


def require_raqm():
    """Both conditions, because the test needs both.

    A TTF alone is not enough for the fontgen success path: without
    Pillow's Raqm layout engine every advance comes out identical and
    the kern table comes out empty, which is exactly the silent wrong
    answer fontgen refuses to write. Guarding this on the TTF alone
    would turn "no Raqm" into a failure that reads like a kerning bug.
    """
    require_ttf()
    from PIL import features
    if not features.check("raqm"):
        _no_fonts("this Pillow has no Raqm layout engine")
