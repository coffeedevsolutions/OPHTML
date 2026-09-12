# Page: reference/uib-format (.uib)

Page type: `format`. Section order: `51`. Wave: `0`.

## Purpose and audience

The blob the console loads: header, every record type, offsets, alignment, the CRC hole, feature bits, the tint table, the v7 pledge and what enforces it.

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
| D12 | README.md Quick start C comment | `PS2UI_VERSION` keeps baker and runtime from drifting | It is the frozen format version, 7. Baker and runtime match because `ps2ui vendor-runtime` ships both files from one package. |

## Sources of truth

Line numbers are hints from the exploration that produced this brief; re-locate by symbol name. Authority order: code, tests, docs/*.md, README.md.

- docs/format-uib.md - the whole file; restate in tables
- runtime/ps2ui.h ~36-260 - the structs
- packages/baker/ps2ui_bake/uib.py - writer and reader
- tools/check-format-frozen.py - what is frozen
- runtime/tests/test_runtime.c 'struct layout matches the on-disk format'

## Claims to verify, and how

Each item is `claim -> how to prove it`. Run every command. Paste real output into the page where the structure calls for it and record the result in the facts file.

1. Header is 84 bytes with the listed fields -> parse memcard's header in Python with struct and print each field beside the table
2. Record sizes: tex 20, clut 8, cmd 32, focus 24, font 24, slot 28, screen 24, tint 4 -> cite the test section and check-format-frozen
3. Blob section and every baked texture 16-aligned; CRC covers the file with the 4 bytes at offset 48 as zero -> cite ps2ui.c and format-uib.md
4. Feature bits and what each gates -> cite ps2ui.h
5. The pledge: v7 is the last incompatible layout; additions go in feature bits; frozen by check-format-frozen -> run `python3 tools/check-format-frozen.py` and paste
6. Version history v1..v7 one line each -> from format-uib.md Versioning

## Screenshots

None. Do not add decorative images.

## Page structure

Skeleton for type `format`: Layout · Records · Invariants · Versioning.

Format skeleton. Layout: the offset map. Records: one table per record type (offset · size · type · field · meaning). Invariants: alignment, CRC, counts. Versioning: the pledge and the history table.

Frontmatter:

```yaml
---
id: reference/uib-format
title: .uib
description: <one sentence>
section: reference
order: 51
version: 0.6.0
sources: [<every repository path opened>]
---
```

## Cross-links

Write links as `[text](page:<id>#<anchor>)`. Every id below must appear on the page at the place named.

- runtime/errors-and-constants - what load rejects
- cli/ps2ui-check - offline validation
- authoring/theming - tint table
- reference/compatibility - the pledge in practice
- runtime/api-reference - the structs

## Facts to emit

Write `_facts/<page-id>.md` before writing the page:

```markdown
# facts: <page-id>

| id | fact | source | verified by | status |
|---|---|---|---|---|
```

Status is `verified` (a command or test in this session proved it), `code-only` (read in source; say why nothing executable exists), or `contradicts-readme` (verified, and README.md says otherwise; cite the README line). If a parent fact is wrong, append `## disputes` with the id and evidence, and stop.

Required ids (downstream pages read these by name):

- `uib.header`
- `uib.records`
- `uib.invariants`
- `uib.pledge`
- `uib.history`

## Out of scope

- error codes -> runtime/errors-and-constants

## Done when

- [ ] Environment block ran clean.
- [ ] `_facts/reference/uib-format.md` exists with every fact id listed under "Facts to emit", each with a status.
- [ ] Every command shown on the page was run in this session; every output block is pasted from that run.
- [ ] Every screenshot listed exists under `assets/reference/uib-format/`, is registered in `assets/assets.json` with its command, and has alt text.
- [ ] Frontmatter present: `id: reference/uib-format`, `title`, `description`, `section`, `order: 51`, `version: 0.6.0`, `sources` (every path opened).
- [ ] Every `page:` link names an id from the page index in ARCHITECTURE.md.
- [ ] Word count of prose is 300 to 1500 (`pandoc -t plain` or a `wc -w` after stripping tables and code).
- [ ] Forbidden-phrase grep over the page returns nothing.
- [ ] Nothing from the drift rows' "claim" column appears on the page.
- [ ] Sections appear in the order given under Page structure and every table has the named columns.
