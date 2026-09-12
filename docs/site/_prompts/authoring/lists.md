# Page: authoring/lists (Lists)

Page type: `guide`. Section order: `16`. Wave: `1`.

## Purpose and audience

`data-repeat` at compile time and the list window at runtime, as one worked example: six baked rows, N items, the D-pad moves the window and focus, rows past the end are hidden.

## Read first

1. `docs/site/ARCHITECTURE.md`, all of it. The rules below are copied from it and are binding.
2. Parent facts files, before opening any source: `_facts/authoring/html.md`, `_facts/authoring/dynamic-text.md`, `_facts/runtime/api-reference.md`, `_facts/runtime/moving-and-hiding.md`. Reuse their fact ids; do not restate a parent fact differently. If one is wrong, write a `## disputes` section and stop.
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
| D3 | README.md (absent) | the runtime API is what README shows | `ps2ui_theme_set`, `ps2ui_clut_set`, `ps2ui_slot_get`, `ps2ui_visible_get`, `ps2ui_list_select`, `ps2ui_list_selected_row`, `ps2ui_screen_name`, `ps2ui_arena_size`, `ps2ui_offset_get`, `ps2ui_crc32`, `ps2ui_clut_csm1` exist in `runtime/ps2ui.h` and are documented. |

## Sources of truth

Line numbers are hints from the exploration that produced this brief; re-locate by symbol name. Authority order: code, tests, docs/*.md, README.md.

- packages/layout/src/repeat.js - count 1..256, literal, {i}/{n}, no nesting, not on root, no-index warning, consumed before cascade
- runtime/ps2ui.h ~760-822 - the list struct and the seven functions
- runtime/ps2ui.c ~1666-1770 - scroll-into-view (minimum, not centred), clamping, focus sync, prefix by pointer, silent prefix mismatch
- docs/tutorial-uc3.md step 8 - the refill loop
- packages/layout/test/layout.test.js data-repeat cases; runtime/tests/test_runtime.c "list window (F6)" and "lists and visibility against a real data-repeat blob"

## Claims to verify, and how

Each item is `claim -> how to prove it`. Run every command. Paste real output into the page where the structure calls for it and record the result in the facts file.

1. data-repeat rules and errors -> compile `data-repeat="0"`, `"300"`, `"2.5"`, nested, and on the root; paste each message
2. A repeated row compiles to the same commands as a typed-out one -> cite layout.test.js `copies lay out as if they had been typed out`
3. list_init binds prefix+index rows and stores the prefix pointer; set_count clamps and moves focus (NULL ctx moves indices only); move clamps at both ends, scrolls the minimum, returns 1 on change; select is absolute; item_at returns -1 past the end; selected_row -1 when empty; apply_visibility hides rows past the end -> cite ps2ui.h comments and the runtime test sections; run `make -C runtime test` and paste the section lines
4. A prefix that matches no baked focus name fails silently -> cite ps2ui.c `list_sync_focus`
5. The window never wraps -> cite ps2ui.h

## Screenshots

Each line is `path <- command // alt text`. Register every file in `assets/assets.json` with the exact command (`OUT` for the output path) and `checked: true` unless the line says otherwise. Previewer renders only; Playwright only where the line says so.

- assets/authoring/lists/rows.png <- the tutorial library screen (six rows) `--preview` // six baked rows before any runtime data
- assets/authoring/lists/rows-states.png <- `--montage` // focus on each row

## Page structure

Skeleton for type `guide`: What it is · Minimal example · Reference table · Behaviour · Limits and errors · Related pages.

Guide skeleton. Minimal example: the tutorial row markup plus the C refill loop. Reference table 1: data-repeat (attribute · rule). Table 2: list functions (signature · returns · notes). Behaviour: expansion, the window policy, focus sync, visibility. Limits and errors.

Frontmatter:

```yaml
---
id: authoring/lists
title: Lists
description: <one sentence>
section: authoring
order: 16
version: 0.6.0
sources: [<every repository path opened>]
---
```

## Cross-links

Write links as `[text](page:<id>#<anchor>)`. Every id below must appear on the page at the place named.

- authoring/dynamic-text - refill
- runtime/moving-and-hiding - apply_visibility
- runtime/api-reference - the functions
- authoring/focus-and-navigation - row names

## Facts to emit

Write `_facts/<page-id>.md` before writing the page:

```markdown
# facts: <page-id>

| id | fact | source | verified by | status |
|---|---|---|---|---|
```

Status is `verified` (a command or test in this session proved it), `code-only` (read in source; say why nothing executable exists), or `contradicts-readme` (verified, and README.md says otherwise; cite the README line). If a parent fact is wrong, append `## disputes` with the id and evidence, and stop.

Required ids (downstream pages read these by name):

- `repeat.rules` - count range, literal, substitution, nesting, root
- `list.api.semantics` - one row per function

## Out of scope

- visibility in general -> runtime/moving-and-hiding

## Done when

- [ ] Environment block ran clean.
- [ ] `_facts/authoring/lists.md` exists with every fact id listed under "Facts to emit", each with a status.
- [ ] Every command shown on the page was run in this session; every output block is pasted from that run.
- [ ] Every screenshot listed exists under `assets/authoring/lists/`, is registered in `assets/assets.json` with its command, and has alt text.
- [ ] Frontmatter present: `id: authoring/lists`, `title`, `description`, `section`, `order: 16`, `version: 0.6.0`, `sources` (every path opened).
- [ ] Every `page:` link names an id from the page index in ARCHITECTURE.md.
- [ ] Word count of prose is 300 to 1500 (`pandoc -t plain` or a `wc -w` after stripping tables and code).
- [ ] Forbidden-phrase grep over the page returns nothing.
- [ ] Nothing from the drift rows' "claim" column appears on the page.
- [ ] Sections appear in the order given under Page structure and every table has the named columns.
