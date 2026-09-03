# Releasing

Nothing here has been released. Both packages carry a prerelease —
`0.3.0.dev0` for `ophtml` on PyPI, `0.3.0-dev.0` for `@ophtml/layout`
on npm — and
there are no git tags at all. This file exists because
`tools/check-versions.py` enforces a rule that is otherwise a trap:

> A version that is **not** a prerelease must name a git tag.

The first person to bump a version to `0.3.0` and push will get a red
CI with no idea what satisfies it, and the cheapest way out of a rule
you do not understand is to delete it. So the order of operations is
written down, and the check's failure message points here.

## What a prerelease actually protects

Less than it looks like, and the exact amount matters.

**npm.** A range like `^0.3.0` does not match `0.3.0-dev.0`, so a
dependent asking for the package by range never resolves a prerelease.
But `npm install @ophtml/layout` resolves the **`latest` dist-tag**, and
`npm publish` sets `latest` regardless of whether the version is a
prerelease. `packages/layout/package.json` therefore carries

```json
"publishConfig": { "tag": "next" }
```

so a publish of the current tree lands under `@next` and leaves
`latest` unset. `npm install @ophtml/layout` then fails outright rather
than handing someone an unverified renderer, which is the intended
answer while the renderer is unverified. `check-versions.py` holds the
two together: a prerelease version may not publish to `latest`.

**pip has no equivalent, and the gap is real.** Pip excludes
prereleases from a specifier *unless* one is explicitly requested or
**no stable version exists that satisfies it**. `ophtml` has never
been published, so if `0.3.0.dev0` were the first upload, a plain
`pip install ophtml` would resolve it — the prerelease marker would
buy nothing at all.

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
   open a fresh `## Unreleased — <next>.dev0` above it carrying the
   `.uib` format paragraph. That paragraph is read by
   `check-versions.py`: it must name the current format version, count
   the moves since the section below it, and enumerate them.

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

8. **Then publish**, npm and PyPI, in that order or either. This is the
   step Phase 4's exit gate is about: a stranger with npm, pip and a
   TTF reproduces the memcard example, and its hardware screenshot,
   without cloning the repo. Until that has actually been done by
   someone who is not us, the gate is not met.

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
whatever version comes after the pledge. Steps 2 through 7 are hand
edits that CI checks, not a script that performs them. That is
deliberate at this size: the checks are the part that has to be
reliable.
