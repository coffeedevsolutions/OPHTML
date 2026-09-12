# Page: authoring/video-modes (Video modes)

Page type: `guide`. Section order: `20`. Wave: `1`.

## Purpose and audience

The four modes, what the framebuffer and the panel each are, why 16:9 is anamorphic, how to preview at the panel's aspect, the distortion lint, and the header field the runtime reports.

## Read first

1. `docs/site/ARCHITECTURE.md`, all of it. The rules below are copied from it and are binding.
2. Parent facts files, before opening any source: `_facts/cli/ps2ui-layout.md`, `_facts/cli/ps2ui-bake.md`, `_facts/authoring/crt-linter.md`, `_facts/runtime/api-reference.md`. Reuse their fact ids; do not restate a parent fact differently. If one is wrong, write a `## disputes` section and stop.
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
| D4 | README.md "Focus and navigation", "Widescreen and video modes" | `--focus-wrap`, `--mode`, `--display-aspect` read as bake flags | They are `ps2ui-layout` flags. `--mode` is also on `ps2ui build`. `ps2ui-bake` has none of them. |

## Sources of truth

Line numbers are hints from the exploration that produced this brief; re-locate by symbol name. Authority order: code, tests, docs/*.md, README.md.

- packages/layout/src/aspect.js ~47-52 - MODES; the PAR derivation
- packages/layout/bin/ps2ui-layout.js ~43-45, ~66-86 - --mode, --canvas, --display-aspect precedence
- packages/layout/src/lint.js ~154-172 - aspect-distortion
- runtime/ps2ui.c ~1493-1500 - pixel_aspect_x1000
- packages/baker/ps2ui_bake/cli.py - --preview-display; serve_page.html aspect select
- examples/channel6/build.sh - the ntsc16x9 bake
- packages/layout/test/layout.test.js aspect cases; test_baker.py TestDisplayAspect; test_runtime.c "display aspect"

## Claims to verify, and how

Each item is `claim -> how to prove it`. Run every command. Paste real output into the page where the structure calls for it and record the result in the facts file.

1. The mode table: ntsc 640x448 4:3, ntsc16x9 640x448 16:9, pal 640x512 4:3, pal16x9 640x512 16:9, with PAR -> read aspect.js; compile with each and print `ir.canvas`
2. `--canvas` and `--display-aspect` override `--mode` -> read the CLI; compile `--mode pal --canvas 704x448` and print canvas
3. `--preview-display` writes the panel-aspect PNG and prints its size -> run channel6's 16:9 bake and paste the line
4. The distortion lint fires above 0.08 PAR deviation with the divisor -> compile channel6 games at ntsc16x9 and paste the warning
5. `ps2ui_pixel_aspect_x1000` returns 933 for ntsc, 1244 for ntsc16x9 -> cite the runtime test
6. PAL adjusts the linter's safe inset (5% of the canvas) -> read lint.js defaults

## Screenshots

Each line is `path <- command // alt text`. Register every file in `assets/assets.json` with the exact command (`OUT` for the output path) and `checked: true` unless the line says otherwise. Previewer renders only; Playwright only where the line says so.

- assets/authoring/video-modes/games-1x1.png <- channel6 `build/ui-16x9.uib` at 1:1 // channel6 games, 16:9 blob, framebuffer pixels
- assets/authoring/video-modes/games-display.png <- `build/preview-16x9-display.png` from the channel6 build // the same frame resampled to the panel's 16:9 aspect
- assets/authoring/video-modes/serve-forced-4x3.png <- Playwright: serve the 16:9 blob with `--uib`, set aspect to force 4:3, capture; `checked: false` // a 16:9-authored screen forced to 4:3 in the previewer

## Page structure

Skeleton for type `guide`: What it is · Minimal example · Reference table · Behaviour · Limits and errors · Related pages.

Guide skeleton. Minimal example: a project with `"mode": "ntsc16x9"`. Reference table: mode · framebuffer · panel · PAR. Table 2: flag · effect. Behaviour: anamorphic pixels, previewing, the lint, the header field, PAL. Limits.

Frontmatter:

```yaml
---
id: authoring/video-modes
title: Video modes
description: <one sentence>
section: authoring
order: 20
version: 0.6.0
sources: [<every repository path opened>]
---
```

## Cross-links

Write links as `[text](page:<id>#<anchor>)`. Every id below must appear on the page at the place named.

- cli/ps2ui-layout - flags
- cli/ps2ui-bake - --preview-display
- authoring/crt-linter - distortion rule
- cli/previewer - aspect menu
- runtime/api-reference - pixel_aspect_x1000
- runtime/first-boot - step 10

## Facts to emit

Write `_facts/<page-id>.md` before writing the page:

```markdown
# facts: <page-id>

| id | fact | source | verified by | status |
|---|---|---|---|---|
```

Status is `verified` (a command or test in this session proved it), `code-only` (read in source; say why nothing executable exists), or `contradicts-readme` (verified, and README.md says otherwise; cite the README line). If a parent fact is wrong, append `## disputes` with the id and evidence, and stop.

Required ids (downstream pages read these by name):

- `modes.table` - the four rows
- `aspect.par` - formula and values
- `aspect.flags` - precedence

## Out of scope

- the probe screen's ASPECT cell -> runtime/first-boot

## Done when

- [ ] Environment block ran clean.
- [ ] `_facts/authoring/video-modes.md` exists with every fact id listed under "Facts to emit", each with a status.
- [ ] Every command shown on the page was run in this session; every output block is pasted from that run.
- [ ] Every screenshot listed exists under `assets/authoring/video-modes/`, is registered in `assets/assets.json` with its command, and has alt text.
- [ ] Frontmatter present: `id: authoring/video-modes`, `title`, `description`, `section`, `order: 20`, `version: 0.6.0`, `sources` (every path opened).
- [ ] Every `page:` link names an id from the page index in ARCHITECTURE.md.
- [ ] Word count of prose is 300 to 1500 (`pandoc -t plain` or a `wc -w` after stripping tables and code).
- [ ] Forbidden-phrase grep over the page returns nothing.
- [ ] Nothing from the drift rows' "claim" column appears on the page.
- [ ] Sections appear in the order given under Page structure and every table has the named columns.
