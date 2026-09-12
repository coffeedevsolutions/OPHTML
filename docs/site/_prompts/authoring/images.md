# Page: authoring/images (Images)

Page type: `guide`. Section order: `14`. Wave: `1`.

## Purpose and audience

Baked images: PNG only, relative to the HTML file, sized from the PNG or CSS, pre-scaled at bake, palettize rules for indexed and RGBA sources, what each format costs. Streamed slots get one paragraph and a link.

## Read first

1. `docs/site/ARCHITECTURE.md`, all of it. The rules below are copied from it and are binding.
2. Parent facts files, before opening any source: `_facts/authoring/css.md`, `_facts/cli/ps2ui-bake.md`, `_facts/authoring/vram-budget.md`. Reuse their fact ids; do not restate a parent fact differently. If one is wrong, write a `## disputes` section and stop.
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
| D7 | README.md "Supported CSS" | the property list | Missing: `opacity`, `min-*`/`max-*`, `align-self`, `flex` shorthand, `row-gap`, `column-gap`, `:root` custom properties, `var()`, `@theme`, `data-nocontrast`, capacity default 63, the `name` attribute, `--min-font-size`. Overstated: `border-radius` takes one px value; named colours are eight; keyword-valued properties are unvalidated; the `:focus` geometry guard does not cover `letter-spacing`, `font-weight`, `text-align`, `text-overflow`; no `white-space: pre`; `&nbsp;` collapses to a space. |

## Sources of truth

Line numbers are hints from the exploration that produced this brief; re-locate by symbol name. Authority order: code, tests, docs/*.md, README.md.

- packages/layout/src/box.js ~215-285 - img attributes, palettize, src resolution
- packages/layout/src/image.js - PNG signature and IHDR read, errors
- packages/layout/src/flex.js ~124-156 and ~461-468 - intrinsic sizing, one-axis aspect, no stretch
- packages/baker/ps2ui_bake/quads.py ~322-361 (decode, indexed rules), ~515-521 (texture key, palette padding), ~592-597 (FASTOCTREE)
- packages/baker/tests/test_baker.py TestImages; packages/layout/test/layout.test.js image cases
- examples/channel6/ui/assets - real palettized covers and make_assets.py

## Claims to verify, and how

Each item is `claim -> how to prove it`. Run every command. Paste real output into the page where the structure calls for it and record the result in the facts file.

1. PNG only; other formats error at layout -> compile an `<img src=x.jpg>` and paste
2. src resolves relative to the HTML file -> read box.js; compile from a subdirectory
3. Intrinsic size from IHDR; one CSS axis keeps aspect; both axes scale -> cite layout.test.js cases
4. The baker pre-scales to the laid-out size -> cite `test_image_prescaled_to_layout_size`
5. `palettize` attribute = PSMT8 + 256-entry CLUT; indexed PNGs keep their palette; short palettes are padded; size mismatch is an error under the attribute and a warning under `--palettize-images` -> run `python3 -m unittest tests.test_baker.TestImages -v` and paste; trigger the mismatch error with a scratch PNG
6. VRAM cost: PSMT8 is a quarter of PSMCT32 per texel plus 1 KiB CLUT -> bake channel6 with and without `--palettize-images` and paste the two `tex[` rows for one cover
7. Same asset at two sizes is two textures -> read the texture key in quads.py
8. Images never stretch -> cite flex.js

## Screenshots

Each line is `path <- command // alt text`. Register every file in `assets/assets.json` with the exact command (`OUT` for the output path) and `checked: true` unless the line says otherwise. Previewer renders only; Playwright only where the line says so.

- assets/authoring/images/covers.png <- examples/channel6 games screen `preview.render(..., screen='games')` // the channel6 games screen with six palettized covers

## Page structure

Skeleton for type `guide`: What it is · Minimal example · Reference table · Behaviour · Limits and errors · Related pages.

Guide skeleton. Minimal example: an img with CSS width. Reference table: attribute/flag · effect (src, palettize, --palettize-images, width/height in CSS). Behaviour: sizing, scaling, palettize rules, cost. Limits and errors table.

Frontmatter:

```yaml
---
id: authoring/images
title: Images
description: <one sentence>
section: authoring
order: 14
version: 0.6.0
sources: [<every repository path opened>]
---
```

## Cross-links

Write links as `[text](page:<id>#<anchor>)`. Every id below must appear on the page at the place named.

- runtime/streaming-art - streamed slots paragraph
- authoring/vram-budget - cost
- authoring/css - sizing
- reference/uib-format - texture formats

## Facts to emit

Write `_facts/<page-id>.md` before writing the page:

```markdown
# facts: <page-id>

| id | fact | source | verified by | status |
|---|---|---|---|---|
```

Status is `verified` (a command or test in this session proved it), `code-only` (read in source; say why nothing executable exists), or `contradicts-readme` (verified, and README.md says otherwise; cite the README line). If a parent fact is wrong, append `## disputes` with the id and evidence, and stop.

Required ids (downstream pages read these by name):

- `images.formats` - PNG only; PSMT8 vs PSMCT32
- `images.sizing` - intrinsic, one-axis, no stretch
- `images.palettize.rules` - attribute vs flag; indexed handling

## Out of scope

- data-tex-slot -> runtime/streaming-art and authoring/html
- the VRAM model -> authoring/vram-budget

## Done when

- [ ] Environment block ran clean.
- [ ] `_facts/authoring/images.md` exists with every fact id listed under "Facts to emit", each with a status.
- [ ] Every command shown on the page was run in this session; every output block is pasted from that run.
- [ ] Every screenshot listed exists under `assets/authoring/images/`, is registered in `assets/assets.json` with its command, and has alt text.
- [ ] Frontmatter present: `id: authoring/images`, `title`, `description`, `section`, `order: 14`, `version: 0.6.0`, `sources` (every path opened).
- [ ] Every `page:` link names an id from the page index in ARCHITECTURE.md.
- [ ] Word count of prose is 300 to 1500 (`pandoc -t plain` or a `wc -w` after stripping tables and code).
- [ ] Forbidden-phrase grep over the page returns nothing.
- [ ] Nothing from the drift rows' "claim" column appears on the page.
- [ ] Sections appear in the order given under Page structure and every table has the named columns.
