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

8. **Then publish**, npm and PyPI, in that order or either.
   `@ophtml/layout` is scoped and npm defaults a scoped package to
   `restricted`, so `publishConfig.access` is set to `public` beside the
   tag — `check-versions.py` requires it, because the alternative is a
   first publish that fails or lands private with nothing having said
   so. This is the
   step Phase 4's exit gate is about: a stranger with npm, pip and a
   TTF reproduces the memcard example, and its hardware screenshot,
   without cloning the repo. Until that has actually been done by
   someone who is not us, the gate is not met.

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
