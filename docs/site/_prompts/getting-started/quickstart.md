# Page: getting-started/quickstart (Quick start)

Page type: `guide`. Section order: `2`. Wave: `3`.

## Purpose and audience

Eight commands from a TTF to a served preview, each with real output, in one directory. A reader who has installed the packages has a blob and a browser preview in ten minutes.

## Read first

1. `docs/site/ARCHITECTURE.md`, all of it. The rules below are copied from it and are binding.
2. Parent facts files, before opening any source: `_facts/getting-started/installation.md`, `_facts/authoring/project-file.md`, `_facts/cli/ps2ui.md`, `_facts/cli/previewer.md`. Reuse their fact ids; do not restate a parent fact differently. If one is wrong, write a `## disputes` section and stop.
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
| D5 | README.md "Previewing in a browser" | the serve option list omits `--uib` | Options: project positional, `--uib`, `--port`, `--screen`, `--theme`, `--no-watch`, `--selftest`. |
| D13 | README.md Quick start C snippet | `arena[1662]` | Blob-specific and target-specific. Quote the arena line from a bake in this session, with the command. The bake prints the EE figure; `ps2ui-check` prints the EE and 64-bit host figures. |

## Sources of truth

Line numbers are hints from the exploration that produced this brief; re-locate by symbol name. Authority order: code, tests, docs/*.md, README.md.

- docs/tutorial-uc3.md - blocks 1 (fontgen), 2-4 (the three heredocs), 5 (build), 6 (check), 7 (serve --selftest); these are executed by CI so their `text` blocks are trustworthy
- tools/check-tutorial.py - `ASSERTED_BLOCKS` and the shim table
- packages/baker/ps2ui_bake/ps2ui.py - the build/check/serve subcommands

## Claims to verify, and how

Each item is `claim -> how to prove it`. Run every command. Paste real output into the page where the structure calls for it and record the result in the facts file.

1. Every command runs from an empty directory and prints the output shown -> run all eight blocks in a scratch directory under `sh -e` with `TTF_REGULAR`/`TTF_BOLD` pointed at fonts/vendor; paste each output
2. `ps2ui build` prints the arena line -> paste it from the run; the number on the page is this run's
3. `ps2ui check` prints TAP ending in `PASS:` -> paste the trailer
4. `ps2ui serve --selftest` asserts the served frame equals `--preview` -> paste the two `ok -` lines and `PASS: 6 route(s)`
5. `ps2ui serve` binds 127.0.0.1 on 8080 or the next free port -> run it, paste the URL line, then stop it

## Screenshots

Each line is `path <- command // alt text`. Register every file in `assets/assets.json` with the exact command (`OUT` for the output path) and `checked: true` unless the line says otherwise. Previewer renders only; Playwright only where the line says so.

- assets/getting-started/quickstart/preview.png <- the `build/preview.png` the quick start writes (copy; command is the `ps2ui build` line) // the library screen, initial focus, theme 0, 1:1
- assets/getting-started/quickstart/serve.png <- Playwright: `ps2ui serve` on the scratch project, viewport 1280x800, wait for `#frame` to load, full-page screenshot; `checked: false` // the ps2ui serve page showing the library screen with the inspector panels

## Page structure

Skeleton for type `guide`: What it is · Minimal example · Reference table · Behaviour · Limits and errors · Related pages.

Guide skeleton collapsed to: What you get (2 sentences) · the eight steps, each a heading with the command, its output, and one sentence on what it did · Next (three links). No reference table.

Frontmatter:

```yaml
---
id: getting-started/quickstart
title: Quick start
description: <one sentence>
section: getting-started
order: 2
version: 0.6.0
sources: [<every repository path opened>]
---
```

## Cross-links

Write links as `[text](page:<id>#<anchor>)`. Every id below must appear on the page at the place named.

- getting-started/tutorial-game-browser - Next
- authoring/project-file - step 4
- cli/previewer - step 8
- getting-started/installation - What you get

## Facts to emit

Write `_facts/<page-id>.md` before writing the page:

```markdown
# facts: <page-id>

| id | fact | source | verified by | status |
|---|---|---|---|---|
```

Status is `verified` (a command or test in this session proved it), `code-only` (read in source; say why nothing executable exists), or `contradicts-readme` (verified, and README.md says otherwise; cite the README line). If a parent fact is wrong, append `## disputes` with the id and evidence, and stop.

Required ids (downstream pages read these by name):

- `quickstart.outputs` - the arena line, the check trailer, the selftest lines from this run

## Out of scope

- explaining each HTML attribute -> getting-started/tutorial-game-browser and authoring/*
- the C side -> runtime/frame-loop

## Done when

- [ ] Environment block ran clean.
- [ ] `_facts/getting-started/quickstart.md` exists with every fact id listed under "Facts to emit", each with a status.
- [ ] Every command shown on the page was run in this session; every output block is pasted from that run.
- [ ] Every screenshot listed exists under `assets/getting-started/quickstart/`, is registered in `assets/assets.json` with its command, and has alt text.
- [ ] Frontmatter present: `id: getting-started/quickstart`, `title`, `description`, `section`, `order: 2`, `version: 0.6.0`, `sources` (every path opened).
- [ ] Every `page:` link names an id from the page index in ARCHITECTURE.md.
- [ ] Word count of prose is 300 to 1500 (`pandoc -t plain` or a `wc -w` after stripping tables and code).
- [ ] Forbidden-phrase grep over the page returns nothing.
- [ ] Nothing from the drift rows' "claim" column appears on the page.
- [ ] Sections appear in the order given under Page structure and every table has the named columns.
