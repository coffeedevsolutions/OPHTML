# Page: runtime/frame-loop (The frame loop)

Page type: `guide`. Section order: `41`. Wave: `1`.

## Purpose and audience

The lifecycle in order and the guarantees: arena sizing, load, one upload, the per-frame order with the app's clear, the blend assertion, never clears, scissor restored, stats per render, no unload, the arena's lifetime, and the checked error handling.

## Read first

1. `docs/site/ARCHITECTURE.md`, all of it. The rules below are copied from it and are binding.
2. Parent facts files, before opening any source: `_facts/runtime/api-reference.md`, `_facts/runtime/errors-and-constants.md`. Reuse their fact ids; do not restate a parent fact differently. If one is wrong, write a `## disputes` section and stop.
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
| D6 | README.md C snippet under Quick start | `ps2ui_load` and `ps2ui_upload` called without checking returns | Document the checked form from `runtime/sample/main.c` (load failure and upload failure are fatal there). |
| D12 | README.md Quick start C comment | `PS2UI_VERSION` keeps baker and runtime from drifting | It is the frozen format version, 7. Baker and runtime match because `ps2ui vendor-runtime` ships both files from one package. |
| D13 | README.md Quick start C snippet | `arena[1662]` | Blob-specific and target-specific. Quote the arena line from a bake in this session, with the command. The bake prints the EE figure; `ps2ui-check` prints the EE and 64-bit host figures. |
| D14 | README.md "Multiple screens" | a second `ps2ui_render` in one frame with nothing else said | `gsKit_TexManager_nextFrame` is called once after the flip, never between the two renders; `ctx->stats` holds only the last render's counters. |

## Sources of truth

Line numbers are hints from the exploration that produced this brief; re-locate by symbol name. Authority order: code, tests, docs/*.md, README.md.

- runtime/ps2ui.h ~430-500 (arena, load, upload), ~600-640 (render guarantees)
- runtime/ps2ui.c ~238-330 (arena_size, load), ~567-660 (upload), ~940-1060 (render, blend), ~1166 (scissor restore)
- runtime/sample/main.c ~1638-1660 (arena and checked load/upload), ~2630-2750 (the frame)
- runtime/tests/test_runtime.c sections loader, upload, the arena, the blend equation, PrimAlphaEnable, geometry stays on canvas

## Claims to verify, and how

Each item is `claim -> how to prove it`. Run every command. Paste real output into the page where the structure calls for it and record the result in the facts file.

1. Order: arena_size -> static aligned arena -> load -> upload once -> per frame clear (PrimAlphaEnable off/on around it), render, queue_exec, sync_flip, nextFrame -> paste the sample's lines with line numbers
2. arena_size returns 0 when the blob is not worth loading; load validates before touching the arena; ERR_ARENA when too small -> cite tests
3. The arena must outlive every render because the CLUT region is a DMA source -> cite ps2ui.h
4. upload returns -1 on VRAM refusal, is all-or-nothing, and must not be called twice -> cite ps2ui.h and ps2ui.c
5. render asserts the blend equation and PrimAlphaEnable every call; never clears; leaves the scissor at full canvas; stats reset per render -> cite the test sections; run `make -C runtime test` and paste those lines
6. The app owns the clear and brackets it -> cite main.c comments
7. There is no unload -> cite ps2ui.h
8. The checked form: red fill on load error, yellow on upload -> cite main.c

## Screenshots

None. Do not add decorative images.

## Page structure

Skeleton for type `guide`: What it is · Minimal example · Reference table · Behaviour · Limits and errors · Related pages.

Guide skeleton. Minimal example: the full loop from main.c, 20 lines, with checks. Reference table: step · call · must hold. Behaviour: guarantees as a table (guarantee · consequence). Limits and errors: the two return conventions and what each error means here.

Frontmatter:

```yaml
---
id: runtime/frame-loop
title: The frame loop
description: <one sentence>
section: runtime
order: 41
version: 0.6.0
sources: [<every repository path opened>]
---
```

## Cross-links

Write links as `[text](page:<id>#<anchor>)`. Every id below must appear on the page at the place named.

- runtime/api-reference - every call
- runtime/errors-and-constants - codes
- authoring/screens-and-overlays - two renders
- authoring/vram-budget - the refusal
- runtime/telemetry - stats
- runtime/first-boot - the blend fault history

## Facts to emit

Write `_facts/<page-id>.md` before writing the page:

```markdown
# facts: <page-id>

| id | fact | source | verified by | status |
|---|---|---|---|---|
```

Status is `verified` (a command or test in this session proved it), `code-only` (read in source; say why nothing executable exists), or `contradicts-readme` (verified, and README.md says otherwise; cite the README line). If a parent fact is wrong, append `## disputes` with the id and evidence, and stop.

Required ids (downstream pages read these by name):

- `loop.order` - the ordered steps
- `loop.guarantees` - the table
- `arena.contract` - align, size, lifetime
- `upload.contract` - once, -1, all-or-nothing

## Out of scope

- deploying -> runtime/deploying

## Done when

- [ ] Environment block ran clean.
- [ ] `_facts/runtime/frame-loop.md` exists with every fact id listed under "Facts to emit", each with a status.
- [ ] Every command shown on the page was run in this session; every output block is pasted from that run.
- [ ] Every screenshot listed exists under `assets/runtime/frame-loop/`, is registered in `assets/assets.json` with its command, and has alt text.
- [ ] Frontmatter present: `id: runtime/frame-loop`, `title`, `description`, `section`, `order: 41`, `version: 0.6.0`, `sources` (every path opened).
- [ ] Every `page:` link names an id from the page index in ARCHITECTURE.md.
- [ ] Word count of prose is 300 to 1500 (`pandoc -t plain` or a `wc -w` after stripping tables and code).
- [ ] Forbidden-phrase grep over the page returns nothing.
- [ ] Nothing from the drift rows' "claim" column appears on the page.
- [ ] Sections appear in the order given under Page structure and every table has the named columns.
