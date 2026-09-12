# Page: authoring/crt-linter (CRT linter)

Page type: `guide`. Section order: `21`. Wave: `1`.

## Purpose and audience

Every lint rule with threshold, message and opt-out; how contrast is computed; what `--strict` does; the one CLI threshold; per-theme linting; and the baker-side CRT warnings with their exact-count flags.

## Read first

1. `docs/site/ARCHITECTURE.md`, all of it. The rules below are copied from it and are binding.
2. Parent facts files, before opening any source: `_facts/cli/ps2ui-layout.md`, `_facts/cli/ps2ui-check.md`, `_facts/authoring/css.md`. Reuse their fact ids; do not restate a parent fact differently. If one is wrong, write a `## disputes` section and stop.
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
| D7 | README.md "Supported CSS" | the property list | Missing: `opacity`, `min-*`/`max-*`, `align-self`, `flex` shorthand, `row-gap`, `column-gap`, `:root` custom properties, `var()`, `@theme`, `data-nocontrast`, capacity default 63, the `name` attribute, `--min-font-size`. Overstated: `border-radius` takes one px value; named colours are eight; keyword-valued properties are unvalidated; the `:focus` geometry guard does not cover `letter-spacing`, `font-weight`, `text-align`, `text-overflow`; no `white-space: pre`; `&nbsp;` collapses to a space. |
| D9 | packages/layout/bin/ps2ui-dev.js comment; ps2ui.py `cmd_dev` | `ps2ui dev` honours `--strict` and `--min-font-size` | Both are set on `options` while `src/index.js` reads lint overrides from `options.lint` only. Accepted and inert. Document as a limit until the code fix lands. |

## Sources of truth

Line numbers are hints from the exploration that produced this brief; re-locate by symbol name. Authority order: code, tests, docs/*.md, README.md.

- packages/layout/src/lint.js - DEFAULTS (~12-27), SAFE_SYMBOL_RANGES (~50-56), coexists (~87-101), contrast (~120-131, ~229-265), each rule (~154-282)
- packages/layout/src/index.js ~219-236, ~272 - lint options, per-theme, dedup
- packages/layout/bin/ps2ui-layout.js ~52-56, ~73-79, ~106-109 - --strict, --min-font-size
- packages/layout/src/box.js ~190-193 - data-nocontrast
- packages/baker/ps2ui_bake/check.py ~520-592 - check_crt and _declared_count
- packages/layout/test/layout.test.js lint cases; test_baker.py TestCheck

## Claims to verify, and how

Each item is `claim -> how to prove it`. Run every command. Paste real output into the page where the structure calls for it and record the result in the facts file.

1. The rule table: aspect-distortion, interlace-flicker, ntsc-red-bleed, min-font-size (14), overscan (5% inset), charset, contrast (3.0, composited, black and white brackets when translucent), focus-target-size (24), overscan for focusables -> read lint.js; compile a scratch screen that trips each and paste the messages
2. `--strict` promotes every warning; there is no per-rule strictness -> read the CLI
3. `--min-font-size` is the only CLI threshold; `data-nocontrast` is the only per-rule opt-out and does not cascade -> compile with `--min-font-size 20` on the tutorial screen and paste the count
4. Lints run per theme; geometry lints dedup, colour lints do not -> cite layout.test.js cases
5. `ps2ui-check` CRT warnings: 1px quads, dead commands, undrawn textures; `--allow-dead N`/`--allow-hairline N` are exact counts -> run `ps2ui-check --strict --allow-hairline 1` on memcard and paste the failure
6. `ps2ui dev` accepts --strict and --min-font-size without effect (D9) -> run `ps2ui dev --once` on opl-env and compare warning counts with `ps2ui build`; document as a limit

## Screenshots

Each line is `path <- command // alt text`. Register every file in `assets/assets.json` with the exact command (`OUT` for the output path) and `checked: true` unless the line says otherwise. Previewer renders only; Playwright only where the line says so.

- assets/authoring/crt-linter/warning.png <- Playwright: serve a scratch project with a lint warning, click the warning so the inspector jumps to the command, capture; `checked: false` // the previewer with a lint warning selected and its command highlighted

## Page structure

Skeleton for type `guide`: What it is · Minimal example · Reference table · Behaviour · Limits and errors · Related pages.

Guide skeleton. Minimal example: one warning line and the fix. Reference table columns: rule · threshold · message · opt-out. Table 2: baker-side checks (label · severity · flag). Behaviour: contrast, strict, per theme. Limits.

Frontmatter:

```yaml
---
id: authoring/crt-linter
title: CRT linter
description: <one sentence>
section: authoring
order: 21
version: 0.6.0
sources: [<every repository path opened>]
---
```

## Cross-links

Write links as `[text](page:<id>#<anchor>)`. Every id below must appear on the page at the place named.

- cli/ps2ui-layout - flags
- cli/ps2ui-check - CRT checks
- authoring/video-modes - distortion
- authoring/css - colours
- reference/diagnostics - every message

## Facts to emit

Write `_facts/<page-id>.md` before writing the page:

```markdown
# facts: <page-id>

| id | fact | source | verified by | status |
|---|---|---|---|---|
```

Status is `verified` (a command or test in this session proved it), `code-only` (read in source; say why nothing executable exists), or `contradicts-readme` (verified, and README.md says otherwise; cite the README line). If a parent fact is wrong, append `## disputes` with the id and evidence, and stop.

Required ids (downstream pages read these by name):

- `lint.rules` - the table
- `lint.strict` - all or nothing
- `lint.thresholds` - which are CLI-settable
- `check.crt.exact-count` - allow flags semantics
- `dev.inert-flags` - the D9 limit

## Out of scope

- the full message index -> reference/diagnostics

## Done when

- [ ] Environment block ran clean.
- [ ] `_facts/authoring/crt-linter.md` exists with every fact id listed under "Facts to emit", each with a status.
- [ ] Every command shown on the page was run in this session; every output block is pasted from that run.
- [ ] Every screenshot listed exists under `assets/authoring/crt-linter/`, is registered in `assets/assets.json` with its command, and has alt text.
- [ ] Frontmatter present: `id: authoring/crt-linter`, `title`, `description`, `section`, `order: 21`, `version: 0.6.0`, `sources` (every path opened).
- [ ] Every `page:` link names an id from the page index in ARCHITECTURE.md.
- [ ] Word count of prose is 300 to 1500 (`pandoc -t plain` or a `wc -w` after stripping tables and code).
- [ ] Forbidden-phrase grep over the page returns nothing.
- [ ] Nothing from the drift rows' "claim" column appears on the page.
- [ ] Sections appear in the order given under Page structure and every table has the named columns.
