# Page: runtime/api-reference (C API reference)

Page type: `api`. Section order: `42`. Wave: `0`.

## Purpose and audience

Every public function in `ps2ui.h`, grouped, with signature, return convention, scope (screen or blob) and the one note a caller needs; the public structs; the ordering rules.

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
| D2 | README.md "Moving things at runtime"; runtime/ps2ui.h comment near `ps2ui_offset_set` | `ps2ui_focus_rect` | Not declared. Geometry is read from `ctx->focus_nodes[ctx->focus]`. |
| D3 | README.md (absent) | the runtime API is what README shows | `ps2ui_theme_set`, `ps2ui_clut_set`, `ps2ui_slot_get`, `ps2ui_visible_get`, `ps2ui_list_select`, `ps2ui_list_selected_row`, `ps2ui_screen_name`, `ps2ui_arena_size`, `ps2ui_offset_get`, `ps2ui_crc32`, `ps2ui_clut_csm1` exist in `runtime/ps2ui.h` and are documented. |
| D11 | runtime/ps2ui.c comments near the upload loop and `list_row_name` | `PS2UI_MAX_TEXTURES`, `PS2UI_MAX_LIST_ROWS` | Neither exists. The only runtime cap is `PS2UI_MAX_SCISSOR_DEPTH` (8). Table counts are bounded by the format's uint16 fields. |
| D12 | README.md Quick start C comment | `PS2UI_VERSION` keeps baker and runtime from drifting | It is the frozen format version, 7. Baker and runtime match because `ps2ui vendor-runtime` ships both files from one package. |

## Sources of truth

Line numbers are hints from the exploration that produced this brief; re-locate by symbol name. Authority order: code, tests, docs/*.md, README.md.

- runtime/ps2ui.h - the whole file; every prototype and its comment
- runtime/ps2ui.c - implementations, for scope rules (slot lookup global ~1398; focus/visible per screen ~1557, ~1593; visible_reset global ~1619)
- runtime/tests/test_runtime.c - the section list
- runtime/stub/gskit_stub.h - for compiling the check file

## Claims to verify, and how

Each item is `claim -> how to prove it`. Run every command. Paste real output into the page where the structure calls for it and record the result in the facts file.

1. The function list is exactly the prototypes in ps2ui.h -> `grep -E '^[a-z].*ps2ui_[a-z_0-9]+\(' runtime/ps2ui.h` (adjust for the header's style) and diff against the page's tables; count must match
2. Return conventions: PS2UI_OK/negative codes; upload returns 0/-1; screen_set/focus_set/slot_set/visible_set/move/list_move/list_select return 1/0 -> read each prototype
3. Scope: slot_set/slot_get blob-wide; focus_set, visible_set, visible_get screen-scoped; visible_reset blob-wide -> cite ps2ui.c lines
4. Ordering: clut_set after upload; tex_set before or after upload; set_count after list_init; apply_visibility after set_count and after move -> cite ps2ui.h
5. Every function compiles as documented -> write a scratch C file calling each with plausible arguments, compile with `cc -std=c99 -Wall -Wextra -Werror -Istub -Ivendor/gsKit -Ivendor/host-shim -I. -c` from runtime/; paste the command
6. ctx fields that may be read and the ones that must be written through a function -> cite the struct comments
7. ps2ui_list fields are public -> cite the struct

## Screenshots

None. Do not add decorative images.

## Page structure

Skeleton for type `api`: Function tables by group · Structs · Constants · Ordering rules.

API skeleton. Groups: Lifecycle (arena_size, load, upload) · Rendering (render) · Screens (screen_set, screen_name) · Focus (move, focus_set, focus_name) · Slots (slot_set, slot_get) · Textures and palettes (tex_set, clut_set, clut_csm1) · Visibility (visible_set, visible_get, visible_reset) · Offset (offset_set, offset_get) · Lists (seven) · Queries (pixel_aspect_x1000, crc32). Columns: signature · returns · scope · notes. Structs: ps2ui_ctx readable fields, ps2ui_list, ps2ui_stats, ps2ui_dir. Ordering rules table.

Frontmatter:

```yaml
---
id: runtime/api-reference
title: C API reference
description: <one sentence>
section: runtime
order: 42
version: 0.6.0
sources: [<every repository path opened>]
---
```

## Cross-links

Write links as `[text](page:<id>#<anchor>)`. Every id below must appear on the page at the place named.

- runtime/errors-and-constants - codes
- runtime/frame-loop - order
- authoring/lists - list functions
- runtime/streaming-art - tex_set, clut_set
- runtime/moving-and-hiding - visibility, offset
- authoring/theming - theme_set
- runtime/telemetry - stats

## Facts to emit

Write `_facts/<page-id>.md` before writing the page:

```markdown
# facts: <page-id>

| id | fact | source | verified by | status |
|---|---|---|---|---|
```

Status is `verified` (a command or test in this session proved it), `code-only` (read in source; say why nothing executable exists), or `contradicts-readme` (verified, and README.md says otherwise; cite the README line). If a parent fact is wrong, append `## disputes` with the id and evidence, and stop.

Required ids (downstream pages read these by name):

- `api.functions` - one row per function
- `api.scope.rules`
- `api.return-conventions`
- `api.ordering`
- `api.structs` - readable fields

## Out of scope

- error triggers -> runtime/errors-and-constants
- the frame order -> runtime/frame-loop

## Done when

- [ ] Environment block ran clean.
- [ ] `_facts/runtime/api-reference.md` exists with every fact id listed under "Facts to emit", each with a status.
- [ ] Every command shown on the page was run in this session; every output block is pasted from that run.
- [ ] Every screenshot listed exists under `assets/runtime/api-reference/`, is registered in `assets/assets.json` with its command, and has alt text.
- [ ] Frontmatter present: `id: runtime/api-reference`, `title`, `description`, `section`, `order: 42`, `version: 0.6.0`, `sources` (every path opened).
- [ ] Every `page:` link names an id from the page index in ARCHITECTURE.md.
- [ ] Word count of prose is 300 to 1500 (`pandoc -t plain` or a `wc -w` after stripping tables and code).
- [ ] Forbidden-phrase grep over the page returns nothing.
- [ ] Nothing from the drift rows' "claim" column appears on the page.
- [ ] Sections appear in the order given under Page structure and every table has the named columns.
