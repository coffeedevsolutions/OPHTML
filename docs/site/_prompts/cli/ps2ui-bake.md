# Page: cli/ps2ui-bake (ps2ui-bake)

Page type: `cli`. Section order: `32`. Wave: `0`.

## Purpose and audience

The baker: options, the annotated stderr transcript, every exit-1 condition, font manifest resolution, multi-IR screens, and the arena line. This brief also owns writing `tools/check-site-assets.py`.

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
| D4 | README.md "Focus and navigation", "Widescreen and video modes" | `--focus-wrap`, `--mode`, `--display-aspect` read as bake flags | They are `ps2ui-layout` flags. `--mode` is also on `ps2ui build`. `ps2ui-bake` has none of them. |
| D13 | README.md Quick start C snippet | `arena[1662]` | Blob-specific and target-specific. Quote the arena line from a bake in this session, with the command. The bake prints the EE figure; `ps2ui-check` prints the EE and 64-bit host figures. |

## Sources of truth

Line numbers are hints from the exploration that produced this brief; re-locate by symbol name. Authority order: code, tests, docs/*.md, README.md.

- packages/baker/ps2ui_bake/cli.py - options (~131-162), load_font_manifest (~82-127), the refusals (~168-266), prints (~289-348)
- packages/baker/ps2ui_bake/caps.py ~136-139; vram.py ~203-290; arena.py ~36-77
- packages/baker/ps2ui_bake/__main__.py
- packages/baker/tests/test_baker.py TestNewcomerPath, TestCaps, TestArena

## Claims to verify, and how

Each item is `claim -> how to prove it`. Run every command. Paste real output into the page where the structure calls for it and record the result in the facts file.

1. Options: --version, ir (one or more), -o (required), --fonts, --preview, --montage, --preview-display, --palettize-images, --tints, --vram-budget; none of --mode/--display-aspect/--focus-wrap -> run `--help` and paste
2. The transcript: layout warnings, runtime tables line, trim line, VRAM breakdown, tints, summary, arena line, preview lines -> bake memcard's two IRs and paste the whole stderr, then annotate each line
3. The arena line is printed unconditionally with the EE figure -> cite cli.py; note check prints both figures
4. Exit 1 conditions: IR version, duplicate stem, missing manifest (prints a template), bad manifest, IR/manifest font disagreement, flattener ValueError, caps, VRAM -> trigger IR version and duplicate stem; cite tests for the rest
5. Output parent directories are created -> cite `test_bake_creates_its_output_directories`
6. Screen name is the file stem; several IRs share tables -> bake two and read the summary

## Screenshots

Each line is `path <- command // alt text`. Register every file in `assets/assets.json` with the exact command (`OUT` for the output path) and `checked: true` unless the line says otherwise. Previewer renders only; Playwright only where the line says so.

- assets/cli/ps2ui-bake/preview.png <- `ps2ui-bake` memcard IRs `--preview` // memcard library, initial state
- assets/cli/ps2ui-bake/states.png <- `--montage` // memcard focus states

## Page structure

Skeleton for type `cli`: Synopsis · Options · Output · Exit codes · Files written · Related pages.

CLI skeleton. Output section is the annotated transcript as a two-column table (line · meaning) after the raw block. Related pages.

Frontmatter:

```yaml
---
id: cli/ps2ui-bake
title: ps2ui-bake
description: <one sentence>
section: cli
order: 32
version: 0.6.0
sources: [<every repository path opened>]
---
```

## Cross-links

Write links as `[text](page:<id>#<anchor>)`. Every id below must appear on the page at the place named.

- authoring/vram-budget - breakdown
- authoring/theming - --tints
- authoring/images - --palettize-images
- authoring/video-modes - --preview-display
- runtime/frame-loop - the arena line
- reference/uib-format - the output

## Facts to emit

Write `_facts/<page-id>.md` before writing the page:

```markdown
# facts: <page-id>

| id | fact | source | verified by | status |
|---|---|---|---|---|
```

Status is `verified` (a command or test in this session proved it), `code-only` (read in source; say why nothing executable exists), or `contradicts-readme` (verified, and README.md says otherwise; cite the README line). If a parent fact is wrong, append `## disputes` with the id and evidence, and stop.

Required ids (downstream pages read these by name):

- `cli.bake.options`
- `cli.bake.transcript` - the annotated lines
- `cli.bake.exit-conditions`
- `arena.line` - the format and this run's memcard value

## Out of scope

- reading the VRAM table -> authoring/vram-budget

## Done when

- [ ] Environment block ran clean.
- [ ] `_facts/cli/ps2ui-bake.md` exists with every fact id listed under "Facts to emit", each with a status.
- [ ] Every command shown on the page was run in this session; every output block is pasted from that run.
- [ ] Every screenshot listed exists under `assets/cli/ps2ui-bake/`, is registered in `assets/assets.json` with its command, and has alt text.
- [ ] Frontmatter present: `id: cli/ps2ui-bake`, `title`, `description`, `section`, `order: 32`, `version: 0.6.0`, `sources` (every path opened).
- [ ] Every `page:` link names an id from the page index in ARCHITECTURE.md.
- [ ] Word count of prose is 300 to 1500 (`pandoc -t plain` or a `wc -w` after stripping tables and code).
- [ ] Forbidden-phrase grep over the page returns nothing.
- [ ] Nothing from the drift rows' "claim" column appears on the page.
- [ ] Sections appear in the order given under Page structure and every table has the named columns.

Additional deliverable for this brief:

This brief also writes `tools/check-site-assets.py`: read `docs/site/assets/assets.json`, for each entry with `checked: true` run `command` with `OUT` replaced by a temp path (cwd = repo root), compare bytes with the committed file, report `ok`/`not ok` per entry in TAP, exit 1 on any mismatch or missing file. Add a docstring in the style of `tools/check-example-figures.py`. Register the two PNGs above as the first entries. Do not add it to ci.yml; that is a later change once pages exist.
