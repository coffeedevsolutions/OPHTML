# Page: runtime/streaming-art (Streaming art)

Page type: `guide`. Section order: `44`. Wave: `2`.

## Purpose and audience

Art the app supplies at runtime: the reservation, the `tex_set` contract, converting on the host, palettized art through `clut_set`, and the worked bench path.

## Read first

1. `docs/site/ARCHITECTURE.md`, all of it. The rules below are copied from it and are binding.
2. Parent facts files, before opening any source: `_facts/authoring/images.md`, `_facts/authoring/vram-budget.md`, `_facts/runtime/api-reference.md`, `_facts/runtime/frame-loop.md`. Reuse their fact ids; do not restate a parent fact differently. If one is wrong, write a `## disputes` section and stop.
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

- runtime/ps2ui.h ~466-562 - tex_set and clut_set contracts
- runtime/ps2ui.c ~675-800
- tools/make_cover_raw.py - PSMCT32 output, GS alpha
- fixtures/bench-stream/build.sh and ui/
- docs/deploying.md 'What you are actually copying' - mass:/ps2ui/
- runtime/tests/test_runtime.c 'streamed texture slots (v6 §3)' and 'P3b: a CLUT swap'; test_baker.py TestStreamedAuthoring

## Claims to verify, and how

Each item is `claim -> how to prove it`. Run every command. Paste real output into the page where the structure calls for it and record the result in the facts file.

1. A streamed slot is `<img data-tex-slot>` with CSS width and height and no src; same name at two sizes is refused; two elements may share one -> cite images and TestStreamedAuthoring
2. tex_set: len must equal the payload exactly, texels 16-aligned, not copied, must outlive drawing, safe before upload, call again to swap -> cite ps2ui.h; cite the runtime section
3. Unfilled slots draw nothing and count in tex_unfilled -> cite
4. make_cover_raw.py writes w*h*4 bytes with GS alpha 0x80 -> run `--self-test`; run it on a scratch PNG and check the size
5. clut_set: after upload only (ERR_STATE), linear input, every sharing texture changes, short palette blanks the tail, does not survive re-upload -> cite ps2ui.h
6. The bench fixture bakes with reserved slots -> run its build.sh and paste the streamed rows

## Screenshots

Each line is `path <- command // alt text`. Register every file in `assets/assets.json` with the exact command (`OUT` for the output path) and `checked: true` unless the line says otherwise. Previewer renders only; Playwright only where the line says so.

- assets/runtime/streaming-art/covers-empty.png <- bench-stream covers screen `--preview` // the covers screen with unfilled slots, as the console draws it before tex_set

## Page structure

Skeleton for type `guide`: What it is · Minimal example · Reference table · Behaviour · Limits and errors · Related pages.

Guide skeleton. Minimal example: the markup line and the C call. Reference table: constraint · consequence of breaking it. Table 2: clut_set rules. Behaviour: the flow from host file to VRAM. Limits and errors: the three error codes.

Frontmatter:

```yaml
---
id: runtime/streaming-art
title: Streaming art
description: <one sentence>
section: runtime
order: 44
version: 0.6.0
sources: [<every repository path opened>]
---
```

## Cross-links

Write links as `[text](page:<id>#<anchor>)`. Every id below must appear on the page at the place named.

- authoring/images - data-tex-slot
- authoring/vram-budget - payload
- runtime/api-reference - signatures
- runtime/errors-and-constants - SIZE, ALIGN, NOT_STREAMED, STATE
- runtime/deploying - USB
- authoring/theming - tints vs CLUTs

## Facts to emit

Write `_facts/<page-id>.md` before writing the page:

```markdown
# facts: <page-id>

| id | fact | source | verified by | status |
|---|---|---|---|---|
```

Status is `verified` (a command or test in this session proved it), `code-only` (read in source; say why nothing executable exists), or `contradicts-readme` (verified, and README.md says otherwise; cite the README line). If a parent fact is wrong, append `## disputes` with the id and evidence, and stop.

Required ids (downstream pages read these by name):

- `tex.contract`
- `clut.contract`
- `stream.host-format` - bytes and alpha

## Out of scope

- the VRAM model -> authoring/vram-budget

## Done when

- [ ] Environment block ran clean.
- [ ] `_facts/runtime/streaming-art.md` exists with every fact id listed under "Facts to emit", each with a status.
- [ ] Every command shown on the page was run in this session; every output block is pasted from that run.
- [ ] Every screenshot listed exists under `assets/runtime/streaming-art/`, is registered in `assets/assets.json` with its command, and has alt text.
- [ ] Frontmatter present: `id: runtime/streaming-art`, `title`, `description`, `section`, `order: 44`, `version: 0.6.0`, `sources` (every path opened).
- [ ] Every `page:` link names an id from the page index in ARCHITECTURE.md.
- [ ] Word count of prose is 300 to 1500 (`pandoc -t plain` or a `wc -w` after stripping tables and code).
- [ ] Forbidden-phrase grep over the page returns nothing.
- [ ] Nothing from the drift rows' "claim" column appears on the page.
- [ ] Sections appear in the order given under Page structure and every table has the named columns.
