# Page: cli/ps2ui-check (ps2ui-check)

Page type: `cli`. Section order: `33`. Wave: `0`.

## Purpose and audience

The blob validator: options, TAP output, the full check catalogue with what each failure means and what to change, exit codes, the exact-count allow flags, and the CI wrapper.

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
| D13 | README.md Quick start C snippet | `arena[1662]` | Blob-specific and target-specific. Quote the arena line from a bake in this session, with the command. The bake prints the EE figure; `ps2ui-check` prints the EE and 64-bit host figures. |

## Sources of truth

Line numbers are hints from the exploration that produced this brief; re-locate by symbol name. Authority order: code, tests, docs/*.md, README.md.

- packages/baker/ps2ui_bake/check.py - options (~709-728), Report.emit (~86-96), every check function (~122-626), print_tints, main exit logic (~730-753)
- tools/check-blobs.sh - the per-blob flag table
- packages/baker/tests/test_baker.py TestCheck

## Claims to verify, and how

Each item is `claim -> how to prove it`. Run every command. Paste real output into the page where the structure calls for it and record the result in the facts file.

1. Options: --version, uib, --vram-budget, --allow-dead, --allow-hairline, --strict, --tints -> `--help`
2. TAP shape: notes, ok/not ok, `# TODO warning`, plan line, trailer, PASS line -> run on memcard and paste
3. Exit 2 unreadable, 0 for --tints, else 1 when errors (plus warnings under --strict) -> corrupt one byte of a copy and run; run --strict on channel6 without --allow-dead
4. The catalogue: every label in check_tables, check_indices, check_screens, check_scissors, check_gs_domains, check_tints, check_fonts, check_vram, check_crt -> read each function; table rows: label pattern · severity · meaning · change
5. --allow-* are exact in both directions -> run memcard with --allow-hairline 1 and paste the warning
6. The arena note prints EE and host figures -> paste
7. check-blobs.sh is the single source of CI flags -> paste its table

## Screenshots

None. Do not add decorative images.

## Page structure

Skeleton for type `cli`: Synopsis · Options · Output · Exit codes · Files written · Related pages.

CLI skeleton. The catalogue is the Output section's main table. Related pages.

Frontmatter:

```yaml
---
id: cli/ps2ui-check
title: ps2ui-check
description: <one sentence>
section: cli
order: 33
version: 0.6.0
sources: [<every repository path opened>]
---
```

## Cross-links

Write links as `[text](page:<id>#<anchor>)`. Every id below must appear on the page at the place named.

- authoring/vram-budget - VRAM check
- authoring/theming - tints
- authoring/crt-linter - CRT checks
- reference/uib-format - what is checked
- runtime/errors-and-constants - what the loader itself checks
- cli/previewer - --uib pairs with check

## Facts to emit

Write `_facts/<page-id>.md` before writing the page:

```markdown
# facts: <page-id>

| id | fact | source | verified by | status |
|---|---|---|---|---|
```

Status is `verified` (a command or test in this session proved it), `code-only` (read in source; say why nothing executable exists), or `contradicts-readme` (verified, and README.md says otherwise; cite the README line). If a parent fact is wrong, append `## disputes` with the id and evidence, and stop.

Required ids (downstream pages read these by name):

- `check.catalogue` - every row
- `check.exit-codes`
- `check.tap-shape`
- `check.arena-note` - both figures for memcard

## Out of scope

- the runtime's own load checks -> runtime/errors-and-constants

## Done when

- [ ] Environment block ran clean.
- [ ] `_facts/cli/ps2ui-check.md` exists with every fact id listed under "Facts to emit", each with a status.
- [ ] Every command shown on the page was run in this session; every output block is pasted from that run.
- [ ] Every screenshot listed exists under `assets/cli/ps2ui-check/`, is registered in `assets/assets.json` with its command, and has alt text.
- [ ] Frontmatter present: `id: cli/ps2ui-check`, `title`, `description`, `section`, `order: 33`, `version: 0.6.0`, `sources` (every path opened).
- [ ] Every `page:` link names an id from the page index in ARCHITECTURE.md.
- [ ] Word count of prose is 300 to 1500 (`pandoc -t plain` or a `wc -w` after stripping tables and code).
- [ ] Forbidden-phrase grep over the page returns nothing.
- [ ] Nothing from the drift rows' "claim" column appears on the page.
- [ ] Sections appear in the order given under Page structure and every table has the named columns.
