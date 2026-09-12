# Page: authoring/html (HTML)

Page type: `guide`. Section order: `11`. Wave: `1`.

## Purpose and audience

What the parser accepts, how tags are treated, every attribute the compiler reads, `{i}`/`{n}` substitution, entities and whitespace, and every hard error with its text.

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

- packages/layout/src/html.js - the whole parser: void tags (line ~8), transparent html/body (~142, ~173), skipped head/style/script/title (~163-172), entities (~54-66), whitespace collapse (~109-112), errors (~72-188)
- packages/layout/src/box.js - unknown data- attribute warning (~126-158), data-slot rules (~194-214), img attributes (~215-285), focusable nesting (~286-291), data-nocontrast (~193)
- packages/layout/src/repeat.js - data-repeat and {i}/{n}
- packages/layout/src/focus.js line ~114 - node name is id, then name, then boxN
- packages/layout/test/parse.test.js and fonts.test.js - the html and unknown-attribute cases
- docs/tutorial-uc3.md step 2 - the `<screen name=...>` root as used in practice

## Claims to verify, and how

Each item is `claim -> how to prove it`. Run every command. Paste real output into the page where the structure calls for it and record the result in the facts file.

1. No tag whitelist; only img, the void tags, html/body, head/style/script/title are special -> read html.js and box.js; compile `<section><my-thing>x</my-thing></section>` and show it compiles
2. Attribute table: id, class, name, focusable, autofocus, data-slot, data-slot-capacity (default 63), data-repeat, data-tex-slot, data-keep, data-nocontrast, palettize, src -> grep `attrs` reads across src/; compile a slot without capacity and print `ir.slots[0].capacity`
3. `style=` and `<img width=>` are inert and unwarned -> compile with and without them, diff the IR
4. Unknown data- attributes warn with a suggestion -> compile `data-capacity="4"` and paste the warning; run `node --test test/fonts.test.js`
5. Whitespace collapses at parse time and `&nbsp;` collapses too; there is no `white-space: pre` -> compile `a&nbsp;&nbsp;b` and read the text command
6. Named entities are exactly amp lt gt quot apos nbsp middot hellip; numeric entities work -> read html.js
7. Attribute values must be quoted; a bare `<` is an error -> trigger both, paste messages
8. Every hard error with its text -> trigger each of the ten html.js errors in a scratch file and paste; cite `parse.test.js` for the two it tests
9. A data-slot element holds exactly one text node -> trigger, paste

## Screenshots

None. Do not add decorative images.

## Page structure

Skeleton for type `guide`: What it is · Minimal example · Reference table · Behaviour · Limits and errors · Related pages.

Guide skeleton. Minimal example is the tutorial's library.html. Reference table columns: attribute · element · effect · page. Behaviour: tags, text and whitespace, entities, repeat substitution, naming of focus nodes. Limits and errors: a table of message · cause.

Frontmatter:

```yaml
---
id: authoring/html
title: HTML
description: <one sentence>
section: authoring
order: 11
version: 0.6.0
sources: [<every repository path opened>]
---
```

## Cross-links

Write links as `[text](page:<id>#<anchor>)`. Every id below must appear on the page at the place named.

- authoring/dynamic-text - data-slot rows
- authoring/lists - data-repeat row
- authoring/images - img rows
- authoring/focus-and-navigation - focusable, autofocus, name rows
- authoring/crt-linter - data-nocontrast row
- authoring/css - style attribute is inert
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

- `html.attributes` - the attribute table rows
- `html.errors` - message pattern and cause for each hard error
- `html.whitespace` - collapse rules including nbsp
- `html.entities` - the named list

## Out of scope

- CSS -> authoring/css
- what data-slot text can do at runtime -> authoring/dynamic-text

## Done when

- [ ] Environment block ran clean.
- [ ] `_facts/authoring/html.md` exists with every fact id listed under "Facts to emit", each with a status.
- [ ] Every command shown on the page was run in this session; every output block is pasted from that run.
- [ ] Every screenshot listed exists under `assets/authoring/html/`, is registered in `assets/assets.json` with its command, and has alt text.
- [ ] Frontmatter present: `id: authoring/html`, `title`, `description`, `section`, `order: 11`, `version: 0.6.0`, `sources` (every path opened).
- [ ] Every `page:` link names an id from the page index in ARCHITECTURE.md.
- [ ] Word count of prose is 300 to 1500 (`pandoc -t plain` or a `wc -w` after stripping tables and code).
- [ ] Forbidden-phrase grep over the page returns nothing.
- [ ] Nothing from the drift rows' "claim" column appears on the page.
- [ ] Sections appear in the order given under Page structure and every table has the named columns.
