# Page: reference/ir-format (ui.json)

Page type: `format`. Section order: `50`. Wave: `0`.

## Purpose and audience

The intermediate representation as the compiler emits it today, field by field, with invariants and the version check. Supersedes `docs/format-ir.md`, which is stale.

## Read first

1. `docs/site/ARCHITECTURE.md`, all of it. The rules below are copied from it and are binding.
2. No parent pages. This page is a wave-0 leaf; everything comes from code.
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
| D8 | docs/format-ir.md | `canvas` is `{w, h}`; no `themes`; no theme vectors | The emitted IR carries `canvas.displayAspect`, `canvas.par`, `canvas.display`, a top-level `themes` array, and `fillVar`/`fillThemes`/`borderColorVar`/`borderColorThemes`/`colorVar`/`colorThemes` on commands plus `colorBaseVar`/`colorFocusVar`/`colorBaseThemes`/`colorFocusThemes` on slots. |

## Sources of truth

Line numbers are hints from the exploration that produced this brief; re-locate by symbol name. Authority order: code, tests, docs/*.md, README.md.

- packages/layout/src/index.js ~238-263 - the emitted top level
- packages/layout/src/paint.js ~119-154, ~223-237 - command and slot fields
- packages/baker/ps2ui_bake/quads.py ~561-575 - the ops the baker accepts
- packages/baker/ps2ui_bake/cli.py ~168-171 - the version check
- docs/format-ir.md - for the invariants list and the parts still true

## Claims to verify, and how

Each item is `claim -> how to prove it`. Run every command. Paste real output into the page where the structure calls for it and record the result in the facts file.

1. Top-level keys and shapes -> compile memcard and print every key path with a Node one-liner; every path appears in the tables
2. canvas carries w, h, displayAspect, par, display -> print
3. themes is an index-ordered array with root first -> print
4. Command ops and their fields including the theme vectors -> print one of each op
5. Slots carry the four theme fields -> print
6. IR version 1 is checked by the baker -> edit a copy to 2 and bake; paste
7. Invariants -> cite format-ir.md and the tests that hold them

## Screenshots

None. Do not add decorative images.

## Page structure

Skeleton for type `format`: Layout · Records · Invariants · Versioning.

Format skeleton. Layout: an abridged real IR. Records: one table per object (field · type · meaning) for canvas, fonts, themes, rect, text, image, scissor_push/pop, focus node, slot, warnings. Invariants list. Versioning.

Frontmatter:

```yaml
---
id: reference/ir-format
title: ui.json
description: <one sentence>
section: reference
order: 50
version: 0.6.0
sources: [<every repository path opened>]
---
```

## Cross-links

Write links as `[text](page:<id>#<anchor>)`. Every id below must appear on the page at the place named.

- cli/ps2ui-layout - producer
- cli/ps2ui-bake - consumer
- authoring/theming - theme vectors
- authoring/focus-and-navigation - focus nodes
- reference/uib-format - what it becomes

## Facts to emit

Write `_facts/<page-id>.md` before writing the page:

```markdown
# facts: <page-id>

| id | fact | source | verified by | status |
|---|---|---|---|---|
```

Status is `verified` (a command or test in this session proved it), `code-only` (read in source; say why nothing executable exists), or `contradicts-readme` (verified, and README.md says otherwise; cite the README line). If a parent fact is wrong, append `## disputes` with the id and evidence, and stop.

Required ids (downstream pages read these by name):

- `ir.schema` - the field tables
- `ir.version`

## Out of scope

- the binary format -> reference/uib-format

## Done when

- [ ] Environment block ran clean.
- [ ] `_facts/reference/ir-format.md` exists with every fact id listed under "Facts to emit", each with a status.
- [ ] Every command shown on the page was run in this session; every output block is pasted from that run.
- [ ] Every screenshot listed exists under `assets/reference/ir-format/`, is registered in `assets/assets.json` with its command, and has alt text.
- [ ] Frontmatter present: `id: reference/ir-format`, `title`, `description`, `section`, `order: 50`, `version: 0.6.0`, `sources` (every path opened).
- [ ] Every `page:` link names an id from the page index in ARCHITECTURE.md.
- [ ] Word count of prose is 300 to 1500 (`pandoc -t plain` or a `wc -w` after stripping tables and code).
- [ ] Forbidden-phrase grep over the page returns nothing.
- [ ] Nothing from the drift rows' "claim" column appears on the page.
- [ ] Sections appear in the order given under Page structure and every table has the named columns.

Additional deliverable for this brief:

Also append to the facts file a `## follow-up` note listing the four stale statements in `docs/format-ir.md` (from drift row D8) so a separate change can fix the repository document.
