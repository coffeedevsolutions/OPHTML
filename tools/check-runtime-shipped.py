#!/usr/bin/env python3
"""Does a built wheel actually carry the C runtime, and can a stranger get it?

WHY THIS EXISTS RATHER THAN TRUSTING pyproject.toml.

F25 shipped the runtime as package data staged at build time by
packages/baker/setup.py. The declaration alone proves nothing, and that
is not a worry -- it is measured. Before the hook existed:

    package-data "../fakeruntime/ps2ui.c"  -> lands at WHEEL ROOT,
                                              installing into
                                              site-packages/fakeruntime/
    package-data "../../runtime/ps2ui.c"   -> SILENTLY OMITTED.
                                              Build succeeds, rc=0, no
                                              warning of any kind.

A manifest naming a file that is not there is not an error to setuptools
and not an error to twine. That is the same failure pyproject.toml's own
package-data comment records about serve_page.html, which was found only
when somebody ran `ps2ui serve` from outside a checkout. So this builds
the wheel and looks inside it.

AND THEN INSTALLS IT, WHICH IS THE HALF THAT MATTERS.

A file being in the zip is necessary and not sufficient: it has to land
somewhere `ps2ui vendor-runtime` finds. So the wheel is installed into a
throwaway venv and the command is run from a directory OUTSIDE this
checkout -- because inside one, vendor.py's checkout fallback would
answer and the whole check would pass without the wheel contributing
anything.

That is not hypothetical. The first manual test of that fallback
reported "the installed package" when it should have said "this
checkout", because a stale staged directory was answering. The check
below therefore asserts the SOURCE LABEL as well as the bytes: a pass
has to say the files came from the installed package, or it is passing
for the wrong reason.

Cheap enough for every push: --no-deps, because nothing on the
vendor-runtime path imports Pillow.
"""
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BAKER = os.path.join(ROOT, "packages", "baker")
CANONICAL = os.path.join(ROOT, "runtime")
FILES = ("ps2ui.c", "ps2ui.h")

fail = []


def check(ok, ok_msg, bad_msg):
    print("%s - %s" % ("ok" if ok else "not ok", ok_msg if ok else bad_msg))
    if not ok:
        fail.append(bad_msg)


def main():
    tmp = tempfile.mkdtemp(prefix="ps2ui-shipped-")
    try:
        return run(tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# Build state that setuptools will happily reuse, and which makes this
# check pass on evidence from a previous run.
STALE = ("build", "ophtml.egg-info", os.path.join("ps2ui_bake", "runtime"))


def purge_build_state():
    """Delete cached build state before building. NOT housekeeping.

    Falsifying this check the first time reported PASSED -- HOLE twice,
    against sabotages that were real: package-data stopped naming the
    runtime, and setup.py stopped staging it. Both were invisible
    because `build/` and `ophtml.egg-info/` survived from an earlier
    run, and egg-info/SOURCES.txt caches the file list setuptools built
    last time. The wheel was assembled partly from the previous build's
    answer.

    Isolated afterwards, with this purge in place, the same sabotage is
    decisive:

        package-data NAMES the runtime      -> in the wheel
        package-data does NOT name it       -> ABSENT

    So the declaration is load-bearing and the check does work -- it
    just could not see anything while a cache was answering for it.
    That is the third time in one day this repository has been bitten by
    leftover state standing in for a fresh result: a .pyc that outlived
    its source in tools/falsify.sh, a wheel left in dist/ when a build
    refused, and this. A check that builds must control what it builds
    from.
    """
    for rel in STALE:
        shutil.rmtree(os.path.join(BAKER, rel), ignore_errors=True)


def run(tmp):
    purge_build_state()
    wheels = os.path.join(tmp, "wheels")

    # `pip wheel` rather than `python -m build`: pip drives the same
    # PEP 517 hook and is always present, so this adds no dependency to
    # a job whose whole point is checking what gets distributed.
    proc = subprocess.run(
        [sys.executable, "-m", "pip", "wheel", "--no-deps", "--no-cache-dir",
         "-w", wheels, BAKER],
        capture_output=True, text=True)
    if proc.returncode != 0:
        check(False, "", "building the wheel failed:\n%s"
                         % (proc.stderr or proc.stdout)[-2000:])
        return 1
    built = [f for f in os.listdir(wheels) if f.endswith(".whl")]
    check(len(built) == 1, "built one wheel: %s" % (built[0] if built else ""),
          "expected exactly one wheel, got %r" % built)
    if not built:
        return 1
    whl = os.path.join(wheels, built[0])

    # 1. The files are in the archive, at the path that makes them
    #    package data rather than site-packages litter.
    names = set(zipfile.ZipFile(whl).namelist())
    for name in FILES:
        want = "ps2ui_bake/runtime/%s" % name
        check(want in names,
              "the wheel carries %s" % want,
              "the wheel does NOT carry %s. package-data declared it and "
              "setuptools omitted it without a word -- the measured "
              "failure this file exists for. Check that "
              "packages/baker/setup.py staged it before the build." % want)

    # 2. And they are the canonical bytes, not something older that
    #    happened to be staged in the tree when the wheel was built.
    zf = zipfile.ZipFile(whl)
    for name in FILES:
        want = "ps2ui_bake/runtime/%s" % name
        if want not in names:
            continue
        with open(os.path.join(CANONICAL, name), "rb") as fh:
            canonical = fh.read()
        check(zf.read(want) == canonical,
              "%s in the wheel is byte-identical to runtime/%s" % (name, name),
              "%s in the wheel DIFFERS from runtime/%s. A stale staged "
              "copy was packaged instead of the canonical source."
              % (name, name))

    if fail:
        return 1

    # 3. Install it and run the command the way a stranger does.
    venv = os.path.join(tmp, "v")
    subprocess.run([sys.executable, "-m", "venv", venv],
                   capture_output=True, check=True)
    bindir = "Scripts" if os.name == "nt" else "bin"
    pip = os.path.join(venv, bindir, "pip")
    ps2ui = os.path.join(venv, bindir, "ps2ui")
    proc = subprocess.run([pip, "install", "--no-deps", "--no-cache-dir", whl],
                          capture_output=True, text=True)
    if proc.returncode != 0:
        check(False, "", "installing the wheel failed:\n%s"
                         % (proc.stderr or proc.stdout)[-2000:])
        return 1

    # OUTSIDE the checkout on purpose. Run from inside one and vendor.py
    # falls back to repo-root runtime/, which would pass this check with
    # the wheel contributing nothing at all.
    workdir = os.path.join(tmp, "someones-project")
    os.makedirs(workdir)
    proc = subprocess.run([ps2ui, "vendor-runtime", "."],
                          cwd=workdir, capture_output=True, text=True)
    check(proc.returncode == 0,
          "`ps2ui vendor-runtime` runs from an installed wheel",
          "`ps2ui vendor-runtime` failed from an installed wheel:\n%s"
          % (proc.stderr or proc.stdout)[-2000:])

    # THE LABEL, not just the bytes. This is what distinguishes "the
    # wheel worked" from "something else answered".
    check("the installed package" in proc.stdout,
          "and it read them from the installed package, not a fallback",
          "vendor-runtime succeeded but did not report the installed "
          "package as its source. It answered from somewhere else, so "
          "this check would have passed without the wheel carrying "
          "anything. Output:\n%s" % proc.stdout)

    for name in FILES:
        got = os.path.join(workdir, name)
        if not os.path.exists(got):
            check(False, "", "%s was not written into the project dir" % name)
            continue
        with open(got, "rb") as a, open(os.path.join(CANONICAL, name), "rb") as b:
            check(a.read() == b.read(),
                  "%s landed byte-identical to runtime/%s" % (name, name),
                  "%s landed but differs from runtime/%s" % (name, name))

    if fail:
        print("not ok - %d part(s) of the runtime's distribution are broken"
              % len(fail))
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
