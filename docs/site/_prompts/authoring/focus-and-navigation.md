# Page: authoring/focus-and-navigation (Focus and navigation)

Page type: `guide`. Section order: `17`. Wave: `1`.

## Purpose and audience

How an element becomes navigable, how the compiler solves D-pad edges, what `--focus-wrap` adds, how names are chosen, what the runtime does with the graph, and why nesting is refused.

## Read first

1. `docs/site/ARCHITECTURE.md`, all of it. The rules below are copied from it and are binding.
2. Parent facts files, before opening any source: `_facts/authoring/html.md`, `_facts/runtime/api-reference.md`, `_facts/cli/ps2ui-layout.md`. Reuse their fact ids; do not restate a parent fact differently. If one is wrong, write a `## disputes` section and stop.
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
| D4 | README.md "Focus and navigation", "Widescreen and video modes" | `--focus-wrap`, `--mode`, `--display-aspect` read as bake flags | They are `ps2ui-layout` flags. `--mode` is also on `ps2ui build`. `ps2ui-bake` has none of them. |

## Sources of truth

Line numbers are hints from the exploration that produced this brief; re-locate by symbol name. Authority order: code, tests, docs/*.md, README.md.

- packages/layout/src/focus.js - the solver (~28-63), wrap (~73-96), naming (~114), autofocus (~126-129), reachability (~139-158)
- packages/layout/src/box.js ~286-301 - nesting error, :focus warning
- packages/baker/ps2ui_bake/quads.py ~544-557 - per-screen remap
- runtime/ps2ui.h ~641-652, ~828-831; runtime/ps2ui.c ~1506-1640 - move, focus_set, focus_name, hidden skip
- packages/layout/test/layout.test.js focus cases; runtime/tests/test_runtime.c "focus graph walk" and "focus API (F10)"

## Claims to verify, and how

Each item is `claim -> how to prove it`. Run every command. Paste real output into the page where the structure calls for it and record the result in the facts file.

1. `focusable` makes a node; `autofocus` picks the initial, first in document order wins; with none, the first focusable -> compile a two-autofocus screen and print `ir.focus.initial`
2. Name is id, else name, else boxN -> compile a focusable with only `name=` and print the node name
3. The solver: progress on the axis, in-beam candidates win, then along + 2*perp, then document order -> read focus.js; compile a 2x3 grid and print each node's four edges
4. `--focus-wrap` fills only null edges with the farthest in-beam node on the opposite side -> recompile with the flag and diff the edges
5. Unreachable nodes warn; --strict fails -> compile an island and paste the warning
6. Nesting is an error -> trigger and paste
7. Focus names are unique per screen; the baker remaps per screen; `focus_set` is screen-scoped -> cite quads.py and ps2ui.c
8. `ps2ui_move` returns 1 on change, skips hidden nodes, stops at an edge with no neighbour -> cite the runtime sections

## Screenshots

Each line is `path <- command // alt text`. Register every file in `assets/assets.json` with the exact command (`OUT` for the output path) and `checked: true` unless the line says otherwise. Previewer renders only; Playwright only where the line says so.

- assets/authoring/focus-and-navigation/graph.png <- Playwright: `ps2ui serve examples/memcard`, toggle Focus graph on, capture; `checked: false` // the memcard library with the solved D-pad graph drawn over it
- assets/authoring/focus-and-navigation/states.png <- `preview.montage` of memcard // every focus state of the memcard library

## Page structure

Skeleton for type `guide`: What it is · Minimal example · Reference table · Behaviour · Limits and errors · Related pages.

Guide skeleton. Minimal example: a row of three tiles with autofocus. Reference table: attribute/flag · effect (focusable, autofocus, name, --focus-wrap). Table 2: runtime calls (move, focus_set, focus_name). Behaviour: the solver in five lines, wrap, names, screens, hidden nodes. Limits and errors.

Frontmatter:

```yaml
---
id: authoring/focus-and-navigation
title: Focus and navigation
description: <one sentence>
section: authoring
order: 17
version: 0.6.0
sources: [<every repository path opened>]
---
```

## Cross-links

Write links as `[text](page:<id>#<anchor>)`. Every id below must appear on the page at the place named.

- authoring/html - attributes
- cli/ps2ui-layout - --focus-wrap
- authoring/project-file - focusWrap
- runtime/api-reference - calls
- runtime/moving-and-hiding - hidden nodes
- cli/previewer - the focus graph overlay

## Facts to emit

Write `_facts/<page-id>.md` before writing the page:

```markdown
# facts: <page-id>

| id | fact | source | verified by | status |
|---|---|---|---|---|
```

Status is `verified` (a command or test in this session proved it), `code-only` (read in source; say why nothing executable exists), or `contradicts-readme` (verified, and README.md says otherwise; cite the README line). If a parent fact is wrong, append `## disputes` with the id and evidence, and stop.

Required ids (downstream pages read these by name):

- `focus.naming` - id, name, boxN
- `focus.solver` - the four ranking rules
- `focus.wrap` - semantics
- `focus.scope` - per screen
- `focus.runtime` - move/focus_set/focus_name semantics

## Out of scope

- the activation convention (switch on focus_name) -> runtime/frame-loop

## Done when

- [ ] Environment block ran clean.
- [ ] `_facts/authoring/focus-and-navigation.md` exists with every fact id listed under "Facts to emit", each with a status.
- [ ] Every command shown on the page was run in this session; every output block is pasted from that run.
- [ ] Every screenshot listed exists under `assets/authoring/focus-and-navigation/`, is registered in `assets/assets.json` with its command, and has alt text.
- [ ] Frontmatter present: `id: authoring/focus-and-navigation`, `title`, `description`, `section`, `order: 17`, `version: 0.6.0`, `sources` (every path opened).
- [ ] Every `page:` link names an id from the page index in ARCHITECTURE.md.
- [ ] Word count of prose is 300 to 1500 (`pandoc -t plain` or a `wc -w` after stripping tables and code).
- [ ] Forbidden-phrase grep over the page returns nothing.
- [ ] Nothing from the drift rows' "claim" column appears on the page.
- [ ] Sections appear in the order given under Page structure and every table has the named columns.
