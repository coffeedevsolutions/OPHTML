---
id: authoring/theming
title: Theming
description: Name colours in :root, give them a second value in @theme, read them with var(), and select a row on the console with ps2ui_theme_set.
section: authoring
order: 18
version: 0.8.0
sources: [packages/layout/src/css.js, packages/layout/src/index.js, packages/layout/src/paint.js, packages/layout/test/parse.test.js, packages/layout/test/layout.test.js, packages/baker/ps2ui_bake/uib.py, packages/baker/ps2ui_bake/cli.py, packages/baker/ps2ui_bake/check.py, packages/baker/ps2ui_bake/preview.py, packages/baker/ps2ui_bake/serve.py, packages/baker/ps2ui_bake/serve_page.html, packages/baker/tests/test_baker.py, runtime/ps2ui.h, runtime/ps2ui.c, runtime/tests/test_runtime.c, runtime/sample/main.c, examples/opl-env/ui/opl.css, examples/opl-env/build.sh, docs/design-p3b-theming.md, README.md]
---

# Theming

A theme is a second value for every named colour. One blob carries every theme, and the console selects one by index.

## What it is

Give a colour a name in `:root`. Give that name another value in an `@theme` block. Read the name at a use site with `var()`. The compiler resolves each name into a vector of one colour per theme. The baker interns those vectors into the tint table, and every painting command and every slot stores an index into it. `ps2ui_theme_set` moves which row of that table is live.

A theme moves colour and nothing else. Both rows share one baked layout, so no geometry reflows and no texture is re-uploaded. Names exist at build time only. The blob stores a row count, the runtime selects by index, and no `var()` name is written into the file. The [tint entry](page:reference/uib-format#tint-entry) is the record it selects.

These two pictures are the same screen of the same blob, row 0 and row 1:

![opl-env library screen, theme 0 (root), 4:3, initial focus: dark panels, pale titles, a blue accent chip](../assets/authoring/theming/library-theme-0.png)

![opl-env library screen, theme 1 (light), 4:3, initial focus: white panels, dark titles, the same layout](../assets/authoring/theming/library-theme-1.png)

The reasoning behind role keying is in the design document listed on [Internals](page:project/internals).

## Minimal example

Two names, one alternative theme, one rule:

```css
:root        { --panel: #12182a; --ink: #dde3f0 }
@theme light { --panel: #ffffff; --ink: #1a2033 }

.row { background: var(--panel); color: var(--ink); padding: 32px }
```

Compile it against `<ui><div class="row">Library</div></ui>`:

```
$ ps2ui-layout theme.html theme.css --fonts fonts/fonts.json -o theme.json
ps2ui-layout: 2 paint commands, 0 focusables -> theme.json
```

The IR names the themes in index order and gives every colour a vector of that width:

```
$ python3 -c "
import json; d = json.load(open('theme.json'))
print(d['themes'])
print(d['commands'][0]['fillVar'], d['commands'][0]['fillThemes'])
print(d['commands'][1]['colorVar'], d['commands'][1]['colorThemes'])"
['root', 'light']
--panel [[18, 24, 42, 255], [255, 255, 255, 255]]
--ink [[221, 227, 240, 255], [26, 32, 51, 255]]
```

Baking it writes two rows of two entries:

```
$ ps2ui-bake theme.json -o theme.uib --fonts fonts/fonts.json --tints
...
# 2 tint entries over 2 theme(s): root, light
    0  ( 18, 24, 42,128)  (255,255,255,128)  --panel
    1  (111,114,120,128)  ( 13, 16, 26,128)  --ink
ps2ui-bake: 1 screen(s), 8 records, 1 textures (16 KiB baked), 1 CLUTs -> theme.uib
```

## Reference table

| syntax | effect |
|---|---|
| `:root { --name: <color> }` | Defines `--name` and gives it theme 0's value. The only definition site. The value must be a colour. |
| `@theme <ident> { --name: <color> }` | Adds one theme, in source order, starting at index 1. Sets the value a name takes in that theme. Custom properties only. |
| `var(--name)` | Reads a name at a use site. The whole declaration value, with one exception below. No fallback, and an undefined name is an error. |
| `border: <n>px solid var(--name)` | The one place a `var()` sits beside other tokens. Sets a themed border colour. |
| a colour literal | One entry, the same colour in every theme. No theme can move it. In a sheet that declares a theme it warns. |
| an ordinary property in `:root` | Ignored, with a warning. There is no root cascade on this target. |
| a custom property outside `:root` | Ignored, with a warning. Names resolve globally. |

Which colour spellings parse is on [CSS](page:authoring/css#colours). A name holding anything else is refused at the definition:

```
$ ps2ui-layout theme.html gap.css --fonts fonts/fonts.json -o out-gap.json
error: css: line 1: --gap: "4px" is not a color, and ps2ui custom properties are colors only -- geometry is baked, so a themeable length would be a different and much larger design
```

## Behaviour

### Roles, not values

A tint entry is keyed on the `var()` name together with the whole vector behind it. One name used at many sites is one entry. Two names holding the same colour stay two entries, because a theme has to be able to move one and not the other. Two literals that agree collapse, but never into a named entry.

`examples/opl-env/ui/opl.css` defines its palette once and writes `var(--accent)` at nine sites:

```
$ grep -c "var(--accent)" examples/opl-env/ui/opl.css
9
```

Those nine are entry 8 of a 28-entry table:

```
$ ps2ui-bake landing.json library.json detail.json filters.json recent.json confirm.json -o opl.uib --tints
...
# 28 tint entries over 2 theme(s): root, light
    0  ( 11, 15, 22,128)  (244,246,250,128)  --bg-page
...
    8  ( 62, 78,112,128)  ( 24, 48, 96,128)  --accent
    9  (128,128,128,128)  (128,128,128,128)  (literal, unthemed)   FIXED in every theme
...
   21  (128,128,128,128)  (  0,  0,  0,128)  --ink-max
```

Entries 9 and 21 hold the same colour in row 0 and different colours in row 1. Value keying would have fused them, and moving `--ink-max` would have recoloured every untinted nine-patch.

Once a sheet declares a theme, a colour written at a use site warns once per authored line:

```
$ ps2ui-layout theme.html literal.css --fonts fonts/fonts.json -o out-literal.json
warning: css: line 3: color: "#8b94a7" is a literal in a sheet that declares a theme, so no theme can move it -- name it in :root, or leave it if staying fixed is deliberate
ps2ui-layout: 2 paint commands, 0 focusables -> out-literal.json
```

A sheet with no `@theme` block never warns about a literal. Leaving a colour unnamed is a choice, and the warning fires only where a theme could have reached it.

Colour lives in two tables. Slot base and focus colours intern through the same key, so a theme reaches dynamic text as well as panels. See [dynamic text](page:authoring/dynamic-text#behaviour).

### Opacity splits a role

`opacity` folds into alpha before the key is formed. One name at two opacities is two painted colours, so it is two entries:

```
$ ps2ui-bake op.json -o op.uib --fonts fonts/fonts.json --tints
...
# 3 tint entries over 2 theme(s): root, light
    0  ( 51,102,153,128)  (238,238,238,128)  --panel
    1  (111,114,120,128)  ( 13, 16, 26,128)  --ink
    2  ( 51,102,153, 64)  (238,238,238, 64)  --panel
```

The fold runs over every row, so no theme is left at full alpha.

### Lints run per theme

The linter runs once per theme. Colour lints are reported for every row that fails, and a lint from a later row is prefixed with its theme name. Geometry lints are reported once. A theme whose ink stays dark fails contrast in that row alone:

```
$ ps2ui-layout theme.html omitted.css --fonts fonts/fonts.json -o out-omitted.json
warning: css: line 2: @theme light does not set --ink (defined at line 1), so it keeps the :root value -- a theme that covers some of the palette recolours some of the screen
warning: @theme light: contrast: "Library" contrast 1.29:1 < 3:1 — CRTs crush shadows harder than your monitor
ps2ui-layout: 2 paint commands, 0 focusables -> out-omitted.json
```

Run with `--strict` to make both warnings an exit 1. See the [CRT linter](page:authoring/crt-linter#behaviour).

### Seeing each theme

Four views, in build order. `ps2ui-bake --tints` prints the table as it writes it, with the `var()` name behind each entry. An entry no theme moves is marked `FIXED in every theme`. `ps2ui-check --tints` prints what a loader finds: no names, and a `where` column naming the commands and slots that point at each entry. Run both; each answers half of "why did this not change colour".

```
$ ps2ui-check --tints examples/opl-env/build/ui.uib
# 28 tint entries over 2 theme(s)
  idx  theme 0               theme 1               where
    0  ( 11, 15, 22,128)     (244,246,250,128)     cmd
    1  (121,123,125,128)     (  8, 11, 18,128)     cmd, slot
...
    9  (128,128,128,128)     (128,128,128,128)     cmd, fixed in every theme
```

The flags are documented on [ps2ui-bake](page:cli/ps2ui-bake#options) and [ps2ui-check](page:cli/ps2ui-check#the-tint-table).

For pictures, `preview.render` takes a row number. `ps2ui-bake --preview` renders row 0 only, so render the others directly:

```
$ PYTHONPATH=packages/baker python3 -c "from ps2ui_bake.uib import read_uib; from ps2ui_bake import preview; preview.render(read_uib('examples/opl-env/build/ui.uib'), screen='library', theme=1).save('docs/site/assets/authoring/theming/library-theme-1.png')"
```

`examples/opl-env/build.sh` loops over `range(len(uib.themes))` and writes one set per row. The [previewer](page:cli/previewer#options) carries a Theme control, disabled below two themes, and a `--theme` option that opens on a chosen row.

### Runtime

`ps2ui_theme_set(ctx, n)` selects row `n`. It takes no `GSGLOBAL`, touches no texture state and schedules no transfer. It takes effect on the next `ps2ui_render`. Call it before or after `ps2ui_upload`; it survives an upload, which a CLUT swap does not. A row at or past `n_theme` returns `PS2UI_ERR_RANGE` and leaves the live row where it was.

Read the row count from the header and cycle:

```c
unsigned n = ui.hdr->n_theme;
if (n > 1) {
    cur_theme = (cur_theme + 1) % n;
    ps2ui_theme_set(&ui, cur_theme);
}
```

More than one row requires `PS2UI_FEAT_ROLE_TINTS`, which says the indices are keyed on the declaration rather than on the resolved colour. The baker sets the bit whenever it writes more than one row. Without it `ps2ui_load` returns `PS2UI_ERR_TINTS` rather than opening a blob it cannot recolour correctly. `ps2ui-check` asserts the pair:

```
$ ps2ui-check examples/opl-env/build/ui.uib
...
ok 64 - 2 theme(s) with FEAT_ROLE_TINTS set: more than one row needs the bit, or ps2ui_load refuses the blob
...
```

The signature and its return codes are on the [C API reference](page:runtime/api-reference#textures-and-palettes).

## Limits and errors

Whether a command exists is decided by row 0 alone. A fill that is transparent in `:root` paints nothing in any theme. A theme that could delete a command would make the command list depend on the row chosen at runtime.

| message | stage | severity | cause | fix |
|---|---|---|---|---|
| `css: line <n>: <name>: "<value>" is not a color, and ps2ui custom properties are colors only ...` | layout | error | A custom property holding a length, a font or a keyword | Keep custom properties to colours; geometry is baked |
| `css: line <n>: "<head>" -- @theme takes one identifier, e.g. "@theme light" ...` | layout | error | An `@theme` head that is not one identifier starting with a letter | Name the theme, for example `@theme light` |
| `css: line <n>: unterminated @theme block` | layout | error | A missing closing brace | Close the block |
| `css: line <n>: @theme <name> { <prop>: ... } -- a theme supplies custom properties and nothing else ...` | layout | error | A theme setting a size, a font or a layout property | Move it to an ordinary rule |
| `css: line <n>: @theme <name> defines <prop>, which :root does not ...` | layout | error | A theme setting a name with no `:root` definition | Define the name in `:root`, or delete the line |
| `css: line <n>: @theme <name> sets <prop> twice` | layout | error | One name declared twice in one block | Keep one |
| `css: line <n>: @theme <name> is declared twice` | layout | error | Two blocks with the same theme name | Rename one, or merge them |
| `css: line <n>: <prop>: var(<name>, ...) has a fallback ...` | layout | error | `var(--x, #fff)` | Drop the fallback; a role has one value per theme |
| `css: line <n>: <prop>: <name> is not defined in :root ...` | layout | error | A `var()` naming an undefined name | Define it in `:root`, or fix the spelling |
| `css: line <n>: <prop>: bad color "var(--x) ..." ...` | layout | error | A `var()` that is not the whole value, outside the `border` shorthand | Give the property the `var()` alone |
| `css: line <n>: ":root { <prop>: ... }" is ignored ...` | layout | warning | An ordinary property inside `:root` | Move it to a real selector |
| `css: line <n>: custom property "<name>" outside :root is ignored ...` | layout | warning | A `--name` declared on a class or id | Move the definition to `:root` |
| `css: line <n>: @theme <name> does not set <prop> ...` | layout | warning | A theme covering part of the palette | Set the name, or accept the `:root` value |
| `css: line <n>: <prop>: "<token>" is a literal in a sheet that declares a theme ...` | layout | warning | A colour written at a use site once a theme exists | Name it in `:root`, or leave it fixed on purpose |
| `layout: internal: <prop> has 1 theme values, expected <n>` | layout | error | A sheet with an `@theme` block and no `:root` custom property at all | Define at least one name in `:root`. The message is a defect, not a diagnostic |

The last row is a code defect. `themeCount` reports a width of 1 for an empty name table while the theme list is already longer. The first painted colour then trips an internal guard instead of a named refusal.

`ps2ui-check` refuses a blob with `n_theme` of zero, and the runtime refuses more than one row without the feature bit. Both are listed with the rest of the catalogue on [ps2ui-check](page:cli/ps2ui-check#the-catalogue).

## Related pages

| page | why |
|---|---|
| [CSS](page:authoring/css#colours) | The colour forms a name and a theme may hold |
| [ps2ui-bake](page:cli/ps2ui-bake#options) | `--tints`, with the names |
| [ps2ui-check](page:cli/ps2ui-check#the-tint-table) | `--tints`, as a loader sees it |
| [Previewer](page:cli/previewer#options) | The theme control and `--theme` |
| [C API reference](page:runtime/api-reference#textures-and-palettes) | `ps2ui_theme_set` and its return codes |
| [.uib](page:reference/uib-format#tint-entry) | The tint table and the feature bit |
| [Internals](page:project/internals) | The theming design document |
