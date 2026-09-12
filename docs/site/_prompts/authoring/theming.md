# Page: authoring/theming (Theming)

Page type: `guide`. Section order: `18`. Wave: `1`.

## Purpose and audience

How to author a second theme: `:root` custom properties, `@theme`, `var()`, what becomes a tint-table role and what stays fixed, the diagnostics, how to see each theme, and the runtime call. None of this is in README.md today.

## Read first

1. `docs/site/ARCHITECTURE.md`, all of it. The rules below are copied from it and are binding.
2. Parent facts files, before opening any source: `_facts/authoring/css.md`, `_facts/cli/ps2ui-bake.md`, `_facts/cli/ps2ui-check.md`, `_facts/runtime/api-reference.md`, `_facts/reference/uib-format.md`. Reuse their fact ids; do not restate a parent fact differently. If one is wrong, write a `## disputes` section and stop.
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
| D3 | README.md (absent) | the runtime API is what README shows | `ps2ui_theme_set`, `ps2ui_clut_set`, `ps2ui_slot_get`, `ps2ui_visible_get`, `ps2ui_list_select`, `ps2ui_list_selected_row`, `ps2ui_screen_name`, `ps2ui_arena_size`, `ps2ui_offset_get`, `ps2ui_crc32`, `ps2ui_clut_csm1` exist in `runtime/ps2ui.h` and are documented. |
| D7 | README.md "Supported CSS" | the property list | Missing: `opacity`, `min-*`/`max-*`, `align-self`, `flex` shorthand, `row-gap`, `column-gap`, `:root` custom properties, `var()`, `@theme`, `data-nocontrast`, capacity default 63, the `name` attribute, `--min-font-size`. Overstated: `border-radius` takes one px value; named colours are eight; keyword-valued properties are unvalidated; the `:focus` geometry guard does not cover `letter-spacing`, `font-weight`, `text-align`, `text-overflow`; no `white-space: pre`; `&nbsp;` collapses to a space. |

## Sources of truth

Line numbers are hints from the exploration that produced this brief; re-locate by symbol name. Authority order: code, tests, docs/*.md, README.md.

- packages/layout/src/css.js ~243-538 - :root, @theme, var() rules and every theme diagnostic
- packages/layout/src/index.js ~224-236, ~253-258 - lint per theme, themes array
- packages/baker/ps2ui_bake/uib.py ~180-280 - tint interning: (name, vector) key, literals, opacity split, uint16 limit
- packages/baker/ps2ui_bake/cli.py ~289-302 (--tints) and check.py ~646-705 (print_tints)
- runtime/ps2ui.h ~565-600; runtime/ps2ui.c theme_set - bounds, FEAT_ROLE_TINTS
- docs/design-p3b-theming.md §4 and §9.2 - rationale only, for one link
- packages/layout/test/parse.test.js theme cases; test_baker.py TestTintTable; test_runtime.c "P3b-2: ps2ui_theme_set"
- examples/opl-env/ui/opl.css - a real two-theme sheet

## Claims to verify, and how

Each item is `claim -> how to prove it`. Run every command. Paste real output into the page where the structure calls for it and record the result in the facts file.

1. `:root` is the only definition site; values are colours only -> compile a `--gap: 4px` and paste the error
2. `@theme name {}` sets only existing names; omitted names warn; unknown names error; duplicate theme errors -> trigger each
3. `var()` has no fallback and must be the whole value, except inside `border` shorthand -> trigger the fallback error; compile `border: 1px solid var(--x)`
4. A name is a role shared by every use site; a literal is fixed in every theme; opacity splits a role -> cite TestTintTable cases
5. A literal in a themed sheet warns -> compile and paste
6. Theme 0 is root; names are build-time only -> print `ir.themes`
7. `ps2ui-bake --tints` and `ps2ui-check --tints` print the table with the var name -> run both on opl-env and paste
8. `ps2ui_theme_set` bounds the index; more than one theme requires FEAT_ROLE_TINTS which the baker sets -> cite the runtime test section; run `ps2ui-check` on opl-env and paste the theme line
9. Lints run per theme; colour lints report per theme -> cite layout.test.js theme lint cases

## Screenshots

Each line is `path <- command // alt text`. Register every file in `assets/assets.json` with the exact command (`OUT` for the output path) and `checked: true` unless the line says otherwise. Previewer renders only; Playwright only where the line says so.

- assets/authoring/theming/library-theme-0.png <- `preview.render(read_uib('examples/opl-env/build/ui.uib'), screen='library', theme=0)` // opl-env library, theme 0
- assets/authoring/theming/library-theme-1.png <- same with theme=1 // opl-env library, theme 1

## Page structure

Skeleton for type `guide`: What it is · Minimal example · Reference table · Behaviour · Limits and errors · Related pages.

Guide skeleton. Minimal example: the 4-line sheet from the design doc. Reference table: syntax · effect (:root, @theme, var(), literal). Behaviour: roles, opacity, seeing themes (previewer theme menu, --tints), the runtime call. Limits and errors table with real messages.

Frontmatter:

```yaml
---
id: authoring/theming
title: Theming
description: <one sentence>
section: authoring
order: 18
version: 0.6.0
sources: [<every repository path opened>]
---
```

## Cross-links

Write links as `[text](page:<id>#<anchor>)`. Every id below must appear on the page at the place named.

- authoring/css - colour forms
- cli/ps2ui-bake - --tints
- cli/ps2ui-check - --tints
- cli/previewer - theme menu
- runtime/api-reference - theme_set
- reference/uib-format - tint table
- project/internals - design doc

## Facts to emit

Write `_facts/<page-id>.md` before writing the page:

```markdown
# facts: <page-id>

| id | fact | source | verified by | status |
|---|---|---|---|---|
```

Status is `verified` (a command or test in this session proved it), `code-only` (read in source; say why nothing executable exists), or `contradicts-readme` (verified, and README.md says otherwise; cite the README line). If a parent fact is wrong, append `## disputes` with the id and evidence, and stop.

Required ids (downstream pages read these by name):

- `theme.syntax` - the rules
- `theme.tint-table.keying` - name+vector, literals, opacity
- `theme.diagnostics` - messages
- `theme.runtime` - theme_set semantics

## Out of scope

- clut_set for palettized art -> runtime/streaming-art

## Done when

- [ ] Environment block ran clean.
- [ ] `_facts/authoring/theming.md` exists with every fact id listed under "Facts to emit", each with a status.
- [ ] Every command shown on the page was run in this session; every output block is pasted from that run.
- [ ] Every screenshot listed exists under `assets/authoring/theming/`, is registered in `assets/assets.json` with its command, and has alt text.
- [ ] Frontmatter present: `id: authoring/theming`, `title`, `description`, `section`, `order: 18`, `version: 0.6.0`, `sources` (every path opened).
- [ ] Every `page:` link names an id from the page index in ARCHITECTURE.md.
- [ ] Word count of prose is 300 to 1500 (`pandoc -t plain` or a `wc -w` after stripping tables and code).
- [ ] Forbidden-phrase grep over the page returns nothing.
- [ ] Nothing from the drift rows' "claim" column appears on the page.
- [ ] Sections appear in the order given under Page structure and every table has the named columns.
