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

--orphans FAILS; EVERYTHING ELSE WARNS AND NEVER DOES, and the split
is an argument rather than a mood. See the bottom of orphans().

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
  - A BARE FILENAME IS NOT A PATH WAS THE LIMIT HERE, AND IS NOW
    RESOLVED. `resolve()` reaches the file a bare `check.py` or a
    project-relative `ui/probe.html` names, and reports rather than
    guesses when several answer. Measured across the change: 512 more
    edges on real files, 38 files newly reachable, and
    `runtime/ps2ui.h` went from 45 documents to 58. It also dropped
    454 index keys that named nothing tracked -- three quarters of the
    old index was tokens like `../../../../Users/you/repo/fonts.json`
    from a pasted shell transcript, harmless because they matched no
    changed file, and noise the moment anything asks what is unresolved.

  - A DELETED FILE UNDER A GITIGNORE RULE READS AS A BUILD ARTIFACT,
    not an orphan, which is the price of not reporting `build/ui.uib`
    on every run. It is narrow here: nothing in the library cites a
    path under any ignore rule except the generated
    `runtime/sample/ps2ui.[ch]` copies, and no citation targets those.

Usage:
    tools/check-doc-impact.py [<base>]        # default: origin/main
    tools/check-doc-impact.py --impact <path> # who names this file
    tools/check-doc-impact.py --orphans       # citations the tree lost
"""
import fnmatch
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


def sh(*args, required=True):
    """Run git and return its stdout lines.

    THE FOURTH DOOR INTO THE SILENT-ZERO ROOM, and the one that opens
    where it costs most. `changed()` below enumerates three: a diff of
    nothing, a diff entirely of ignored files, and a suppressed result.
    This function was the fourth, because it kept stdout and threw away
    the exit status -- so a ref git cannot resolve produced an empty
    diff, and an empty diff reads as "nothing changed":

        $ check-doc-impact.py v0.6.O        # capital O, not zero
        ok - nothing changed against v0.6.O
        rc 0

    That is not a hypothetical spelling. docs/releasing.md step 5b is
    the one place this tool is invoked with an argument -- a release
    tag, typed by hand, once a cycle -- and the failure says the
    release has no documentation surface, which is the one answer that
    stops the step. Found while running step 5b for 0.7.0.
    """
    r = subprocess.run(args, cwd=ROOT, capture_output=True, text=True)
    if required and r.returncode != 0:
        raise GitError(" ".join(args), r.stderr.strip())
    return r.stdout.splitlines()


class GitError(Exception):
    def __init__(self, cmd, err):
        super().__init__(cmd)
        self.cmd, self.err = cmd, err


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
    # merge-base is allowed to fail (a tag with no common ancestor is
    # still a usable diff base); `git diff` is not, because that is the
    # call whose empty output means "nothing changed".
    merge_base = sh("git", "merge-base", base, "HEAD", required=False)
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

    TWO EXCLUSIONS, AND BOTH LOOK EXACTLY LIKE WHAT THIS WANTS.

    _prompts/ is the first, and the trap worth naming: those are
    briefs, one per planned page, and each carries a literal
    `sources: [<every repository path opened>]` INSIDE A FENCED BLOCK
    -- the frontmatter template the page agent is told to emit, not a
    page's own sources. A naive walk turns them into as many nodes as
    the library has pages, every one of them wrong.

    _facts/README.md is the second and the quieter one. It is the
    legend, and its example rows parse as facts and cite REAL paths --
    on this tree packages/layout/src/box.js, runtime/ps2ui.c and
    runtime/tests/test_runtime.c -- so they produce plausible false
    edges rather than obvious ones. The legend documents the row
    format, not box.js.
    """
    files = [p for p in sh("git", "ls-files", "docs/site/*.md")
             if "/_prompts/" not in p
             and not p.endswith("_facts/README.md")]
    return files or None


def tracked():
    """Every tracked path, and an index of them by basename and suffix."""
    global _TRACKED, _BY_SUFFIX
    if _TRACKED is None:
        _TRACKED = sh("git", "ls-files")
        _BY_SUFFIX = {}
        for path in _TRACKED:
            parts = path.split("/")
            for k in range(len(parts)):
                _BY_SUFFIX.setdefault("/".join(parts[k:]), []).append(path)
    return _TRACKED


_TRACKED = None
_BY_SUFFIX = None


def resolve(tok):
    """What a cited token names, as (kind, [tracked paths]).

    THE BARE BASENAME IS THE WHOLE REASON THIS FUNCTION EXISTS, and
    F30's constraint 4 is why it refuses to guess. The `source` column
    mixes qualified paths with bare names, and the ambiguity is
    concentrated rather than spread: measured on this tree, 234 of the
    fact half's 1759 path references are bare, over 24 names, and
    `check.py` alone is 58 of them -- answering to three real files.
    156 of the 234 resolve to exactly one tracked file and are edges
    the tool could not see before. 75 are ambiguous, and attaching
    them to every candidate would invent citations while dropping them
    UNDER-REPORTS SILENTLY, which is the worse of the two failure
    modes. They are reported instead, as something a human fixes by
    qualifying the path.

    Suffix rather than basename, because the same defect appears one
    level up: `ui/probe.html` names `examples/channel6/ui/probe.html`
    and resolves uniquely, while `ui/library.css` answers to four
    files and must not be guessed at either.

    The kinds:
      exact      the token is a tracked path
      glob       a literal glob matching tracked files, expanded
      suffix     a unique suffix of exactly one tracked path
      ambiguous  a suffix of several -- reported, never guessed
      artifact   resolves nowhere but is gitignored: a build output,
                 cited on purpose and absent from a clean checkout
      route      not a repo path at all (see below)
      unanchored names no directory and matches nothing -- usually
                 prose rather than a citation
      orphan     none of the above
    """
    # A LEADING SLASH MEANS IT IS NOT A REPO PATH. `previewer.md` says
    # the server answers GET `/frame.png` and `/montage.png`; those are
    # HTTP routes, and the old index took them for files. They never
    # matched a changed path, so they were harmless phantoms there and
    # would have been reported as orphans here.
    if tok.startswith("/"):
        return "route", []
    # lstrip("./") STRIPS CHARACTERS, NOT A PREFIX, and the first
    # version of this line used it: `.github/workflows/ci.yml` came
    # back as `github/workflows/ci.yml`, resolved to nothing, and was
    # reported as an orphan. Five of the eight this mode first printed
    # were that one call -- the same shape as constraint 5's extension
    # alternation, where three quarters of the output was the reader
    # misreading itself.
    bare = tok[2:] if tok.startswith("./") else tok
    while bare.startswith("../"):
        bare = bare[3:]
    if "*" in tok or "?" in tok:
        hits = [p for p in tracked()
                if fnmatch.fnmatch(p, bare) or fnmatch.fnmatch(p, "*/" + bare)]
        if hits:
            return "glob", sorted(hits)
    if bare in set(tracked()):
        return "exact", [bare]
    hits = _BY_SUFFIX.get(bare, [])
    if len(hits) == 1:
        return "suffix", hits
    if hits:
        return "ambiguous", sorted(hits)
    if _ignored(bare):
        return "artifact", []
    # A token naming no directory that matches no file is most often
    # not a path: `self.uib` is an attribute access in prose about
    # serve.py, and `ui-16x9.uib` is an output filename from a command
    # line. Kept apart from a real orphan so a reader is not sent
    # looking for a file that was never meant to exist.
    if "/" not in bare:
        return "unanchored", []
    return "orphan", []


def _ignored(path, _seen={}):
    """True when git would ignore this path. Build outputs are cited
    on purpose -- `build/ui.uib` and `build/preview.png` are what the
    documents tell a reader to produce -- and are absent from a clean
    checkout, so an existence test calls every one of them an orphan.
    F30's row predicted exactly this and named three; this tree has
    five, the two extra reached through `../`."""
    if path not in _seen:
        r = subprocess.run(["git", "check-ignore", "-q", "--", path],
                           cwd=ROOT, capture_output=True)
        _seen[path] = r.returncode == 0
    return _seen[path]


def fact_rows(path):
    """The `source` cell of every fact row in a facts file.

    STRUCTURAL, NOT A SCAN OF THE WHOLE DOCUMENT, because a fact's
    citation and a mention of a path in its prose are different
    claims. The source column is what the row was verified against.
    """
    out = []
    try:
        with open(os.path.join(ROOT, path), encoding="utf-8") as fh:
            lines = fh.readlines()
    except (OSError, UnicodeDecodeError):
        return out
    for n, line in enumerate(lines, 1):
        if not line.lstrip().startswith("|"):
            continue
        cells = split_cells(line)
        if len(cells) < 5:
            continue
        ident = cells[1]
        if not ident or ident == "id" or set(ident) <= set("-: "):
            continue
        out.append((n, ident, cells[3]))
    return out


def references(path):
    """Repo paths a document names.

    Tokens are resolved rather than taken literally, so a bare
    `check.py` or a project-relative `ui/probe.html` reaches the file
    it names. What cannot be resolved to exactly one tracked path is
    left out of the edge set and reported by --orphans instead.
    """
    full = os.path.join(ROOT, path)
    try:
        with open(full, encoding="utf-8") as fh:
            body = fh.read()
    except (OSError, UnicodeDecodeError):
        return set()
    hits = set()
    for m in PATH.finditer(body):
        tok = m.group(0)
        kind, found = resolve(tok)
        if kind in ("exact", "suffix", "glob"):
            hits.update(p for p in found if not p.startswith("docs/site/"))
    return hits


def cited_tokens():
    """Every token the library cites, as {token: {(document, how)}}.

    Two sources, kept apart because F30's constraint 2 is that they
    mix: frontmatter `sources:` lists repository code beside intra-doc
    paths like `_facts/authoring/css.md`, and a tool that does not
    separate them flags every page whenever any document is edited.
    """
    out = {}
    for doc in library_documents() or []:
        try:
            with open(os.path.join(ROOT, doc), encoding="utf-8") as fh:
                text = fh.read()
        except (OSError, UnicodeDecodeError):
            continue
        front = re.match(r"^---\n(.*?)\n---\n", text, re.S)
        if front:
            listed = re.search(r"^sources:\s*\[(.*?)\]", front.group(1),
                               re.S | re.M)
            for entry in (listed.group(1).split(",") if listed else []):
                entry = entry.strip()
                if entry:
                    out.setdefault(entry, set()).add((doc, "sources"))
        if "/_facts/" in doc:
            for lineno, ident, cell in fact_rows(doc):
                for m in PATH.finditer(cell):
                    out.setdefault(m.group(0), set()).add(
                        ("%s:%d (%s)" % (doc, lineno, ident), "fact"))
    return out


def orphans():
    """Report what the library cites that the tree no longer holds.

    THE DIRECTION THAT ROTS SILENTLY. --impact asks what a change
    breaks; this asks the reverse, and it is the half nothing else
    covers: a file deleted or moved leaves every citation of it
    pointing at nothing, and no check reads a `sources:` entry.

    IT CLASSIFIES RATHER THAN LISTING, because a flat existence test
    on this tree returns 35 and almost all of them are correct. F30's
    row predicted the shape and named three; measured here they fall
    into five kinds, and only what survives all of them is an orphan.
    """
    cited = cited_tokens()
    buckets = {}
    for tok, where in sorted(cited.items()):
        kind, _found = resolve(tok)
        buckets.setdefault(kind, []).append((tok, sorted(where)))
    ok_kinds = ("exact", "suffix", "glob")
    resolved = sum(len(buckets.get(k, ())) for k in ok_kinds)
    print("# %d distinct token(s) cited by the library; %d resolve"
          % (len(cited), resolved))
    for kind, note in (
            ("route", "not a repository path -- a leading slash, so an HTTP "
                      "route or a fragment the path pattern misread"),
            ("artifact", "gitignored build output, cited on purpose and "
                         "absent from a clean checkout"),
            ("unanchored", "names no directory and matches no file -- "
                           "usually prose, not a citation"),
    ):
        rows = buckets.get(kind, [])
        if rows:
            print("# %d %s: %s" % (len(rows), kind, note))
            for tok, _w in rows:
                print("#     %s" % tok)
    for tok, where in buckets.get("ambiguous", []):
        _k, found = resolve(tok)
        # THE COUNT OF CITING PLACES, NOT ONE OF THEM. The first
        # version printed a single location per token, and `check.py`
        # has 55 -- so the reader was handed one row to fix out of 55
        # and no way to find the rest. F44 carries the cleanup and
        # needs the population, not an example.
        print("warning - %s answers to %d tracked files (%s%s) -- qualify "
              "it, because guessing invents a citation and dropping it "
              "hides one. %d citation(s): %s%s"
              % (tok, len(found), ", ".join(found[:3]),
                 ", ..." if len(found) > 3 else "", len(where),
                 ", ".join(w for w, _h in where[:3]),
                 ", ..." if len(where) > 3 else ""))
    for tok, where in buckets.get("orphan", []):
        print("not ok - %s resolves to nothing in the tree and is not "
              "ignored. Cited by %s" % (tok, where[0][0]), file=sys.stderr)
    amb, dead = buckets.get("ambiguous", []), buckets.get("orphan", [])
    print("%s - %d ambiguous citation(s), %d pointing at nothing"
          % ("not ok" if dead else "ok", len(amb), len(dead)))
    # AND THIS MODE FAILS, WHICH THE REST OF THIS TOOL DOES NOT.
    #
    # "It warns and never fails" is an argument about DOC-NEUTRALITY: a
    # change can genuinely invalidate no prose, so --changed firing on
    # correct work would get an exemption bolted onto it. That argument
    # does not reach here. A citation naming a file the tree does not
    # hold, and that git is not ignoring, is not a judgement call and
    # is never correct -- so it fails.
    #
    # AMBIGUITY STILL ONLY WARNS, for a different reason: the 6 on this
    # tree are pre-existing and span 58 rows, 55 of them `check.py`,
    # and which of the three files each means is contextual. Failing on
    # them would block every commit on a documentation pass that has to
    # be done by reading, not by pattern.
    return 1 if dead else 0


def impact(target):
    """Which documents name this file. The query F30 opens with."""
    kind, found = resolve(target)
    if kind == "ambiguous":
        print("not ok - %r answers to %d tracked files: %s"
              % (target, len(found), ", ".join(found)), file=sys.stderr)
        return 2
    if not found:
        print("not ok - %r names nothing tracked (%s)" % (target, kind),
              file=sys.stderr)
        return 2
    corpus = repo_documents() + (library_documents() or [])
    index = {}
    for doc in corpus:
        for ref in references(doc):
            index.setdefault(ref, set()).add(doc)
    total = 0
    for path in found:
        docs = sorted(index.get(path, ()))
        total += len(docs)
        print("  %s" % path)
        for doc in docs:
            print("      cited by  %s" % doc)
        if not docs:
            print("      cited by  nothing -- which is not the same as "
                  "nothing depending on it")
    print("\n# %d document(s) name %s. File-level: this bounds the review "
          "surface, it does not decide correctness." % (total, target))
    return 0


def main():
    # --all: DO NOT HIDE A CITATION BECAUSE THE DIFF ALSO EDITS THE
    # DOCUMENT. That suppression is right for a pull request, where a
    # document you already touched is one you have already thought
    # about. It is wrong for a release, and quietly so: run against the
    # previous tag, the diff edits nearly every document in the
    # library, so 420 of 427 citations vanish and the tool reports
    # seven. docs/releasing.md step 5b calls this exact invocation
    # "the release's documentation surface" and says to read the list
    # -- so the list has to be the surface. Measured at 0.7.0, which is
    # when this flag was added.
    args = sys.argv[1:]
    if "--orphans" in args:
        return orphans()
    if "--impact" in args:
        i = args.index("--impact")
        if i + 1 >= len(args):
            print("not ok - --impact needs a path", file=sys.stderr)
            return 2
        return impact(args[i + 1])
    argv = [a for a in args if a != "--all"]
    show_all = "--all" in args
    base = argv[0] if argv else "origin/main"
    try:
        touched, ignored = changed(base)
    except GitError as e:
        # THE ONE PLACE THIS TOOL EXITS NON-ZERO, and it is not a
        # finding about the tree. "This tool warns and never fails" is
        # about DOCUMENTS; a base it cannot resolve is not a warning
        # about documents, it is the tool being unable to run -- and
        # returning 0 there is what made a typo'd tag look like a clean
        # release. See sh().
        print("not ok - cannot diff against %r: %s" % (base, e.err),
              file=sys.stderr)
        print("         %s failed. Check the ref exists: git rev-parse %s"
              % (e.cmd, base), file=sys.stderr)
        return 2
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
            if doc in docs_changed and not show_all:
                suppressed += 1
                continue
            flagged.setdefault(path, []).append(doc)

    shown_count = sum(len(v) for v in flagged.values())

    def note_suppressed():
        if suppressed:
            print("#  %d citation(s) hidden because this change already "
                  "edits the document. That is the intended rule for a\n"
                  "#  PR and the wrong one for a branch that adds "
                  "documents wholesale, so it is counted rather than\n"
                  "#  folded into the result above." % suppressed)
            # AND WHEN THE HIDDEN LIST IS THE LIST, SAY SO LOUDER.
            # Counting it is enough when it hides a handful. At release
            # scope it hid 420 of 427 and the reader still saw a
            # confident seven-line answer.
            if suppressed > shown_count:
                print("#  THAT IS MORE THAN THIS RUN REPORTED (%d shown). "
                      "Re-run with --all to see them;\n"
                      "#  docs/releasing.md step 5b wants the whole "
                      "surface." % shown_count)

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
