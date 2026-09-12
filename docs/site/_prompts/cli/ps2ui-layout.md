# Page: cli/ps2ui-layout (ps2ui-layout and ps2ui-dev)

Page type: `cli`. Section order: `31`. Wave: `0`.

## Purpose and audience

The compiler and the watch loop: options, exit codes, output lines, the mode table, font resolution, what `ps2ui-dev` writes, and the known inert flags.

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
| D9 | packages/layout/bin/ps2ui-dev.js comment; ps2ui.py `cmd_dev` | `ps2ui dev` honours `--strict` and `--min-font-size` | Both are set on `options` while `src/index.js` reads lint overrides from `options.lint` only. Accepted and inert. Document as a limit until the code fix lands. |

## Sources of truth

Line numbers are hints from the exploration that produced this brief; re-locate by symbol name. Authority order: code, tests, docs/*.md, README.md.

- packages/layout/bin/ps2ui-layout.js - usage, switch table (~40-62), MODES use (~66-86), exit paths (~63-113)
- packages/layout/bin/ps2ui-dev.js - switch table (~51-82), the spawn (~104-138), output lines, watch (~157-171)
- packages/layout/src/index.js ~219 - options.lint; ~64-113 fromDir/fromManifest
- packages/layout/src/aspect.js ~47-52 - MODES
- packages/layout/package.json - bin, scripts.test
- packages/layout/test/cli.test.js, fonts.test.js

## Claims to verify, and how

Each item is `claim -> how to prove it`. Run every command. Paste real output into the page where the structure calls for it and record the result in the facts file.

1. Options for ps2ui-layout: -o (required), --canvas, --mode, --display-aspect, --font-dir, --fonts, --focus-wrap, --strict, --min-font-size, -h, -V -> run `--help` and paste; run `npm test` in packages/layout and paste the summary
2. Exit 2 for usage errors, 1 for compile errors and for --strict with warnings, 0 otherwise -> run without -o; run --strict on a screen with a warning
3. Output lines: `warning: ...`, `ps2ui-layout: N paint commands, N focusables -> out`, `--strict: N warning(s)` -> paste from runs
4. -o creates its directory; IR is written with indent 1 -> run into a missing dir
5. --font-dir uses fixed filenames default.metrics.json and default-bold.metrics.json; --fonts takes a manifest -> cite fonts.test.js
6. ps2ui-dev: -o is a directory; writes <stem>.json, ui.uib, preview.png, states.png with --montage; --once exits with the build status; 120 ms debounce -> run `ps2ui-dev ... -o /tmp/d --once` and list
7. ps2ui-dev --strict and --min-font-size are inert (D9) -> run dev --once with --min-font-size 40 on the memcard screen and show no new warnings; state as a limit

## Screenshots

None. Do not add decorative images.

## Page structure

Skeleton for type `cli`: Synopsis · Options · Output · Exit codes · Files written · Related pages.

CLI skeleton twice (ps2ui-layout, then ps2ui-dev). Mode table under Options. Related pages.

Frontmatter:

```yaml
---
id: cli/ps2ui-layout
title: ps2ui-layout and ps2ui-dev
description: <one sentence>
section: cli
order: 31
version: 0.6.0
sources: [<every repository path opened>]
---
```

## Cross-links

Write links as `[text](page:<id>#<anchor>)`. Every id below must appear on the page at the place named.

- authoring/video-modes - modes
- authoring/crt-linter - --strict, --min-font-size
- authoring/text-and-fonts - --fonts
- authoring/focus-and-navigation - --focus-wrap
- reference/ir-format - the output
- cli/ps2ui - build and dev wrappers

## Facts to emit

Write `_facts/<page-id>.md` before writing the page:

```markdown
# facts: <page-id>

| id | fact | source | verified by | status |
|---|---|---|---|---|
```

Status is `verified` (a command or test in this session proved it), `code-only` (read in source; say why nothing executable exists), or `contradicts-readme` (verified, and README.md says otherwise; cite the README line). If a parent fact is wrong, append `## disputes` with the id and evidence, and stop.

Required ids (downstream pages read these by name):

- `cli.layout.options` - the table
- `cli.layout.exit-codes`
- `cli.layout.output-lines`
- `cli.dev.files` - what dev writes
- `cli.dev.inert-flags` - the D9 limit with evidence
- `modes.table` - from aspect.js

## Out of scope

- what the IR contains -> reference/ir-format
- the lint rules -> authoring/crt-linter

## Done when

- [ ] Environment block ran clean.
- [ ] `_facts/cli/ps2ui-layout.md` exists with every fact id listed under "Facts to emit", each with a status.
- [ ] Every command shown on the page was run in this session; every output block is pasted from that run.
- [ ] Every screenshot listed exists under `assets/cli/ps2ui-layout/`, is registered in `assets/assets.json` with its command, and has alt text.
- [ ] Frontmatter present: `id: cli/ps2ui-layout`, `title`, `description`, `section`, `order: 31`, `version: 0.6.0`, `sources` (every path opened).
- [ ] Every `page:` link names an id from the page index in ARCHITECTURE.md.
- [ ] Word count of prose is 300 to 1500 (`pandoc -t plain` or a `wc -w` after stripping tables and code).
- [ ] Forbidden-phrase grep over the page returns nothing.
- [ ] Nothing from the drift rows' "claim" column appears on the page.
- [ ] Sections appear in the order given under Page structure and every table has the named columns.
