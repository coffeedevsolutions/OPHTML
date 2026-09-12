# Page: authoring/vram-budget (VRAM budget)

Page type: `guide`. Section order: `22`. Wave: `1`.

## Purpose and audience

What the budget is, how it is computed, how to read the breakdown table, which number `tex_set` wants, how to override it, what the impossible-default diagnostic means, and what the console does when textures do not fit.

## Read first

1. `docs/site/ARCHITECTURE.md`, all of it. The rules below are copied from it and are binding.
2. Parent facts files, before opening any source: `_facts/cli/ps2ui-bake.md`, `_facts/cli/ps2ui-check.md`, `_facts/authoring/project-file.md`, `_facts/runtime/api-reference.md`. Reuse their fact ids; do not restate a parent fact differently. If one is wrong, write a `## disputes` section and stop.
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
| D13 | README.md Quick start C snippet | `arena[1662]` | Blob-specific and target-specific. Quote the arena line from a bake in this session, with the command. The bake prints the EE figure; `ps2ui-check` prints the EE and 64-bit host figures. |

## Sources of truth

Line numbers are hints from the exploration that produced this brief; re-locate by symbol name. Authority order: code, tests, docs/*.md, README.md.

- packages/baker/ps2ui_bake/vram.py - VRAM_TOTAL, PAGE_BYTES, page_rounded_size vs alloc_size, default_budget (~133-149), budget_note (~158-200), report (~203-290)
- packages/baker/ps2ui_bake/cli.py ~258-266; check.py ~595-626
- runtime/ps2ui.c ~567-660; runtime/ps2ui.h ~463 - the upload preflight and all-or-nothing refusal
- CHANGELOG.md 0.6.0 - `ps2ui check` receives the budget; negative budget diagnostic
- tools/check-vram-model.py; test_baker.py TestVram

## Claims to verify, and how

Each item is `claim -> how to prove it`. Run every command. Paste real output into the page where the structure calls for it and record the result in the facts file.

1. Total 4 MiB; default budget = total minus three framebuffers at the canvas -> run `ps2ui-bake` on memcard and paste the `framebuffers assumed` and `textures ... of ... budget` lines
2. Two models: 8 KiB page rounding for the budget, 256-byte blocks for the allocator -> cite vram.py header; run `python3 tools/check-vram-model.py`
3. Each breakdown column explained; `payload` is the `tex_set` length -> paste a bake of fixtures/bench-stream and annotate one streamed row
4. `--vram-budget`/`vramBudget` reaches build and check alike (new in 0.6.0) -> set it in a scratch project and run both; paste the agreeing lines
5. Above 769 px wide at 448 lines the default is negative and the note says so; above 1153 no budget helps -> compile a scratch screen with `--canvas 796x448`, bake, paste the note; cite `test_the_advice_stops_when_two_buffers_stop_fitting`
6. `ps2ui_upload` preflights and refuses all-or-nothing with -1 -> cite ps2ui.c and the runtime "upload" section
7. PSMT8 saves a quarter -> link images

## Screenshots

None. Do not add decorative images.

## Page structure

Skeleton for type `guide`: What it is · Minimal example · Reference table · Behaviour · Limits and errors · Related pages.

Guide skeleton. Minimal example: the memcard breakdown. Reference table: column · meaning. Table 2: flag/key · effect. Behaviour: the model, overriding, impossible defaults, the console side. Limits and errors.

Frontmatter:

```yaml
---
id: authoring/vram-budget
title: VRAM budget
description: <one sentence>
section: authoring
order: 22
version: 0.6.0
sources: [<every repository path opened>]
---
```

## Cross-links

Write links as `[text](page:<id>#<anchor>)`. Every id below must appear on the page at the place named.

- cli/ps2ui-bake - transcript
- cli/ps2ui-check - VRAM check
- authoring/images - PSMT8
- runtime/streaming-art - payload
- runtime/api-reference - upload
- runtime/first-boot - step 9

## Facts to emit

Write `_facts/<page-id>.md` before writing the page:

```markdown
# facts: <page-id>

| id | fact | source | verified by | status |
|---|---|---|---|---|
```

Status is `verified` (a command or test in this session proved it), `code-only` (read in source; say why nothing executable exists), or `contradicts-readme` (verified, and README.md says otherwise; cite the README line). If a parent fact is wrong, append `## disputes` with the id and evidence, and stop.

Required ids (downstream pages read these by name):

- `vram.default-budget` - formula and memcard numbers
- `vram.breakdown.columns` - meanings
- `vram.payload-vs-pages` - which number tex_set wants
- `vram.impossible-default` - thresholds

## Out of scope

- texture formats -> authoring/images

## Done when

- [ ] Environment block ran clean.
- [ ] `_facts/authoring/vram-budget.md` exists with every fact id listed under "Facts to emit", each with a status.
- [ ] Every command shown on the page was run in this session; every output block is pasted from that run.
- [ ] Every screenshot listed exists under `assets/authoring/vram-budget/`, is registered in `assets/assets.json` with its command, and has alt text.
- [ ] Frontmatter present: `id: authoring/vram-budget`, `title`, `description`, `section`, `order: 22`, `version: 0.6.0`, `sources` (every path opened).
- [ ] Every `page:` link names an id from the page index in ARCHITECTURE.md.
- [ ] Word count of prose is 300 to 1500 (`pandoc -t plain` or a `wc -w` after stripping tables and code).
- [ ] Forbidden-phrase grep over the page returns nothing.
- [ ] Nothing from the drift rows' "claim" column appears on the page.
- [ ] Sections appear in the order given under Page structure and every table has the named columns.
