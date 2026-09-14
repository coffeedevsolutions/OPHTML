#!/usr/bin/env python3
"""Which documents cite the files this change touched?

WHY THIS EXISTS. Nothing mapped a code change to the documentation it
invalidates, so the answer to "I changed ps2ui.h, which documents are
now suspect?" was to re-read them. The cost of not having it is on the
board four times over in one month: a header comment that outlived its
macro by 20 days, a README naming a Makefile target #39 deleted, a
bench card naming a cause F-005 proved impossible, and a stylesheet
still citing constants #52 removed -- that last one ten lines from
prose corrected the day before, in the same file, missed because the
grep that found the others keyed on a different removal's vocabulary.

WHAT IT DOES. Reads a diff, and for every changed file that is not
itself a document, names the documents that reference it. Two corpora,
because the project has two levels of documentation and the request
that prompted this named both:

  repo documents   every tracked *.md outside docs/site/ -- README,
                   CONTRIBUTING, docs/*.md, the example READMEs
  the library      docs/site/, when it is present: page frontmatter
                   `sources:` and the `source` column of _facts rows

The second landed on main in #133, so an ordinary checkout has both.
An absent library is still REPORTED rather than skipped silently --
"no output" and "no corpus" look identical and one of them is a defect
-- because a sparse checkout or a worktree at an older commit can
still produce it.

IT WARNS AND NEVER FAILS, and that is a decision rather than timidity.
A change can be genuinely doc-neutral -- a comment fix, a rename inside
a function -- and a fence that fires on correct work gets an exemption
bolted onto it within a week, which is how a check becomes something
everybody passes with a flag. The same argument `--except-tag` and
rule 5's two-state design were built around. Exit is 0 whatever it
finds; a human reads the list and decides.

WHAT IT CANNOT DO, stated here rather than discovered later:

  - FILE-LEVEL, NOT CLAIM-LEVEL. A one-line comment fix flags the same
    documents as an API removal. It bounds the review surface; it does
    not decide correctness.
  - IT CANNOT SEE A DOCUMENT THAT SHOULD HAVE CITED A FILE AND DID
    NOT. That is F24's failure mode one layer up, and it is the half
    of the problem this does not touch.
  - A DOCUMENT THAT NAMES NO PATHS IS INVISIBLE TO IT. Prose about
    behaviour, with no file reference, cannot be reached from a diff.
  - A BARE FILENAME IS NOT A PATH, and this one bites hardest on the
    question in the first line. Only tokens containing "/" are
    indexed, so a document writing `ps2ui.h` rather than
    `runtime/ps2ui.h` is not reached by a change to that header.
    Measured on this tree: 14 tracked documents name it bare and
    never qualified -- README.md, CHANGELOG.md, docs/bringup.md,
    docs/deploying.md, docs/releasing.md, docs/tutorial-uc3.md and
    eight more. Resolving them is F30's, because `check.py` alone
    answers to three real files and guessing is worse than missing;
    naming the limit here is not.

Usage:
    tools/check-doc-impact.py [<base>]        # default: origin/main
"""
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join("docs", "site")

# EXTENSIONS LONGEST FIRST, AND THIS IS NOT COSMETIC. An alternation
# ending (?:py|js|c|h|md|css|html|json|...) matches `c` before `css`
# and `js` before `json`, so `library.css` reads as `library.c` and
# `ps2ui.json` as `ps2ui.js`. The truncated phantoms then resolve
# against nothing. Measured while writing F30's row: a first pass
# returned 12 unresolvable paths and 9 were this bug -- three quarters
# of the output was the regex misreading itself.
_EXT = ("py js c h md css html json yaml yml sh uib png toml mk txt "
        "ini cfg").split()
PATH = re.compile(r"[A-Za-z0-9_./*-]+\.(?:%s)(?![A-Za-z0-9])"
                  % "|".join(sorted(_EXT, key=len, reverse=True)))

# Files whose change says nothing about any document.
#
# `.github/` WAS IN HERE AND IS THE REASON THIS COMMENT IS LONG. It
# looked like obvious noise and is the opposite: 33 tracked markdown
# files cite .github/workflows/ paths, 17 of them ci.yml -- PLAN.md,
# the channel-6 README, and the library's integrating, deploying and
# first-boot pages among them. A workflow is a documented subject
# here, not plumbing. #132 edited registry.yml and #133 edited
# ci.yml; under the rule this tool serves, both would have been told
# nothing changed.
#
# What remains is genuinely unreadable by anything: compiled caches
# and lockfiles. Adding to this set is a claim that NO document can
# cite the thing, and the claim above was wrong once already.
IGNORE = re.compile(r"^(.*/__pycache__/|.*\.lock$)")


def sh(*args):
    return subprocess.run(args, cwd=ROOT, capture_output=True,
                          text=True).stdout.splitlines()


def changed(base):
    """Changed paths, and how many were filtered out reaching them.

    THE COUNT IS RETURNED RATHER THAN DISCARDED, and that is the whole
    point of this signature. The filter used to run here and throw the
    number away, so a diff of nothing and a diff entirely of ignored
    files both produced "nothing changed" -- and with .github/ in the
    set, a workflow-only PR got exactly that.

    This module already knew the shape: the absent-library path says
    so out loud, and the suppression path counts. Those are two doors
    into one room and this was the third, left open because a filter
    that runs before the counting does not look like a result.
    """
    merge_base = sh("git", "merge-base", base, "HEAD")
    ref = merge_base[0] if merge_base else base
    all_paths = [p for p in sh("git", "diff", "--name-only", ref, "--") if p]
    kept = [p for p in all_paths if not IGNORE.match(p)]
    return kept, len(all_paths) - len(kept)


def split_cells(line):
    """Markdown row cells, respecting code spans.

    A `|` inside backticks is content, not a delimiter. A naive
    split('|') shreds these rows -- a first pass over the facts files
    produced 30-odd bogus statuses before the parser respected code
    spans.
    """
    cells, buf, tick = [], [], False
    for ch in line:
        if ch == "`":
            tick = not tick
            buf.append(ch)
        elif ch == "|" and not tick:
            cells.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
    cells.append("".join(buf))
    return [c.strip() for c in cells]


def repo_documents():
    """Every tracked markdown outside the library."""
    return [p for p in sh("git", "ls-files", "*.md")
            if not p.startswith(SITE + os.sep) and not p.startswith("docs/site/")]


def library_documents():
    """Pages and facts files, or None when the library is not here.

    _prompts/ IS EXCLUDED, and it is the trap worth naming: those are
    briefs, one per planned page, and each carries a literal
    `sources: [<every repository path opened>]` INSIDE A FENCED BLOCK
    -- the frontmatter template the page agent is told to emit, not a
    page's own sources. A naive walk turns them into as many nodes as
    the library has pages, every one of them wrong.
    """
    files = [p for p in sh("git", "ls-files", "docs/site/*.md")
             if "/_prompts/" not in p]
    return files or None


def references(path):
    """Repo paths a document names, as (path, how) pairs."""
    full = os.path.join(ROOT, path)
    try:
        with open(full, encoding="utf-8") as fh:
            body = fh.read()
    except (OSError, UnicodeDecodeError):
        return set()
    hits = set()
    for m in PATH.finditer(body):
        tok = m.group(0)
        if "/" in tok and not tok.startswith("docs/site/"):
            hits.add(tok)
    return hits


def main():
    base = sys.argv[1] if len(sys.argv) > 1 else "origin/main"
    touched, ignored = changed(base)
    if not touched:
        if ignored:
            print("ok - %d changed file(s) against %s, all of them "
                  "ignored (%s)" % (ignored, base, IGNORE.pattern))
            print("#    NOT an empty diff. If one of those is cited by a "
                  "document, this tool cannot say so.")
        else:
            print("ok - nothing changed against %s" % base)
        return 0

    code = [p for p in touched if not p.endswith(".md")]
    docs_changed = set(p for p in touched if p.endswith(".md"))

    repo = repo_documents()
    library = library_documents()

    print("# %d changed file(s) against %s, %d of them not documents%s"
          % (len(touched), base, len(code),
             ", %d ignored" % ignored if ignored else ""))
    if library is None:
        # SAID OUT LOUD. An empty corpus and a clean result read the
        # same, and one of them means this check knew nothing.
        print("# docs/site/ is not in this checkout, so the deep-dive "
              "library was NOT consulted. Only repo documents below.")
    else:
        print("# docs/site/: %d page and facts file(s) consulted" % len(library))

    corpus = repo + (library or [])
    index = {}
    for doc in corpus:
        for ref in references(doc):
            index.setdefault(ref, set()).add(doc)

    # A DOCUMENT THE SAME CHANGE ALREADY TOUCHED IS NOT NEWS, which is
    # right for an ordinary PR and catastrophic on a branch that adds
    # documents wholesale -- so the suppressed count is REPORTED and
    # never folded into a bare zero.
    #
    # Found by running this against the branch that carries the
    # deep-dive library: 39 of its files cite runtime/ps2ui.h, all 39
    # are "changed" relative to main because they are new there, and
    # the first version printed "no document cites any changed file".
    # An empty result and a fully suppressed one looked identical, and
    # the wrong one was true.
    flagged, suppressed = {}, 0
    for path in code:
        for doc in sorted(index.get(path, ())):
            if doc in docs_changed:
                suppressed += 1
                continue
            flagged.setdefault(path, []).append(doc)

    def note_suppressed():
        if suppressed:
            print("#  %d citation(s) hidden because this change already "
                  "edits the document. That is the intended rule for a\n"
                  "#  PR and the wrong one for a branch that adds "
                  "documents wholesale, so it is counted rather than\n"
                  "#  folded into the result above." % suppressed)

    if not flagged:
        print("ok - no document in the corpus cites any changed file")
        note_suppressed()
        print("#    file-level only: a document that SHOULD cite one and "
              "does not is invisible here")
        return 0

    print("\nwarning - documents that cite files this change touched.")
    print("          Not a failure: a change can be genuinely "
          "doc-neutral. Read them and decide.\n")
    for path in sorted(flagged):
        print("  %s" % path)
        for doc in flagged[path]:
            print("      cited by  %s" % doc)
    print("\n#  %d changed file(s) are cited by %d document(s)."
          % (len(flagged), len({d for v in flagged.values() for d in v})))
    note_suppressed()
    return 0            # ALWAYS. See the docstring.


if __name__ == "__main__":
    sys.exit(main())
