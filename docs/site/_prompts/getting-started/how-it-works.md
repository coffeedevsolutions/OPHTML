# Page: getting-started/how-it-works (How it works)

Page type: `project`. Section order: `4`. Wave: `4`.

## Purpose and audience

A concept page. The reader learns the three stages, the two seams, why everything moves to build time, why there are exactly three pens, what the previewer is, and what the runtime never does. No tables of flags.

## Read first

1. `docs/site/ARCHITECTURE.md`, all of it. The rules below are copied from it and are binding.
2. Parent facts files, before opening any source: `_facts/reference/ir-format.md`, `_facts/reference/uib-format.md`, `_facts/runtime/frame-loop.md`, `_facts/cli/previewer.md`, `_facts/authoring/text-and-fonts.md`. Reuse their fact ids; do not restate a parent fact differently. If one is wrong, write a `## disputes` section and stop.
3. The drift rows below. A page documents the truth column and never repeats the claim column.

### Voice and format (from ARCHITECTURE.md, binding)

- Imperative mood for instructions, present tense for behaviour. "Run `ps2ui build`." Never "you can run".
- Forbidden: let's, we, we'll, in this section, in this guide, simply, seamless, seamlessly, robust, leverage, powerful, note that, it's worth noting, keep in mind, as you can see, of course, essentially, basically, easily, straightforward, delve, dive into, unlock, empower, journey, crucial, vital. No emoji, no exclamation marks, no rhetorical questions.
- Lead with what the thing does and how to use it. Say why only when the reason changes what the reader does, in at most two sentences. Longer reasons are a link to `project/internals` or a `repo:` link.
- One fact per sentence, under 25 words. No em dashes.
- Flags, keys, functions, error codes and attributes live in tables with the column set named under Page structure. Prose never restates a table.
- Every code block comes from a command run in this session or a file in the tree. Output blocks are real output, trimmed with `...` only where the trimmed lines are irrelevant.
- Numbers appear only when a command in this session produced them, and the command sits beside them.
- Do not copy README.md sentences. Re-derive from code and restate.
- A feature new in 0.6.0 opens its section with `New in 0.6.0.` Nothing else carries a version.
- 300 to 1500 words of prose plus tables.
- Links: `[text](page:<id>#<anchor>)` for pages, `[path](repo:<path>#L<n>)` for repository files. Kebab-case anchors.

### Environment (run first, stop on failure)

```sh
python3 -m pip install Pillow
pip install -e packages/baker
(cd packages/layout && npm link)
python3 tools/check-versions.py --except-tag
./examples/memcard/build.sh
```

`ps2ui`, `ps2ui-bake`, `ps2ui-check`, `ps2ui-fontgen`, `ps2ui-layout`, `ps2ui-dev` are then on PATH and point at this tree. Pages show the installed spelling. The checkout spelling (`PYTHONPATH=packages/baker python3 -m ps2ui_bake.ps2ui`, `node packages/layout/bin/ps2ui-layout.js`) appears only on `cli/ps2ui` under "From a checkout".

When code, tests, a repository doc and README.md disagree, the order of authority is: code, then tests, then `docs/*.md`, then README.md. Cite the code line in the facts file.

### Known drift touching this page

| tag | where the stale claim lives | claim | truth |
|---|---|---|---|
| D12 | README.md Quick start C comment | `PS2UI_VERSION` keeps baker and runtime from drifting | It is the frozen format version, 7. Baker and runtime match because `ps2ui vendor-runtime` ships both files from one package. |

## Sources of truth

Line numbers are hints from the exploration that produced this brief; re-locate by symbol name. Authority order: code, tests, docs/*.md, README.md.

- docs/architecture.md - Shape and Decisions
- CONTRIBUTING.md rules 1-5
- packages/layout/README.md and packages/baker/README.md - what each stage decides
- packages/baker/ps2ui_bake/__init__.py docstring - the stages inside the baker

## Claims to verify, and how

Each item is `claim -> how to prove it`. Run every command. Paste real output into the page where the structure calls for it and record the result in the facts file.

1. Every claim on this page cites a fact id from a facts file -> no new verification; list the ids used in the facts file with status `verified` and the parent id in source

## Screenshots

Each line is `path <- command // alt text`. Register every file in `assets/assets.json` with the exact command (`OUT` for the output path) and `checked: true` unless the line says otherwise. Previewer renders only; Playwright only where the line says so.

- assets/getting-started/how-it-works/stages.svg <- hand-drawn SVG: three stage boxes (layout, baker, runtime) with the two seams labelled ui.json and .uib and the three pens marked // the three stages and the two files between them

## Page structure

Skeleton for type `project`: free-form, short.

Five short sections: The three stages · The two seams · Build time does the work · Three pens, one pixel · What the previewer shows and what it cannot. Each 60 to 150 words. Ends with Related pages.

Frontmatter:

```yaml
---
id: getting-started/how-it-works
title: How it works
description: <one sentence>
section: getting-started
order: 4
version: 0.6.0
sources: [<every repository path opened>]
---
```

## Cross-links

Write links as `[text](page:<id>#<anchor>)`. Every id below must appear on the page at the place named.

- reference/ir-format - The two seams
- reference/uib-format - The two seams
- authoring/text-and-fonts - Three pens
- cli/previewer - What the previewer shows
- runtime/frame-loop - Build time does the work
- project/internals - Related pages

## Facts to emit

Write `_facts/<page-id>.md` before writing the page:

```markdown
# facts: <page-id>

| id | fact | source | verified by | status |
|---|---|---|---|---|
```

Status is `verified` (a command or test in this session proved it), `code-only` (read in source; say why nothing executable exists), or `contradicts-readme` (verified, and README.md says otherwise; cite the README line). If a parent fact is wrong, append `## disputes` with the id and evidence, and stop.

This page emits no new facts. Its facts file lists the parent fact ids it relied on, each with the parent page as source.

## Out of scope

- decision history -> project/internals

## Done when

- [ ] Environment block ran clean.
- [ ] `_facts/getting-started/how-it-works.md` exists with every fact id listed under "Facts to emit", each with a status.
- [ ] Every command shown on the page was run in this session; every output block is pasted from that run.
- [ ] Every screenshot listed exists under `assets/getting-started/how-it-works/`, is registered in `assets/assets.json` with its command, and has alt text.
- [ ] Frontmatter present: `id: getting-started/how-it-works`, `title`, `description`, `section`, `order: 4`, `version: 0.6.0`, `sources` (every path opened).
- [ ] Every `page:` link names an id from the page index in ARCHITECTURE.md.
- [ ] Word count of prose is 300 to 1500 (`pandoc -t plain` or a `wc -w` after stripping tables and code).
- [ ] Forbidden-phrase grep over the page returns nothing.
- [ ] Nothing from the drift rows' "claim" column appears on the page.
- [ ] Sections appear in the order given under Page structure and every table has the named columns.
