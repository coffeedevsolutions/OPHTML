# Page: runtime/moving-and-hiding (Moving and hiding)

Page type: `guide`. Section order: `45`. Wave: `2`.

## Purpose and audience

The two runtime changes that are not paint: hiding a focus subtree, and the draw-time offset new in 0.6.0. What each does, what it does not, and how the previewer shows them.

## Read first

1. `docs/site/ARCHITECTURE.md`, all of it. The rules below are copied from it and are binding.
2. Parent facts files, before opening any source: `_facts/runtime/api-reference.md`, `_facts/authoring/focus-and-navigation.md`, `_facts/authoring/lists.md`, `_facts/cli/previewer.md`. Reuse their fact ids; do not restate a parent fact differently. If one is wrong, write a `## disputes` section and stop.
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
| D2 | README.md "Moving things at runtime"; runtime/ps2ui.h comment near `ps2ui_offset_set` | `ps2ui_focus_rect` | Not declared. Geometry is read from `ctx->focus_nodes[ctx->focus]`. |
| D3 | README.md (absent) | the runtime API is what README shows | `ps2ui_theme_set`, `ps2ui_clut_set`, `ps2ui_slot_get`, `ps2ui_visible_get`, `ps2ui_list_select`, `ps2ui_list_selected_row`, `ps2ui_screen_name`, `ps2ui_arena_size`, `ps2ui_offset_get`, `ps2ui_crc32`, `ps2ui_clut_csm1` exist in `runtime/ps2ui.h` and are documented. |

## Sources of truth

Line numbers are hints from the exploration that produced this brief; re-locate by symbol name. Authority order: code, tests, docs/*.md, README.md.

- runtime/ps2ui.h ~680-760 - visible_* and offset_*
- runtime/ps2ui.c ~1574-1625
- packages/baker/ps2ui_bake/preview.py - render(..., offset=)
- CHANGELOG.md 0.6.0 - the F27 entry
- runtime/tests/test_runtime.c 'runtime visibility (F21)' and 'F27: a draw-time offset'; test_baker.py TestPreviewOffset, TestPreviewOffsetMovesText

## Claims to verify, and how

Each item is `claim -> how to prove it`. Run every command. Paste real output into the page where the structure calls for it and record the result in the facts file.

1. visible_set hides a focus node's subtree, keeps its space, skips it in move, focus_set still reaches it; visible_get is 1/0/-1; visible_reset is blob-wide while set/get are screen-scoped -> cite; run the runtime section
2. display: none is compile-time and closes the gap -> contrast in one sentence
3. offset_set translates every command and derived scissor, not the canvas rect; int16 else ERR_RANGE; queries stay in UI coordinates; no format change; composes with a (0,0) dialog render -> cite ps2ui.h; run the F27 section
4. preview.render takes offset and serve matches the console -> render at three offsets; cite TestPreviewOffset
5. The previewer does not show visibility -> cite serve.limits

## Screenshots

Each line is `path <- command // alt text`. Register every file in `assets/assets.json` with the exact command (`OUT` for the output path) and `checked: true` unless the line says otherwise. Previewer renders only; Playwright only where the line says so.

- assets/runtime/moving-and-hiding/offset-0.png <- memcard library offset (0,0) // no offset
- assets/runtime/moving-and-hiding/offset-up.png <- offset (0,-60) // slid up 60 px, clipped at the display edge
- assets/runtime/moving-and-hiding/offset-right.png <- offset (80,0) // slid right 80 px

## Page structure

Skeleton for type `guide`: What it is · Minimal example · Reference table · Behaviour · Limits and errors · Related pages.

Guide skeleton. Minimal example: three C lines each. Reference table: function · effect · scope. Behaviour: hiding, moving, the two together. Limits and errors.

Frontmatter:

```yaml
---
id: runtime/moving-and-hiding
title: Moving and hiding
description: <one sentence>
section: runtime
order: 45
version: 0.6.0
sources: [<every repository path opened>]
---
```

## Cross-links

Write links as `[text](page:<id>#<anchor>)`. Every id below must appear on the page at the place named.

- runtime/api-reference - signatures
- authoring/lists - apply_visibility
- authoring/screens-and-overlays - dialog over a scrolled page
- cli/previewer - what it shows
- runtime/errors-and-constants - RANGE

## Facts to emit

Write `_facts/<page-id>.md` before writing the page:

```markdown
# facts: <page-id>

| id | fact | source | verified by | status |
|---|---|---|---|---|
```

Status is `verified` (a command or test in this session proved it), `code-only` (read in source; say why nothing executable exists), or `contradicts-readme` (verified, and README.md says otherwise; cite the README line). If a parent fact is wrong, append `## disputes` with the id and evidence, and stop.

Required ids (downstream pages read these by name):

- `visible.semantics`
- `offset.contract`

## Out of scope

- list windowing -> authoring/lists

## Done when

- [ ] Environment block ran clean.
- [ ] `_facts/runtime/moving-and-hiding.md` exists with every fact id listed under "Facts to emit", each with a status.
- [ ] Every command shown on the page was run in this session; every output block is pasted from that run.
- [ ] Every screenshot listed exists under `assets/runtime/moving-and-hiding/`, is registered in `assets/assets.json` with its command, and has alt text.
- [ ] Frontmatter present: `id: runtime/moving-and-hiding`, `title`, `description`, `section`, `order: 45`, `version: 0.6.0`, `sources` (every path opened).
- [ ] Every `page:` link names an id from the page index in ARCHITECTURE.md.
- [ ] Word count of prose is 300 to 1500 (`pandoc -t plain` or a `wc -w` after stripping tables and code).
- [ ] Forbidden-phrase grep over the page returns nothing.
- [ ] Nothing from the drift rows' "claim" column appears on the page.
- [ ] Sections appear in the order given under Page structure and every table has the named columns.
