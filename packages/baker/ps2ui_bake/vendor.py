"""`ps2ui vendor-runtime` -- write the C runtime into somebody's project.

WHAT THIS CLOSES. `pip install ophtml` gives a stranger the whole
authoring path: HTML and CSS in, a `.uib` blob out, previewer included.
Then README.md told them to "drop runtime/ps2ui.c and runtime/ps2ui.h
into your ps2sdk/gsKit project" -- a repo path, in a package that
carried neither file. The console half, which is the point of the
project, required a clone, and Phase 4's exit gate says "without cloning
the repo". F26.

WHY THE FILES COME FROM THE INSTALL RATHER THAN A DOWNLOAD. The runtime
a person compiles has to be the one that matches the baker that wrote
their blob. `.uib` carries a version, `ps2ui.h` carries PS2UI_VERSION,
and check-versions.py holds the two together in the tree -- but only in
the tree. Handing out a runtime fetched from anywhere else reintroduces
exactly the skew that fence exists to prevent, and it would do it at the
moment the two are hardest to compare: on a stranger's machine, with a
blob already baked. One install, one version, both halves.

It also means this works with no network, which the rest of the
toolchain does too.

TWO PLACES TO LOOK, AND THE ORDER IS THE POINT. An installed package
carries the files as package data. A checkout does not -- setup.py
stages them at BUILD time, so `pip install -e` and a bare PYTHONPATH
checkout both have an empty `runtime/` beside this module. So the
canonical repo-root `runtime/` is the fallback, and a checkout keeps
working without anybody staging anything by hand.

That is the same candidate-resolution shape as load_font_manifest in
cli.py, and for the same reason: the code says which one it used rather
than leaving a person to guess which of two copies they are looking at.

It differs from load_font_manifest in one way, and find_source() below
explains why: BOTH candidates can exist in a checkout that has been
built, so "first existing wins" is not safe here. They are compared,
and a disagreement is refused.
"""
import os
import shutil

# What a person needs to compile against gsKit, and nothing else.
# runtime/ also holds the Makefile, the sample, the host shims and
# vendored gsKit -- none of which belongs in somebody's project tree,
# and a glob here would start handing out whatever lands there next.
FILES = ("ps2ui.c", "ps2ui.h")

_HERE = os.path.dirname(os.path.abspath(__file__))

# Staged into the package at build time (setup.py), present in a wheel
# and an sdist, absent in a checkout.
_PACKAGED = os.path.join(_HERE, "runtime")

# The canonical home, present in a checkout, absent in an install.
_CHECKOUT = os.path.normpath(
    os.path.join(_HERE, "..", "..", "..", "runtime"))


def _complete(path):
    return all(os.path.exists(os.path.join(path, n)) for n in FILES)


def _same_file(a, b):
    with open(a, "rb") as fa, open(b, "rb") as fb:
        return fa.read() == fb.read()


def _differ(a, b):
    """Which of FILES differ between two candidate directories."""
    out = []
    for name in FILES:
        with open(os.path.join(a, name), "rb") as fa, \
             open(os.path.join(b, name), "rb") as fb:
            if fa.read() != fb.read():
                out.append(name)
    return out


def find_source():
    """Return (directory, label) for the candidate to vendor from.

    Label rather than a bare path because the two answers mean different
    things to a person debugging: "the installed package" is a version
    pinned to their baker, "this checkout" is whatever their working
    tree currently says.

    BOTH CAN EXIST AT ONCE, AND THAT IS A TRAP THIS FOUND THE HARD WAY.
    setup.py stages the files into the package at build time, and the
    staged copy stays on disk afterwards -- gitignored, but present. So
    a checkout that has ever run `python -m build` has two copies, the
    packaged one shadows the canonical one, and the day somebody edits
    runtime/ps2ui.c without rebuilding, this hands out the stale one
    while printing "the installed package".

    That is the stale-second-copy defect the build hook was designed to
    avoid, reappearing inside a working tree rather than in git. It was
    caught because the first test of the checkout fallback reported
    "the installed package" -- the fallback had not run at all, and the
    test would have passed for the wrong reason.

    So when both exist they are COMPARED, and a disagreement is refused
    rather than silently resolved by ordering. An install has no
    checkout beside it and never reaches this.
    """
    packaged, checkout = _complete(_PACKAGED), _complete(_CHECKOUT)

    # A COMPLETE _CHECKOUT MEANS WE ARE IN ONE, so _PACKAGED beside it is
    # a build artifact rather than an install and must not be labelled as
    # one. An earlier version returned "the installed package" from a
    # clone with no install anywhere near it -- the identical wrong
    # reading this comparison exists to catch, printed by the line meant
    # to prevent it. The canonical source is the honest answer here, and
    # it is also the right one: it is what a contributor just edited.
    if checkout:
        if packaged:
            drifted = _differ(_PACKAGED, _CHECKOUT)
            if drifted:
                raise _Stale(drifted)
        return _CHECKOUT, "this checkout"
    if packaged:
        return _PACKAGED, "the installed package"
    return None, None


class _Stale(Exception):
    def __init__(self, names):
        self.names = names
        Exception.__init__(self, ", ".join(names))


def cmd_vendor_runtime(args):
    from .project import ProjectError

    try:
        src, label = find_source()
    except _Stale as stale:
        raise ProjectError(
            "two copies of the runtime disagree, so this will not guess "
            "which one you meant.\n"
            "  %s\n    the canonical source\n"
            "  %s\n    staged by setup.py at build time, now out of date "
            "in %s\n"
            "Rebuild (`python -m build` in packages/baker) to restage it, "
            "or delete the staged directory -- it is gitignored and a "
            "checkout does not need it."
            % (_CHECKOUT, _PACKAGED, ", ".join(stale.names)))
    if src is None:
        # Neither. For an installed package that means the build hook
        # did not run and the wheel shipped without its runtime -- the
        # exact bug F26 is about, so the message says so rather than
        # just naming two missing directories.
        raise ProjectError(
            "no C runtime to vendor.\n"
            "  looked in %s (installed package data)\n"
            "  and       %s (a checkout)\n"
            "If you installed this from PyPI, the wheel was built "
            "without its runtime and that is a packaging bug worth "
            "reporting -- `pip download --no-binary ophtml ophtml` and "
            "building from the sdist is the workaround."
            % (_PACKAGED, _CHECKOUT))

    dest = os.path.abspath(args.dest)
    os.makedirs(dest, exist_ok=True)

    # EVERY FILE IS CLASSIFIED BEFORE ANY FILE IS WRITTEN, and that
    # ordering is the whole fix.
    #
    # The first version skipped what already existed, wrote what did
    # not, printed "Compile these with your project against gsKit" and
    # exited 0. Vendor once, upgrade the package, re-run: a FRESH
    # ps2ui.h lands beside a STALE ps2ui.c, which includes it on line 4
    # and is written against its structs. One invocation, a split pair,
    # a success status.
    #
    # PS2UI_VERSION does not save this. ps2ui.c rejects a blob whose
    # version disagrees, which sounds like the backstop -- but of 30
    # commits touching runtime/ps2ui.c only 7 moved PS2UI_VERSION, and
    # #110 pledged the format frozen at v7, so from here none will. The
    # drift this command exists to prevent is exactly the drift that
    # check cannot see.
    #
    # It is also the asymmetry find_source() already refuses: two copies
    # disagreeing inside the toolchain exit 1, and two copies
    # disagreeing in somebody's project used to get "already there" and
    # exit 0 -- in the place this module's own docstring calls the
    # harder one to compare, "on a stranger's machine, with a blob
    # already baked".
    absent, same, drifted = [], [], []
    for name in FILES:
        target = os.path.join(dest, name)
        if not os.path.exists(target):
            absent.append(name)
        elif _same_file(os.path.join(src, name), target):
            same.append(name)
        else:
            drifted.append(name)

    if drifted and not args.force:
        raise ProjectError(
            "%s in %s %s from the runtime this toolchain ships, so "
            "nothing was written.\n"
            "  Writing the rest would leave you compiling a mixed pair "
            "-- ps2ui.c includes ps2ui.h and is written against its "
            "structs, and a version check will not catch it: the format "
            "is pledged frozen at v7, so PS2UI_VERSION no longer moves "
            "when the runtime does.\n"
            "  Pass --force to take this toolchain's copy, or move your "
            "edited file aside first."
            % (", ".join(drifted), args.dest,
               "differs" if len(drifted) == 1 else "differ"))

    for name in (absent + drifted if args.force else absent):
        shutil.copyfile(os.path.join(src, name),
                        os.path.join(dest, name))
        print("wrote %s" % os.path.join(args.dest, name))

    # Idempotent re-runs say so and stay quiet, which the first version
    # could not: it reported an unchanged file as "already there; not
    # overwritten", the same words it used for a real disagreement.
    if same:
        print("%s already up to date." % ", ".join(same))

    print("runtime source: %s (%s)" % (src, label))
    if not absent and not (args.force and drifted):
        return 0

    print("\nCompile these with your project against gsKit. "
          "`ps2ui check` validates the blob; docs/deploying.md is the "
          "path onto a console.")
    return 0
