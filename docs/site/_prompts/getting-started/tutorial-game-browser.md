# Page: getting-started/tutorial-game-browser (Tutorial: a game browser)

Page type: `guide`. Section order: `3`. Wave: `3`.

## Purpose and audience

The CI-executed tutorial, rewritten in the library voice: same eight steps and files, shorter prose, each step ending with what the reader now has. The `sh` and `text` blocks stay byte-identical to `docs/tutorial-uc3.md` so `tools/check-tutorial.py` can be pointed at this page.

## Read first

1. `docs/site/ARCHITECTURE.md`, all of it. The rules below are copied from it and are binding.
2. Parent facts files, before opening any source: `_facts/getting-started/installation.md`, `_facts/authoring/project-file.md`, `_facts/authoring/dynamic-text.md`, `_facts/authoring/lists.md`, `_facts/authoring/theming.md`, `_facts/runtime/frame-loop.md`, `_facts/runtime/integrating.md`. Reuse their fact ids; do not restate a parent fact differently. If one is wrong, write a `## disputes` section and stop.
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
| D13 | README.md Quick start C snippet | `arena[1662]` | Blob-specific and target-specific. Quote the arena line from a bake in this session, with the command. The bake prints the EE figure; `ps2ui-check` prints the EE and 64-bit host figures. |
| D14 | README.md "Multiple screens" | a second `ps2ui_render` in one frame with nothing else said | `gsKit_TexManager_nextFrame` is called once after the flip, never between the two renders; `ctx->stats` holds only the last render's counters. |

## Sources of truth

Line numbers are hints from the exploration that produced this brief; re-locate by symbol name. Authority order: code, tests, docs/*.md, README.md.

- docs/tutorial-uc3.md - the whole file; the eight ```sh blocks and their ```text blocks are the contract
- tools/check-tutorial.py - `BLOCK` regex, `ASSERTED_BLOCKS = {1, 5, 6, 7}`, `SHIMS`; the page must keep exactly eight ```sh blocks in the same order
- runtime/sample/main.c lines 1638-1660 and 2630-2750 - the checked load/upload and the frame order, for step 8

## Claims to verify, and how

Each item is `claim -> how to prove it`. Run every command. Paste real output into the page where the structure calls for it and record the result in the facts file.

1. The page executes under the tutorial checker -> copy the page to a temp path, run `python3 tools/check-tutorial.py` with `DOC` pointed at it (edit a copy of the script or add an env override in the scratch copy); it must report the same asserted blocks passing
2. Step 8's C loop calls `gsKit_TexManager_nextFrame` once after the flip -> compare with `main.c`; keep the tutorial's block since it is not executed, but check it against `loop.order`
3. The tutorial's arena figure is that project's -> re-derive from the run; do not carry the README's 1662

## Screenshots

Each line is `path <- command // alt text`. Register every file in `assets/assets.json` with the exact command (`OUT` for the output path) and `checked: true` unless the line says otherwise. Previewer renders only; Playwright only where the line says so.

- assets/getting-started/tutorial-game-browser/preview.png <- build/preview.png from the run // the tutorial library screen, six rows, theme 0
- assets/getting-started/tutorial-game-browser/states.png <- `preview.montage` over the tutorial blob (add `"montage": "build/states.png"` in a scratch copy of the project, not in the tutorial block) // every focus state of the library screen on one sheet
- assets/getting-started/tutorial-game-browser/serve.png <- Playwright capture after step 7; `checked: false` // the served page after the tutorial's step 7

## Page structure

Skeleton for type `guide`: What it is · Minimal example · Reference table · Behaviour · Limits and errors · Related pages.

Numbered steps 1 to 8 as headings, the tutorial's own titles shortened. Each: one sentence of intent, the block, the output block where the tutorial has one, one sentence 'You now have ...'. Then 'From a checkout' as a table (command · checkout spelling). Then Related pages. Keep the macOS Raqm note as one sentence plus a link to installation.

Frontmatter:

```yaml
---
id: getting-started/tutorial-game-browser
title: Tutorial: a game browser
description: <one sentence>
section: getting-started
order: 3
version: 0.6.0
sources: [<every repository path opened>]
---
```

## Cross-links

Write links as `[text](page:<id>#<anchor>)`. Every id below must appear on the page at the place named.

- getting-started/installation - step 1
- authoring/dynamic-text - step 2
- authoring/lists - step 2 and 8
- authoring/theming - step 3
- authoring/project-file - step 4
- cli/ps2ui-check - step 6
- cli/previewer - step 7
- runtime/frame-loop - step 8
- runtime/integrating - step 8

## Facts to emit

Write `_facts/<page-id>.md` before writing the page:

```markdown
# facts: <page-id>

| id | fact | source | verified by | status |
|---|---|---|---|---|
```

Status is `verified` (a command or test in this session proved it), `code-only` (read in source; say why nothing executable exists), or `contradicts-readme` (verified, and README.md says otherwise; cite the README line). If a parent fact is wrong, append `## disputes` with the id and evidence, and stop.

Required ids (downstream pages read these by name):

- `tutorial.blocks` - the eight sh blocks' first lines, in order, so the checker can be re-pointed

## Out of scope

- why flex-direction is required -> authoring/css
- list window semantics -> authoring/lists

## Done when

- [ ] Environment block ran clean.
- [ ] `_facts/getting-started/tutorial-game-browser.md` exists with every fact id listed under "Facts to emit", each with a status.
- [ ] Every command shown on the page was run in this session; every output block is pasted from that run.
- [ ] Every screenshot listed exists under `assets/getting-started/tutorial-game-browser/`, is registered in `assets/assets.json` with its command, and has alt text.
- [ ] Frontmatter present: `id: getting-started/tutorial-game-browser`, `title`, `description`, `section`, `order: 3`, `version: 0.6.0`, `sources` (every path opened).
- [ ] Every `page:` link names an id from the page index in ARCHITECTURE.md.
- [ ] Word count of prose is 300 to 1500 (`pandoc -t plain` or a `wc -w` after stripping tables and code).
- [ ] Forbidden-phrase grep over the page returns nothing.
- [ ] Nothing from the drift rows' "claim" column appears on the page.
- [ ] Sections appear in the order given under Page structure and every table has the named columns.
