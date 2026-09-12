# Page: cli/ps2ui-fontgen (ps2ui-fontgen)

Page type: `cli`. Section order: `34`. Wave: `0`.

## Purpose and audience

Metrics from a TTF: the bare tool's argv and the `ps2ui fontgen` form, the Raqm refusal, the metrics JSON, the default charset, and regenerating the shipped metrics.

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

None recorded. If a README.md claim disagrees with what you verify, add it to the facts file with status `contradicts-readme`.

## Sources of truth

Line numbers are hints from the exploration that produced this brief; re-locate by symbol name. Authority order: code, tests, docs/*.md, README.md.

- packages/baker/ps2ui_bake/fontgen.py - argv (~259-294), refusal (~272-276), _raqm_remedy, build_metrics (~79-100), DEFAULT_CHARSET (~26-29), build_kerning
- packages/baker/ps2ui_bake/ps2ui.py ~218-243 - the wrapper's three outputs
- fonts/regen.sh; fonts/fonts.json; fonts/default.metrics.json
- packages/baker/tests/test_baker.py TestFontgenRefusesWithoutRaqm, TestKerningExtraction

## Claims to verify, and how

Each item is `claim -> how to prove it`. Run every command. Paste real output into the page where the structure calls for it and record the result in the facts file.

1. Bare argv: `<ttf> <family> <weight> <out> [charset-file]`; fewer than four is exit 2; --version/-V -> run with no args and paste
2. `ps2ui fontgen <regular> <bold> [-o dir]` writes default.metrics.json, default-bold.metrics.json, fonts.json with absolute TTF paths -> run on fonts/vendor into a temp dir and list; paste the three stderr lines
3. Without Raqm it exits 2 before writing; the remedy checks fribidi separately -> cite the test; quote the remedy from source, `code-only` if this machine has Raqm
4. Metrics fields: family, weight, unitsPerEm, ascent, descent, advances, kerning, missing, source -> print the keys of default.metrics.json
5. Kerning is measured with substitutions disabled -> cite fontgen.py
6. regen.sh reads fonts.json and reproduces the committed files byte for byte -> run and git diff

## Screenshots

None. Do not add decorative images.

## Page structure

Skeleton for type `cli`: Synopsis · Options · Output · Exit codes · Files written · Related pages.

CLI skeleton twice (bare tool, then the wrapper). Metrics field table under Output. Related pages.

Frontmatter:

```yaml
---
id: cli/ps2ui-fontgen
title: ps2ui-fontgen
description: <one sentence>
section: cli
order: 34
version: 0.6.0
sources: [<every repository path opened>]
---
```

## Cross-links

Write links as `[text](page:<id>#<anchor>)`. Every id below must appear on the page at the place named.

- authoring/text-and-fonts - what the metrics drive
- getting-started/installation - Raqm
- authoring/project-file - fonts key

## Facts to emit

Write `_facts/<page-id>.md` before writing the page:

```markdown
# facts: <page-id>

| id | fact | source | verified by | status |
|---|---|---|---|---|
```

Status is `verified` (a command or test in this session proved it), `code-only` (read in source; say why nothing executable exists), or `contradicts-readme` (verified, and README.md says otherwise; cite the README line). If a parent fact is wrong, append `## disputes` with the id and evidence, and stop.

Required ids (downstream pages read these by name):

- `fontgen.argv` - both forms
- `fontgen.metrics-schema` - the fields
- `fontgen.outputs` - the wrapper's three files
- `fontgen.raqm` - refusal and remedy summary

## Out of scope

- measuring and kerning -> authoring/text-and-fonts

## Done when

- [ ] Environment block ran clean.
- [ ] `_facts/cli/ps2ui-fontgen.md` exists with every fact id listed under "Facts to emit", each with a status.
- [ ] Every command shown on the page was run in this session; every output block is pasted from that run.
- [ ] Every screenshot listed exists under `assets/cli/ps2ui-fontgen/`, is registered in `assets/assets.json` with its command, and has alt text.
- [ ] Frontmatter present: `id: cli/ps2ui-fontgen`, `title`, `description`, `section`, `order: 34`, `version: 0.6.0`, `sources` (every path opened).
- [ ] Every `page:` link names an id from the page index in ARCHITECTURE.md.
- [ ] Word count of prose is 300 to 1500 (`pandoc -t plain` or a `wc -w` after stripping tables and code).
- [ ] Forbidden-phrase grep over the page returns nothing.
- [ ] Nothing from the drift rows' "claim" column appears on the page.
- [ ] Sections appear in the order given under Page structure and every table has the named columns.
