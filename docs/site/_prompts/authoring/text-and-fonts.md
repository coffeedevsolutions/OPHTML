# Page: authoring/text-and-fonts (Text and fonts)

Page type: `guide`. Section order: `13`. Wave: `1`.

## Purpose and audience

How fonts reach the toolchain (`fonts.json`, two faces, metrics JSON), what glyphs exist, how text is measured (half-up rounding, kerning per size, spaces-only wrapping, ellipsis with `nowrap`), and how to regenerate the shipped metrics.

## Read first

1. `docs/site/ARCHITECTURE.md`, all of it. The rules below are copied from it and are binding.
2. Parent facts files, before opening any source: `_facts/cli/ps2ui-fontgen.md`, `_facts/authoring/css.md`. Reuse their fact ids; do not restate a parent fact differently. If one is wrong, write a `## disputes` section and stop.
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

## Sources of truth

Line numbers are hints from the exploration that produced this brief; re-locate by symbol name. Authority order: code, tests, docs/*.md, README.md.

- packages/layout/src/text.js - the whole pen: rounding (~34), kern lookup (~48-52), the single walk (~54-75), wrapText (~114-149), ellipsize (~160-180), resolveLineHeight (~183-187), missing glyph (~25-30)
- packages/layout/src/index.js - FontContext.fromManifest (~93-113), fromDir fixed filenames (~64-74), resolve(weight) >= 600 (~61-63)
- packages/baker/ps2ui_bake/fontgen.py - DEFAULT_CHARSET (~26-29), build_metrics (~79-100), NO_SUBSTITUTION
- packages/baker/ps2ui_bake/pen.py and rounding.py - the Python pen and `round_half_up`
- fonts/fonts.json, fonts/regen.sh, fonts/default.metrics.json
- packages/baker/tests/test_baker.py TestCrossLanguagePen, TestKerningPen, TestKernTable, TestRounding; packages/layout/test/layout.test.js text cases

## Claims to verify, and how

Each item is `claim -> how to prove it`. Run every command. Paste real output into the page where the structure calls for it and record the result in the facts file.

1. `fonts.json` schema: per face, `ttf` candidate list (first existing wins, `~` expands) and `metrics` -> read fonts.json and cli.py `load_font_manifest`
2. Weight >= 600 is bold; there is no weight axis -> read index.js; compile `font-weight: 500` and `700` and show which face each text command names
3. The shipped charset is 115 codepoints: 32-126 and a listed set of symbols -> load default.metrics.json and print sorted keys; list the ranges
4. A missing glyph takes the `?` advance in layout and the `?` glyph in the baker -> cite text.js and test_baker `test_a_codepoint_with_no_glyph_falls_back_to_question_mark`
5. Advance = floor(units*size/1000 + 0.5); kerns round independently by the same rule; `To` at -170 units is -5px at 32px and 0 at 11px -> compute in a Python one-liner and paste
6. All three pens agree per glyph -> run `python3 -m unittest tests.test_baker.TestCrossLanguagePen -v` and paste
7. Wrapping breaks on spaces only; an overlong word overflows as its own line -> cite layout.test.js cases
8. Ellipsis needs `white-space: nowrap`; the `…` is measured where it lands -> compile with and without nowrap
9. line-height: px, unitless multiplier, or % -> compile all three and read the text y positions
10. `./fonts/regen.sh` regenerates byte-identical metrics -> run it and `git diff --exit-code fonts/`

## Screenshots

Each line is `path <- command // alt text`. Register every file in `assets/assets.json` with the exact command (`OUT` for the output path) and `checked: true` unless the line says otherwise. Previewer renders only; Playwright only where the line says so.

- assets/authoring/text-and-fonts/sizes.png <- a scratch screen with the same string at 32px and 14px in both weights; bake `--preview` // the same heading at two sizes and two weights, showing where kerning is visible

## Page structure

Skeleton for type `guide`: What it is · Minimal example · Reference table · Behaviour · Limits and errors · Related pages.

Guide skeleton. Minimal example: a fonts.json. Reference table 1: metrics JSON fields (field · type · meaning). Table 2: text properties (property · effect on the pen). Behaviour: faces and weights, charset, measuring and rounding, kerning, wrapping, ellipsis, baseline. Limits and errors.

Frontmatter:

```yaml
---
id: authoring/text-and-fonts
title: Text and fonts
description: <one sentence>
section: authoring
order: 13
version: 0.6.0
sources: [<every repository path opened>]
---
```

## Cross-links

Write links as `[text](page:<id>#<anchor>)`. Every id below must appear on the page at the place named.

- cli/ps2ui-fontgen - fonts.json and metrics
- authoring/css - text properties
- authoring/dynamic-text - slot text uses the same pen
- getting-started/installation - the Raqm refusal

## Facts to emit

Write `_facts/<page-id>.md` before writing the page:

```markdown
# facts: <page-id>

| id | fact | source | verified by | status |
|---|---|---|---|---|
```

Status is `verified` (a command or test in this session proved it), `code-only` (read in source; say why nothing executable exists), or `contradicts-readme` (verified, and README.md says otherwise; cite the README line). If a parent fact is wrong, append `## disputes` with the id and evidence, and stop.

Required ids (downstream pages read these by name):

- `fonts.manifest` - schema
- `fonts.weight-rule` - >= 600 is bold
- `fonts.charset` - the ranges
- `text.rounding` - the formula and the To example
- `text.wrap` - spaces only
- `text.ellipsis` - needs nowrap

## Out of scope

- fontgen argv -> cli/ps2ui-fontgen
- the glyph atlas format -> reference/uib-format

## Done when

- [ ] Environment block ran clean.
- [ ] `_facts/authoring/text-and-fonts.md` exists with every fact id listed under "Facts to emit", each with a status.
- [ ] Every command shown on the page was run in this session; every output block is pasted from that run.
- [ ] Every screenshot listed exists under `assets/authoring/text-and-fonts/`, is registered in `assets/assets.json` with its command, and has alt text.
- [ ] Frontmatter present: `id: authoring/text-and-fonts`, `title`, `description`, `section`, `order: 13`, `version: 0.6.0`, `sources` (every path opened).
- [ ] Every `page:` link names an id from the page index in ARCHITECTURE.md.
- [ ] Word count of prose is 300 to 1500 (`pandoc -t plain` or a `wc -w` after stripping tables and code).
- [ ] Forbidden-phrase grep over the page returns nothing.
- [ ] Nothing from the drift rows' "claim" column appears on the page.
- [ ] Sections appear in the order given under Page structure and every table has the named columns.
