#!/usr/bin/env python3
"""Hold every version number in this repository to every other one.

WHY THIS EXISTS. There were five version claims here and nothing read
any of them, so all five were free to be wrong and three of them were:

  * `packages/baker/pyproject.toml` said 0.2.0 while
    `packages/baker/ps2ui_bake/__init__.py` said 0.1.0. One package,
    two numbers, four format versions of disagreement.
  * `CHANGELOG.md`'s open section said "`.uib` format version 5" and
    "two format moves have landed since 0.2.0". The writer was at v7
    and there had been four.
  * Both packages claimed 0.2.0 against zero git tags, so the number
    named a release that does not exist and never did -- which is the
    part a stranger acts on, since it is what pip and npm see.

None of that is exotic. It is the failure this project keeps finding:
a number that is true the day it is written and unfalsifiable after,
because the only thing that would notice is a person re-deriving it.
So the numbers get read, here, by CI.

WHAT THIS DOES NOT VOUCH FOR. That the version is the RIGHT one. It
proves the claims agree with each other and with the format the code
actually writes; choosing 0.3.0 over 0.4.0 is a judgement no check
makes. It also cannot see a tag that was never fetched -- a shallow
clone without tags makes rule 8 unprovable, so rule 8 says so out loud
rather than passing.
"""
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def literal(relpath, pattern, what):
    """Read a declaration out of a file's TEXT, never by importing it.

    Importing ps2ui_bake would answer the same questions and drag in
    Pillow, which is not installed when this runs -- it is the first
    step in CI precisely because it needs no toolchain and nothing
    built. Reading the text is also the honest instrument here: what is
    under test is what each file SAYS, and an import would happily
    report a version that a `try: import ... except:` fallback had
    substituted.
    """
    text = open(os.path.join(ROOT, *relpath.split("/")), encoding="utf-8").read()
    m = re.search(pattern, text, re.M)
    if not m:
        raise SystemExit("check-versions: no %s in %s -- it was renamed or "
                         "deleted, and this check has stopped reading it"
                         % (what, relpath))
    return m.group(1)


BAKER_VERSION = literal("packages/baker/ps2ui_bake/__init__.py",
                        r'^__version__ = "([^"]+)"\s*$',
                        "__version__")
UIB_VERSION = int(literal("packages/baker/ps2ui_bake/uib.py",
                          r"^VERSION = (\d+)\s*$", "VERSION"))

# dev < alpha < beta < rc < release. The rank exists so "the open
# section's version is ahead of the last released one" is a comparison
# and not a string match.
_RANK = {"dev": 0, "a": 1, "b": 2, "rc": 3, None: 4}
_ALIAS = {"alpha": "a", "beta": "b"}

_PEP440 = re.compile(r"^(\d+)\.(\d+)\.(\d+)(?:\.?(dev|a|b|rc)\.?(\d+))?$")
_SEMVER = re.compile(
    r"^(\d+)\.(\d+)\.(\d+)(?:-(dev|alpha|beta|rc)\.(\d+))?$")

# "one", "two", ... as the CHANGELOG spells small counts.
_WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
          "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10}


def parse(text, pattern, what):
    """A version string -> (major, minor, patch, rank, prerelease_n).

    Two spellings, one meaning: PEP 440 writes 0.3.0.dev0 and semver
    writes 0.3.0-dev.0. Comparing the strings would make the two
    packages permanently unequal, so both are parsed to the same tuple
    and the ecosystems keep their own spelling.
    """
    m = pattern.match(text.strip())
    if not m:
        raise SystemExit("check-versions: %s is %r, which neither PEP 440 "
                         "nor semver spells the way this file parses. "
                         "Widen the parser deliberately; do not loosen it "
                         "until it matches." % (what, text))
    major, minor, patch, kind, num = m.groups()
    kind = _ALIAS.get(kind, kind)
    return (int(major), int(minor), int(patch), _RANK[kind],
            int(num) if num is not None else 0)


def is_prerelease(v):
    return v[3] != _RANK[None]


def pyproject_derives():
    """Rule 1: the baker has ONE version literal, and it is __init__.py.

    Reads the text rather than the parsed table, because the hole was a
    literal `version = "0.2.0"` sitting under [project] beside the
    __init__ that disagreed with it. A parser sees a version either
    way; what matters is that the literal is gone.
    """
    path = os.path.join(ROOT, "packages", "baker", "pyproject.toml")
    section, dynamic, literal = None, False, None
    for raw in open(path, encoding="utf-8"):
        line = raw.strip()
        if line.startswith("[") and line.endswith("]"):
            section = line[1:-1]
            continue
        if section != "project":
            continue
        if re.match(r"^dynamic\s*=.*\bversion\b", line):
            dynamic = True
        m = re.match(r'^version\s*=\s*"([^"]+)"', line)
        if m:
            literal = m.group(1)
    out = []
    if literal is not None:
        out.append("not ok - packages/baker/pyproject.toml declares "
                   "version = %r under [project]. That is the second "
                   "number; delete it and let dynamic pick up "
                   "ps2ui_bake.__version__." % literal)
    if not dynamic:
        out.append("not ok - packages/baker/pyproject.toml does not declare "
                   'dynamic = ["version"], so its version no longer comes '
                   "from ps2ui_bake/__init__.py")
    return out


def changelog_sections():
    """[(heading, body)] newest first, from `## ...` headings."""
    text = open(os.path.join(ROOT, "CHANGELOG.md"), encoding="utf-8").read()
    parts = re.split(r"^## +(.*)$", text, flags=re.M)[1:]
    return list(zip(parts[0::2], parts[1::2]))


def format_version_in(body):
    """The `.uib` format version a CHANGELOG section claims.

    Both spellings the file uses: bolded in the open section, bare in
    the 0.2.0 one. A section with no such claim returns None, which is
    a failure only where a claim is required.
    """
    m = re.search(r"`\.uib` format \*{0,2}version (\d+)", body)
    return int(m.group(1)) if m else None


def git_tags():
    try:
        out = subprocess.run(["git", "tag"], cwd=ROOT, check=True,
                             capture_output=True, text=True).stdout
    except (OSError, subprocess.CalledProcessError):
        return None
    return set(out.split())


def main():
    fail = []

    def check(ok, ok_msg, bad_msg):
        print("%s - %s" % ("ok" if ok else "not ok", ok_msg if ok else bad_msg))
        if not ok:
            fail.append(bad_msg)

    # 1. The baker's version has one home.
    bad = pyproject_derives()
    for line in bad:
        print(line)
        fail.append(line)
    if not bad:
        print("ok - packages/baker derives its version from "
              "ps2ui_bake.__version__ and declares it nowhere else")

    # 2. The two packages ship as one product, so they name one version.
    baker = parse(BAKER_VERSION, _PEP440, "ps2ui_bake.__version__")
    layout_raw = literal("packages/layout/package.json",
                         r'^\s*"version"\s*:\s*"([^"]+)"',
                         "version")
    layout = parse(layout_raw, _SEMVER, "@ps2ui/layout version")
    check(baker == layout,
          "@ps2ui/layout %s and ps2ui-bake %s are the same version in the "
          "two spellings" % (layout_raw, BAKER_VERSION),
          "@ps2ui/layout is %s and ps2ui-bake is %s; they bake and load one "
          "format and cannot be released apart" % (layout_raw, BAKER_VERSION))

    # 3. The reader and the writer agree on the format they speak.
    rt = int(literal("runtime/ps2ui.h",
                     r"^#define\s+PS2UI_VERSION\s+(\d+)\s*$",
                     "PS2UI_VERSION"))
    check(rt == UIB_VERSION,
          "PS2UI_VERSION and uib.VERSION are both %d" % UIB_VERSION,
          "runtime/ps2ui.h says PS2UI_VERSION %d, the writer emits %d; "
          "every blob this tree bakes would be rejected by its own runtime"
          % (rt, UIB_VERSION))

    # 4. The format document describes the format that is written.
    fmt = open(os.path.join(ROOT, "docs", "format-uib.md"),
               encoding="utf-8").read()
    m = re.search(r"^\|\s*4\s*\|\s*u16\s*\|\s*version\s*\|\s*(\d+)",
                  fmt, re.M)
    check(m is not None and int(m.group(1)) == UIB_VERSION,
          "docs/format-uib.md's header table says version %d" % UIB_VERSION,
          "docs/format-uib.md's header table says version %s, the writer "
          "emits %d" % (m.group(1) if m else "nothing", UIB_VERSION))
    check(re.search(r"^- \*\*v%d\*\* —" % UIB_VERSION, fmt, re.M) is not None,
          "docs/format-uib.md's Versioning list explains v%d" % UIB_VERSION,
          "docs/format-uib.md's Versioning list has no `- **v%d** —` entry, "
          "so the current format is undocumented" % UIB_VERSION)

    # 5-7. The open CHANGELOG section states the same facts.
    sections = changelog_sections()
    head, body = sections[0]
    m = re.match(r"^Unreleased — (\S+)$", head)
    check(m is not None and m.group(1) == BAKER_VERSION,
          "CHANGELOG's open section is headed with %s" % BAKER_VERSION,
          "CHANGELOG's first heading is %r; it must read "
          "'Unreleased — %s' so the notes and the packages carry one "
          "number" % (head, BAKER_VERSION))

    claimed = format_version_in(body)
    check(claimed == UIB_VERSION,
          "CHANGELOG's open section names format v%d" % UIB_VERSION,
          "CHANGELOG's open section names format v%s, the writer emits v%d"
          % (claimed, UIB_VERSION))

    # The released section below it, and the drift the prose claims.
    released = [(h, b) for h, b in sections[1:]
                if re.match(r"^\d+\.\d+\.\d+", h)]
    prev_head, prev_body = released[0]
    prev_ver = prev_head.split(" ")[0]
    prev_fmt = format_version_in(prev_body)
    check(prev_fmt is not None,
          "CHANGELOG's %s section records the format it shipped (v%s)"
          % (prev_ver, prev_fmt),
          "CHANGELOG's %s section names no `.uib` format version, so the "
          "drift since it cannot be counted" % prev_ver)

    m = re.search(r"^(\w+) format moves have landed since (\S+)", body, re.M)
    if m is None:
        check(False, "", "CHANGELOG's open section has no 'N format moves "
                         "have landed since X' line; that sentence is the "
                         "one this check reads")
    else:
        said, since = m.group(1).lower(), m.group(2)
        n = _WORDS.get(said, said if not said.isdigit() else int(said))
        want = UIB_VERSION - (prev_fmt or 0)
        check(n == want,
              "CHANGELOG counts %s format moves since %s, and v%s -> v%d is "
              "%d" % (said, since, prev_fmt, UIB_VERSION, want),
              "CHANGELOG says %r format moves since %s; v%s -> v%d is %d"
              % (said, since, prev_fmt, UIB_VERSION, want))
        check(since == prev_ver,
              "CHANGELOG counts the drift from %s, the section below it"
              % prev_ver,
              "CHANGELOG counts the drift since %s but the newest released "
              "section is %s" % (since, prev_ver))
        # The prose enumerates the moves. If it names any, it names all
        # of them and nothing else -- an enumeration missing an entry is
        # how "two format moves" stayed on the page through v6 and v7.
        # Bounded to the paragraph the sentence lives in. A fixed
        # character window would start reading whichever paragraph
        # follows, and then a later edit two paragraphs down decides
        # whether this check passes.
        end = body.find("\n\n", m.start())
        para = body[m.start():end if end != -1 else len(body)]
        named = sorted(int(x) for x in re.findall(r"\bv(\d+)\b", para))
        want_list = list(range((prev_fmt or 0) + 1, UIB_VERSION + 1))
        if named:
            check(named == want_list,
                  "and enumerates exactly %s"
                  % ", ".join("v%d" % v for v in want_list),
                  "CHANGELOG enumerates %s beside that count; the moves are "
                  "%s" % (", ".join("v%d" % v for v in named),
                          ", ".join("v%d" % v for v in want_list)))

    # 10. The README's Quick start note. It is the first thing a
    #     stranger reads and the only place that tells them the
    #     toolchain is unpublished, so it names all four facts and is
    #     read back here rather than trusted.
    readme = open(os.path.join(ROOT, "README.md"), encoding="utf-8").read()
    m = re.search(r"\*\*Neither package is published.*?\n\n", readme, re.S)
    if m is None:
        check(False, "", "README.md has no '**Neither package is "
                         "published' paragraph under Quick start; that is "
                         "the only place a stranger is told this tree is "
                         "not a release, and this check has stopped "
                         "reading it")
    else:
        note = m.group(0)
        missing = [w for w in (BAKER_VERSION, layout_raw,
                               "format **v%d**" % UIB_VERSION,
                               "%s moves" % {2: "two", 3: "three",
                                             4: "four", 5: "five"}.get(
                                   UIB_VERSION - (prev_fmt or 0),
                                   str(UIB_VERSION - (prev_fmt or 0))))
                   if w not in note]
        check(not missing,
              "README's Quick start note names %s, %s, format v%d and the "
              "drift since %s" % (BAKER_VERSION, layout_raw, UIB_VERSION,
                                  prev_ver),
              "README's Quick start note does not say %s"
              % "; does not say ".join(repr(w) for w in missing))

    # 9. The sequencing document's own format lineage. It is the file
    #    people read to decide what to build next, it restates the
    #    history in one arrow chain, and it stopped at v5 through two
    #    further breaks -- the same failure as the CHANGELOG's, in the
    #    document with the most readers.
    plan = open(os.path.join(ROOT, "docs", "PLAN.md"), encoding="utf-8").read()
    m = re.search(r"\*\*Format history:\*\*(.*?)Struct-size", plan, re.S)
    if m is None:
        check(False, "", "docs/PLAN.md has no '**Format history:**' chain "
                         "ending in 'Struct-size'; that sentence is the one "
                         "this check reads")
    else:
        chain = sorted(set(int(x) for x in re.findall(r"\bv(\d+)\b",
                                                     m.group(1))))
        want = list(range(1, UIB_VERSION + 1))
        check(chain == want,
              "docs/PLAN.md's format history runs v1 through v%d"
              % UIB_VERSION,
              "docs/PLAN.md's format history names %s; the format has run "
              "%s" % (", ".join("v%d" % v for v in chain),
                      ", ".join("v%d" % v for v in want)))

    # 8. A release version names a tag. A prerelease is allowed to name
    #    nothing, which is the whole reason to carry one.
    tags = git_tags()
    if is_prerelease(baker):
        print("ok - %s is a prerelease, so it is not claiming to be a "
              "release that has no tag" % BAKER_VERSION)
    elif tags is None:
        check(False, "", "check-versions cannot run `git tag`, so it cannot "
                         "prove %s is a real release" % BAKER_VERSION)
    else:
        want = {BAKER_VERSION, "v" + BAKER_VERSION}
        check(bool(want & tags),
              "%s is tagged" % BAKER_VERSION,
              "%s is not a prerelease but no tag names it%s. Either tag the "
              "release or carry a .dev/rc version until you do."
              % (BAKER_VERSION,
                 " (this checkout has no tags at all -- if it is a shallow "
                 "clone, fetch them)" if not tags else ""))

    if fail:
        print("not ok - %d version claim(s) above disagree with the code"
              % len(fail))
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
