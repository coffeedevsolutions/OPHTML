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
import re
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
    def __init__(self, dest, force=False, starter=False):
        self.dest = dest
        self.force = force
        self.starter = starter


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


class StarterTest(unittest.TestCase):
    """`vendor-runtime --starter`, whose rules are the opposite of the
    runtime pair's on purpose.

    ps2ui.c and ps2ui.h must stay matched, so a drifted one stops the
    command. main.c and the Makefile are a starting point that exists
    to be edited, so a drifted one is left alone and reported -- and
    the command still succeeds. Getting that backwards would turn
    "you edited your own main" into an error, which is what the first
    draft of this did.
    """

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self._saved = (vendor._PACKAGED, vendor._CHECKOUT)
        self.addCleanup(self._restore)
        d = os.path.join(self.tmp, "pkg")
        os.makedirs(d)
        for f in vendor.FILES:
            with open(os.path.join(d, f), "w") as fh:
                fh.write("/* runtime */ " + f)
        vendor._PACKAGED = d
        vendor._CHECKOUT = os.path.join(self.tmp, "absent")
        self.dest = os.path.join(self.tmp, "someproject")

    def _restore(self):
        vendor._PACKAGED, vendor._CHECKOUT = self._saved

    def test_no_starter_by_default(self):
        rc, out = run_quiet(Args(self.dest))
        self.assertEqual(rc, 0)
        for f in vendor.STARTER_FILES:
            self.assertFalse(os.path.exists(os.path.join(self.dest, f)),
                             "%s was written without --starter" % f)

    def test_starter_writes_both_files_from_the_package(self):
        rc, out = run_quiet(Args(self.dest, starter=True))
        self.assertEqual(rc, 0)
        for f in vendor.STARTER_FILES:
            got = os.path.join(self.dest, f)
            self.assertTrue(os.path.exists(got), "%s not written" % f)
            with open(got, "rb") as a, \
                    open(os.path.join(vendor._STARTER, f), "rb") as b:
                self.assertEqual(a.read(), b.read())

    def test_an_edited_main_is_left_alone_and_is_not_an_error(self):
        os.makedirs(self.dest)
        mine = os.path.join(self.dest, "main.c")
        with open(mine, "w") as fh:
            fh.write("/* six months of my app */\n")
        rc, out = run_quiet(Args(self.dest, starter=True))
        self.assertEqual(rc, 0)
        with open(mine) as fh:
            self.assertEqual(fh.read(), "/* six months of my app */\n")
        self.assertIn("already here", out)
        # and the file that was NOT there still lands
        self.assertTrue(os.path.exists(os.path.join(self.dest, "Makefile")))

    def test_force_replaces_an_edited_starter(self):
        os.makedirs(self.dest)
        with open(os.path.join(self.dest, "main.c"), "w") as fh:
            fh.write("/* mine */\n")
        rc, out = run_quiet(Args(self.dest, starter=True, force=True))
        self.assertEqual(rc, 0)
        with open(os.path.join(self.dest, "main.c"), "rb") as a, \
                open(os.path.join(vendor._STARTER, "main.c"), "rb") as b:
            self.assertEqual(a.read(), b.read())

    def test_the_message_changes_with_the_flag(self):
        _, plain = run_quiet(Args(os.path.join(self.tmp, "a")))
        _, started = run_quiet(Args(os.path.join(self.tmp, "b"), starter=True))
        # Without it: the three build lines, and a pointer to the flag.
        self.assertIn("--starter", plain)
        self.assertIn("EE_CFLAGS", plain)
        # With it: what to run, and no instructions for a Makefile the
        # reader has already been handed.
        self.assertIn("buildable project", started)
        self.assertNotIn("your Makefile needs these three lines", started)

    # THE ONE COPY. vendor.py prints the gsKit wiring for somebody
    # integrating into an app they already have, and the starter
    # Makefile carries it as build rules. Two statements of one fact
    # that moves whenever the ps2dev image moves gsKit -- so the
    # message reads the Makefile rather than restating it, and this is
    # what holds the extraction to the file.
    def test_the_printed_build_line_matches_the_makefile_default(self):
        """The blob path the message names is the Makefile's own default.

        BOTH SPELLINGS OF THIS WERE WRONG BEFORE THIS TEST EXISTED, in
        opposite directions, and nothing caught either. The message said
        "put your baked blob beside it" and passed `UIB=build/ui.uib`,
        which fails for the layout that sentence describes; correcting
        it to `UIB=ui.uib` then failed for the DEFAULT layout, which is
        the common one, since `ps2ui build` writes `build/ui.uib` and
        the Makefile defaults `UIB` to the same path.

        So the message names neither: plain `make` is right whenever the
        blob is where `ps2ui build` puts it, and that is what this pins.
        `_gskit_lines()` has been held to the Makefile this way since it
        shipped; the build line was the one piece of printed wiring that
        was not.
        """
        import io, contextlib
        mk = os.path.join(vendor._STARTER, "Makefile")
        with open(mk) as fh:
            body = fh.read()
        m = re.search(r"^UIB \?= (\S+)$", body, re.M)
        self.assertIsNotNone(m, "the starter Makefile has no UIB default")
        default = m.group(1)

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            vendor._say_build("PROJDIR")
        out = buf.getvalue()

        self.assertIn("PROJDIR/%s" % default, out,
                      "the message must name the Makefile's own default "
                      "blob path, not a second spelling of it")
        # THE COMMAND LINE ITSELF, not the whole message: the trailing
        # sentence names `make UIB=<path>` on purpose, for a blob kept
        # somewhere else, so asserting over `out` as a whole passes on
        # both defects. A first version of this test did exactly that
        # and caught only one of the two spellings it exists for.
        cmd = [ln for ln in out.splitlines() if "docker run" in ln]
        self.assertEqual(len(cmd), 1, out)
        self.assertNotIn("UIB=", cmd[0],
                         "the default layout needs no UIB= at all, and "
                         "naming any path here is wrong for one of the "
                         "two layouts")
        self.assertTrue(cmd[0].rstrip().endswith("make"), cmd[0])

    def test_the_printed_wiring_is_the_makefile_s(self):
        mk = os.path.join(vendor._STARTER, "Makefile")
        with open(mk) as fh:
            body = fh.read()
        self.assertIn("# >>> gskit wiring", body)
        self.assertIn("# <<< gskit wiring", body)
        for line in vendor._gskit_wiring().split("\n"):
            self.assertIn(line.strip(), body)
        self.assertEqual(len(vendor._gskit_wiring().split("\n")), 3)

    def test_a_moved_marker_is_an_error_not_a_shorter_message(self):
        import tempfile as _tf
        saved = vendor._STARTER
        self.addCleanup(setattr, vendor, "_STARTER", saved)
        d = _tf.mkdtemp()
        self.addCleanup(shutil.rmtree, d, True)
        with open(os.path.join(d, "Makefile"), "w") as fh:
            fh.write("EE_CFLAGS += -I$(PS2DEV)/gsKit/include\n")
        vendor._STARTER = d
        del vendor._GSKIT_CACHE[:]
        self.addCleanup(vendor._GSKIT_CACHE.clear)
        with self.assertRaises(RuntimeError):
            vendor._gskit_wiring()

    # THE IMPORT-TIME RAISE, which is what this looked like before.
    # Reading the starter Makefile at module scope meant a missing
    # starter killed `vendor-runtime` in the form that needs no
    # starter -- before argument handling, with a bare traceback, in a
    # module where every other failure explains itself. Deferring the
    # read to the one place that prints the lines is the fix; this is
    # what says the fix is still in place.
    def test_a_missing_starter_does_not_break_the_plain_command(self):
        saved = vendor._STARTER
        self.addCleanup(setattr, vendor, "_STARTER", saved)
        self.addCleanup(vendor._GSKIT_CACHE.clear)
        vendor._STARTER = os.path.join(self.tmp, "no-starter-here")
        del vendor._GSKIT_CACHE[:]
        rc, out = run_quiet(Args(self.dest))
        self.assertEqual(rc, 0)
        for f in vendor.FILES:
            self.assertTrue(os.path.exists(os.path.join(self.dest, f)))

    # And asking for a starter this install does not carry is a
    # sentence, not a traceback. Same reasoning as the plain command
    # above, one step further in: the runtime pair has already landed,
    # so the failure must not read like nothing worked.
    def test_asking_for_an_absent_starter_explains_itself(self):
        from ps2ui_bake.project import ProjectError
        saved = vendor._STARTER
        self.addCleanup(setattr, vendor, "_STARTER", saved)
        self.addCleanup(vendor._GSKIT_CACHE.clear)
        vendor._STARTER = os.path.join(self.tmp, "no-starter-here")
        del vendor._GSKIT_CACHE[:]
        with self.assertRaises(ProjectError) as caught:
            run_quiet(Args(self.dest, starter=True))
        self.assertIn("carries no starter", str(caught.exception))
        # ...and the runtime still landed, which is what the message says
        for f in vendor.FILES:
            self.assertTrue(os.path.exists(os.path.join(self.dest, f)))
