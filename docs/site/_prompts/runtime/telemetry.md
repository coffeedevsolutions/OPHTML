# Page: runtime/telemetry (Telemetry)

Page type: `guide`. Section order: `46`. Wave: `2`.

## Purpose and audience

What `ps2ui_stats` counts, when it resets, and how the sample turns it into one line per second.

## Read first

1. `docs/site/ARCHITECTURE.md`, all of it. The rules below are copied from it and are binding.
2. Parent facts files, before opening any source: `_facts/runtime/api-reference.md`, `_facts/runtime/frame-loop.md`. Reuse their fact ids; do not restate a parent fact differently. If one is wrong, write a `## disputes` section and stop.
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

- runtime/ps2ui.h ~310-331 - the struct
- runtime/ps2ui.c - increment sites (cmds ~1071, prims, skipped_hidden ~1118, slot_glyphs, slots_hidden ~1320, scissor_overflow ~1080, tex_unfilled ~1153, vram_lost ~989)
- runtime/sample/main.c ~2643-2649, ~2759-2791 - timing and aggregation; Makefile TELEMETRY
- runtime/tests/test_runtime.c 'render telemetry (ps2ui_stats)'

## Claims to verify, and how

Each item is `claim -> how to prove it`. Run every command. Paste real output into the page where the structure calls for it and record the result in the facts file.

1. Fields and meanings -> cite the struct comments; run the runtime section
2. Reset at the top of every render; a composited frame ends with the last render's numbers -> cite
3. The sample's line format and aggregation (peaks, sum, OR) -> quote the printf from main.c
4. `make -C runtime/sample TELEMETRY=1 EE_BIN=telemetry.elf` exists -> grep the Makefile; `make -C runtime syntax-check` covers the variant

## Screenshots

None. Do not add decorative images.

## Page structure

Skeleton for type `guide`: What it is · Minimal example · Reference table · Behaviour · Limits and errors · Related pages.

Guide skeleton. Minimal example: reading two fields after render. Reference table: field · counts · note. Behaviour: reset, the sample readout (table: token · meaning · aggregation). Limits: counters only.

Frontmatter:

```yaml
---
id: runtime/telemetry
title: Telemetry
description: <one sentence>
section: runtime
order: 46
version: 0.6.0
sources: [<every repository path opened>]
---
```

## Cross-links

Write links as `[text](page:<id>#<anchor>)`. Every id below must appear on the page at the place named.

- runtime/api-reference - ps2ui_stats
- runtime/frame-loop - per render
- runtime/integrating - the sample build
- runtime/moving-and-hiding - hidden counters
- authoring/vram-budget - vram_lost

## Facts to emit

Write `_facts/<page-id>.md` before writing the page:

```markdown
# facts: <page-id>

| id | fact | source | verified by | status |
|---|---|---|---|---|
```

Status is `verified` (a command or test in this session proved it), `code-only` (read in source; say why nothing executable exists), or `contradicts-readme` (verified, and README.md says otherwise; cite the README line). If a parent fact is wrong, append `## disputes` with the id and evidence, and stop.

Required ids (downstream pages read these by name):

- `stats.fields`
- `stats.readout-format`

## Out of scope

- bench methodology -> project/internals

## Done when

- [ ] Environment block ran clean.
- [ ] `_facts/runtime/telemetry.md` exists with every fact id listed under "Facts to emit", each with a status.
- [ ] Every command shown on the page was run in this session; every output block is pasted from that run.
- [ ] Every screenshot listed exists under `assets/runtime/telemetry/`, is registered in `assets/assets.json` with its command, and has alt text.
- [ ] Frontmatter present: `id: runtime/telemetry`, `title`, `description`, `section`, `order: 46`, `version: 0.6.0`, `sources` (every path opened).
- [ ] Every `page:` link names an id from the page index in ARCHITECTURE.md.
- [ ] Word count of prose is 300 to 1500 (`pandoc -t plain` or a `wc -w` after stripping tables and code).
- [ ] Forbidden-phrase grep over the page returns nothing.
- [ ] Nothing from the drift rows' "claim" column appears on the page.
- [ ] Sections appear in the order given under Page structure and every table has the named columns.
