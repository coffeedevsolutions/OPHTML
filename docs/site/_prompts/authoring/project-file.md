# Page: authoring/project-file (The project file)

Page type: `guide`. Section order: `10`. Wave: `0`.

## Purpose and audience

Every `ps2ui.json` key, its type, default and which tool it reaches; how paths resolve; the per-screen object form; what `-o` does to intermediates; what the loader refuses.

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

## Sources of truth

Line numbers are hints from the exploration that produced this brief; re-locate by symbol name. Authority order: code, tests, docs/*.md, README.md.

- packages/baker/ps2ui_bake/project.py - `DEFAULTS` (lines ~39-55), `SCREEN_DEFAULTS` (~59), `_attr`, path resolution (~79-136), `ir_path`, `set_out_override` (~162-176), `load` and its refusals (~189-224)
- packages/baker/ps2ui_bake/ps2ui.py - `compile_screens` (~83-115) and `bake_argv` (~135-142): which keys become which flags; `cmd_check` (~170-215): which keys reach the checker
- examples/memcard/ps2ui.json, examples/opl-env/ps2ui.json, examples/channel6/ps2ui.json - real files
- packages/baker/tests/test_baker.py `TestProjectFile` - every behaviour below has a test

## Claims to verify, and how

Each item is `claim -> how to prove it`. Run every command. Paste real output into the page where the structure calls for it and record the result in the facts file.

1. The key table (screens, css, fonts, out, preview, montage, previewDisplay, mode, canvas, displayAspect, strict, minFontSize, focusWrap, palettizeImages, vramBudget) with defaults -> read `DEFAULTS`; run `python3 -m unittest tests.test_baker.TestProjectFile -v` and paste the summary line
2. `vramBudget` and `strict` reach `ps2ui check` (new in 0.6.0) -> run `TestProjectFile.test_every_project_key_the_checker_accepts_actually_reaches_it`; cite CHANGELOG 0.6.0
3. Unknown keys are refused by name with the accepted list -> write a project with `"colour": 1`, run `ps2ui build`, paste the error
4. Paths resolve against the project file's directory, not the cwd -> run `ps2ui build examples/memcard/ps2ui.json` from the repo root and list `examples/memcard/build/`
5. `fonts` falls back to `fonts/fonts.json` beside the project when it exists, else the baker's default -> read `fonts_path`; cite the tutorial project which has no `fonts` key
6. A screen may be a string or an object with `html`, `css`, `focusWrap` -> cite channel6's `probe.html` entry
7. `-o build/ui-16x9.uib` renames intermediates with the suffix -> run channel6's second build line and list `build/`
8. A directory argument means `<dir>/ps2ui.json` -> run `ps2ui check examples/memcard`

## Screenshots

None. Do not add decorative images.

## Page structure

Skeleton for type `guide`: What it is · Minimal example · Reference table · Behaviour · Limits and errors · Related pages.

Guide skeleton. Minimal example is the two-key file. Reference table columns: key · type · default · reaches (layout / bake / check / dev). Second table: per-screen keys. Behaviour: path resolution, `-o`, directory argument, `false` to suppress a preview. Limits and errors: the refusal list with real messages.

Frontmatter:

```yaml
---
id: authoring/project-file
title: The project file
description: <one sentence>
section: authoring
order: 10
version: 0.6.0
sources: [<every repository path opened>]
---
```

## Cross-links

Write links as `[text](page:<id>#<anchor>)`. Every id below must appear on the page at the place named.

- cli/ps2ui - reaches column header
- cli/ps2ui-layout - mode, canvas, displayAspect, focusWrap, strict, minFontSize
- cli/ps2ui-bake - out, preview, montage, previewDisplay, palettizeImages, vramBudget
- cli/ps2ui-check - strict, vramBudget
- authoring/video-modes - mode
- authoring/vram-budget - vramBudget

## Facts to emit

Write `_facts/<page-id>.md` before writing the page:

```markdown
# facts: <page-id>

| id | fact | source | verified by | status |
|---|---|---|---|---|
```

Status is `verified` (a command or test in this session proved it), `code-only` (read in source; say why nothing executable exists), or `contradicts-readme` (verified, and README.md says otherwise; cite the README line). If a parent fact is wrong, append `## disputes` with the id and evidence, and stop.

Required ids (downstream pages read these by name):

- `project.keys` - the full key table as rows key|type|default|reaches
- `project.screen-keys` - html, css, focusWrap
- `project.resolution` - relative to the project file; directory argument; fonts fallback order
- `project.out-override` - the suffix rule

## Out of scope

- what each flag does -> the cli/* pages
- the layout of build/ under serve and dev -> cli/ps2ui

## Done when

- [ ] Environment block ran clean.
- [ ] `_facts/authoring/project-file.md` exists with every fact id listed under "Facts to emit", each with a status.
- [ ] Every command shown on the page was run in this session; every output block is pasted from that run.
- [ ] Every screenshot listed exists under `assets/authoring/project-file/`, is registered in `assets/assets.json` with its command, and has alt text.
- [ ] Frontmatter present: `id: authoring/project-file`, `title`, `description`, `section`, `order: 10`, `version: 0.6.0`, `sources` (every path opened).
- [ ] Every `page:` link names an id from the page index in ARCHITECTURE.md.
- [ ] Word count of prose is 300 to 1500 (`pandoc -t plain` or a `wc -w` after stripping tables and code).
- [ ] Forbidden-phrase grep over the page returns nothing.
- [ ] Nothing from the drift rows' "claim" column appears on the page.
- [ ] Sections appear in the order given under Page structure and every table has the named columns.
