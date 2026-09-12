# Page: examples/memcard (memcard)

Page type: `example`. Section order: `60`. Wave: `3`.

## Purpose and audience

What the `memcard` example demonstrates, how to build and check it, the numbers its blob carries, and which files to read first. Covers: the smallest example: two screens, slots, a montage; the runtime tests run over its blob.

## Read first

1. `docs/site/ARCHITECTURE.md`, all of it. The rules below are copied from it and are binding.
2. Parent facts files, before opening any source: `_facts/authoring/project-file.md`, `_facts/cli/ps2ui.md`, `_facts/cli/ps2ui-check.md`, `_facts/authoring/dynamic-text.md`, `_facts/authoring/lists.md`. Reuse their fact ids; do not restate a parent fact differently. If one is wrong, write a `## disputes` section and stop.
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

- examples/memcard/ - every file: ps2ui.json, build.sh, ui/*, screenshots/
- tools/check-blobs.sh - the flags CI checks this blob with
- runtime/Makefile test target - runs over this blob
- .github/workflows/ci.yml - the step that builds it

## Claims to verify, and how

Each item is `claim -> how to prove it`. Run every command. Paste real output into the page where the structure calls for it and record the result in the facts file.

1. `./examples/memcard/build.sh` builds, tests and refreshes screenshots -> run it and paste the last lines
2. The blob's numbers (screens, commands, textures, slots, arena) -> run `ps2ui-check examples/memcard/build/ui.uib` and paste the trailer and arena note
3. The mechanisms table: each mechanism names the file and line where the example uses it -> grep the ui/ files
4. check-blobs.sh flags for this blob -> read and paste
5. Committed screenshots match the renderer -> `git diff --exit-code examples/memcard/screenshots`
6. The runtime tests run over this blob -> `make -C runtime test` tail

## Screenshots

Each line is `path <- command // alt text`. Register every file in `assets/assets.json` with the exact command (`OUT` for the output path) and `checked: true` unless the line says otherwise. Previewer renders only; Playwright only where the line says so.

- assets/examples/memcard/<screen>[-theme-N].png <- `preview.render` per screen (per theme where n_theme > 1) // <screen>, theme N
- assets/examples/memcard/states.png <- `preview.montage` // every focus state

## Page structure

Skeleton for type `example`: Screenshots · What it demonstrates · Build and check · Numbers from the blob · Source tour · Start from this.

Example skeleton. Screenshots strip first. 'What it demonstrates' table: mechanism · where. 'Build and check' with real output. 'Numbers from the blob' as a table from the check trailer. 'Source tour': three to six file pointers with one sentence each. 'Start from this': what to copy and what to replace.

Frontmatter:

```yaml
---
id: examples/memcard
title: memcard
description: <one sentence>
section: examples
order: 60
version: 0.6.0
sources: [<every repository path opened>]
---
```

## Cross-links

Write links as `[text](page:<id>#<anchor>)`. Every id below must appear on the page at the place named.

- authoring/project-file - the project file
- cli/ps2ui-check - numbers
- runtime/first-boot - probe (channel6)
- authoring/screens-and-overlays - overlays
- authoring/theming - themes (opl-env)
- runtime/streaming-art - covers (opl-env, channel6)
- authoring/lists - rows

## Facts to emit

Write `_facts/<page-id>.md` before writing the page:

```markdown
# facts: <page-id>

| id | fact | source | verified by | status |
|---|---|---|---|---|
```

Status is `verified` (a command or test in this session proved it), `code-only` (read in source; say why nothing executable exists), or `contradicts-readme` (verified, and README.md says otherwise; cite the README line). If a parent fact is wrong, append `## disputes` with the id and evidence, and stop.

Required ids (downstream pages read these by name):

- `example.memcard.numbers` - the trailer values
- `example.memcard.mechanisms` - the table

## Out of scope

- explaining mechanisms -> the authoring pages

## Done when

- [ ] Environment block ran clean.
- [ ] `_facts/examples/memcard.md` exists with every fact id listed under "Facts to emit", each with a status.
- [ ] Every command shown on the page was run in this session; every output block is pasted from that run.
- [ ] Every screenshot listed exists under `assets/examples/memcard/`, is registered in `assets/assets.json` with its command, and has alt text.
- [ ] Frontmatter present: `id: examples/memcard`, `title`, `description`, `section`, `order: 60`, `version: 0.6.0`, `sources` (every path opened).
- [ ] Every `page:` link names an id from the page index in ARCHITECTURE.md.
- [ ] Word count of prose is 300 to 1500 (`pandoc -t plain` or a `wc -w` after stripping tables and code).
- [ ] Forbidden-phrase grep over the page returns nothing.
- [ ] Nothing from the drift rows' "claim" column appears on the page.
- [ ] Sections appear in the order given under Page structure and every table has the named columns.
