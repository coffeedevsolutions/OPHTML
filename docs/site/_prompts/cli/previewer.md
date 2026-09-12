# Page: cli/previewer (Previewer)

Page type: `cli`. Section order: `35`. Wave: `2`.

## Purpose and audience

`ps2ui serve` in depth: options, the page's controls, the HTTP routes, the blob inspector, the self-test, port and output rules, and the stated limits.

## Read first

1. `docs/site/ARCHITECTURE.md`, all of it. The rules below are copied from it and are binding.
2. Parent facts files, before opening any source: `_facts/cli/ps2ui.md`, `_facts/authoring/project-file.md`, `_facts/authoring/focus-and-navigation.md`, `_facts/authoring/theming.md`. Reuse their fact ids; do not restate a parent fact differently. If one is wrong, write a `## disputes` section and stop.
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
| D10 | packages/baker/ps2ui_bake/serve.py `prog="ps2ui-serve"` | a `ps2ui-serve` command | Not installed. The command is `ps2ui serve`. |

## Sources of truth

Line numbers are hints from the exploration that produced this brief; re-locate by symbol name. Authority order: code, tests, docs/*.md, README.md.

- packages/baker/ps2ui_bake/serve.py - bind (~651-666), routes (~594-648), snapshot/apply (~481-544), watcher (~547-589), selftest (~741-800), build_server (~698-723), pipeline output override (~330-336)
- packages/baker/ps2ui_bake/serve_page.html - toolbar (~122-137), panels (~142-173), keys (~683-706), slot boxes (~604-613), polling (~714)
- packages/baker/ps2ui_bake/ps2ui.py ~373-397 - the option list and why it is duplicated
- packages/baker/tests/test_serve.py - every class
- docs/tutorial-uc3.md step 7 and README 'What it will not tell you' - the stated limits; restate

## Claims to verify, and how

Each item is `claim -> how to prove it`. Run every command. Paste real output into the page where the structure calls for it and record the result in the facts file.

1. Options -> `ps2ui serve --help`
2. Routes: /, /frame.png, /montage.png, /state, /rev, /input (POST) with types; 404 JSON; 400 on bad input -> start a server on memcard, curl each route with -i, paste status and content-type; POST a bad body
3. Controls: arrows, screen/theme/aspect/zoom selects, toggles, keys f/Esc/g/s/b/n/[/], slot boxes with maxLength, click to inspect -> read the page; verify each by Playwright where cheap, else `code-only`
4. --uib skips Node and watching; --screen/--theme validated against the blob -> run `--uib` with a bad screen name and paste
5. --selftest asserts routes and byte-identity with --preview -> run and paste
6. Port 8080 wandering to 8099 unless --port; 127.0.0.1 only; build/serve/ output; 250 ms poll; watch debounce -> read serve.py; start two servers and paste both URL lines
7. A build error keeps the last frame and shows a banner -> break the CSS while serving, capture, fix
8. Limits: no runtime visibility, no composite, no hardware faults -> restate from sources; cite serve.limits

## Screenshots

Each line is `path <- command // alt text`. Register every file in `assets/assets.json` with the exact command (`OUT` for the output path) and `checked: true` unless the line says otherwise. Previewer renders only; Playwright only where the line says so.

- assets/cli/previewer/page.png <- Playwright default page on memcard; `checked: false` // the previewer with the library screen and both panels
- assets/cli/previewer/inspector.png <- click a panel, capture // a command selected in the inspector
- assets/cli/previewer/aspect-16x9.png <- force 16:9 // the memcard screen forced to 16:9
- assets/cli/previewer/error-banner.png <- CSS typo while watching // the error banner over the last good frame

## Page structure

Skeleton for type `cli`: Synopsis · Options · Output · Exit codes · Files written · Related pages.

CLI skeleton. Output section holds three tables: controls (control · drives), routes (route · method · type · purpose), limits (cannot show · why). Related pages.

Frontmatter:

```yaml
---
id: cli/previewer
title: Previewer
description: <one sentence>
section: cli
order: 35
version: 0.6.0
sources: [<every repository path opened>]
---
```

## Cross-links

Write links as `[text](page:<id>#<anchor>)`. Every id below must appear on the page at the place named.

- cli/ps2ui - serve subcommand
- cli/ps2ui-check - check then inspect
- authoring/theming - theme menu
- authoring/video-modes - aspect menu
- authoring/dynamic-text - slot boxes
- runtime/moving-and-hiding - visibility not shown
- runtime/first-boot - hardware faults

## Facts to emit

Write `_facts/<page-id>.md` before writing the page:

```markdown
# facts: <page-id>

| id | fact | source | verified by | status |
|---|---|---|---|---|
```

Status is `verified` (a command or test in this session proved it), `code-only` (read in source; say why nothing executable exists), or `contradicts-readme` (verified, and README.md says otherwise; cite the README line). If a parent fact is wrong, append `## disputes` with the id and evidence, and stop.

Required ids (downstream pages read these by name):

- `serve.routes`
- `serve.controls`
- `serve.limits`
- `serve.ports` - binding rules

## Out of scope

- the renderer internals -> project/internals

## Done when

- [ ] Environment block ran clean.
- [ ] `_facts/cli/previewer.md` exists with every fact id listed under "Facts to emit", each with a status.
- [ ] Every command shown on the page was run in this session; every output block is pasted from that run.
- [ ] Every screenshot listed exists under `assets/cli/previewer/`, is registered in `assets/assets.json` with its command, and has alt text.
- [ ] Frontmatter present: `id: cli/previewer`, `title`, `description`, `section`, `order: 35`, `version: 0.6.0`, `sources` (every path opened).
- [ ] Every `page:` link names an id from the page index in ARCHITECTURE.md.
- [ ] Word count of prose is 300 to 1500 (`pandoc -t plain` or a `wc -w` after stripping tables and code).
- [ ] Forbidden-phrase grep over the page returns nothing.
- [ ] Nothing from the drift rows' "claim" column appears on the page.
- [ ] Sections appear in the order given under Page structure and every table has the named columns.
