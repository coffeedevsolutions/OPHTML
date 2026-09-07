"""`ps2ui vendor-runtime`: where the C comes from, and when it refuses.

WHAT IS WORTH FENCING HERE AND WHAT IS NOT. The file contents are not:
they are `runtime/ps2ui.c` byte for byte, and asserting that a copy is a
copy would be a test of shutil. What is worth fencing is the RESOLUTION
-- which of two candidate directories it reads, what it does when both
exist, and what it does when neither does.

That is where the bug was. The first manual test of the checkout
fallback reported "the installed package", because an earlier
`python -m build` had left a staged copy on disk and the fallback never
ran at all. The test would have passed while testing nothing, which is
this repository's most-repeated defect and the reason every case below
constructs its own directories rather than trusting the tree it runs in.
"""
import contextlib
import io
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))

from ps2ui_bake import vendor                                  # noqa: E402
from ps2ui_bake.project import ProjectError                    # noqa: E402


def run_quiet(args):
    """Call the command with its stdout captured.

    The command PRINTS -- what it wrote, where the source was, what to do
    next -- because a person running it needs that. A test suite does
    not, and eleven cases spraying it makes a real failure harder to see.
    """
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = vendor.cmd_vendor_runtime(args)
    return rc, buf.getvalue()


class Args(object):
    def __init__(self, dest, force=False):
        self.dest = dest
        self.force = force


class VendorRuntimeTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        # Both module-level candidates are repointed for every case, so
        # no test depends on whether this checkout happens to have been
        # built. Saved and restored rather than assumed.
        self._saved = (vendor._PACKAGED, vendor._CHECKOUT)
        self.addCleanup(self._restore)

    def _restore(self):
        vendor._PACKAGED, vendor._CHECKOUT = self._saved

    def _make(self, name, body="/* c */"):
        d = os.path.join(self.tmp, name)
        os.makedirs(d)
        for f in vendor.FILES:
            with open(os.path.join(d, f), "w") as fh:
                fh.write(body + " " + f)
        return d

    # 1. An install: package data present, no checkout beside it.
    def test_installed_package_is_used(self):
        vendor._PACKAGED = self._make("pkg")
        vendor._CHECKOUT = os.path.join(self.tmp, "absent")
        src, label = vendor.find_source()
        self.assertEqual(src, vendor._PACKAGED)
        self.assertEqual(label, "the installed package")

    # 2. A checkout that has never been built: no staged copy.
    #
    #    This is the case the first manual test SILENTLY SKIPPED, so it
    #    asserts the label as well as the path -- the path alone would
    #    still pass if the two candidates pointed at the same place.
    def test_checkout_fallback_when_nothing_is_staged(self):
        vendor._PACKAGED = os.path.join(self.tmp, "absent")
        vendor._CHECKOUT = self._make("repo")
        src, label = vendor.find_source()
        self.assertEqual(src, vendor._CHECKOUT)
        self.assertEqual(label, "this checkout")

    # 3. Both present and in agreement: the CHECKOUT answers, and says
    #    so. A complete _CHECKOUT means we are in one, so the staged
    #    copy beside the module is a build artifact -- calling it "the
    #    installed package" was the exact misreading find_source()
    #    exists to catch, printed by the line meant to prevent it.
    #    Caught in review of #114.
    def test_both_present_and_identical(self):
        vendor._PACKAGED = self._make("pkg", "/* same */")
        vendor._CHECKOUT = self._make("repo", "/* same */")
        src, label = vendor.find_source()
        self.assertEqual(src, vendor._CHECKOUT)
        self.assertEqual(label, "this checkout")

    def test_never_calls_a_staged_copy_an_install(self):
        vendor._PACKAGED = self._make("pkg", "/* same */")
        vendor._CHECKOUT = self._make("repo", "/* same */")
        _, label = vendor.find_source()
        self.assertNotEqual(label, "the installed package")

    # 4. Both present and DISAGREEING: refuse.
    #
    #    A built checkout keeps its staged copy on disk, gitignored but
    #    real, so the day somebody edits runtime/ps2ui.c without
    #    rebuilding there are two copies and the stale one shadows the
    #    canonical one. Ordering would resolve this silently and hand
    #    out the wrong file.
    def test_both_present_and_drifted_refuses(self):
        vendor._PACKAGED = self._make("pkg", "/* old */")
        vendor._CHECKOUT = self._make("repo", "/* new */")
        with self.assertRaises(vendor._Stale) as caught:
            vendor.find_source()
        self.assertEqual(sorted(caught.exception.names),
                         sorted(vendor.FILES))

    #    ...and the drift is per-file, not all-or-nothing: one moved
    #    header is still a disagreement.
    def test_drift_in_one_file_only(self):
        vendor._PACKAGED = self._make("pkg", "/* same */")
        vendor._CHECKOUT = self._make("repo", "/* same */")
        with open(os.path.join(vendor._CHECKOUT, "ps2ui.h"), "a") as fh:
            fh.write("\n/* later */\n")
        with self.assertRaises(vendor._Stale) as caught:
            vendor.find_source()
        self.assertEqual(caught.exception.names, ["ps2ui.h"])

    # 5. Neither: the packaging bug F26 exists to prevent, so the
    #    message has to name it rather than just listing two paths.
    def test_neither_present(self):
        vendor._PACKAGED = os.path.join(self.tmp, "a")
        vendor._CHECKOUT = os.path.join(self.tmp, "b")
        src, label = vendor.find_source()
        self.assertIsNone(src)
        with self.assertRaises(ProjectError) as caught:
            run_quiet(Args(self.tmp))
        self.assertIn("packaging bug", str(caught.exception))

    # 6. An incomplete candidate is not a candidate. Half a runtime is
    #    worse than none: it compiles until it does not.
    def test_partial_candidate_is_skipped(self):
        vendor._PACKAGED = self._make("pkg")
        os.remove(os.path.join(vendor._PACKAGED, "ps2ui.h"))
        vendor._CHECKOUT = self._make("repo")
        src, label = vendor.find_source()
        self.assertEqual(src, vendor._CHECKOUT)
        self.assertEqual(label, "this checkout")

    # 7. Writing: both files land, and their bytes are the source's.
    def test_writes_both_files(self):
        vendor._PACKAGED = self._make("pkg", "/* payload */")
        vendor._CHECKOUT = os.path.join(self.tmp, "absent")
        dest = os.path.join(self.tmp, "someproject")
        rc, out = run_quiet(Args(dest))
        self.assertEqual(rc, 0)
        for f in vendor.FILES:
            with open(os.path.join(dest, f)) as fh:
                self.assertEqual(fh.read(), "/* payload */ " + f)

    # 8. THE MISMATCHED PAIR, which is the case this command will meet
    #    most often: vendor once, upgrade the package, re-run.
    #
    #    The first version skipped the existing ps2ui.c, WROTE a fresh
    #    ps2ui.h beside it, printed "Compile these with your project
    #    against gsKit" and exited 0 -- a split pair with a success
    #    status. ps2ui.c includes that header and is written against its
    #    structs, and PS2UI_VERSION cannot catch it: 7 of 30 commits
    #    touching runtime/ps2ui.c moved it historically, and #110 pledged
    #    the format frozen, so from here none will.
    #
    #    So: nothing is written when anything has drifted, and the exit
    #    is nonzero. Found in review of #114.
    def test_drifted_file_refuses_and_writes_nothing(self):
        vendor._PACKAGED = self._make("pkg", "/* new */")
        vendor._CHECKOUT = os.path.join(self.tmp, "absent")
        dest = os.path.join(self.tmp, "proj")
        os.makedirs(dest)
        mine = os.path.join(dest, "ps2ui.c")
        with open(mine, "w") as fh:
            fh.write("MY EDIT")
        with self.assertRaises(ProjectError) as caught:
            run_quiet(Args(dest))
        self.assertIn("--force", str(caught.exception))
        with open(mine) as fh:
            self.assertEqual(fh.read(), "MY EDIT")
        # THE HALF THAT WAS THE BUG: the other file must not have been
        # written. Asserting only that ps2ui.c survived would pass on
        # the broken version too.
        self.assertFalse(os.path.exists(os.path.join(dest, "ps2ui.h")))

    # ...and an unchanged file is not drift. A re-run with nothing to do
    # says so and exits 0, where the first version reported it in the
    # same words it used for a real disagreement.
    def test_identical_file_is_up_to_date_not_drift(self):
        vendor._PACKAGED = self._make("pkg", "/* payload */")
        vendor._CHECKOUT = os.path.join(self.tmp, "absent")
        dest = os.path.join(self.tmp, "proj")
        rc, _ = run_quiet(Args(dest))
        self.assertEqual(rc, 0)
        rc, out = run_quiet(Args(dest))
        self.assertEqual(rc, 0)
        self.assertIn("up to date", out)
        self.assertNotIn("wrote ", out)

    def test_force_overwrites(self):
        vendor._PACKAGED = self._make("pkg", "/* new */")
        vendor._CHECKOUT = os.path.join(self.tmp, "absent")
        dest = os.path.join(self.tmp, "proj")
        os.makedirs(dest)
        mine = os.path.join(dest, "ps2ui.c")
        with open(mine, "w") as fh:
            fh.write("MY EDIT")
        run_quiet(Args(dest, force=True))
        with open(mine) as fh:
            self.assertNotEqual(fh.read(), "MY EDIT")


class ShippedListTest(unittest.TestCase):
    """setup.py and vendor.py name the same two files, separately.

    They have to agree or the wheel carries something the command does
    not hand out, or the command reaches for something the wheel does
    not have -- and the second is a FileNotFoundError on a stranger's
    machine. Two lists in two files is exactly the shape this repository
    keeps finding stale, so it is read back rather than trusted.
    """

    def test_setup_py_and_vendor_agree(self):
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        setup_py = os.path.join(root, "setup.py")
        if not os.path.exists(setup_py):
            self.skipTest("no setup.py (installed package, not a checkout)")
        src = open(setup_py).read()
        # The literal, read out of the source rather than imported:
        # importing setup.py runs stage_runtime() and would copy files
        # as a side effect of collecting tests.
        import ast
        tree = ast.parse(src)
        shipped = None
        for node in ast.walk(tree):
            if (isinstance(node, ast.Assign)
                    and any(getattr(t, "id", None) == "SHIPPED"
                            for t in node.targets)):
                shipped = tuple(ast.literal_eval(node.value))
        self.assertIsNotNone(shipped, "setup.py has no SHIPPED literal")
        self.assertEqual(shipped, vendor.FILES)


if __name__ == "__main__":
    unittest.main()
