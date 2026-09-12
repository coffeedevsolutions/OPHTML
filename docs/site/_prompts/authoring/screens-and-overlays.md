# Page: authoring/screens-and-overlays (Screens and overlays)

Page type: `guide`. Section order: `19`. Wave: `1`.

## Purpose and audience

Multiple screens in one blob and the compositing technique that gives dialogs and overlays without a modal feature.

## Read first

1. `docs/site/ARCHITECTURE.md`, all of it. The rules below are copied from it and are binding.
2. Parent facts files, before opening any source: `_facts/runtime/frame-loop.md`, `_facts/runtime/api-reference.md`, `_facts/cli/ps2ui-bake.md`. Reuse their fact ids; do not restate a parent fact differently. If one is wrong, write a `## disputes` section and stop.
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
| D14 | README.md "Multiple screens" | a second `ps2ui_render` in one frame with nothing else said | `gsKit_TexManager_nextFrame` is called once after the flip, never between the two renders; `ctx->stats` holds only the last render's counters. |

## Sources of truth

Line numbers are hints from the exploration that produced this brief; re-locate by symbol name. Authority order: code, tests, docs/*.md, README.md.

- runtime/ps2ui.h ~600-633 - composition contract, nextFrame rule, stats per render, no overlay_push
- runtime/ps2ui.c ~1469-1490 - screen_set focus memory
- packages/baker/ps2ui_bake/quads.py ~535-538 - all screens share one canvas
- runtime/sample/main.c ~2726-2732 - the live two-render frame
- BACKLOG.md "Two gaps a real UI found" - the previewer cannot composite (renders over a colour)
- runtime/tests/test_runtime.c "multi-screen (F4)" and "composition: two screens in one frame"
- examples/opl-env/ui/confirm.html - a real overlay screen

## Claims to verify, and how

Each item is `claim -> how to prove it`. Run every command. Paste real output into the page where the structure calls for it and record the result in the facts file.

1. Each IR file is a screen named by its stem; textures and fonts are shared; canvases must match -> bake two IRs at different canvases and paste the error
2. `screen_set` saves and restores focus per screen; re-setting the current screen is a no-op -> cite the runtime section
3. `render` never clears; two renders composite; input follows the last `screen_set`; `nextFrame` once after the flip; stats per render -> cite ps2ui.h and the composition test section
4. The previewer renders over a colour and cannot show a composite -> cite BACKLOG
5. There is no overlay_push, by decision -> cite ps2ui.h

## Screenshots

Each line is `path <- command // alt text`. Register every file in `assets/assets.json` with the exact command (`OUT` for the output path) and `checked: true` unless the line says otherwise. Previewer renders only; Playwright only where the line says so.

- assets/authoring/screens-and-overlays/library.png <- opl-env `library` // the base screen
- assets/authoring/screens-and-overlays/confirm.png <- opl-env `confirm` rendered alone // the overlay screen: scrim and panel over a flat background
- assets/authoring/screens-and-overlays/in-game.png <- `python3 examples/channel6/preview_in_game.py` output // the channel6 browser composited over a synthetic scene; labelled synthetic

## Page structure

Skeleton for type `guide`: What it is · Minimal example · Reference table · Behaviour · Limits and errors · Related pages.

Guide skeleton. Minimal example: the two-render frame from main.c. Reference table: call · effect (screen_set, screen_name, render). Behaviour: naming, shared tables, focus memory, compositing rules as a five-row table (rule · why it matters). Limits and errors.

Frontmatter:

```yaml
---
id: authoring/screens-and-overlays
title: Screens and overlays
description: <one sentence>
section: authoring
order: 19
version: 0.6.0
sources: [<every repository path opened>]
---
```

## Cross-links

Write links as `[text](page:<id>#<anchor>)`. Every id below must appear on the page at the place named.

- runtime/frame-loop - the frame order
- runtime/api-reference - calls
- cli/previewer - cannot composite
- examples/opl-env - confirm screen
- examples/channel6 - overlay

## Facts to emit

Write `_facts/<page-id>.md` before writing the page:

```markdown
# facts: <page-id>

| id | fact | source | verified by | status |
|---|---|---|---|---|
```

Status is `verified` (a command or test in this session proved it), `code-only` (read in source; say why nothing executable exists), or `contradicts-readme` (verified, and README.md says otherwise; cite the README line). If a parent fact is wrong, append `## disputes` with the id and evidence, and stop.

Required ids (downstream pages read these by name):

- `screens.rules` - naming, sharing, canvas
- `compose.contract` - the five rules

## Out of scope

- offset with dialogs -> runtime/moving-and-hiding

## Done when

- [ ] Environment block ran clean.
- [ ] `_facts/authoring/screens-and-overlays.md` exists with every fact id listed under "Facts to emit", each with a status.
- [ ] Every command shown on the page was run in this session; every output block is pasted from that run.
- [ ] Every screenshot listed exists under `assets/authoring/screens-and-overlays/`, is registered in `assets/assets.json` with its command, and has alt text.
- [ ] Frontmatter present: `id: authoring/screens-and-overlays`, `title`, `description`, `section`, `order: 19`, `version: 0.6.0`, `sources` (every path opened).
- [ ] Every `page:` link names an id from the page index in ARCHITECTURE.md.
- [ ] Word count of prose is 300 to 1500 (`pandoc -t plain` or a `wc -w` after stripping tables and code).
- [ ] Forbidden-phrase grep over the page returns nothing.
- [ ] Nothing from the drift rows' "claim" column appears on the page.
- [ ] Sections appear in the order given under Page structure and every table has the named columns.
