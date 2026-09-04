# Releasing

`0.3.0` is released and tagged `v0.3.0` — the first tag this
repository has ever had. Neither package has been **uploaded** yet;
tagging and publishing are steps 7 and 8 and they are not the same
event. This file exists because `tools/check-versions.py` enforces a
rule that is otherwise a trap:

> A version that is **not** a prerelease must name a git tag.

Someone bumping a version and pushing gets a red CI with no idea what
satisfies it, and the cheapest way out of a rule you do not understand
is to delete it. So the order of operations is written down, and the
check's failure message points here.

**This file and that check had never been run against each other.**
Cutting 0.3.0 by following the steps below as they were written
produced a red CI: step 4 said to open a fresh `## Unreleased —
<next>.dev0` section above the release, and rule 5 read the newest
heading and demanded it name the version the packages carry. The two
were mutually unsatisfiable, and no amount of reading either one said
so — applying the runbook and reading the checker's output did. The
retitle and the fresh section are two steps now, 4 and 9, and rule 5
tracks both headings. A runbook nobody has executed is a draft.

## What a prerelease actually protects

Less than it looks like, and the exact amount matters.

This section is about the state the tree was in before `v0.3.0` and
will be in again after step 9. It is not describing the tree today.

**npm.** A range like `^0.3.0` does not match `0.3.0-dev.0`, so a
dependent asking for the package by range never resolves a prerelease.
But `npm install @ophtml/layout` resolves the **`latest` dist-tag**, and
`npm publish` sets `latest` regardless of whether the version is a
prerelease. While the version carries a prerelease,
`packages/layout/package.json` therefore carries

```json
"publishConfig": { "tag": "next" }
```

so a publish of that tree lands under `@next` and leaves `latest`
unset. `npm install @ophtml/layout` then fails outright rather than
handing someone an unverified renderer, which is the intended answer
while the renderer is unverified. `check-versions.py` holds the two
together in **both** directions: a prerelease may not publish to
`latest`, and a release may not be pinned away from it — so step 6
drops the tag and step 9 puts it back. `publishConfig.access` is
`public` throughout, because the scope needs it whatever the version
says.

**pip has no equivalent, and the gap is real.** Pip excludes
prereleases from a specifier *unless* one is explicitly requested or
**no stable version exists that satisfies it**. `ophtml` has still
never been published, so if `0.3.0.dev0` had been the first upload, a
plain `pip install ophtml` would have resolved it — the prerelease
marker would have bought nothing at all. That is still true of the
next `.dev0`, and stays true until a stable version is actually on
PyPI.

The mitigation is procedural, not mechanical: **the first PyPI upload
must be a real release.** Do not upload a `.dev`/`rc` build to PyPI to
"reserve the name". Use TestPyPI if you need to rehearse the upload.

## Cutting a release

The format pledge is the precondition, not a step. `docs/PLAN.md`
Phase 4 puts the stability pledge **post-v7**, and P3b-3 is the last
planned format-visible change in Phase 3. Do not tag a release while a
format break is still expected — that is the situation the pledge was
written twice to avoid.

1. **Decide the number.** No check makes this judgement.
   `check-versions.py` proves the claims agree with each other and with
   the format the code writes; whether `0.3.0` is the right next number
   is yours. Under 0.x, a format break is a minor bump, and four of
   them collapse into one.

2. **`packages/baker/ps2ui_bake/__init__.py`** — set `__version__`.
   This is the baker's only version literal; `pyproject.toml` derives
   from it and must keep `dynamic = ["version"]`.

3. **`packages/layout/package.json`** — set `version` to the semver
   spelling of the same number. PEP 440 `0.3.0.dev0` is semver
   `0.3.0-dev.0`; a plain release is spelled identically in both.

4. **`CHANGELOG.md`** — retitle the open section from
   `## Unreleased — <version>` to `## <version> — <YYYY-MM-DD>`, and
   stop there. Do **not** open the next `Unreleased` section yet; that
   is step 9, and doing it here puts a heading naming the *next*
   version where rule 5 reads the *current* one.

   Rule 5 accepts two heading shapes and picks by whether
   `__version__` is a prerelease — `## Unreleased — 0.4.0.dev0` while
   it is, `## 0.3.0 — 2026-09-04` once it is not. Either way the
   newest section names the version the packages carry, which is the
   invariant; the shape just says which state the tree is in.

   The section keeps its `.uib` format paragraph, which
   `check-versions.py` reads: it must name the current format version,
   count the moves since the released section below it, and enumerate
   them. Retitling does not disturb any of that — the section that was
   open becomes the released one, and the section below it is still
   the one the drift is counted from.

5. **`README.md`** — the Quick start note names both versions, the
   format version and the drift; it is checked, so it moves with them.
   A published release means rewriting it to say how to install rather
   than why not to.

6. **`packages/layout/package.json`** — drop `publishConfig.tag` (or
   set it to `latest`) only when the version stops being a prerelease.
   The check requires the two to agree in both directions.

7. **Tag it**, `0.3.0` or `v0.3.0` — `check-versions.py` accepts
   either, and it is the rule that fails until you do. CI checks out
   with `fetch-depth: 0` so the tag is visible to it.

   **The pull request carrying steps 2–6 will be red on exactly this
   rule, and that is the only honest ordering.** The tag has to name a
   commit on `main`, and with squash merges the branch commit is not
   that commit — so the tag cannot exist until after the merge. Tagging
   the branch head instead would turn the check green and leave the tag
   pointing at a commit no branch contains. Merge first, tag `main`,
   and let the rule go green on `main`. Every *other* rule must be
   green before the merge; if a second one is red, that is a real
   failure and not this ordering.

   Cutting 0.3.0 is also what showed that this rule, sitting in CI's
   first step, took the whole job down with it — the baker suite, both
   example builds and the tutorial never ran on the commit that cut
   the release, because a check needing no toolchain had been placed
   in front of every check that does. `ci.yml` runs
   `check-versions.py --except-tag` first, so a real disagreement
   still fails before anything is installed, and the full unflagged
   command last, where its failure can no longer hide a suite. So the
   red on this rule now sits at the *end* of a job that otherwise
   passed, and the rest of the run means something.

   That arrangement is itself checked, and it had to be: it lived
   entirely in `ci.yml`, which nothing parsed, so deleting the final
   unflagged step or giving it the flag left every check green while
   the tag rule stopped being enforced anywhere at all. `check-
   versions.py` now reads the workflow and requires exactly one
   unflagged invocation of itself, as the last `run:` step in the
   file. Moving it means editing that rule in the same commit.

8. **Then publish, npm and PyPI in one sitting.** Not staggered: the
   two halves are one product on one version number, and
   `check-versions.py` rule 2 exists to keep them that way. A stagger
   leaves a window where `npm install` works and `pip install` does
   not, which is the exact confusion the shared number prevents.

   `@ophtml/layout` is scoped and npm defaults a scoped package to
   `restricted`, so `publishConfig.access` is `public` —
   `check-versions.py` requires it, because the alternative is a first
   publish that fails or lands private with nothing having said so.

   **Build and look at the artifacts before uploading either.** Both
   packagers ship what exists and say nothing about what does not:

   ```sh
   git checkout v0.3.0

   cd packages/layout && npm pack --dry-run
   cd ../baker && rm -rf dist/ && python3 -m build && python3 -m twine check dist/*
   ```

   Read the file lists. `npm pack --dry-run` before the first publish
   is what caught `packages/layout/README.md` missing while
   `package.json` named it in `files` — the tarball was 16 files, the
   installed package was `bin src package.json`, and the npm page would
   have been blank. Rule 19 fences that now, but the habit is the point:
   a manifest naming a file that is not there is not an error to either
   tool.

   Then install what you built and run it from outside the checkout,
   which is the only way to see a packaging bug at all:

   ```sh
   python3 -m venv /tmp/v && /tmp/v/bin/pip install dist/*.whl
   /tmp/v/bin/ps2ui --version
   cd /tmp && /tmp/v/bin/ps2ui serve --uib <any>.uib --selftest
   ```

   That last command is the real smoke test: it exercises
   `serve_page.html`, which is package DATA and was omitted from both
   artifacts until `[tool.setuptools.package-data]` declared it. In a
   checkout the page is simply there, so nothing local can fail.

   Rehearse the PyPI upload on TestPyPI first —
   `twine upload --repository testpypi dist/*`. **PyPI never re-accepts
   a version**, so a bad `0.3.0` means `0.3.1` and the bad one is
   permanent; npm gives 72 hours and then blocks the name. These are
   the only genuinely irreversible steps in this document.

   **The upload is three edits, not one command.** Publishing makes the
   README's Quick start note false, and the note is checked:

   - `PUBLISHED = False` → `True` in `tools/check-versions.py`.
   - the README's Quick start paragraph, which must then open
     `**Both packages are published` instead of `**Neither package is
     published` — rule 10 reads whichever opener `PUBLISHED` selects,
     in both directions, so flipping one without the other fails.
   - the CHANGELOG's **"Tagged is not published"** paragraph in the
     `0.3.0` section, which is present-tense and stops being true.

   Rule 10 used to key on the literal `Neither package is published`,
   which meant rewriting the note the day it stopped being true would
   have *failed the check* — a document instructing you to do the thing
   a checker forbids, the same trap step 4 and rule 5 were in. That was
   found by reading rule 10 while writing this step rather than by
   hitting it, which is the only time in this file's history that has
   happened.

   This is the step Phase 4's exit gate is about: a stranger with npm,
   pip and a TTF reproduces the memcard example, and its hardware
   screenshot, without cloning the repo. Until that has actually been
   done by someone who is not us, the gate is not met — uploading is
   necessary for it and not sufficient.

9. **Back to development**, once the tag is pushed. This is the other
   half of the old step 4, and it is four edits that move together:

   - `__version__` → `<next>.dev0`, `package.json` → `<next>-dev.0`.
   - `publishConfig.tag` → `"next"` again. Rule 11 runs in both
     directions: a prerelease may not publish to `latest`, and a
     release may not be pinned away from it. Step 6 dropped the tag;
     this puts it back, for the same reason it existed.
   - a fresh `## Unreleased — <next>.dev0` above the release section,
     carrying its own `.uib` format paragraph.
   - the README's Quick start note, which names both versions.

   That paragraph's drift count is **zero** straight after a release —
   the section below it shipped the format the tree still writes — and
   `check-versions.py` spells zero as a word like every other count it
   reads. If it is not zero, a format move landed in the same change
   as the release, which is its own problem.

   Two things about that paragraph are load-bearing and neither is
   obvious, both found by writing it and watching the check fail:

   - **The drift sentence starts a line and finishes on it.** The rule
     is anchored to a line start and reads the version off the same
     line, so wrapping between "landed since" and the version makes the
     sentence invisible and the check reports it missing rather than
     wrong.
   - **With a drift of zero, do not write `vN` in it.** The rule reads
     every `vN` in that paragraph as a claimed move and holds the list
     to exactly the moves there were — which, after a release, is none.
     Say "format **version 7**" in the words the format-version rule
     reads and leave the `v`-spelling for a paragraph with moves in it.

   Nothing forces this step. It is the one part of the procedure no
   check demands, because a tree sitting at a tagged release is
   internally consistent and will stay green indefinitely; the cost of
   skipping it is that the next change lands with no section to go in.

## Names, and what deliberately did not change

The two **distribution** names are `@ophtml/layout` on npm and `ophtml`
on PyPI. npm is scoped because the `ophtml` organisation is owned and a
scope is unambiguously ours; PyPI has no scopes, so it is the bare name.

Nothing else was renamed, and that is a decision rather than an
oversight:

| | name | why |
|---|---|---|
| commands | `ps2ui`, `ps2ui-bake`, `ps2ui-check`, `ps2ui-fontgen`, `ps2ui-layout` | they drive the ps2ui format |
| Python module | `ps2ui_bake` | imported by nothing outside the package; renaming it churns every import, every `PYTHONPATH`, and every `python3 -m` line in the docs for no reader's benefit |
| format, runtime | `.uib`, `ps2ui.h`, `ps2ui_load` | the format is ps2ui and always was |

A later change that "finishes the rename" by moving the module or the
commands is not finishing anything. The product is OPHTML; the format
and its tooling are ps2ui, and the two names are doing different jobs.

## What is still not automated

There is no release workflow, no build-and-upload job, and no
provenance in the blob — a `.uib` does not record which baker version
wrote it, and adding a field for it is a format change, so it waits for
whatever version comes after the pledge. Steps 2 through 6 and step 9
are hand edits that CI checks, not a script that performs them. That is
deliberate at this size: the checks are the part that has to be
reliable.

What CI cannot check is this document. Rule 12 reads it for two
keywords and says so in its own ok-line — it exists to stop the tag
rule being a trap, not to prove the steps are right. The steps were
wrong for as long as nobody ran them, and the thing that found it was
executing them, so the next person to change this file should cut a
release against a scratch copy before believing it.
