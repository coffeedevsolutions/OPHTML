# Page: project/changelog (Changelog)

Page type: `project`. Section order: `70`. Wave: `4`.

## Purpose and audience

The 0.6.0 release notes rewritten for readers (Added, Fixed, Format), a link to the full changelog, and a table of earlier releases.

## Read first

1. `docs/site/ARCHITECTURE.md`, all of it. The rules below are copied from it and are binding.
2. Parent facts files, before opening any source: `_facts/reference/compatibility.md`, `_facts/runtime/moving-and-hiding.md`, `_facts/authoring/vram-budget.md`, `_facts/runtime/integrating.md`, `_facts/cli/ps2ui-fontgen.md`. Reuse their fact ids; do not restate a parent fact differently. If one is wrong, write a `## disputes` section and stop.
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

None recorded. If a README.md claim disagrees with what you verify, add it to the facts file with status `contradicts-readme`.

## Sources of truth

Line numbers are hints from the exploration that produced this brief; re-locate by symbol name. Authority order: code, tests, docs/*.md, README.md.

- CHANGELOG.md - the Unreleased 0.6.0 section and the 0.5.0, 0.4.0, 0.3.0 headings and format paragraphs
- tools/check-versions.py - the version strings

## Claims to verify, and how

Each item is `claim -> how to prove it`. Run every command. Paste real output into the page where the structure calls for it and record the result in the facts file.

1. Every 0.6.0 bullet maps to a `### ` entry in CHANGELOG.md -> list the mapping in the facts file
2. Version and format strings agree with check-versions -> paste its ok lines for rules 2-7
3. Earlier releases table: version · date · format · headline -> read the headings

## Screenshots

None. Do not add decorative images.

## Page structure

Skeleton for type `project`: free-form, short.

Project skeleton: '0.6.0' with Added / Fixed / Format subsections, each bullet one or two sentences with a page link; then 'Earlier releases' table; then a repo link to CHANGELOG.md.

Frontmatter:

```yaml
---
id: project/changelog
title: Changelog
description: <one sentence>
section: project
order: 70
version: 0.6.0
sources: [<every repository path opened>]
---
```

## Cross-links

Write links as `[text](page:<id>#<anchor>)`. Every id below must appear on the page at the place named.

- runtime/moving-and-hiding - offset
- authoring/vram-budget - check budget and negative budget
- runtime/integrating - vendor-runtime message
- cli/ps2ui-fontgen - Raqm remedy
- reference/compatibility - format

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

- release procedure -> project/internals

## Done when

- [ ] Environment block ran clean.
- [ ] `_facts/project/changelog.md` exists with every fact id listed under "Facts to emit", each with a status.
- [ ] Every command shown on the page was run in this session; every output block is pasted from that run.
- [ ] Every screenshot listed exists under `assets/project/changelog/`, is registered in `assets/assets.json` with its command, and has alt text.
- [ ] Frontmatter present: `id: project/changelog`, `title`, `description`, `section`, `order: 70`, `version: 0.6.0`, `sources` (every path opened).
- [ ] Every `page:` link names an id from the page index in ARCHITECTURE.md.
- [ ] Word count of prose is 300 to 1500 (`pandoc -t plain` or a `wc -w` after stripping tables and code).
- [ ] Forbidden-phrase grep over the page returns nothing.
- [ ] Nothing from the drift rows' "claim" column appears on the page.
- [ ] Sections appear in the order given under Page structure and every table has the named columns.
