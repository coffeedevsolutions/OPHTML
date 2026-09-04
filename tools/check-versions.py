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
# THE NAMES THIS REPOSITORY PUBLISHES UNDER. The `ophtml` organisation
# is owned, so npm is scoped; PyPI has no scopes, so it is the bare
# name. Renaming means editing these two lines, deliberately, in the
# commit that renames -- see the rule that reads them.
EXPECTED_NPM = "@ophtml/layout"
EXPECTED_PYPI = "ophtml"

# HAS EITHER PACKAGE ACTUALLY BEEN UPLOADED? A hand-set fact, flipped
# by the commit that publishes, for the same reason EXPECTED_NPM is
# written down rather than inferred: nothing here may ask the network,
# and a rule that guesses is a rule that is wrong on the day it
# matters.
#
# It exists because the README's Quick start note is the one place a
# stranger is told what to run, and the true sentence is different on
# either side of the upload. Keying rule 10 to a literal
# "Neither package is published" meant that rewriting the note the day
# it stopped being true FAILED the check -- the paragraph it searches
# for would be gone -- which is the same trap docs/releasing.md step 4
# and rule 5 were in: a document telling you to do the thing a checker
# forbids. Found before publishing this time, by reading rule 10 while
# planning step 8 rather than by hitting it.
PUBLISHED = True

# "zero" is not padding. The section opened straight after a release
# counts its drift from a release that shipped the CURRENT format, so
# the count is 0 and the prose has to be able to say so in words like
# every other count here.
_WORDS = {"zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
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


# The paths that end up inside an artifact. A change to any of these
# between the tag and HEAD means the tag does not name what a publish
# from HEAD would upload -- which is rule 21 below.
PACKAGED_PATHS = [
    "packages/layout/src", "packages/layout/bin",
    "packages/layout/README.md", "packages/layout/package.json",
    "packages/baker/ps2ui_bake", "packages/baker/README.md",
    "packages/baker/pyproject.toml",
]


def git_packaged_diff(tag):
    """Files under PACKAGED_PATHS differing between `tag` and HEAD.

    None when git cannot answer -- no repository, no such tag, a shallow
    clone without the tag's objects. A rule that cannot be evaluated
    must say so rather than pass.
    """
    try:
        out = subprocess.run(
            ["git", "diff", "--name-only", tag + "^{commit}", "HEAD", "--"]
            + PACKAGED_PATHS,
            cwd=ROOT, check=True, capture_output=True, text=True).stdout
    except (OSError, subprocess.CalledProcessError):
        return None
    return [ln for ln in out.split("\n") if ln]



def main(argv=None):
    # `--except-tag` runs every rule BUT the tag rule.
    #
    # WHY A FLAG AND NOT A REORDER. Rule 8 is the only rule here that
    # compares the tree against something the tree cannot contain: the
    # repository's tag namespace. Every other rule reads two claims
    # inside the checkout and holds them to each other, and the step's
    # comment in ci.yml is right about those -- a disagreement means
    # the rest of the run is measuring something that does not know
    # what it is, so failing before the toolchain is even installed is
    # correct.
    #
    # Rule 8 is different in kind, and cutting 0.3.0 is what showed it.
    # A release commit on a branch CANNOT satisfy it: the tag has to
    # name a commit on the default branch, and with squash merges the
    # branch commit is not that commit. So the rule failed at step one
    # and took the whole job with it -- 242 baker tests, both example
    # builds, the tutorial and every other check never ran on the
    # commit that cut the release. A cheap check placed first had
    # hidden every expensive check behind it, which is the same shape
    # as the baker tests that ran before the builds they needed.
    #
    # So CI runs this file twice: `--except-tag` early, where a real
    # disagreement still fails fast, and the FULL command at the end,
    # unflagged and authoritative. The late run is the complete check,
    # so a rule added later is covered by it whatever this flag does --
    # the flag can only ever subtract from a run that is not the one
    # the verdict comes from.
    argv = sys.argv[1:] if argv is None else list(argv)
    except_tag = "--except-tag" in argv
    for a in argv:
        if a != "--except-tag":
            raise SystemExit("check-versions: unknown argument %r. The only "
                             "flag is --except-tag, and the unflagged run "
                             "is the authoritative one." % a)
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
    # Read once, up here, because rule 11 needs the npm name too.
    npm_name = literal("packages/layout/package.json",
                       r'^\s*"name"\s*:\s*"([^"]+)"', "name")
    pypi_name = literal("packages/baker/pyproject.toml",
                        r'^name\s*=\s*"([^"]+)"', "name")
    layout_raw = literal("packages/layout/package.json",
                         r'^\s*"version"\s*:\s*"([^"]+)"',
                         "version")
    layout = parse(layout_raw, _SEMVER, "@ophtml/layout version")
    check(baker == layout,
          "@ophtml/layout %s and ophtml %s are the same version in the "
          "two spellings" % (layout_raw, BAKER_VERSION),
          "@ophtml/layout is %s and ophtml is %s; they bake and load one "
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

    # 5-7. The newest CHANGELOG section states the same facts.
    #
    #     TWO HEADING SHAPES, ONE INVARIANT. The rule being enforced is
    #     "the newest section names the version the packages carry" --
    #     the heading shape then says which state the tree is in:
    #
    #         prerelease  ->  ## Unreleased — 0.4.0.dev0
    #         release     ->  ## 0.3.0 — 2026-09-04
    #
    #     The first version of this rule demanded `Unreleased — X`
    #     unconditionally, which made docs/releasing.md's own step 4
    #     UNSATISFIABLE: that step says to retitle the open section to
    #     `## <version> — <date>` and open a fresh `## Unreleased —
    #     <next>.dev0` above it, and doing exactly that put a heading
    #     naming the NEXT version where this rule reads the current
    #     one. Nobody noticed because nobody had cut a release -- the
    #     runbook and its checker had never been run against each
    #     other. Found by applying releasing.md literally and reading
    #     the output, which is the only way that class of disagreement
    #     surfaces.
    #
    #     So the retitle and the fresh Unreleased section are now two
    #     steps in releasing.md rather than one, and this rule tracks
    #     both states instead of forbidding half of the procedure.
    sections = changelog_sections()
    head, body = sections[0]
    if is_prerelease(baker):
        m = re.match(r"^Unreleased — (\S+)$", head)
        check(m is not None and m.group(1) == BAKER_VERSION,
              "CHANGELOG's open section is headed with %s" % BAKER_VERSION,
              "CHANGELOG's first heading is %r; %s is a prerelease, so it "
              "must read 'Unreleased — %s' -- the notes and the packages "
              "carry one number" % (head, BAKER_VERSION, BAKER_VERSION))
    else:
        m = re.match(r"^(\S+) — (\d{4}-\d{2}-\d{2})$", head)
        check(m is not None and m.group(1) == BAKER_VERSION,
              "CHANGELOG's newest section is headed '%s', dated, and is "
              "the release the packages carry" % head,
              "CHANGELOG's first heading is %r; %s is a release, so it "
              "must read '%s — <YYYY-MM-DD>'. A section still headed "
              "'Unreleased' over a tagged version says the notes were "
              "never cut" % (head, BAKER_VERSION, BAKER_VERSION))

    claimed = format_version_in(body)
    check(claimed == UIB_VERSION,
          "CHANGELOG's open section names format v%d" % UIB_VERSION,
          "CHANGELOG's open section names format v%s, the writer emits v%d"
          % (claimed, UIB_VERSION))

    # The released section below it, and the drift the prose claims.
    #
    # AND THE ONE THING TAKEN ON FAITH. Everything below derives the
    # four-move count and the v4-v7 enumeration from "0.2.0 shipped
    # format v3", read out of the CHANGELOG's own 0.2.0 section --
    # which nothing in the tree can confirm, because there is no 0.2.0
    # tag and no artifact to inspect. These rules make the CHANGELOG
    # self-consistent about an anchor that rests on memory. That is
    # exactly what "0.2.0 named nothing" means, so there is no fix
    # available now; it is written down here and in the CHANGELOG so
    # the arithmetic is not mistaken for a measurement.
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

    # `(\S+)` here used to swallow whatever punctuation followed the
    # version, so "since 0.3.0, which shipped v7" captured "0.3.0,"
    # and failed against "0.3.0". A rule that a comma defeats is the
    # same species of trap as the tag rule: the failure names a
    # mismatch that is not one, and the reader's cheapest way out is
    # to stop believing the check. A version is the only thing that
    # goes there, so it says so.
    m = re.search(r"^(\w+) format moves have landed since (\d+\.\d+\.\d+)",
                  body, re.M)
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
    opener = ("Both packages are published" if PUBLISHED
              else "Neither package is published")
    m = re.search(r"\*\*" + opener + r".*?\n\n", readme, re.S)
    if m is None:
        check(False, "", "README.md has no '**%s' paragraph under Quick "
                         "start. That is the only place a stranger is told "
                         "how to get this toolchain, and PUBLISHED is %s in "
                         "check-versions.py -- flip it in the same commit "
                         "that uploads, and rewrite the paragraph to match "
                         "(docs/releasing.md step 8)." % (opener, PUBLISHED))
    else:
        note = m.group(0)
        missing = [w for w in (BAKER_VERSION, layout_raw,
                               "format **v%d**" % UIB_VERSION,
                               "%s moves" % {0: "zero", 1: "one",
                                             2: "two", 3: "three",
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

    # 11. A prerelease may not publish to `latest`. npm resolves
    #     `npm install <pkg>` against the `latest` dist-tag, and
    #     `npm publish` sets `latest` regardless of whether the version
    #     is a prerelease -- so without publishConfig the honesty above
    #     survives exactly until someone runs publish. Both directions:
    #     a release version must NOT be pinned to a side channel it
    #     would then be stuck behind. docs/releasing.md carries the
    #     reasoning, and pip's weaker guarantee, which has no
    #     mechanical fix here at all.
    tag = re.search(r'"publishConfig"\s*:\s*\{[^}]*?"tag"\s*:\s*"([^"]+)"',
                    open(os.path.join(ROOT, "packages", "layout",
                                      "package.json"),
                         encoding="utf-8").read(), re.S)
    tag = tag.group(1) if tag else "latest"
    # SCOPED PACKAGES DEFAULT TO `restricted`. There is no `access`
    # key and no `--access public` anywhere in releasing.md, whose step
    # 8 reads as the complete procedure -- so the first publish would
    # either fail or land private. Cheap to fix after the fact, cheaper
    # to state once next to the tag it already sets.
    access = re.search(r'"publishConfig"\s*:\s*\{[^}]*?"access"\s*:\s*'
                       r'"([^"]+)"',
                       open(os.path.join(ROOT, "packages", "layout",
                                         "package.json"),
                            encoding="utf-8").read(), re.S)
    if npm_name.startswith("@"):
        check(access is not None and access.group(1) == "public",
              "@%s is scoped and publishes with access: public"
              % npm_name.split("/")[0].lstrip("@"),
              "%s is scoped, and npm defaults a scoped package to "
              "`restricted`. Set publishConfig.access to \"public\" beside "
              "the tag, or the first publish lands private or fails."
              % npm_name)

    if is_prerelease(layout):
        check(tag != "latest",
              "@ophtml/layout publishes to the %r dist-tag, so a publish of "
              "this prerelease would not take `latest`" % tag,
              "@ophtml/layout is the prerelease %s but would publish to "
              "`latest`; `npm install @ophtml/layout` would then hand "
              "someone an unverified renderer. Set publishConfig.tag "
              "(see docs/releasing.md)" % layout_raw)
    else:
        check(tag == "latest",
              "@ophtml/layout %s is a release and publishes to `latest`"
              % layout_raw,
              "@ophtml/layout %s is a release but publishConfig pins it to "
              "%r, so `npm install @ophtml/layout` would not find it. Drop "
              "publishConfig.tag when the version stops being a prerelease "
              "(see docs/releasing.md)" % (layout_raw, tag))

    # 12. The release procedure exists and covers the rule below, which
    #     is otherwise a trap: it fails on a version nobody has tagged,
    #     with nothing to say what would satisfy it, and the cheapest
    #     way out of a rule you do not understand is to delete it.
    rel = os.path.join(ROOT, "docs", "releasing.md")
    steps = (open(rel, encoding="utf-8").read()
             if os.path.exists(rel) else "")
    #     EXISTENCE AND KEYWORDS, and the ok-line says so. A procedure
    #     that drifts out of date keeps passing this: nothing here can
    #     tell whether step 4 still describes what the CHANGELOG rules
    #     read. That is the right scope for a rule whose job is to stop
    #     the tag rule being a trap, but the first version of this line
    #     read "documents the steps the tag rule demands", which claims
    #     the correctness it does not check -- the exact overstatement
    #     this file exists to stop.
    check(bool(steps) and "__version__" in steps and "Tag it" in steps,
          "docs/releasing.md exists and still names __version__ and the "
          "tagging step (keywords, not correctness)",
          "docs/releasing.md is missing or no longer names __version__ and "
          "the tagging step; the rule below fails a release with no "
          "instructions for satisfying it")

    # 17. THE DISTRIBUTION NAMES, which nothing read until now.
    #
    #     The rename to @ophtml/layout and ophtml is the one
    #     IRREVERSIBLE thing in the release -- npm's unpublish window
    #     closes in 72 hours and leaves the name blocked, PyPI never
    #     releases a name -- and it was the one thing with no fence,
    #     while the versions, which are freely reversible, had sixteen.
    #
    #     Demonstrated rather than argued: reverting the rename across
    #     the whole tree and leaving this file's message strings alone
    #     left the output BYTE-IDENTICAL at 16/16, printing
    #     "ok - @ophtml/layout ... and ophtml ..." over manifests that
    #     said @ps2ui/layout and ps2ui-bake. Every name in this file is
    #     a literal inside a format string; rule 2 reads `version` and
    #     rule 11 reads `publishConfig.tag`, and neither has ever read
    #     `name`. A rename that only prose remembers is one the next
    #     sed can undo in silence.
    # NAMED HERE, NOT INFERRED. A consistency rule is not enough: a
    # wholesale sed back to the old names is SELF-CONSISTENT and passes
    # it, which is exactly the reversal this rule exists to catch. So
    # the checker states what the packages are called, and renaming
    # them means editing this line -- the same friction ASSERTED_BLOCKS
    # has, for a stronger reason: a published name is permanent, and
    # npm gives back neither the name nor the 72 hours.
    for got, want, where in ((npm_name, EXPECTED_NPM,
                              "packages/layout/package.json"),
                             (pypi_name, EXPECTED_PYPI,
                              "packages/baker/pyproject.toml")):
        check(got == want,
              "%s is named %s" % (where.split("/")[1], got),
              "%s is named %r; this repository publishes %r. If that is "
              "a deliberate rename, change EXPECTED_NPM/EXPECTED_PYPI in "
              "check-versions.py in the same commit -- a name is "
              "permanent once published, so it should not be something a "
              "sed can move in silence." % (where, got, want))
    # 19. EACH PACKAGE HAS THE README ITS REGISTRY PAGE RENDERS.
    #
    #     Found by running `npm pack --dry-run` before the first
    #     publish rather than after: packages/layout/ had no README.md
    #     and @ophtml/layout's npm page would have been blank. npm
    #     takes a version once, so the repair would have been 0.3.1 and
    #     0.3.0's page would stay empty for good.
    #
    #     THE TWO HALVES ARE NOT THE SAME CHECK, and the first version
    #     of this rule pretended they were. It required `files` to name
    #     README.md and shared one failure message -- "the package
    #     would publish with no front page" -- across both. Measured on
    #     this package, npm ships README.md whatever `files` says:
    #
    #         files: [src/, bin/, README.md]  -> 17 files, README in
    #         files: [src/, bin/]             -> 17 files, README in
    #         README.md deleted               -> 16 files
    #
    #     So on the npm side the FILE is load-bearing and the manifest
    #     entry is not, and the rule asserted the consequence backwards:
    #     dropping the entry fired a failure claiming a blank page for a
    #     package that packs the README anyway. A check that misdescribes
    #     what the tool does is the thing this repository spends its time
    #     undoing, so the npm half now checks only what npm acts on.
    #
    #     setuptools is the opposite and the rule stays strict there:
    #     with `readme` removed, the wheel's METADATA loses
    #     Description-Content-Type entirely and the description is 0
    #     bytes, so PyPI really does render nothing. Measured the same
    #     way, by building the wheel and reading its METADATA.
    for what, declared, path in (
            ("npm always ships README.md whatever `files` says, so the "
             "file itself is the whole of it", True,
             "packages/layout/README.md"),
            ("setuptools renders it from `readme` in pyproject.toml, and "
             "without that key the wheel's description is 0 bytes",
             bool(re.search(r'^readme\s*=\s*"README\.md"\s*$',
                            open(os.path.join(ROOT, "packages", "baker",
                                              "pyproject.toml"),
                                 encoding="utf-8").read(), re.M)),
             "packages/baker/README.md")):
        exists = os.path.exists(os.path.join(ROOT, *path.split("/")))
        check(declared and exists,
              "%s is there%s" % (path, "" if path.endswith("layout/README.md")
                                 else " and pyproject.toml declares it"),
              "%s: %s%s. %s"
              % (path,
                 "the file is missing" if not exists
                 else "packages/baker/pyproject.toml does not declare "
                      "readme = \"README.md\"",
                 "", "The registry page would be blank, and neither "
                     "packager calls that an error -- " + what))

    # 20. THE RELEASE NOTES DO NOT OUTLIVE THEIR OWN CLAIM.
    #
    #     docs/releasing.md step 8 lists three edits the upload
    #     requires. PUBLISHED and the README's Quick start note were
    #     fenced against each other in both directions; the CHANGELOG's
    #     "Tagged is not published" paragraph was the third, and
    #     nothing read it -- so the upload could happen with the
    #     release notes still telling a reader neither package exists
    #     on a registry, and no check would say so. Two of three edits
    #     mechanical and the third a matter of remembering is the
    #     arrangement this file exists to end.
    #
    #     Raised in review of the commit that added the other two.
    changelog = open(os.path.join(ROOT, "CHANGELOG.md"),
                     encoding="utf-8").read()
    claim = "**Tagged is not published.**"
    present = claim in changelog
    check(present != PUBLISHED,
          "CHANGELOG's %s paragraph is %s, matching PUBLISHED = %s"
          % (claim.strip("*."), "present" if present else "gone", PUBLISHED),
          "CHANGELOG.md %s %r while PUBLISHED is %s in check-versions.py. "
          "%s (docs/releasing.md step 8 lists all three edits: this "
          "paragraph, the README's Quick start note, and PUBLISHED "
          "itself)."
          % ("still says" if present else "no longer says", claim, PUBLISHED,
             "The release notes tell a reader nothing has been uploaded "
             "when it has." if present else
             "Nothing has been uploaded, so the release notes should "
             "still say so."))

    check(npm_name.startswith("@") and "/" in npm_name,
          "the npm package is scoped: %s" % npm_name,
          "packages/layout/package.json is named %r; the ophtml org is "
          "owned and the scope is what makes the name unambiguously ours"
          % npm_name)
    # Read back where a person is told what to install. Same shape as
    # rule 10: the document has to carry the fact, and the fact has to
    # be the one the manifest states.
    for rel, needles in (
            ("README.md", (npm_name, pypi_name)),
            ("CHANGELOG.md", (npm_name, pypi_name)),
            ("docs/releasing.md", (npm_name, pypi_name)),
            ("docs/tutorial-uc3.md", ("npm install -g " + npm_name,
                                      "pip install " + pypi_name))):
        text = open(os.path.join(ROOT, *rel.split("/")),
                    encoding="utf-8").read()
        if rel.endswith("tutorial-uc3.md"):
            # THE BLOCK A READER COPIES, not the document. Both names
            # appear twice in the tutorial -- once in the install block
            # and once in the prose explaining it -- so a search of the
            # whole file is satisfied by the prose while the block says
            # something else. Sabotaging the block passed until this
            # narrowed to it.
            block = re.search(r"```\n(npm install -g .*?)```", text, re.S)
            if block is None:
                check(False, "", "docs/tutorial-uc3.md has no install "
                                 "block starting `npm install -g`; that "
                                 "block is what this rule reads")
                continue
            text = block.group(1)
        missing = [n for n in needles if n not in text]
        check(not missing,
              "%s names the packages it tells people to install" % rel,
              "%s does not mention %s. The manifests say %s and %s; a "
              "document that names something else sends a reader to a "
              "package that does not exist."
              % (rel, " or ".join(repr(m) for m in missing),
                 npm_name, pypi_name))

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

    # 18. THE WORKFLOW ACTUALLY RUNS THE RULE BELOW.
    #
    #     `--except-tag` split this file's run in two, and the whole
    #     arrangement lived in `.github/workflows/ci.yml`, which
    #     nothing in the tree parsed. Two one-line edits left every
    #     check green while the tag rule stopped being enforced
    #     ANYWHERE -- delete the final unflagged step, or give it the
    #     flag, and no run in either workflow ever evaluates rule 8
    #     again. `--except-tag` would go on printing its honest `skip`
    #     line into a log nobody reads, and CI would be green on a
    #     release naming a tag that does not exist.
    #
    #     That is the failure the flag was introduced to fix, one
    #     level up and inverted: the version that went RED was found
    #     the day it happened, and this one goes GREEN. A convention
    #     protecting the one rule whose entire purpose is to be
    #     un-skippable is not protection, so it becomes a fact the way
    #     this repository makes other cross-file orderings facts --
    #     check-timing-probe.py reads main.c, check-tutorial.py names
    #     ASSERTED_BLOCKS.
    #
    #     THIS RULE RUNS IN BOTH INVOCATIONS, deliberately. Only rule
    #     8 is gated, so the early `--except-tag` step evaluates this
    #     one -- a rule that could only be checked by the step being
    #     deleted would protect nothing.
    wf = os.path.join(ROOT, ".github", "workflows", "ci.yml")
    if not os.path.exists(wf):
        check(False, "", ".github/workflows/ci.yml is missing or was "
                         "renamed, so nothing proves this file is run at "
                         "all. Point this rule at the workflow that runs "
                         "it, in the same commit that moves it.")
    else:
        # `run:` LINES ONLY. The file names this script in prose twice,
        # and a rule satisfied by a comment is satisfied by deleting
        # the step and leaving the comment behind.
        wf_text = open(wf, encoding="utf-8").read()
        runs = list(re.finditer(r"^[ \t]*run:[ \t]*python3 "
                                r"tools/check-versions\.py[ \t]*(.*?)[ \t]*$",
                                wf_text, re.M))
        bare = [m for m in runs if not m.group(1)]
        check(len(bare) == 1,
              "ci.yml runs this file unflagged exactly once, so the tag "
              "rule is evaluated (%d invocation(s) in total)" % len(runs),
              "ci.yml has %d unflagged invocation(s) of check-versions.py "
              "and needs exactly one. With none, rule 8 below is enforced "
              "nowhere and a release can name a tag that does not exist; "
              "the flagged runs would stay green and say nothing."
              % len(bare))
        # AND IT IS THE LAST `run:` IN THE FILE. Moving it back in
        # front of the suite is the regression `--except-tag` exists to
        # prevent: the run would still evaluate rule 8, and would still
        # take the 242 baker tests, both example builds and the
        # tutorial down with it on every release commit.
        #
        # ANCHORED TO THE LAST `run:` STEP, NOT TO THIS FILE'S OTHER
        # INVOCATIONS. The first version compared the unflagged run's
        # index against the count of check-versions.py invocations and
        # skipped the comparison whenever there was only one -- so
        # deleting the final step and un-flagging the first one left a
        # single unflagged run sitting in front of the whole suite,
        # which is precisely the arrangement being fixed, and it
        # PASSED. Found by sabotage; a guard that steps aside in the
        # case it is meant to catch is not a guard.
        if len(bare) == 1:
            last_run = list(re.finditer(r"^[ \t]*run:", wf_text, re.M))[-1]
            check(bare[0].start() == last_run.start(),
                  "and it is the last `run:` step in the workflow, so a "
                  "red tag rule cannot mask the checks before it",
                  "ci.yml's unflagged check-versions.py run is not the "
                  "last `run:` step in the file. A release commit cannot "
                  "satisfy rule 8, so an unflagged run placed before the "
                  "suite fails there and takes every later step with it -- "
                  "which is exactly what moving it to the end fixed.")

    # 8. A release version names a tag. A prerelease is allowed to name
    #    nothing, which is the whole reason to carry one.
    tags = git_tags()
    if except_tag:
        # SAID OUT LOUD. A green `--except-tag` run is not a pass, and
        # the one thing that would make this flag dangerous is someone
        # reading its exit status as one.
        print("skip - the tag rule, deferred to the full unflagged run at "
              "the end of this job (--except-tag)")
    elif is_prerelease(baker):
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
              "release or carry a .dev/rc version until you do -- "
              "docs/releasing.md is the order of operations."
              % (BAKER_VERSION,
                 " (this checkout has no tags at all -- if it is a shallow "
                 "clone, fetch them)" if not tags else ""))

        # 21. THE TAG NAMES THE TREE THAT WOULD BE PUBLISHED.
        #
        #     The rule above asks only whether a tag with that NAME
        #     exists. It never resolves it to a commit, so a tag
        #     pointing anywhere at all passes -- and docs/releasing.md
        #     step 8 says `git checkout v0.3.0` before building. Steps
        #     7 and 8 are separate events with merges possible in
        #     between, and nothing re-checked that the packaged tree had
        #     not moved. That produced a stale v0.3.0 twice: the tag sat
        #     at the commit that cut the release while main carried
        #     later edits to both package READMEs, so a publish from the
        #     tag would have shipped prose nobody had reviewed as the
        #     release.
        #
        #     Sits inside the same --except-tag gate as the rule above,
        #     and for the same reason: on the release PR the tag does not
        #     exist yet, and failing a PR for that is the trap the flag
        #     was added to avoid. It is evaluated on the authoritative
        #     unflagged run, where the tag is on main and can be wrong.
        tag = next((t for t in ("v" + BAKER_VERSION, BAKER_VERSION)
                    if t in tags), None)
        if tag is not None:
            moved = git_packaged_diff(tag)
            if moved is None:
                check(False, "", "%s exists but git cannot diff it against "
                                 "HEAD, so it cannot be shown to name the "
                                 "tree a publish would upload (shallow "
                                 "clone? fetch the tag's objects)" % tag)
            else:
                check(not moved,
                      "%s names the packaged tree at HEAD" % tag,
                      "%s does not name the tree a publish from HEAD would "
                      "upload: %s %s under %s. docs/releasing.md step 8 "
                      "builds from the tag, so publishing now ships the "
                      "tag's version of %s and not HEAD's. Either move the "
                      "tag to the commit being published or cut the next "
                      "version from HEAD."
                      % (tag, ", ".join(moved),
                         "differs" if len(moved) == 1 else "differ",
                         "the packaged paths", "them"))

    if fail:
        print("not ok - %d version claim(s) above disagree with the code"
              % len(fail))
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
