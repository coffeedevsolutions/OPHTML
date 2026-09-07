"""Put the C runtime into the distribution, from its one canonical copy.

WHY THIS FILE EXISTS AT ALL. Everything else about this package is
declared in pyproject.toml, deliberately; this is the one thing
setuptools cannot express there.

F25: `pip install ophtml` gives a stranger the whole authoring path and
then README.md tells them to "drop runtime/ps2ui.c and runtime/ps2ui.h
into your ps2sdk/gsKit project" -- a repo path, in a package that does
not contain either file. So the console half of the toolchain, which is
the point of the project, required a clone. Phase 4's exit gate says
"without cloning the repo", and the two have contradicted each other
since the gate was written.

WHY A BUILD HOOK RATHER THAN A SECOND COPY IN GIT. `runtime/` is not
inside this package and cannot be reached from it. Both halves of that
were measured rather than assumed:

    package-data "../fakeruntime/ps2ui.c"  -> lands at WHEEL ROOT,
                                              installing into
                                              site-packages/fakeruntime/
    package-data "../../runtime/ps2ui.c"   -> SILENTLY OMITTED,
                                              build succeeds, rc=0,
                                              no warning of any kind

That second line is the same failure the package-data comment in
pyproject.toml already records about serve_page.html: a manifest naming
a file that is not there is not an error to either tool. It is the
reason this file raises rather than warns.

So the copy is made at build time and never committed. A committed
duplicate would be a second copy of 112 KB of C that can go stale, and
the stale second copy is the defect this repository has now found in a
font path list four separate times, in a .pyc that outlived its source,
and in a published claim corrected twice. There is no second copy here
to go stale: git holds exactly one, and the artifact is built from it.

THE THREE STATES THIS HAS TO HANDLE, AND WHY THE THIRD IS FATAL.

  1. Building from the repository. `runtime/` is three levels up. Copy
     it in. This is what `python -m build` does during a release.

  2. Building a wheel from the sdist. `runtime/` is NOT there -- it is
     outside the sdist root -- but the copy made in state 1 was inside
     the package, so the sdist already carries it. Nothing to do, and
     nothing missing. This is the `pip install --no-binary ophtml`
     path, and it is why the copy has to land inside the package rather
     than beside it.

  3. Neither present. That is a distribution with no runtime in it,
     which is exactly the bug F25 exists to fix, arriving silently.
     RAISE. A build that cannot ship the runtime must fail while
     somebody is watching, not produce a wheel that is quietly missing
     the thing the release was about.
"""
import os
import shutil

from setuptools import setup

HERE = os.path.dirname(os.path.abspath(__file__))

# The one canonical home. runtime/ stays where it is: the runtime is a C
# library that this package DISTRIBUTES, not one it owns, and moving it
# under packages/baker/ would invert that and strand ~20 references
# across README, PLAN.md, findings.md, bringup.md and the examples.
CANONICAL = os.path.normpath(os.path.join(HERE, "..", "..", "runtime"))
STAGED = os.path.join(HERE, "ps2ui_bake", "runtime")

# Named one by one rather than globbed. runtime/ also holds the Makefile,
# the sample, the stubs and vendored gsKit, none of which belongs in a
# Python wheel -- and a glob would quietly start shipping whatever lands
# there next.
SHIPPED = ("ps2ui.c", "ps2ui.h")


def stage_runtime():
    """Make state 1 look like state 2, or fail loudly in state 3."""
    have_canonical = all(os.path.exists(os.path.join(CANONICAL, n))
                         for n in SHIPPED)
    have_staged = all(os.path.exists(os.path.join(STAGED, n))
                      for n in SHIPPED)

    if have_canonical:
        os.makedirs(STAGED, exist_ok=True)
        for name in SHIPPED:
            src = os.path.join(CANONICAL, name)
            dst = os.path.join(STAGED, name)
            # copy2 for the mtime: a same-second overwrite that changes
            # nothing else is how a stale .pyc survived a restore in
            # tools/falsify.sh, and the same reasoning applies to any
            # build system that compares timestamps.
            shutil.copy2(src, dst)
        return "copied from %s" % CANONICAL

    if have_staged:
        # Building from an sdist. The files came with it.
        return "already staged (building from an sdist)"

    raise SystemExit(
        "ophtml: cannot find the C runtime.\n"
        "\n"
        "  looked for %s in\n"
        "    %s   (the repository)\n"
        "    %s   (staged, as an sdist would carry it)\n"
        "\n"
        "Building without it would produce a distribution that installs\n"
        "cleanly and cannot put anything on a console, which is the bug\n"
        "F25 exists to fix. Refusing rather than shipping that.\n"
        % (" and ".join(SHIPPED), CANONICAL, STAGED))


# At module level on purpose, so it runs for `build`, `sdist`, `bdist_wheel`
# and `pip install -e` alike rather than for whichever subcommand somebody
# remembered to subclass. Subclassing build_py would miss sdist, and then
# `pip install --no-binary ophtml` would build state 3 and raise -- for a
# release that looked fine when it was uploaded.
stage_runtime()

setup()
