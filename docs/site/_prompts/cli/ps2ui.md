# Page: cli/ps2ui (ps2ui)

Page type: `cli`. Section order: `30`. Wave: `1`.

## Purpose and audience

The umbrella command: every subcommand, its options, which project keys it forwards, what it writes and where, its exit codes, and how it finds the layout compiler. Deep detail lives on the per-tool pages.

## Read first

1. `docs/site/ARCHITECTURE.md`, all of it. The rules below are copied from it and are binding.
2. Parent facts files, before opening any source: `_facts/authoring/project-file.md`, `_facts/cli/ps2ui-layout.md`, `_facts/cli/ps2ui-bake.md`, `_facts/cli/ps2ui-check.md`, `_facts/cli/ps2ui-fontgen.md`. Reuse their fact ids; do not restate a parent fact differently. If one is wrong, write a `## disputes` section and stop.
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
| D9 | packages/layout/bin/ps2ui-dev.js comment; ps2ui.py `cmd_dev` | `ps2ui dev` honours `--strict` and `--min-font-size` | Both are set on `options` while `src/index.js` reads lint overrides from `options.lint` only. Accepted and inert. Document as a limit until the code fix lands. |
| D10 | packages/baker/ps2ui_bake/serve.py `prog="ps2ui-serve"` | a `ps2ui-serve` command | Not installed. The command is `ps2ui serve`. |

## Sources of truth

Line numbers are hints from the exploration that produced this brief; re-locate by symbol name. Authority order: code, tests, docs/*.md, README.md.

- packages/baker/ps2ui_bake/ps2ui.py - the whole file: parser (~336-425), cmd_build, cmd_check, cmd_fontgen, serve options (~385-397), vendor-runtime, cmd_dev, pick_screen, layout discovery (~36-57), error path (~429-433)
- packages/baker/pyproject.toml [project.scripts]
- packages/baker/tests/test_baker.py TestConsoleScriptVersions, TestProjectFile; tests/test_serve.py TestImportRule, TestDevAgreesWithBuild

## Claims to verify, and how

Each item is `claim -> how to prove it`. Run every command. Paste real output into the page where the structure calls for it and record the result in the facts file.

1. `ps2ui --version` prints the package version -> run and paste
2. Subcommands: build, check, fontgen, serve, vendor-runtime, dev; a bare `ps2ui` exits 2 -> run `ps2ui`; run `ps2ui <sub> --help` for each and paste
3. build forwards --fonts --mode --canvas --display-aspect --strict --min-font-size --focus-wrap to layout and -o --fonts --palettize-images --vram-budget to bake; check forwards --vram-budget and --strict; dev forwards the layout set plus --palettize-images --once -> read the three argv builders
4. Files: build writes `build/<stem>.json` per screen, `build/ui.uib`, the PNGs; dev writes `build/dev/`; serve writes `build/serve/` -> run each on memcard and `find build`
5. `ps2ui check` never builds; a missing blob is an error naming `ps2ui build` -> delete the blob and run
6. `-o` on build moves intermediates -> cite project.out-override
7. Layout discovery: PS2UI_LAYOUT, PATH, checkout, else an npm install message -> run with `PS2UI_LAYOUT=/bin/false`
8. Exit codes: 1 on ProjectError with `ps2ui: ` prefix; otherwise the tool's code -> read main
9. `ps2ui dev --strict`/`--min-font-size` are inert (D9) -> cite dev.inert-flags from crt-linter if already emitted, else verify by running dev --once on opl-env

## Screenshots

None. Do not add decorative images.

## Page structure

Skeleton for type `cli`: Synopsis · Options · Output · Exit codes · Files written · Related pages.

CLI skeleton, once per subcommand under one H2 each: Synopsis, Options table (flag · argument · default · effect), Output, Exit codes, Files written. Then 'How build finds the compiler', then 'From a checkout' (table: command · checkout spelling). Related pages.

Frontmatter:

```yaml
---
id: cli/ps2ui
title: ps2ui
description: <one sentence>
section: cli
order: 30
version: 0.6.0
sources: [<every repository path opened>]
---
```

## Cross-links

Write links as `[text](page:<id>#<anchor>)`. Every id below must appear on the page at the place named.

- cli/ps2ui-layout - build, dev
- cli/ps2ui-bake - build
- cli/ps2ui-check - check
- cli/ps2ui-fontgen - fontgen
- cli/previewer - serve
- runtime/integrating - vendor-runtime
- authoring/project-file - every subcommand

## Facts to emit

Write `_facts/<page-id>.md` before writing the page:

```markdown
# facts: <page-id>

| id | fact | source | verified by | status |
|---|---|---|---|---|
```

Status is `verified` (a command or test in this session proved it), `code-only` (read in source; say why nothing executable exists), or `contradicts-readme` (verified, and README.md says otherwise; cite the README line). If a parent fact is wrong, append `## disputes` with the id and evidence, and stop.

Required ids (downstream pages read these by name):

- `cli.ps2ui.subcommands` - options per subcommand
- `cli.ps2ui.forwarding` - key to flag per subcommand
- `cli.ps2ui.files` - output paths
- `cli.ps2ui.checkout` - the spelling table

## Out of scope

- the serve page in depth -> cli/previewer
- vendor-runtime in depth -> runtime/integrating

## Done when

- [ ] Environment block ran clean.
- [ ] `_facts/cli/ps2ui.md` exists with every fact id listed under "Facts to emit", each with a status.
- [ ] Every command shown on the page was run in this session; every output block is pasted from that run.
- [ ] Every screenshot listed exists under `assets/cli/ps2ui/`, is registered in `assets/assets.json` with its command, and has alt text.
- [ ] Frontmatter present: `id: cli/ps2ui`, `title`, `description`, `section`, `order: 30`, `version: 0.6.0`, `sources` (every path opened).
- [ ] Every `page:` link names an id from the page index in ARCHITECTURE.md.
- [ ] Word count of prose is 300 to 1500 (`pandoc -t plain` or a `wc -w` after stripping tables and code).
- [ ] Forbidden-phrase grep over the page returns nothing.
- [ ] Nothing from the drift rows' "claim" column appears on the page.
- [ ] Sections appear in the order given under Page structure and every table has the named columns.
