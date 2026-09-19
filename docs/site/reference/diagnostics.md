---
id: reference/diagnostics
title: Diagnostics
description: Every message the compiler, baker, checker, previewer and runtime can produce, with its cause, its fix and the page that explains it.
section: reference
order: 52
version: 0.7.0
sources: [packages/layout/src/aspect.js, packages/layout/src/box.js, packages/layout/src/css.js, packages/layout/src/flex.js, packages/layout/src/focus.js, packages/layout/src/html.js, packages/layout/src/image.js, packages/layout/src/index.js, packages/layout/src/lint.js, packages/layout/src/paint.js, packages/layout/src/repeat.js, packages/layout/bin/ps2ui-layout.js, packages/layout/bin/ps2ui-dev.js, packages/baker/ps2ui_bake/caps.py, packages/baker/ps2ui_bake/check.py, packages/baker/ps2ui_bake/cli.py, packages/baker/ps2ui_bake/fontgen.py, packages/baker/ps2ui_bake/preview.py, packages/baker/ps2ui_bake/project.py, packages/baker/ps2ui_bake/ps2ui.py, packages/baker/ps2ui_bake/quads.py, packages/baker/ps2ui_bake/rounding.py, packages/baker/ps2ui_bake/serve.py, packages/baker/ps2ui_bake/uib.py, packages/baker/ps2ui_bake/vendor.py, packages/baker/ps2ui_bake/vram.py, runtime/ps2ui.h]
---

# Diagnostics

Search this page for the text you were shown. Each row names what produced
the message and what to change. The last column is the page that explains the
mechanism behind it.

Two severities exist and nothing sits between them. An error ends its stage
with a non-zero exit and writes no output file. A warning is printed and the
stage carries on at exit 0. `ps2ui-layout --strict` promotes every compiler
warning to exit 1. `ps2ui-check --strict` promotes every check warning to exit
1. Neither flag can pick out one rule.

Each stage prefixes its own lines. Placeholders below are written `<n>`,
`<name>` and `<prop>`. The rest of every message is verbatim.

```
$ ps2ui-layout ok.html c2.css --fonts fonts/fonts.json -o x.json
error: css: line 1: border-color: bad color "orange"
$ echo $?
1
```

## HTML parse

[html.js](repo:packages/layout/src/html.js) raises eleven errors. Ten carry a
`line <n>:` prefix. `ps2ui-layout` prints each as `error: <message>` on stderr
and exits 1. The parser emits no warnings.

| message | severity | cause | fix | page |
|---|---|---|---|---|
| `html: line <n>: unexpected end of input in tag` | error | input ends between the tag name and `>` | close the tag | [HTML](page:authoring/html#limits-and-errors) |
| `html: line <n>: malformed attribute` | error | an attribute name is empty, such as a leading `=` or a stray `/` inside the tag | delete the stray character | [HTML](page:authoring/html#limits-and-errors) |
| `html: line <n>: attribute <name> must be quoted` | error | `=` is followed by something other than `"` or `'` | quote the value | [HTML](page:authoring/html#limits-and-errors) |
| `html: line <n>: unterminated attribute <name>` | error | input ends before the closing quote | close the quote | [HTML](page:authoring/html#limits-and-errors) |
| `html: line <n>: unterminated comment` | error | `<!--` has no `-->` | close the comment | [HTML](page:authoring/html#limits-and-errors) |
| `html: line <n>: closing </tag> with no open element` | error | a close tag appears with the stack empty | delete the close tag | [HTML](page:authoring/html#limits-and-errors) |
| `html: line <n>: closing </tag> but <open> (line <m>) is open` | error | the close tag does not match the innermost open element | close the elements in order | [HTML](page:authoring/html#limits-and-errors) |
| `html: line <n>: bare "<" in content; write &lt;` | error | `<` is followed by something that cannot start a tag name | write `&lt;` | [HTML](page:authoring/html#entities) |
| `html: line <n>: unterminated <tag>` | error | a `head`, `style`, `script` or `title` element has no close tag | close it | [HTML](page:authoring/html#tags) |
| `html: <tag> opened on line <n> is never closed` | error | the open-element stack is not empty at end of input | close the element | [HTML](page:authoring/html#limits-and-errors) |
| `html: line <n>: malformed tag <tag>` | error | unreachable; `parseAttrs` returns only on `>` or `/>`, and the caller handles both | nothing to fix | [HTML](page:authoring/html#limits-and-errors) |

## CSS

[css.js](repo:packages/layout/src/css.js) raises 30 errors and pushes 6
warnings. An error prints as `error: <message>` and exits 1. A warning prints
as `warning: <message>` and the compile continues. Every message here carries
a line number, and it is the line of the DECLARATION rather than of the rule
that holds it.

A compile reports every CSS error it finds, one `error: ` line each, sorted by
line. A stylesheet with three mistakes took three builds to clear when each
pass stopped at the first.

| message | severity | cause | fix | page |
|---|---|---|---|---|
| `css: line <n>: unsupported selector syntax near "<c>" in "<s>"` | error | a combinator outside type, `.class`, `#id`, `*`, descendant and `:focus` | rewrite as a descendant selector | [CSS](page:authoring/css#selectors-and-the-cascade) |
| `` css: line <n>: "<s>": :<name> does not exist on this target. `` plus the sentence naming `:focus` | error | a pseudo-class other than `:focus`; there is no pointer, so no hover, active or visited state exists | drop it, or use `:focus` | [CSS](page:authoring/css#selectors-and-the-cascade) |
| `css: line <n>: unterminated comment` | error | `/*` has no `*/` | close the comment | [CSS](page:authoring/css#limits-and-errors) |
| `css: line <n>: malformed declaration "<d>"` | error | a declaration with no `:` | add the colon | [CSS](page:authoring/css#limits-and-errors) |
| `css: line <n>: selector without a block` | error | the file ends after a selector | add the block | [CSS](page:authoring/css#limits-and-errors) |
| `css: line <n>: unterminated block` | error | a rule block has no `}` | close the block | [CSS](page:authoring/css#limits-and-errors) |
| `css: line <n>: <prop>: "<value>" is not a length` | error | the value does not parse as a length at all | write a px length | [CSS](page:authoring/css#units) |
| `css: line <n>: <prop>: unitless "<value>" — write "<value>px"` | error | a bare number other than `0` on a px-only property | add `px` | [CSS](page:authoring/css#units) |
| `css: line <n>: <prop>: only px supported, got "<value>"` | error | a length in `%`, `em`, `rem`, `vw` or `vh` on a px-only property | convert to px | [CSS](page:authoring/css#units) |
| `css: line <n>: display: only "flex" and "none" exist on this target (got "<value>")` | error | any other `display` value | use `flex` or `none` | [CSS](page:authoring/css#scissor-and-display-none) |
| `css: line <n>: overflow: only visible\|hidden (there is no scrolling on a memory card browser)` | error | any other `overflow` value | use `hidden` and a list window | [Lists](page:authoring/lists#runtime-window) |
| `css: line <n>: <prop>: unknown value "<value>". <prop> takes <set>` | error | a misspelled keyword on one of the eight checked properties | spell it from the set the message lists | [CSS](page:authoring/css#checked-keywords) |
| `css: line <n>: <prop>: "<value>" is real CSS that this target does not implement -- <what it would have done>. <prop> takes <set>` | error | `space-evenly`, `baseline`, `justify`, `pre`, `pre-wrap`, `pre-line`, `break-spaces` | pick a value the solver has; the message names the layout it would otherwise have produced | [CSS](page:authoring/css#checked-keywords) |
| `css: line <n>: padding: 1-4 values` | error | five or more values in the shorthand | give one to four | [CSS](page:authoring/css#reference-table) |
| `css: line <n>: margin: 1-4 values` | error | five or more values in the shorthand | give one to four | [CSS](page:authoring/css#reference-table) |
| `css: line <n>: border: unsupported token "<token>" (only solid borders exist)` | error | a style keyword other than `solid` or `none` in the shorthand | write `<width> solid <color>` | [CSS](page:authoring/css#reference-table) |
| `css: line <n>: border-color: bad color "<value>"` | error | the value is not one of the eight names, a hex form, `rgb()` or `rgba()` | use a supported colour form | [CSS](page:authoring/css#colours) |
| `css: line <n>: <prop>: bad color "<value>" (flat colors only — gradients are a texture you bake yourself)` | error | the same, on `background` or `background-color` | bake the gradient as a PNG | [Images](page:authoring/images#limits-and-errors) |
| `css: line <n>: color: bad color "<value>"` | error | the same, on `color` | use a supported colour form | [CSS](page:authoring/css#colours) |
| `css: line <n>: opacity: bad value` | error | `parseFloat` cannot read the value | write a number from 0 to 1 | [CSS](page:authoring/css#reference-table) |
| `css: line <n>: :focus may not change "<prop>" — focus is a paint-only delta. Both states share one baked layout; move the geometry to the base rule.` | error | one of the 33 geometry properties inside a `:focus` rule | move it to the base rule | [CSS](page:authoring/css#the-two-hard-rules) |
| `css: line <n>: :focus may not change "<prop>" -- it is read from the base style when the line is emitted, so a value here is parsed, applied and then dropped. Move it to the base rule.` | error | `letter-spacing`, `text-align` or `text-overflow` inside a `:focus` rule | move it to the base rule | [CSS](page:authoring/css#the-two-hard-rules) |
| `css: line <n>: "<selector>" matches <tag> line <n>, but no element in that selector has the focusable attribute, so the :focus delta can never show. Add focusable, or drop the :focus.` | warning | a `:focus` rule whose element carries no `focusable` attribute | add the attribute, or drop the `:focus` | [CSS](page:authoring/css#the-two-hard-rules) |
| `css: <tag> line <n>: a :focus rule changes font-weight to <w>, so this text is measured for the heavier face and wraps to <a> lines where the unfocused text alone needs <b>...` | warning | a `:focus` weight delta on wrapping text whose line count changes under the heavier face | widen the box, or move the weight to the base rule | [CSS](page:authoring/css#the-two-hard-rules) |
| `css: line <n>: <name>: "<value>" is not a color, and ps2ui custom properties are colors only -- geometry is baked, so a themeable length would be a different and much larger design` | error | a `:root` custom property holding anything but a colour | bake the geometry instead | [Theming](page:authoring/theming#roles-not-values) |
| `css: line <n>: "<head>" -- @theme takes one identifier, e.g. "@theme light". A theme is selected by index at runtime and the name exists so a human can say which index they meant, so an unparseable one is refused rather than numbered` | error | the `@theme` head is not one identifier starting with a letter | name the theme | [Theming](page:authoring/theming#limits-and-errors) |
| `css: line <n>: unterminated @theme block` | error | the `@theme` block has no `}` | close the block | [Theming](page:authoring/theming#limits-and-errors) |
| `css: line <n>: @theme <name> is declared twice` | error | two blocks share one name; reusing `root` appends `-- "root" is the theme :root defines, and it is always index 0` | merge the blocks | [Theming](page:authoring/theming#limits-and-errors) |
| `css: line <n>: @theme <name> { <prop>: ... } -- a theme supplies custom properties and nothing else. Sizes, fonts and layout are baked geometry; a themeable length would be a different and much larger design` | error | an ordinary property inside a theme block | move it to a rule | [Theming](page:authoring/theming#roles-not-values) |
| `css: line <n>: @theme <name> defines <prop>, which :root does not. A name only reaches a use site through :root, so this value could never be drawn` | error | the theme sets a name `:root` never defined | define it in `:root` | [Theming](page:authoring/theming#limits-and-errors) |
| `css: line <n>: @theme <name> sets <prop> twice` | error | one block sets one name twice | delete one | [Theming](page:authoring/theming#limits-and-errors) |
| `css: line <n>: @theme <name>: <prop>: "<value>" is not a color` | error | a theme block's custom property holds a non-colour | write a colour | [Theming](page:authoring/theming#limits-and-errors) |
| `css: line <n>: <prop>: var(<name>, ...) has a fallback. A role is one colour per theme; a fallback is a second value for the same name and there is nothing here to choose between them` | error | a `var()` fallback | delete the fallback | [Theming](page:authoring/theming#roles-not-values) |
| `css: line <n>: <prop>: malformed var(<name><rest>)` | error | tokens after the name inside `var()` and no comma | write `var(--name)` alone | [Theming](page:authoring/theming#roles-not-values) |
| `css: line <n>: <prop>: <name> is not defined in :root. Undefined names are refused rather than falling back to a literal, because a theme that cannot reach a colour is exactly the defect this mechanism exists to prevent` | error | a `var()` name with no `:root` definition | define it in `:root` | [Theming](page:authoring/theming#roles-not-values) |
| `css: line <n>: property "<prop>" not supported on this target; ignored` | warning | a property `applyDeclaration` has no case for, `position` included | delete it | [CSS](page:authoring/css#reference-table) |
| `css: line <n>: at-rule "<name>" ignored` | warning | any at-rule but `@theme`, body discarded | delete it | [CSS](page:authoring/css#limits-and-errors) |
| `css: <tag> line <n> sets <prop>: <v>% but its container has no definite <axis>, so the percentage cannot resolve and is treated as auto` | warning | New in 0.7.0. A percentage size whose containing size is indefinite, such as the main axis of a shrink-to-fit row; 0.6.0 resolved it to `auto` and said nothing | give the container a definite size on that axis, or state the size in px | [CSS](page:authoring/css#reference-table) |
| `css: <tag> line <n> sets overflow: hidden with border-radius: <r>px; the clip is a rectangle, so children are cut at the square edge and the rounded corners only cover the background behind them` | warning | New in 0.7.0. One box sets both; either alone is silent. 0.6.0 clipped square and said nothing | drop the radius, or drop the clip and size the children to fit | [CSS](page:authoring/css#reference-table) |
| `css: line <n>: ":root { <prop>: ... }" is ignored -- :root defines custom properties on this target, not inherited style` | warning | an ordinary property inside `:root` | move it to a rule | [Theming](page:authoring/theming#limits-and-errors) |
| `css: line <n>: custom property "<name>" outside :root is ignored -- ps2ui resolves names globally, so an element-scoped value would silently mean the :root one` | warning | a `--name` declared on any other selector | move it into `:root` | [Theming](page:authoring/theming#roles-not-values) |
| `css: line <n>: @theme <name> does not set <prop> (defined at line <m>), so it keeps the :root value -- a theme that covers some of the palette recolours some of the screen` | warning | the theme omits a name `:root` defines | set it, or accept the `:root` value | [Theming](page:authoring/theming#limits-and-errors) |
| `css: line <n>: <prop>: "<token>" is a literal in a sheet that declares a theme, so no theme can move it -- name it in :root, or leave it if staying fixed is deliberate` | warning | a colour literal on `color`, `background`, `background-color`, `border-color` or `border` in a themed sheet | name it in `:root` | [Theming](page:authoring/theming#roles-not-values) |

## Layout

[box.js](repo:packages/layout/src/box.js), the flex solver and the
display-list builder produce these. An error prints as `error: <message>` and
exits 1. A warning prints as `warning: <message>`. Four rows are unreachable
from any sheet, and are listed so a search for them ends here.

| message | severity | cause | fix | page |
|---|---|---|---|---|
| `layout: <tag> line <n>: data-slot needs a name` | error | `data-slot=""` | name the slot | [Dynamic text](page:authoring/dynamic-text#names) |
| `layout: <tag> line <n>: a data-slot element must contain exactly one text node (the placeholder), no child elements` | error | the slot element has an element child or no child | hold one text node | [Dynamic text](page:authoring/dynamic-text#limits-and-errors) |
| `layout: data-slot "<name>" placeholder wraps to <n> lines — slots are single-line; add white-space: nowrap or widen the box` | error | the placeholder does not fit on one line | add `white-space: nowrap` or widen the box | [Dynamic text](page:authoring/dynamic-text#limits-and-errors) |
| `layout: duplicate data-slot name "<name>"` | error | two slots in one document share a name | rename one, or add `{i}` under a repeat | [Dynamic text](page:authoring/dynamic-text#names) |
| `layout: <img> on line <n> has no src attribute (or data-tex-slot, for a slot the app fills at runtime)` | error | an `<img>` with neither attribute | add `src` or `data-tex-slot` | [Images](page:authoring/images#limits-and-errors) |
| `layout: <img src="<src>"> on line <n>: relative path but no asset base — compile from files (compileFiles) or pass options.assetDir` | error | a relative `src` compiled from strings | compile from files | [Images](page:authoring/images#limits-and-errors) |
| `image: cannot read "<path>": <code>` | error | the file named by `src` cannot be opened | fix the path | [Images](page:authoring/images#limits-and-errors) |
| `image: "<path>" is not a PNG — only PNG is supported at build time; convert other formats before compiling` | error | the 8-byte PNG signature does not match | convert to PNG | [Images](page:authoring/images#limits-and-errors) |
| `image: "<path>": malformed PNG (IHDR not first chunk)` | error | the first chunk is not `IHDR` | re-encode the file | [Images](page:authoring/images#limits-and-errors) |
| `image: "<path>": zero-sized PNG` | error | the IHDR width or height is 0 | re-encode the file | [Images](page:authoring/images#limits-and-errors) |
| `layout: <img> on line <n>: data-tex-slot needs a name with no leading or trailing whitespace — it is how the app addresses the slot at runtime, matched byte for byte, and "<value>" would not match what it reads here` | error | the attribute value has surrounding whitespace | trim the name | [Images](page:authoring/images#streamed-slots) |
| `layout: <img> on line <n>: data-tex-slot="<name>" and src are mutually exclusive — a slot is either baked from a file or filled at runtime, and carrying both would leave it ambiguous which one the console draws` | error | both attributes on one `<img>` | keep one | [Images](page:authoring/images#streamed-slots) |
| `layout: <img> on line <n>: palettize is not supported on a streamed slot — quantizing needs the art, which does not exist until runtime. Supply PSMCT32 texels to ps2ui_tex_set` | error | `palettize` on a `data-tex-slot` element | delete `palettize` | [Images](page:authoring/images#streamed-slots) |
| `layout: <img data-tex-slot="<name>"> needs an explicit width and height — a streamed slot has no file to take its intrinsic size from, and the reservation is sized from these` | error | a streamed slot with no CSS `width` and `height` | set both | [Images](page:authoring/images#streamed-slots) |
| `layout: <tag> line <n>: nested focusable inside another focusable — the D-pad model has one focus ring; flatten the hierarchy.` | error | `focusable` inside another focusable's subtree | flatten the markup | [Focus and navigation](page:authoring/focus-and-navigation#limits-and-errors) |
| `layout: <tag> line <n>: data-repeat on the root element has nothing to repeat into; put it on a child` | error | `data-repeat` on the document root | move it to a child | [Lists](page:authoring/lists#expansion) |
| `layout: <tag> line <n>: data-repeat="<raw>" is not a whole number. The count is baked, so it cannot come from data.` | error | the count does not match `/^\d+$/` | write a decimal integer | [Lists](page:authoring/lists#limits-and-errors) |
| `layout: <tag> line <n>: data-repeat="<n>" is out of range 1..256. Every copy costs commands, and a focusable one costs a focus node, so this is a budget you want to feel.` | error | a count of 0, or above 256 | lower the count | [Lists](page:authoring/lists#limits-and-errors) |
| `layout: <tag> line <n>: data-repeat inside data-repeat. Only one index is in scope, so the inner {i} would be ambiguous.` | error | a repeat inside a repeat subtree | write the inner rows out | [Lists](page:authoring/lists#limits-and-errors) |
| `layout: root element is display: none` | error | the root element resolves to `display: none` | give it `display: flex` | [CSS](page:authoring/css#scissor-and-display-none) |
| `layout: <n> container(s) lay out two or more children without stating flex-direction:` then one `  <tag> line <n> (<m> children)` per offender, then `There is no default. CSS's initial value is row, ps2ui once used column, so either silent answer is wrong for half of all authors — add flex-direction: row or column to each.` | error | a container with two or more children and no `flex-direction` declaration | declare `flex-direction` on each named container | [CSS](page:authoring/css#the-two-hard-rules) |
| `no font metrics at <path>.` then five remedy lines naming `ps2ui-fontgen`, `--font-dir` and `--fonts` | error | `--font-dir` points at a directory missing `default.metrics.json` or `default-bold.metrics.json` | generate the metrics, or pass `--fonts` | [Text and fonts](page:authoring/text-and-fonts#limits-and-errors) |
| `<path>: cannot be read as a fonts.json manifest (<reason>). It maps "regular" and "bold" to { ttf: [...], metrics: "..." }; ps2ui-bake reads the same file.` | error | `--fonts` names a file `JSON.parse` rejects | fix the manifest | [Text and fonts](page:authoring/text-and-fonts#limits-and-errors) |
| `<path>: no "<face>" face with a "metrics" path. Generate one with: ps2ui-fontgen <font.ttf> default <400\|700> <out.metrics.json>` | error | the manifest has no `metrics` for that face | add the `metrics` key | [Text and fonts](page:authoring/text-and-fonts#limits-and-errors) |
| `layout: internal: <what> has <n> theme values, expected <m>` | error | reachable from a sheet that declares `@theme` and defines no `:root` custom property | add one `:root` name | [Theming](page:authoring/theming#limits-and-errors) |
| `layout: internal: <what> carries the name <var> but no per-theme values -- a themed colour resolved through a path that did not carry the vector` | error | unreachable; `resolveColorValue` sets the name and the vector together at every return | nothing to fix | [Theming](page:authoring/theming#roles-not-values) |
| `bad direction <dir>` | error | unreachable; `findTarget` is called only from the four-entry direction loop | nothing to fix | [Focus and navigation](page:authoring/focus-and-navigation#the-solver) |
| `warning: unknown attribute: <tag> line <n>: <attr> is not read by anything`, then `— did you mean <known>?` or `— known: <sorted list>` | warning | a `data-` attribute outside the six the compiler reads; one line per typo | correct the spelling | [HTML](page:authoring/html#reference-table) |
| `layout: <tag> line <n>: data-repeat="<n>" but no {i} or {n} anywhere inside, so every copy is identical. Add {i} to the ids and data-slot names, or the copies cannot be told apart.` | warning | a count above 1 with no index substitution in the subtree | add `{i}` to the ids and slot names | [Lists](page:authoring/lists#expansion) |
| `focus: "<name>" is unreachable from the initial focus by D-pad` | warning | the breadth-first walk from `initial` never reaches that node | move the element, or pass `--focus-wrap` | [Focus and navigation](page:authoring/focus-and-navigation#limits-and-errors) |
| `css: :focus styles matched <tag> line <n> but no enclosing element has the focusable attribute; the delta can never show` | warning | unreachable; a `:focus` compound never matches outside a focusable scope | nothing to fix | [Focus and navigation](page:authoring/focus-and-navigation#limits-and-errors) |

## Lints

[lint.js](repo:packages/layout/src/lint.js) pushes ten warnings over eight
rule names. Each prints as `warning: <rule>: <message>` and leaves the exit
code at 0. A lint from a theme row above 0 is prefixed `@theme <name>: `.
`data-nocontrast` is the only per-rule opt-out, and it silences `contrast`
alone.

| message | severity | cause | fix | page |
|---|---|---|---|---|
| `aspect-distortion: <n> rounded corner(s) draw <p>% <wider\|narrower> than tall at PAR <par>; divide the radius by <par> to look round` | warning | `abs(par - 1) > 0.08` and at least one rect has a radius | divide the radius by the PAR | [CRT linter](page:authoring/crt-linter#reference-table) |
| `aspect-distortion: <n> image(s) draw <p>% <wider\|narrower> than tall at PAR <par>; pre-squash the art or set an explicit width` | warning | the same PAR test, with at least one image command | pre-squash the art | [CRT linter](page:authoring/crt-linter#reference-table) |
| `interlace-flicker: 1px line at (<x>,<y>) will shimmer on an interlaced CRT; use 2px` | warning | `border-width: 1px`, or a filled rect one pixel tall | use 2px | [CRT linter](page:authoring/crt-linter#reference-table) |
| `ntsc-red-bleed: saturated red fill rgb(<r>,<g>,<b>) at (<x>,<y>) smears on composite video` | warning | a fill with `r > 200`, `g < 80` and `b < 80` | desaturate the fill | [CRT linter](page:authoring/crt-linter#reference-table) |
| `min-font-size: "<text>" is <n>px; below <m>px is unreadable from a couch` | warning | a text command below the floor, 14px by default | raise `font-size`, or pass `--min-font-size` | [CRT linter](page:authoring/crt-linter#reference-table) |
| `overscan: text "<text>" at (<x>,<y>) leaves the title-safe area; a CRT may crop it` | warning | the text origin sits inside the 5 percent inset, or its baseline runs past the bottom inset | move the text inward | [CRT linter](page:authoring/crt-linter#reference-table) |
| `charset: codepoint U+<hex> in "<text>": non-Latin text wrapping is untested` | warning | the first codepoint above U+24FF outside the five allowed blocks | keep to the shipped charset | [Text and fonts](page:authoring/text-and-fonts#the-charset) |
| `contrast: "<text>" contrast <r>:1 < <m>:1<, over a <bright\|dark> frame showing through the <p>%-transparent background> — CRTs crush shadows harder than your monitor` | warning | the WCAG ratio against the composited background is below 3.0 | recolour the text or its background, or set `data-nocontrast` | [CRT linter](page:authoring/crt-linter#contrast) |
| `focus-target-size: focusable "<name>" is <w>x<h>px; smaller than 24px is hard to see highlighted from 3 meters` | warning | a focusable narrower or shorter than 24px | enlarge the focusable | [CRT linter](page:authoring/crt-linter#reference-table) |
| `overscan: focusable "<name>" extends past the action-safe area` | warning | the focusable's rect leaves the canvas; the message names an inset the check never computes | shrink the focusable | [CRT linter](page:authoring/crt-linter#reference-table) |

## Bake

`ps2ui-bake` prints `error: <message>` for the IR and cap refusals. It prints
`ps2ui-bake: <message>` for anything it caught as an exception. Every refusal
happens before the first write, so no `.uib` appears. Compiler warnings
carried in the IR are re-printed as `warning (layout <stem>): <message>`.

```
$ ps2ui-bake deep.json -o deep.uib --fonts fonts/fonts.json
  runtime tables: 0 textures, 0 CLUTs, 0 slots, 1 screens
error: scissor nesting: 9 levels reaches PS2UI_MAX_SCISSOR_DEPTH = 8. ps2ui_render has a fixed stack and cannot report an overflow, so the deepest subtree would draw under its parent's clip instead of its own. Flatten the nesting or raise PS2UI_MAX_SCISSOR_DEPTH in runtime/ps2ui.h.
$ echo $?
1
```

| message | severity | cause | fix | page |
|---|---|---|---|---|
| `error: <path>: IR version <n>, expected 1` | error | an IR file the compiler did not write, or a stale one | recompile the screen | [ps2ui-bake](page:cli/ps2ui-bake#exit-codes) |
| `error: duplicate screen name '<stem>' (file stems must be unique)` | error | two IR paths share a file stem | rename one IR file | [ps2ui-bake](page:cli/ps2ui-bake#exit-codes) |
| `ps2ui-bake: no font manifest. The built-in default is the repository's fonts/fonts.json, which only exists in a checkout.` plus a template and two remedy lines | error | no `--fonts` and no `fonts/fonts.json` three directories above the package | write a manifest and pass `--fonts` | [ps2ui-bake](page:cli/ps2ui-bake#font-manifest-resolution) |
| `ps2ui-bake: <path>: no such fonts.json. It maps "regular" and "bold" to {ttf: [...], metrics: "..."}; generate the metrics with ps2ui-fontgen, and ps2ui-layout reads the same file via --fonts.` | error | `--fonts` names a file that does not exist | fix the path | [ps2ui-bake](page:cli/ps2ui-bake#font-manifest-resolution) |
| `ps2ui-bake: fonts.json: no candidate TTF for '<face>' exists: [...]` | error | every `ttf` candidate for that face is missing | add a path that exists | [Text and fonts](page:authoring/text-and-fonts#faces-and-weights) |
| `ps2ui-bake: '<key>'` | error | the manifest is missing a key the loader indexes, such as `ttf` | add the key | [ps2ui-bake](page:cli/ps2ui-bake#font-manifest-resolution) |
| `ps2ui-bake: the IR and the font manifest describe different fonts:` then one line per mismatch and a remedy line | error | the compiler measured with one face and the baker would draw another | pass one manifest to both commands | [ps2ui-bake](page:cli/ps2ui-bake#font-manifest-resolution) |
| `ps2ui-bake: image: cannot decode '<src>': <reason>` | error | the file passed the PNG header check and Pillow still refuses it | re-encode the file | [Images](page:authoring/images#limits-and-errors) |
| `` ps2ui-bake: image: '<src>' is an indexed PNG at <w>x<h> but is laid out at <w>x<h>. Indexed sources are baked verbatim to preserve their palette, which resizing cannot do. Author it at the laid-out size, or remove `palettize` to have it requantized instead. `` | error | `palettize` on an indexed PNG whose file size differs from its laid-out size | author it at the laid-out size | [Images](page:authoring/images#palettize) |
| `ps2ui-bake: image: streamed slot '<name>' is laid out at <w>x<h> in one place and <w>x<h> in another; a slot has one reservation, so give them the same size or different names` | error | one `data-tex-slot` name at two sizes | match the sizes, or split the names | [Images](page:authoring/images#streamed-slots) |
| `ps2ui-bake: screen '<name>': canvas <a> differs from <b> — all screens share one video mode` | error | two IR files baked together carry different canvases | compile every screen at one mode | [ps2ui-bake](page:cli/ps2ui-bake#exit-codes) |
| `ps2ui-bake: unknown IR command op: <op>` | error | an IR command the flattener has no case for | recompile the screen | [ps2ui-bake](page:cli/ps2ui-bake#exit-codes) |
| `ps2ui-bake: slot name '<name>' is on screen '<a>' and screen '<b>'; slot names resolve over the whole file, so only the first would ever be reachable from the app` | error | two screens in one bake declare one slot name | prefix the names per screen | [Dynamic text](page:authoring/dynamic-text#names) |
| `ps2ui-bake: slot "<name>": letter-spacing <n>px does not fit the format's i16 field (-32768..32767px). If this is not a typo, the .uib slot entry is the thing to change.` | error | `letter-spacing` on a slot outside the i16 range | use a plausible value | [Dynamic text](page:authoring/dynamic-text#what-the-blob-carries) |
| `error: scissor nesting: <n> levels reaches PS2UI_MAX_SCISSOR_DEPTH = 8. ps2ui_render has a fixed stack and cannot report an overflow, so the deepest subtree would draw under its parent's clip instead of its own. Flatten the nesting or raise PS2UI_MAX_SCISSOR_DEPTH in runtime/ps2ui.h.` | error | eight or more nested `overflow: hidden` boxes on one screen | flatten the nesting | [ps2ui-bake](page:cli/ps2ui-bake#exit-codes) |
| `error: <textures\|slots\|screens\|cluts>: <n> does not fit the format's uint16 count field. This is the format's own limit, not a runtime one.` | error | a table longer than 65535 entries | split the blob | [ps2ui-bake](page:cli/ps2ui-bake#exit-codes) |
| `error: slot '<name>': capacity <n> does not fit the format's uint16 capacity field.` | error | `data-slot-capacity` above 65535 | lower the capacity | [Dynamic text](page:authoring/dynamic-text#reference-table) |
| `error: texture VRAM footprint exceeds budget (see breakdown above; override with --vram-budget)` | error | the page-rounded texture total is over the budget printed above it | palettize, shrink the art, or raise the budget | [VRAM budget](page:authoring/vram-budget#overriding-the-budget) |
| `warning: '<src>' is an indexed PNG at <w>x<h> laid out at <w>x<h>; --palettize-images requantized it, so its authored palette and index values did not survive. Author it at the laid-out size to keep them.` | warning | `--palettize-images` met an indexed PNG at the wrong size | author it at the laid-out size | [Images](page:authoring/images#palettize) |
| `warning (layout <stem>): <message>` | warning | a warning the compiler recorded in that IR file | fix the compiler warning | [ps2ui-bake](page:cli/ps2ui-bake#output) |
| `tint vector has <n> themes, expected <m>` | error | a writer invariant; the compiler refuses a short vector first | nothing to fix | [Theming](page:authoring/theming#roles-not-values) |
| `tint vector row 0 <rgba> does not match the colour it belongs to <rgba>` | error | a writer invariant on the live row | nothing to fix | [Theming](page:authoring/theming#roles-not-values) |
| `more than 65536 distinct tints` | error | the interned tint table passes the uint16 index ceiling | reuse colours through `var()` names | [Theming](page:authoring/theming#roles-not-values) |
| `channel <n> outside 0..255` | error | a host-side colour crossing was handed a value outside the sRGB byte range | nothing to fix | [ps2ui-bake](page:cli/ps2ui-bake#output) |
| `GS alpha <n> outside 0..128` | error | the inverse crossing was handed a value outside the GS alpha domain | nothing to fix | [Previewer](page:cli/previewer#the-inspector) |

## Check

`ps2ui-check` writes TAP on stdout. A passed check is `ok <n> - <label>`.
A failed warning is `ok <n> - <label> # TODO warning`. A failed error is
`not ok <n> - <label>`. A blob it cannot read produces no TAP at all: one
`ps2ui-check: <path>: <message>` line on stderr and exit 2.

```
$ ps2ui-check --vram-budget 1 examples/memcard/build/ui.uib | sed -n '/not ok/p'
not ok 60 - VRAM 160 KiB within budget 0 KiB
```

| message | severity | cause | fix | page |
|---|---|---|---|---|
| `ps2ui-check: <path>: truncated header` | error, exit 2 | the file is shorter than the 84-byte header | rebake | [ps2ui-check](page:cli/ps2ui-check#exit-codes) |
| `ps2ui-check: <path>: not a .uib (magic 0x<n>)` | error, exit 2 | the first four bytes are not `0x31424955` | check the path | [ps2ui-check](page:cli/ps2ui-check#exit-codes) |
| `ps2ui-check: <path>: version <n>, expected 7` | error, exit 2 | a blob from another format version | rebake with this toolchain | [Compatibility](page:reference/compatibility#format-compatibility) |
| `ps2ui-check: <path>: unknown feature bits 0x<n>` | error, exit 2 | a feature bit outside the known `0x1F` | rebake with this toolchain | [Errors and constants](page:runtime/errors-and-constants#feature-bits) |
| `ps2ui-check: <path>: crc mismatch (file 0x<a>, computed 0x<b>)` | error, exit 2 | the file was edited or truncated after the bake | rebake | [ps2ui-check](page:cli/ps2ui-check#exit-codes) |
| `ps2ui-check: <path>: truncated (blob extends past EOF)` | error, exit 2 | the header's blob extent runs past the file | rebake | [ps2ui-check](page:cli/ps2ui-check#exit-codes) |
| `ps2ui-check: <path>: n_theme is 0 (a themeless blob still has one row)` | error, exit 2 | the theme count is zero | rebake | [Theming](page:authoring/theming#runtime) |
| `ps2ui-check: <path>: <n> themes without FEAT_ROLE_TINTS -- tints keyed on the resolved colour cannot diverge between themes` | error, exit 2 | more than one theme row with bit 4 clear | rebake | [Theming](page:authoring/theming#runtime) |
| `ps2ui-check: <path>: <kind> <i> <which> index <n> is past the <m>-entry tint table` | error, exit 2 | a command or slot points outside the tint table | rebake | [ps2ui-check](page:cli/ps2ui-check#exit-codes) |
| `not ok <n> - <label>` | error | one of the catalogue's structural checks failed; the label names the invariant and lists the offending indices | follow the label | [ps2ui-check](page:cli/ps2ui-check#the-catalogue) |
| `ok <n> - <label> # TODO warning` | warning | one of the three CRT checks failed: hairlines, dead commands, undrawn textures | fix the geometry, or declare the count | [ps2ui-check](page:cli/ps2ui-check#declared-counts) |
| `not ok <n> - VRAM <u> KiB within budget <b> KiB` plus ` -- the default budget is unusable at this canvas, see notes` under an impossible default | error | the blob's texture total is over the budget | palettize, shrink the art, or set `vramBudget` | [VRAM budget](page:authoring/vram-budget#when-the-default-cannot-exist) |
| `ok <n> - <m> <noun>, but <k> declared deliberate (--allow-<dead\|hairline>): <k> of the instruments that count names is gone, and the check can no longer see what it measures # TODO warning` | warning | `--allow-dead` and `--allow-hairline` are exact counts, so fewer than declared warns too | set the flag to the count the blob has | [ps2ui-check](page:cli/ps2ui-check#declared-counts) |

## Project and CLI

`ps2ui` prints `ps2ui: <message>` and exits 1 for every project failure.
`ps2ui serve` is the exception and prints `ps2ui serve: <message>`. An
argparse rejection exits 2 from any subcommand. `ps2ui-layout`, `ps2ui-dev`
and `ps2ui-fontgen` answer a malformed command line with a usage line and
exit 2.

| message | severity | cause | fix | page |
|---|---|---|---|---|
| `ps2ui: <path>: no such project file.` plus four lines showing the two required keys | error | the path names no `ps2ui.json` | write the project file | [ps2ui](page:cli/ps2ui#build) |
| `ps2ui: <path>: not valid JSON -- <parser message>` | error | the project file does not parse | fix the JSON | [The project file](page:authoring/project-file#reference-table) |
| `ps2ui: <path>: the top level must be an object` | error | the file holds a list or a scalar | wrap it in an object | [The project file](page:authoring/project-file#reference-table) |
| `ps2ui: <path>: unknown key(s) '<k>'.` then `  A project takes: <every key>` | error | a misspelt or invented top-level key | use a key from the list | [The project file](page:authoring/project-file#reference-table) |
| `ps2ui: <path>: "screens" is required and must not be empty` | error | `screens` is absent or empty | name at least one screen | [The project file](page:authoring/project-file#reference-table) |
| `ps2ui: <path>: "screens" must be a list` | error | `screens` holds something else | write a list | [The project file](page:authoring/project-file#reference-table) |
| `ps2ui: screens[<i>] is <repr>; a screen is a path, or an object with "html" and optionally "css" or "focusWrap"` | error | a screen entry is neither a string nor an object | write a path or an object | [The project file](page:authoring/project-file#reference-table) |
| `ps2ui: screens[<i>] has unknown key(s) '<k>'; a screen takes css, focusWrap, html` | error | a misspelt key on a screen entry | use one of the three | [The project file](page:authoring/project-file#reference-table) |
| `ps2ui: screens[<i>] has no "html"` | error | a screen object with no markup path | add `html` | [The project file](page:authoring/project-file#reference-table) |
| `ps2ui: screens[<i>] (<html>) has no stylesheet: set "css" at the top level for every screen, or on this one` | error | neither the project nor the screen names a stylesheet | set `css` | [The project file](page:authoring/project-file#reference-table) |
| `ps2ui: cannot find ps2ui-layout, which compiles the HTML and CSS.` plus three remedy lines | error | no `PS2UI_LAYOUT`, no `ps2ui-layout` on PATH and no checkout beside the package | install `@ophtml/layout`, or set `PS2UI_LAYOUT` | [ps2ui](page:cli/ps2ui#how-build-finds-the-compiler) |
| `ps2ui: ps2ui-layout failed on <html> (exit <n>)` | error | the compiler refused that screen and already said why | fix what the compiler printed | [ps2ui](page:cli/ps2ui#build) |
| `` ps2ui: <path>: no blob to check. Run `ps2ui build` first -- this does not build, so that a check can never report on a blob it just made and nobody has seen. `` | error | `ps2ui check` ran before any build | run `ps2ui build` | [ps2ui](page:cli/ps2ui#check) |
| `ps2ui: no screen named '<name>' in ps2ui.json. It has: <names>` | error | `ps2ui dev --screen` names a screen the project lacks | use a listed name | [ps2ui](page:cli/ps2ui#dev) |
| `ps2ui: ps2ui dev watches one screen and this project has <n>. Name one: ps2ui dev --screen <name>, where <name> is one of: <names>` | error | `ps2ui dev` on a multi-screen project with no `--screen` | pass `--screen` | [ps2ui](page:cli/ps2ui#dev) |
| `ps2ui: <files> in <dir> <differ\|differs> from the runtime this toolchain ships, so nothing was written.` plus the mixed-pair explanation | error | `ps2ui vendor-runtime` found an edited `ps2ui.c` or `ps2ui.h` in the destination | pass `--force`, or move your copy aside | [ps2ui](page:cli/ps2ui#vendor-runtime) |
| `ps2ui: two copies of the runtime disagree, so this will not guess which one you meant.` plus the two paths and a rebuild line | error | a staged package-data runtime is out of date against the checkout | rebuild the package, or delete the staged directory | [ps2ui](page:cli/ps2ui#vendor-runtime) |
| `ps2ui: no C runtime to vendor.` plus the two directories looked in and a packaging note | error | an installed wheel shipped without its runtime | install from the sdist | [ps2ui](page:cli/ps2ui#vendor-runtime) |
| `ps2ui-fontgen: this Pillow has no Raqm layout engine, so kerning cannot be extracted; refusing to write a metrics file without it.` plus a platform-specific remedy | error, exit 2 | `PIL.features.check("raqm")` is false | install libraqm and rebuild Pillow | [ps2ui-fontgen](page:cli/ps2ui-fontgen#ps2ui-fontgen) |
| `usage: python -m ps2ui_bake.fontgen <font.ttf> <family> <weight> <out.metrics.json> [charset-file]` | error, exit 2 | fewer than four positional arguments | pass all four | [ps2ui-fontgen](page:cli/ps2ui-fontgen#ps2ui-fontgen) |
| `ps2ui-fontgen: no Raqm; kerning table will be empty` | warning | a Python caller reached `build_kerning` without Raqm; `main` refuses earlier | call `main` instead | [ps2ui-fontgen](page:cli/ps2ui-fontgen#ps2ui-fontgen) |
| `usage: ps2ui-layout <page.html> <page.css> -o <ui.json> [--mode ntsc\|ntsc16x9\|pal\|pal16x9] [--display-aspect W:H] [--canvas WxH] [--font-dir DIR] [--fonts fonts.json] [--focus-wrap] [--strict] [--min-font-size PX] [--version]` | error, exit 2 | a missing positional, a missing `-o`, an unknown `--mode`, or a `--canvas` that is not `WxH` | correct the command line | [ps2ui-layout](page:cli/ps2ui-layout#options) |
| `ps2ui-layout: --min-font-size takes a positive integer` | error, exit 2 | `--min-font-size` given zero or a non-number | pass a positive integer | [CRT linter](page:authoring/crt-linter#reference-table) |
| `ps2ui-layout: --strict: <n> warning(s)` | error, exit 1 | `--strict` and at least one warning in the IR | fix the warnings | [CRT linter](page:authoring/crt-linter#strict) |
| `usage: ps2ui-dev <page.html> <page.css> -o <outdir> [--mode ntsc\|pal] [--canvas WxH] [--font-dir DIR] [--fonts fonts.json] [--focus-wrap] [--strict] [--min-font-size PX] [--montage] [--palettize-images] [--once] [--version]` | error, exit 2 | the same argument faults, in the watcher | correct the command line | [ps2ui-dev](page:cli/ps2ui-layout#options) |
| `bake failed` | error, exit 1 under `--once` | `ps2ui-dev` compiled the screen and the bake step returned non-zero | read the baker's own line above it | [ps2ui-dev](page:cli/ps2ui-layout#output) |
| `aspect: "<text>" is not a ratio like 4:3 or 16:9` | error, exit 1 | `--display-aspect` given anything but `<digits>:<digits>`; printed as a Node stack trace, not an `error:` line | write `4:3` or `16:9` | [Video modes](page:authoring/video-modes#reference-table) |
| `aspect: "<text>" has a zero term` | error, exit 1 | `--display-aspect` given a zero numerator or denominator; also a stack trace | write a non-zero ratio | [Video modes](page:authoring/video-modes#reference-table) |

## Previewer

`ps2ui serve` refuses before binding and prints one `ps2ui serve: <message>`
line with exit 1. Once it is running, a bad `/input` body is answered with
HTTP 400 and a JSON `{"error": ...}` body, and the server stays up. The
`ps2ui_bake.preview` module raises `ValueError` to Python callers.

| message | severity | cause | fix | page |
|---|---|---|---|---|
| `ps2ui serve: no screen named '<name>'. The blob has: <names>` | error | `--screen` names a screen the blob lacks | use a listed name | [Previewer](page:cli/previewer#options) |
| `ps2ui serve: no theme <n>; the blob has <m>` | error | `--theme` is at or past the tint table's row count | pass a row that exists | [Previewer](page:cli/previewer#options) |
| `ps2ui serve: the first build failed, so there is nothing to serve:` then the pipeline's summary line | error | the project did not compile on the first pass | fix what the compiler printed to the terminal | [Previewer](page:cli/previewer#watching) |
| `ps2ui serve: watch mode compiles HTML and CSS, which needs the Node half.` plus three remedy lines | error | no compiler is reachable and no `--uib` was given | install `@ophtml/layout`, or pass `--uib` | [Previewer](page:cli/previewer#synopsis) |
| `ps2ui serve: ports <a>-<b> are all busy` | error | every port from 8080 to 8099 is taken | pass `--port` | [Previewer](page:cli/previewer#ports) |
| `{"error": "no recognised field in ['<k>', ...]"}` | error, HTTP 400 | a `/input` body with none of `key`, `screen`, `theme`, `aspect`, `slot` | post one recognised field | [Previewer](page:cli/previewer#routes) |
| `{"error": "'<name>'"}` | error, HTTP 400 | `/input` named a screen the blob lacks; the body is the bare value | post a screen the blob carries | [Previewer](page:cli/previewer#routes) |
| `{"error": "<n>"}` | error, HTTP 400 | `/input` named a theme row past the end | post a row that exists | [Previewer](page:cli/previewer#routes) |
| `{"error": "'<mode>'"}` | error, HTTP 400 | `/input` named an aspect outside the four modes | post `framebuffer`, `authored`, `force-4:3` or `force-16:9` | [Previewer](page:cli/previewer#aspect) |
| `no screen named '<name>'` | error | `preview.render(uib, screen=...)` was given a name the blob lacks | pass an index or a real name | [Previewer](page:cli/previewer#output) |
| `theme <n> is past the <m>-row tint table` | error | `preview.render(uib, theme=...)` was given a row past the end | pass a row that exists | [Theming](page:authoring/theming#seeing-each-theme) |
| `offset (<x>, <y>) does not fit the int16 pair on the context; ps2ui_offset_set returns PS2UI_ERR_RANGE for this` | error | `preview.render(uib, offset=...)` was given a value outside int16 | stay inside the int16 range | [Moving and hiding](page:runtime/moving-and-hiding#limits-and-errors) |
| `slot '<name>': <n> bytes of texels for a <w>x<h> PSMCT32 reservation (<m> B). ps2ui_tex_set would return PS2UI_ERR_SIZE for this.` | error | `tex_fills` handed `preview.render` the wrong payload length | send exactly the reservation | [Streaming art](page:runtime/streaming-art#limits-and-errors) |
| `texture format <n>` | error | a texture format the previewer cannot draw; `read_uib` admits only two | nothing to fix | [Previewer](page:cli/previewer#limits) |
| `op <n>` | error | a command op the previewer has no case for; `read_uib` admits only four | nothing to fix | [Previewer](page:cli/previewer#limits) |
| `unbalanced scissor stack in command list` | error | a screen whose pushes and pops do not balance; `ps2ui-check` refuses one first | run `ps2ui-check` | [ps2ui-check](page:cli/ps2ui-check#the-catalogue) |

## Runtime load

`ps2ui_load` returns a negative code and touches nothing. The checks run in
this order, so the first failure is the one reported. The codes are in
`runtime/ps2ui.h`.

| message | severity | cause | fix | page |
|---|---|---|---|---|
| `PS2UI_ERR_TRUNCATED` (-1) | error | the file is shorter than the 84-byte header, or a table extent or the blob region runs past `size` | pass the real byte count | [Errors and constants](page:runtime/errors-and-constants#error-codes) |
| `PS2UI_ERR_MAGIC` (-2) | error | the header magic is not `0x31424955` | load a `.uib` | [Errors and constants](page:runtime/errors-and-constants#error-codes) |
| `PS2UI_ERR_VERSION` (-3) | error | the header version is not 7 | rebake with this toolchain | [Compatibility](page:reference/compatibility#format-compatibility) |
| `PS2UI_ERR_FEATURES` (-7) | error | a feature bit outside `PS2UI_FEAT_KNOWN`, or a streamed texture with bit 3 clear | rebake with this toolchain | [Errors and constants](page:runtime/errors-and-constants#feature-bits) |
| `PS2UI_ERR_BOUNDS` (-4) | error | `n_screen` 0, `n_theme` 0, or any cross-reference in the per-table loops | rebake, and run `ps2ui-check` on the blob | [Errors and constants](page:runtime/errors-and-constants#load-check-order) |
| `PS2UI_ERR_TINTS` (-14) | error | `n_theme > 1` with `PS2UI_FEAT_ROLE_TINTS` clear | rebake with this toolchain | [Theming](page:authoring/theming#runtime) |
| `PS2UI_ERR_CRC` (-6) | error | crc32 over the file with the crc field zeroed does not match the header | rebake, or reread the file | [Errors and constants](page:runtime/errors-and-constants#error-codes) |
| `PS2UI_ERR_ALIGN` (-8) | error | the blob region address, a baked texture's `data_off`, or the arena is not 16-aligned | align the buffer to 16 bytes | [Integrating the runtime](page:runtime/integrating#limits-and-errors) |
| `PS2UI_ERR_TOO_MANY` (-5) | error | the counts are legal and the arena carve exceeds the target's `size_t` | shrink the UI | [Errors and constants](page:runtime/errors-and-constants#error-codes) |
| `PS2UI_ERR_ARENA` (-9) | error | the arena is NULL, or smaller than `ps2ui_arena_size()` | size the arena from the bake's arena line | [ps2ui-bake](page:cli/ps2ui-bake#the-arena-line) |

## Runtime calls

Only `ps2ui_load`, `ps2ui_tex_set`, `ps2ui_clut_set`, `ps2ui_theme_set` and
`ps2ui_offset_set` return a `PS2UI_ERR_` code. `ps2ui_upload` returns 0 or -1.
Everything else reports failure as 0, NULL or -1, and the runtime prints
nothing at all.

| message | severity | cause | fix | page |
|---|---|---|---|---|
| `PS2UI_ERR_BOUNDS` (-4) | error | a null context passed to `ps2ui_clut_set`, `ps2ui_theme_set` or `ps2ui_offset_set` | pass the context | [Errors and constants](page:runtime/errors-and-constants#error-codes) |
| `PS2UI_ERR_NOT_STREAMED` (-10) | error | `ps2ui_tex_set` with a null context, GS global or texel pointer, an unknown name, or a baked texture | name a `data-tex-slot` reservation | [Streaming art](page:runtime/streaming-art#limits-and-errors) |
| `PS2UI_ERR_ALIGN` (-8) | error | `ps2ui_tex_set` was given a texel buffer that is not 16-aligned | align the buffer to 16 bytes | [Streaming art](page:runtime/streaming-art#limits-and-errors) |
| `PS2UI_ERR_SIZE` (-11) | error | `ps2ui_tex_set` `len` differs from the reservation, or `ps2ui_clut_set` `ncolors` is above the baked count | pass the payload figure the bake printed | [VRAM budget](page:authoring/vram-budget#which-number-the-runtime-wants) |
| `PS2UI_ERR_RANGE` (-12) | error | a CLUT index at or past `n_clut`, a theme at or past `n_theme`, or an offset outside int16 | stay inside the blob's counts | [Errors and constants](page:runtime/errors-and-constants#error-codes) |
| `PS2UI_ERR_STATE` (-13) | error | `ps2ui_clut_set` called before `ps2ui_upload` | upload first | [Streaming art](page:runtime/streaming-art#limits-and-errors) |
| `-1` from `ps2ui_upload` | error | the VRAM preflight exceeds 4 MiB; nothing is transferred and the context stays not-uploaded | cut the texture footprint | [VRAM budget](page:authoring/vram-budget#on-the-console) |
| `0`, `NULL` or `-1` from a query | silent | an unknown name in `ps2ui_focus_set`, `ps2ui_slot_set`, `ps2ui_visible_set` or `ps2ui_screen_set`; an out-of-window list row | check the name against the blob | [C API reference](page:runtime/api-reference#function-tables-by-group) |
