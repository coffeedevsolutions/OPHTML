# Page: index (OPHTML)

Page type: `project`. Section order: `0`. Wave: `4`.

## Purpose and audience

The landing page. A reader who knows nothing about the project learns in one screen what it builds, what runs on the console, what they need installed, and where to go next. Every section of the library is one link away.

## Read first

1. `docs/site/ARCHITECTURE.md`, all of it. The rules below are copied from it and are binding.
2. Parent facts files, before opening any source: `_facts/getting-started/installation.md`, `_facts/getting-started/quickstart.md`, `_facts/getting-started/how-it-works.md`, `_facts/reference/compatibility.md`. Reuse their fact ids; do not restate a parent fact differently. If one is wrong, write a `## disputes` section and stop.
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
| D1 | README.md Tests section; CONTRIBUTING.md | `make -C runtime test test-compat`; `PS2UI_GSKIT_HAS_FUNCTION=0` | No such target or macro. Targets: `test`, `test-narrow`, `syntax-check`, `timing-check`, `clean`. gsKit has no per-texture TFX field (BACKLOG.md F28). |
| D13 | README.md Quick start C snippet | `arena[1662]` | Blob-specific and target-specific. Quote the arena line from a bake in this session, with the command. The bake prints the EE figure; `ps2ui-check` prints the EE and 64-bit host figures. |

## Sources of truth

Line numbers are hints from the exploration that produced this brief; re-locate by symbol name. Authority order: code, tests, docs/*.md, README.md.

- README.md lines 1-110 - scope and the pipeline line only; do not copy prose
- packages/layout/README.md and packages/baker/README.md - the naming rule: OPHTML is the product, ps2ui is the format and the tools
- docs/site/ARCHITECTURE.md page index - the section list to link

## Claims to verify, and how

Each item is `claim -> how to prove it`. Run every command. Paste real output into the page where the structure calls for it and record the result in the facts file.

1. The pipeline is html+css -> ui.json -> .uib -> C runtime -> read compat.versions and loop.order from the facts files; no new verification
2. Requirements table (Node 18+, Python 3.9+, Pillow 9+, a TTF, a C cross toolchain only for the console half) -> copy from install.requirements; do not re-derive
3. The two screenshots (opl-env library dark and light) -> re-render with the commands in assets.json for authoring/theming and reuse those files, do not duplicate

## Screenshots

Each line is `path <- command // alt text`. Register every file in `assets/assets.json` with the exact command (`OUT` for the output path) and `checked: true` unless the line says otherwise. Previewer renders only; Playwright only where the line says so.

- assets/index/pipeline.svg <- hand-drawn SVG, four boxes and three arrows, text only, both themes readable (dark text on transparent) // the build pipeline from HTML and CSS to the console
- reuse assets/authoring/theming/library-theme-0.png and library-theme-1.png

## Page structure

Skeleton for type `project`: free-form, short.

One paragraph (what it is, 3 sentences). Pipeline figure. Two screenshots side by side. 'Start here' list of three links (install, quick start, tutorial). Requirements table (need · version · used by). Section list: one line per section with its pages linked. No headings beyond those five blocks.

Frontmatter:

```yaml
---
id: index
title: OPHTML
description: <one sentence>
section: root
order: 0
version: 0.6.0
sources: [<every repository path opened>]
---
```

## Cross-links

Write links as `[text](page:<id>#<anchor>)`. Every id below must appear on the page at the place named.

- getting-started/installation - Start here
- getting-started/quickstart - Start here
- getting-started/tutorial-game-browser - Start here
- every section index page - Section list

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

- how the stages work -> getting-started/how-it-works
- install detail -> getting-started/installation

## Done when

- [ ] Environment block ran clean.
- [ ] `_facts/index.md` exists with every fact id listed under "Facts to emit", each with a status.
- [ ] Every command shown on the page was run in this session; every output block is pasted from that run.
- [ ] Every screenshot listed exists under `assets/index/`, is registered in `assets/assets.json` with its command, and has alt text.
- [ ] Frontmatter present: `id: index`, `title`, `description`, `section`, `order: 0`, `version: 0.6.0`, `sources` (every path opened).
- [ ] Every `page:` link names an id from the page index in ARCHITECTURE.md.
- [ ] Word count of prose is 300 to 1500 (`pandoc -t plain` or a `wc -w` after stripping tables and code).
- [ ] Forbidden-phrase grep over the page returns nothing.
- [ ] Nothing from the drift rows' "claim" column appears on the page.
- [ ] Sections appear in the order given under Page structure and every table has the named columns.
