# Page: runtime/errors-and-constants (Errors and constants)

Page type: `api`. Section order: `43`. Wave: `0`.

## Purpose and audience

Every error code with its value and what triggers it, the order `ps2ui_load` checks things in, every public macro and constant, the feature bits, and the build-time switches.

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
| D11 | runtime/ps2ui.c comments near the upload loop and `list_row_name` | `PS2UI_MAX_TEXTURES`, `PS2UI_MAX_LIST_ROWS` | Neither exists. The only runtime cap is `PS2UI_MAX_SCISSOR_DEPTH` (8). Table counts are bounded by the format's uint16 fields. |
| D12 | README.md Quick start C comment | `PS2UI_VERSION` keeps baker and runtime from drifting | It is the frozen format version, 7. Baker and runtime match because `ps2ui vendor-runtime` ships both files from one package. |

## Sources of truth

Line numbers are hints from the exploration that produced this brief; re-locate by symbol name. Authority order: code, tests, docs/*.md, README.md.

- runtime/ps2ui.h ~36-80 (magic, version, feature bits, ops, states, formats), ~283-301 (scissor depth, list name max), ~412-434 (error codes, arena align)
- runtime/ps2ui.c ~252-500 (load, in check order), ~117-139 (ARENA_LIMIT), ~537 (CLUT_PERMUTE), ~717 (SKIP_SYNCDCACHE), ~1051 (PRIMALPHA_OFF), ~675-800 (tex_set, clut_set returns), ~1574-1580 (offset range)
- runtime/tests/test_runtime.c loader section and test_narrow.c

## Claims to verify, and how

Each item is `claim -> how to prove it`. Run every command. Paste real output into the page where the structure calls for it and record the result in the facts file.

1. The code table: OK, TRUNCATED, MAGIC, VERSION, BOUNDS, TOO_MANY, CRC, FEATURES, ALIGN, ARENA, NOT_STREAMED, SIZE, RANGE, STATE, TINTS with values -1..-14 and triggers -> read ps2ui.h and ps2ui.c; every row cites a line
2. Load check order: magic, version, features, n_screen, n_theme, tints, truncation, CRC, per-table bounds, arena; a corrupt field usually reads as CRC -> cite ps2ui.c and the test's recrc helper
3. upload returns -1, not a code -> cite
4. Constants: MAGIC, VERSION 7, ARENA_ALIGN 16, MAX_SCISSOR_DEPTH 8, LIST_NAME_MAX 64, VISIBLE_UNKNOWN -1, NONE 0xFFFF, NAME_NONE, feature bits 1/2/4/8/16, FEAT_KNOWN, ops, states, texfmt, texkind, slot align, ELLIPSIS flag -> grep `#define PS2UI_` and table every one
5. PS2UI_VERSION is the format version, frozen -> cite vendor.py comment and format-uib.md
6. Build switches: CLUT_PERMUTE, ARENA_LIMIT (narrow only), PRIMALPHA_OFF, SKIP_SYNCDCACHE -> cite lines; run `make -C runtime test-narrow`
7. PS2UI_MAX_TEXTURES and PS2UI_MAX_LIST_ROWS do not exist (D11) -> grep and show no definition

## Screenshots

None. Do not add decorative images.

## Page structure

Skeleton for type `api`: Function tables by group · Structs · Constants · Ordering rules.

API skeleton reduced to: Error codes table (code · value · triggered by · fix) · Load check order (list) · Constants table (name · value · meaning) · Feature bits table · Build-time switches table.

Frontmatter:

```yaml
---
id: runtime/errors-and-constants
title: Errors and constants
description: <one sentence>
section: runtime
order: 43
version: 0.6.0
sources: [<every repository path opened>]
---
```

## Cross-links

Write links as `[text](page:<id>#<anchor>)`. Every id below must appear on the page at the place named.

- runtime/api-reference - which function returns what
- runtime/frame-loop - handling
- reference/uib-format - the format side of each check
- cli/ps2ui-check - the offline equivalent

## Facts to emit

Write `_facts/<page-id>.md` before writing the page:

```markdown
# facts: <page-id>

| id | fact | source | verified by | status |
|---|---|---|---|---|
```

Status is `verified` (a command or test in this session proved it), `code-only` (read in source; say why nothing executable exists), or `contradicts-readme` (verified, and README.md says otherwise; cite the README line). If a parent fact is wrong, append `## disputes` with the id and evidence, and stop.

Required ids (downstream pages read these by name):

- `errors.table`
- `load.order`
- `constants.table`
- `feature-bits`
- `build-switches`

## Out of scope

- what ps2ui-check validates offline -> cli/ps2ui-check

## Done when

- [ ] Environment block ran clean.
- [ ] `_facts/runtime/errors-and-constants.md` exists with every fact id listed under "Facts to emit", each with a status.
- [ ] Every command shown on the page was run in this session; every output block is pasted from that run.
- [ ] Every screenshot listed exists under `assets/runtime/errors-and-constants/`, is registered in `assets/assets.json` with its command, and has alt text.
- [ ] Frontmatter present: `id: runtime/errors-and-constants`, `title`, `description`, `section`, `order: 43`, `version: 0.6.0`, `sources` (every path opened).
- [ ] Every `page:` link names an id from the page index in ARCHITECTURE.md.
- [ ] Word count of prose is 300 to 1500 (`pandoc -t plain` or a `wc -w` after stripping tables and code).
- [ ] Forbidden-phrase grep over the page returns nothing.
- [ ] Nothing from the drift rows' "claim" column appears on the page.
- [ ] Sections appear in the order given under Page structure and every table has the named columns.
