# Page: authoring/dynamic-text (Dynamic text)

Page type: `guide`. Section order: `15`. Wave: `1`.

## Purpose and audience

`data-slot` and `data-slot-capacity`: what is fixed at compile time (geometry, font, colours, ellipsis), what the app sets at runtime, the rules the compiler enforces, and the two facts the README does not say: capacity defaults to 63 and slot names are global across the blob.

## Read first

1. `docs/site/ARCHITECTURE.md`, all of it. The rules below are copied from it and are binding.
2. Parent facts files, before opening any source: `_facts/authoring/html.md`, `_facts/runtime/api-reference.md`, `_facts/reference/ir-format.md`. Reuse their fact ids; do not restate a parent fact differently. If one is wrong, write a `## disputes` section and stop.
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
| D7 | README.md "Supported CSS" | the property list | Missing: `opacity`, `min-*`/`max-*`, `align-self`, `flex` shorthand, `row-gap`, `column-gap`, `:root` custom properties, `var()`, `@theme`, `data-nocontrast`, capacity default 63, the `name` attribute, `--min-font-size`. Overstated: `border-radius` takes one px value; named colours are eight; keyword-valued properties are unvalidated; the `:focus` geometry guard does not cover `letter-spacing`, `font-weight`, `text-align`, `text-overflow`; no `white-space: pre`; `&nbsp;` collapses to a space. |

## Sources of truth

Line numbers are hints from the exploration that produced this brief; re-locate by symbol name. Authority order: code, tests, docs/*.md, README.md.

- packages/layout/src/box.js ~194-214 - slot rules and the default capacity
- packages/layout/src/paint.js ~195-201, ~223-237, ~330-335 - single-line rule, slot descriptor, duplicate names
- packages/baker/ps2ui_bake/quads.py ~602-611 (global name collision), ~666-676 (capacity not clamped), ~705-711 (letter-spacing i16)
- runtime/ps2ui.h ~655-663; runtime/ps2ui.c ~1398-1465 - slot_set, slot_get, utf8 trim, global lookup
- packages/baker/tests/test_baker.py TestSlotCapacity, TestDynamicText, TestSlotSpacing; runtime/tests/test_runtime.c section "dynamic text (F2)"

## Claims to verify, and how

Each item is `claim -> how to prove it`. Run every command. Paste real output into the page where the structure calls for it and record the result in the facts file.

1. Capacity defaults to 63 and is a uint16 in the format -> compile without the attribute and print the IR capacity; cite `test_a_capacity_the_format_cannot_hold_is_refused`
2. Exactly one text node, no child elements; the placeholder must fit on one line -> trigger both errors
3. Slot names are unique across the whole blob; the baker refuses a collision across screens -> bake two screens sharing a slot name and paste the error
4. `ps2ui_slot_set` copies, truncates at capacity without splitting UTF-8, NULL restores the placeholder, "" blanks -> cite the runtime test section; cite ps2ui.c
5. Lookup is over the whole blob, not the current screen -> cite ps2ui.c `slot_index_by_name` and `sample/main.c` comment on `telem`
6. Font, colours, alignment and ellipsis are baked; the runtime composes glyph quads from the atlas with the same pen -> cite TestDynamicText and the preview being pixel-identical
7. The previewer and serve page show slot text -> check `preview.render` signature for a slots argument; if present render with one; else use the serve page

## Screenshots

Each line is `path <- command // alt text`. Register every file in `assets/assets.json` with the exact command (`OUT` for the output path) and `checked: true` unless the line says otherwise. Previewer renders only; Playwright only where the line says so.

- assets/authoring/dynamic-text/slots.png <- memcard library rendered with slot text set (preview.render with slots if supported, else Playwright of serve after typing into a slot box; mark checked accordingly) // the memcard library with runtime titles filled in

## Page structure

Skeleton for type `guide`: What it is · Minimal example · Reference table · Behaviour · Limits and errors · Related pages.

Guide skeleton. Minimal example: the tutorial's `<span data-slot="count" data-slot-capacity="16">`. Reference table: attribute · effect; second table: runtime calls (function · effect) limited to slot_set and slot_get. Behaviour: what is fixed, truncation, names. Limits and errors.

Frontmatter:

```yaml
---
id: authoring/dynamic-text
title: Dynamic text
description: <one sentence>
section: authoring
order: 15
version: 0.6.0
sources: [<every repository path opened>]
---
```

## Cross-links

Write links as `[text](page:<id>#<anchor>)`. Every id below must appear on the page at the place named.

- runtime/api-reference - runtime calls table
- authoring/lists - refilling rows
- authoring/text-and-fonts - the pen
- cli/previewer - seeing slot text

## Facts to emit

Write `_facts/<page-id>.md` before writing the page:

```markdown
# facts: <page-id>

| id | fact | source | verified by | status |
|---|---|---|---|---|
```

Status is `verified` (a command or test in this session proved it), `code-only` (read in source; say why nothing executable exists), or `contradicts-readme` (verified, and README.md says otherwise; cite the README line). If a parent fact is wrong, append `## disputes` with the id and evidence, and stop.

Required ids (downstream pages read these by name):

- `slot.capacity.default` - 63
- `slot.rules` - one text node, single line, unique names blob-wide
- `slot.lookup.global` - whole-blob lookup
- `slot.runtime.semantics` - copy, truncate, NULL, empty

## Out of scope

- the list window -> authoring/lists
- the slot record layout -> reference/uib-format

## Done when

- [ ] Environment block ran clean.
- [ ] `_facts/authoring/dynamic-text.md` exists with every fact id listed under "Facts to emit", each with a status.
- [ ] Every command shown on the page was run in this session; every output block is pasted from that run.
- [ ] Every screenshot listed exists under `assets/authoring/dynamic-text/`, is registered in `assets/assets.json` with its command, and has alt text.
- [ ] Frontmatter present: `id: authoring/dynamic-text`, `title`, `description`, `section`, `order: 15`, `version: 0.6.0`, `sources` (every path opened).
- [ ] Every `page:` link names an id from the page index in ARCHITECTURE.md.
- [ ] Word count of prose is 300 to 1500 (`pandoc -t plain` or a `wc -w` after stripping tables and code).
- [ ] Forbidden-phrase grep over the page returns nothing.
- [ ] Nothing from the drift rows' "claim" column appears on the page.
- [ ] Sections appear in the order given under Page structure and every table has the named columns.
