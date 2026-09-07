"""`ps2ui vendor-runtime` -- write the C runtime into somebody's project.

WHAT THIS CLOSES. `pip install ophtml` gives a stranger the whole
authoring path: HTML and CSS in, a `.uib` blob out, previewer included.
Then README.md told them to "drop runtime/ps2ui.c and runtime/ps2ui.h
into your ps2sdk/gsKit project" -- a repo path, in a package that
carried neither file. The console half, which is the point of the
project, required a clone, and Phase 4's exit gate says "without cloning
the repo". F25.

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

    if packaged and checkout:
        drifted = _differ(_PACKAGED, _CHECKOUT)
        if drifted:
            raise _Stale(drifted)
        return _PACKAGED, "the installed package"
    if packaged:
        return _PACKAGED, "the installed package"
    if checkout:
        return _CHECKOUT, "this checkout"
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
        # exact bug F25 is about, so the message says so rather than
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

    written, skipped = [], []
    for name in FILES:
        target = os.path.join(dest, name)
        if os.path.exists(target) and not args.force:
            skipped.append(name)
            continue
        shutil.copyfile(os.path.join(src, name), target)
        written.append(name)

    for name in written:
        print("wrote %s" % os.path.join(args.dest, name))
    if skipped:
        # Refuse rather than overwrite, and say the flag. Somebody who
        # has edited ps2ui.c in their own tree loses that edit silently
        # otherwise, and this command is most likely to be re-run
        # exactly when they are upgrading -- the worst moment to be
        # quiet about it.
        print("%s already there; not overwritten. Pass --force to "
              "replace %s." % (", ".join(skipped),
                               "them" if len(skipped) > 1 else "it"))

    print("runtime source: %s (%s)" % (src, label))
    if not written:
        return 0

    print("\nCompile these with your project against gsKit. "
          "`ps2ui check` validates the blob; docs/deploying.md is the "
          "path onto a console.")
    return 0
