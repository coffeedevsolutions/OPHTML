# Page: authoring/css (CSS)

Page type: `guide`. Section order: `12`. Wave: `1`.

## Purpose and audience

The selector grammar, every supported property with its accepted values and default, units, colours, inheritance, and the two hard rules: `flex-direction` is required and `:focus` is paint-only. Also what is silently accepted (unvalidated keywords) and what the `:focus` guard misses.

## Read first

1. `docs/site/ARCHITECTURE.md`, all of it. The rules below are copied from it and are binding.
2. Parent facts files, before opening any source: `_facts/reference/ir-format.md`, `_facts/cli/ps2ui-layout.md`. Reuse their fact ids; do not restate a parent fact differently. If one is wrong, write a `## disputes` section and stop.
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

- packages/layout/src/css.js - GEOMETRY_PROPS (~19-27), INHERITED (~29-44), INITIAL_STYLE (~50-105), parseSelector (~121-175), at-rules (~252-282), applyDeclaration (~577-736), computeStyle and the :focus guard (~769-801)
- packages/layout/src/values.js - named colours (~10-19), parseLength (~33-44), parseColor (~66-104), box expansion (~126-134)
- packages/layout/src/flex.js - axisOf (~28-30), justify/align switches (~367-389), text-align and ellipsis (~408-418), the image stretch deviation (~461-468), border-box (~5-6, ~39-47)
- packages/layout/src/paint.js - opacity fold (~30-33), paint normalisation (~76-97), scissor pairs (~315-326)
- packages/layout/src/box.js - the flex-direction collector (~339-348); index.js (~162-174) - the combined error
- packages/layout/test/parse.test.js and layout.test.js - the cascade, :focus, unit, colour and flex cases

## Claims to verify, and how

Each item is `claim -> how to prove it`. Run every command. Paste real output into the page where the structure calls for it and record the result in the facts file.

1. Selectors: type, .class, #id, *, compounds, descendant by whitespace, :focus on any compound, comma lists; nothing else -> compile `div > p {}` and paste the error; run `node --test test/parse.test.js`
2. `:focus` counts as a class in specificity and matches only elements carrying `focusable` -> cite parse.test.js cases; compile `.x:focus` on a non-focusable and paste the warning
3. The property table with accepted values and defaults -> read applyDeclaration and INITIAL_STYLE; every row cites a line
4. px is the only unit for gap, padding, margin, border-width, border-radius, font-size, letter-spacing; % and auto also on sizes and flex-basis; line-height takes px, unitless or % -> compile `padding: 1em` and `padding: 8` and paste both errors
5. Named colours are black, white, red, green, blue, gray, grey, transparent; hex 3/4/6/8; rgb/rgba -> compile `color: orange` and paste
6. Inherited properties are color, font-size, font-weight, line-height, text-align, white-space, letter-spacing (plus the colour var) -> cite parse.test.js `inherited vs reset properties`
7. `flex-direction` is required on any container with two or more children; all offenders are reported in one error -> compile the case and paste the whole message
8. `:focus` may not change any GEOMETRY_PROPS property -> compile `:focus { width: 10px }` and paste; then compile `:focus { font-weight: bold }` and show it passes; document the four escaping properties as a limit
9. Keyword properties are unvalidated: `flex-direction: rows` is column, `text-align: centre` is left -> compile both and read the IR geometry
10. `display` accepts only flex and none; `overflow` only visible and hidden; `position` is unsupported and warns -> trigger each
11. `opacity` multiplies into the alpha of background, border and text for every theme row -> cite layout.test.js `the opacity fold runs over every row`
12. Images never stretch under align-items: stretch -> cite flex.js; cite layout.test.js image cases

## Screenshots

Each line is `path <- command // alt text`. Register every file in `assets/assets.json` with the exact command (`OUT` for the output path) and `checked: true` unless the line says otherwise. Previewer renders only; Playwright only where the line says so.

- assets/authoring/css/demo.png <- a scratch screen exercising border-radius, translucent background over a fill, ellipsis, and a focus delta; bake with `--preview` // a demo screen showing rounded panels, translucency, an ellipsized title and the focus ring
- assets/authoring/css/demo-states.png <- `--montage` of the same blob // every focus state of the demo screen

## Page structure

Skeleton for type `guide`: What it is · Minimal example · Reference table · Behaviour · Limits and errors · Related pages.

Guide skeleton. Minimal example is a 12-line sheet. Reference table columns: property · values · default · notes; grouped by rows: layout, box, border, colour, text. Second small table: units. Third: colours. Behaviour: selectors and cascade, inheritance, the two hard rules, unvalidated keywords, scissor and display none. Limits and errors: message · cause table.

Frontmatter:

```yaml
---
id: authoring/css
title: CSS
description: <one sentence>
section: authoring
order: 12
version: 0.6.0
sources: [<every repository path opened>]
---
```

## Cross-links

Write links as `[text](page:<id>#<anchor>)`. Every id below must appear on the page at the place named.

- authoring/theming - var(), :root, @theme rows point there
- authoring/text-and-fonts - font and text rows
- authoring/images - img sizing and stretch
- authoring/focus-and-navigation - :focus
- authoring/crt-linter - Related pages
- reference/diagnostics - Limits and errors

## Facts to emit

Write `_facts/<page-id>.md` before writing the page:

```markdown
# facts: <page-id>

| id | fact | source | verified by | status |
|---|---|---|---|---|
```

Status is `verified` (a command or test in this session proved it), `code-only` (read in source; say why nothing executable exists), or `contradicts-readme` (verified, and README.md says otherwise; cite the README line). If a parent fact is wrong, append `## disputes` with the id and evidence, and stop.

Required ids (downstream pages read these by name):

- `css.properties` - the table rows
- `css.units` - which units where
- `css.colors` - the named list and forms
- `css.inherited` - the list
- `css.focus.geometry-props` - the guarded list and the four unguarded text properties
- `css.flex-direction.required` - the rule and the message shape
- `css.selectors` - the grammar

## Out of scope

- theming syntax -> authoring/theming
- kerning and wrapping -> authoring/text-and-fonts
- lint rules -> authoring/crt-linter

## Done when

- [ ] Environment block ran clean.
- [ ] `_facts/authoring/css.md` exists with every fact id listed under "Facts to emit", each with a status.
- [ ] Every command shown on the page was run in this session; every output block is pasted from that run.
- [ ] Every screenshot listed exists under `assets/authoring/css/`, is registered in `assets/assets.json` with its command, and has alt text.
- [ ] Frontmatter present: `id: authoring/css`, `title`, `description`, `section`, `order: 12`, `version: 0.6.0`, `sources` (every path opened).
- [ ] Every `page:` link names an id from the page index in ARCHITECTURE.md.
- [ ] Word count of prose is 300 to 1500 (`pandoc -t plain` or a `wc -w` after stripping tables and code).
- [ ] Forbidden-phrase grep over the page returns nothing.
- [ ] Nothing from the drift rows' "claim" column appears on the page.
- [ ] Sections appear in the order given under Page structure and every table has the named columns.
