#!/usr/bin/env python3
"""Every version a document PRINTS is the version something prints.

WHY THIS EXISTS. `check-site-pages.py` pins citations by line: it records
the text of a cited source line and fails when that line changes. It is
exact and it cannot see this. A row citing `packages/baker/ps2ui_bake/
cli.py:138` keeps its pin when `__init__.py:39` moves, because the line
it pinned did not move -- the version merely FLOWS through the file it
pinned. So a version bump leaves prose asserting the old number with
every citation green.

Measured, not supposed. The 0.8.0.dev0 back-to-development corrected
three rows the citation checker named, and review then found ten more it
could not: `cli.bake.version` ("the tree prints `ps2ui-bake 0.7.0`"),
`check.version`, `cli.layout.options`, `cli.dev.options`, a rendered
table contradicting its own facts file, a session preamble contradicting
its own row nine lines below it, a "run these from the repository root"
transcript, a quoted `check-versions.py` block, and a wheel filename.
Every one of them was a number a command prints, written down.

WHAT IT CHECKS. Each line of `docs/site` that carries a version banner --
`ps2ui 0.8.0.dev0`, `ps2ui-layout 0.8.0-dev.0`, `ophtml-0.8.0.dev0-py3-
none-any.whl`, `@ophtml/layout 0.8.0-dev.0` -- names either the version
this TREE carries or the last RELEASE, and `_versions.tsv` records which
of the two it meant when it was pinned. A banner naming the tree keeps
naming the tree across a bump; a banner naming the release keeps naming
the release. A banner in neither is wrong whatever it says.

THE RECORD IS THE POINT, and it is the same argument `_citations.tsv`
makes. Deciding tree-or-release from the words around a banner was tried
and dropped: "this tree" and "pip install" are the honest cases and the
prose does not always say either, and `check-findings.py`'s rule 6 note
already records keyword matching against prose as too fragile to keep.
A banner with no record fails until `--pin` is run, so the record stays
exact and every new banner is a decision somebody made rather than a
default somebody got.

WHAT IT DOES NOT CHECK. Whether the sentence around the banner is true.
`New in 0.7.0` carries no banner and is not read; a row claiming the
wrong thing about a version it does not print is outside this, and stays
outside it -- the check that would catch that is a person.

    tools/check-doc-versions.py            assert
    tools/check-doc-versions.py --pin      rewrite the record from the
                                           tree as it stands
"""

import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(ROOT, "docs", "site")
RECORD = os.path.join(SITE, "_versions.tsv")

# The banners a command actually prints, plus the wheel a build writes.
# Anchored on the product name so a bare "0.7.0" in prose is not a
# banner -- prose is what this check deliberately cannot read.
BANNER = re.compile(
    r"(?:"
    r"\bps2ui(?:-bake|-check|-fontgen|-layout|-dev)?\s+"
    r"|\bophtml-"
    r"|@ophtml/layout\s+"
    r"|`ophtml`\s+"
    r")"
    r"(?P<v>\d+\.\d+\.\d+(?:\.dev\d+|-dev\.\d+)?)"
)


def tree_versions():
    """(python spelling, npm spelling) as this tree carries them."""
    init = os.path.join(ROOT, "packages", "baker", "ps2ui_bake", "__init__.py")
    with open(init, encoding="utf-8") as fh:
        m = re.search(r'^__version__ = "([^"]+)"', fh.read(), re.M)
    if not m:
        raise SystemExit("not ok - no __version__ in %s" % init)
    pkg = os.path.join(ROOT, "packages", "layout", "package.json")
    with open(pkg, encoding="utf-8") as fh:
        npm = json.load(fh)["version"]
    return m.group(1), npm


def released_versions():
    """The newest CHANGELOG section that is not the open prerelease.

    Read from the CHANGELOG rather than from the tag namespace, because
    a shallow checkout has no tags and this check should not need one.
    `check-versions.py` owns the tag rule; this one only needs a number.
    """
    path = os.path.join(ROOT, "CHANGELOG.md")
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    for m in re.finditer(r"^## (?:Unreleased — )?(\d+\.\d+\.\d+[^\s]*)",
                         text, re.M):
        v = m.group(1)
        if ".dev" not in v and "-dev" not in v:
            return v, v
    raise SystemExit("not ok - CHANGELOG.md has no released section")


def pages():
    out = []
    for d, _, files in os.walk(SITE):
        for f in sorted(files):
            if f.endswith(".md"):
                p = os.path.join(d, f)
                out.append((os.path.relpath(p, SITE), p))
    return sorted(out)


def scan():
    """Every banner, as (relpath, lineno, ordinal, version, line).

    ORDINAL, because one line can carry both kinds on purpose and the
    honest rows do: `cli.ps2ui.version` reads "The released version
    prints `ps2ui 0.7.0`; this tree prints `ps2ui 0.8.0.dev0`". Keyed on
    the line alone, the first record answered for every banner on it and
    the row failed against itself -- found by running this check against
    the tree it was written for, which is the only reason it is keyed
    this way.
    """
    found = []
    for rel, path in pages():
        with open(path, encoding="utf-8") as fh:
            for n, line in enumerate(fh, 1):
                for i, m in enumerate(BANNER.finditer(line)):
                    found.append((rel, n, i, m.group("v"),
                                  line.rstrip("\n")))
    return found


def load_record():
    if not os.path.exists(RECORD):
        return {}
    rec = {}
    with open(RECORD, encoding="utf-8") as fh:
        for line in fh:
            line = line.rstrip("\n")
            if not line or line.startswith("#"):
                continue
            rel, n, idx, kind, version = line.split("\t")
            rec[(rel, int(n), int(idx))] = kind
    return rec


def classify(version, tree, release):
    """Which of the two a banner names, or None for neither."""
    if version in tree:
        return "tree"
    if version in release:
        return "release"
    return None


def main(argv):
    pin = "--pin" in argv[1:]
    for a in argv[1:]:
        if a != "--pin":
            raise SystemExit("usage: check-doc-versions.py [--pin]")

    tree = tree_versions()
    release = released_versions()
    found = scan()

    if pin:
        rows, unknown = [], []
        for rel, n, idx, v, _line in found:
            kind = classify(v, tree, release)
            if kind is None:
                unknown.append((rel, n, v))
                continue
            rows.append("%s\t%d\t%d\t%s\t%s" % (rel, n, idx, kind, v))
        if unknown:
            print("1..%d" % len(unknown))
            for i, (rel, n, v) in enumerate(unknown, 1):
                print("not ok %d - %s:%d names %s, which is neither this "
                      "tree (%s / %s) nor the last release (%s). --pin "
                      "records what a banner MEANS; it cannot record a "
                      "version nothing prints."
                      % (i, rel, n, v, tree[0], tree[1], release[0]))
            return 1
        with open(RECORD, "w", encoding="utf-8") as fh:
            fh.write("# Every version banner in docs/site, and which "
                     "version it means.\n")
            fh.write("# Regenerate with tools/check-doc-versions.py "
                     "--pin. See that file's docstring.\n")
            fh.write("# path\tline\tordinal\tkind\t"
                     "version-when-pinned\n")
            for r in rows:
                fh.write(r + "\n")
        print("ok - pinned %d version banner(s) into %s"
              % (len(rows), os.path.relpath(RECORD, ROOT)))
        return 0

    rec = load_record()
    results = []
    for rel, n, idx, v, line in found:
        kind = classify(v, tree, release)
        want_kinds = [k for (r, ln, i), k in rec.items()
                      if r == rel and ln == n and i == idx]
        if not want_kinds:
            results.append((False,
                            "%s:%d names %s and has no record. Every "
                            "banner is pinned as meaning the tree or the "
                            "release; run --pin and commit the row, so "
                            "the next bump knows which way to move it.\n"
                            "    %s" % (rel, n, v, line.strip())))
            continue
        want = want_kinds[0]
        if kind == want:
            results.append((True, "%s:%d %s (%s)" % (rel, n, v, want)))
        elif kind is None:
            results.append((False,
                            "%s:%d names %s, which is neither this tree "
                            "(%s / %s) nor the last release (%s). It was "
                            "pinned as the %s.\n    %s"
                            % (rel, n, v, tree[0], tree[1], release[0],
                               want, line.strip())))
        else:
            other = tree if want == "tree" else release
            results.append((False,
                            "%s:%d was pinned as the %s and now names %s, "
                            "which is the %s. The %s is %s.\n    %s"
                            % (rel, n, want, v, kind, want,
                               " / ".join(sorted(set(other))), line.strip())))

    stale = [(r, ln) for (r, ln, i) in rec
             if not any(fr == r and fn == ln and fi == i
                        for fr, fn, fi, _fv, _l in found)]
    for rel, n in sorted(stale):
        results.append((False,
                        "%s:%d has a record but no banner. The line moved "
                        "or the banner went; run --pin." % (rel, n)))

    print("1..%d" % len(results))
    bad = 0
    for i, (ok, msg) in enumerate(results, 1):
        print("%s %d - %s" % ("ok" if ok else "not ok", i, msg))
        bad += 0 if ok else 1
    print("# %d banner(s), %d tree (%s / %s), %d release (%s), %d bad"
          % (len(found),
             sum(1 for _r, _n, _i, v, _l in found
                 if classify(v, tree, release) == "tree"),
             tree[0], tree[1],
             sum(1 for _r, _n, _i, v, _l in found
                 if classify(v, tree, release) == "release"),
             release[0], bad))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
