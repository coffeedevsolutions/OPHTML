---
id: authoring/html
title: HTML
description: What the ps2ui parser accepts, every attribute the compiler reads, and every hard error the markup can raise.
section: authoring
order: 11
version: 0.9.0
sources: [packages/layout/src/html.js, packages/layout/src/box.js, packages/layout/src/repeat.js, packages/layout/src/focus.js, packages/layout/src/css.js, packages/layout/test/parse.test.js, packages/layout/test/fonts.test.js, docs/tutorial-uc3.md, examples/memcard/ui/library.html, README.md]
---

# HTML

One HTML file is one screen. `ps2ui-layout` parses it, applies the CSS file beside it, and emits the [IR](page:reference/ir-format#layout).

## What it is

The parser reads the well-formed subset of HTML and refuses everything else with a line number. It is written for markup you author, not markup you scrape. There is no error recovery: a mismatched close tag stops the compile rather than producing a tree nobody wrote.

Structure comes from the element tree. Every visual decision comes from the stylesheet, which the compiler reads from the second positional argument. The document supplies no styling of its own, so a `style` attribute and an inline `<style>` block both go unread.

Thirteen attributes reach the compiler. They are listed under [Reference table](#reference-table). Every other attribute is parsed, kept on the element, and never looked at again.

## Minimal example

This is the screen from the [tutorial](repo:docs/tutorial-uc3.md#L65). `data-repeat` stamps out six rows. Each row holds two slots and one focus node.

```html
<screen name="library">
  <div class="page">
    <div class="header">
      <span class="title">Game Library</span>
      <span class="count" data-slot="count" data-slot-capacity="16">0 titles</span>
    </div>
    <div class="row" data-repeat="6" id="row-{i}" focusable>
      <span class="name" data-slot="name-{i}" data-slot-capacity="40">--</span>
      <span class="size" data-slot="size-{i}" data-slot-capacity="12">--</span>
    </div>
  </div>
</screen>
```

```sh
ps2ui-layout ui/library.html ui/library.css --fonts fonts/fonts.json -o build/library.json
```

```text
ps2ui-layout: 14 paint commands, 6 focusables -> build/library.json
```

`<screen>` is not a ps2ui tag. It is an ordinary element, and the `name` on it does nothing, because the root is not focusable. The IR that run wrote carries 13 slots and 6 focus nodes named `row-0` to `row-5`.

## Reference table

| attribute | element | effect | page |
|---|---|---|---|
| `id` | any | Matches `#id` in the stylesheet. Names the focus node when the element is focusable. | [CSS](page:authoring/css#reference-table) |
| `class` | any | Matches `.class` in the stylesheet. Whitespace-separated. | [CSS](page:authoring/css#reference-table) |
| `name` | any focusable element | Names the focus node when the element carries no `id`. | [Focus and navigation](page:authoring/focus-and-navigation#reference-table) |
| `focusable` | any | Adds a focus node and opens a focus scope. Presence only. | [Focus and navigation](page:authoring/focus-and-navigation#reference-table) |
| `autofocus` | any focusable element | Makes that node the initial focus. Presence only. | [Focus and navigation](page:authoring/focus-and-navigation#behaviour) |
| `src` | `<img>` | PNG path, resolved against the document's directory. | [Images](page:authoring/images#reference-table) |
| `palettize` | `<img>` | Quantizes the image to 8-bit indexed plus CLUT at bake time. Presence only. | [Images](page:authoring/images#behaviour) |
| `data-tex-slot` | `<img>` | Reserves a streamed texture slot under this name instead of baking a file. | [Images](page:authoring/images#behaviour) |
| `data-slot` | any | Marks the element's text as runtime-replaceable under this name. | [Dynamic text](page:authoring/dynamic-text#reference-table) |
| `data-slot-capacity` | a `data-slot` element | Bytes reserved for the runtime string. Defaults to 63. | [Dynamic text](page:authoring/dynamic-text#behaviour) |
| `data-repeat` | any element below the root | Stamps out that many copies of the element at compile time. | [Lists](page:authoring/lists#behaviour) |
| `data-keep` | any | Exempts the element's own geometry from the baker's dead-geometry trim. Presence only. | [ps2ui-bake](page:cli/ps2ui-bake#output) |
| `data-nocontrast` | any | Exempts the element's text from the contrast lint. Presence only. | [CRT linter](page:authoring/crt-linter#reference-table) |

`focusable`, `autofocus`, `palettize`, `data-keep` and `data-nocontrast` test for presence. The value is never read, so `focusable="false"` is focusable.

## Behaviour

### Tags

There is no tag whitelist. Any name matching `[a-zA-Z0-9-]+` becomes an element and lays out under whatever CSS selects it. Tag names and attribute names fold to lower case. Attribute values do not.

| tags | treatment |
|---|---|
| `br`, `hr`, `img`, `input`, `meta`, `link` | Void. They take no closing tag and hold no children. |
| `html`, `body` | Transparent. Both tags are dropped and the children attach to the enclosing element. |
| `head`, `style`, `script`, `title` | Skipped whole, from the open tag to the matching close tag. |
| `<!doctype ...>`, `<!-- ... -->` | Discarded. A comment does not split the text around it. |
| everything else | An ordinary element. |

A document with one top-level element compiles to that element. A document with several gets a synthetic root.

```html
<!doctype html>
<html>
<head><title>skipped</title><style>.page { background: red }</style></head>
<body>
<div class="page">
  <section><my-thing>Any tag lays out</my-thing></section>
  <hr>
  <span>After the rule</span>
</div>
<script>ignored()</script>
</body>
</html>
```

```text
ps2ui-layout: 4 paint commands, 0 focusables -> build/tags.json
```

The four commands are the page rect, the `my-thing` text, the `hr` rect and the `span` text. The inline sheet's red never reaches the page rect, which keeps the external sheet's `#10141f`.

### Text and whitespace

Whitespace collapses once, at parse time. Each text run is entity-decoded, then every whitespace run becomes one space. A run that trims to nothing emits no text node. The stylesheet cannot undo this, and there is no `white-space: pre`.

`&nbsp;` decodes to U+00A0 and then collapses with everything else, so it reaches the IR as an ordinary space. Author a no-break space and it becomes breakable.

### Entities

| entity | character |
|---|---|
| `&amp;` | `&` |
| `&lt;` | `<` |
| `&gt;` | `>` |
| `&quot;` | `"` |
| `&apos;` | `'` |
| `&nbsp;` | U+00A0, then collapsed to a space |
| `&middot;` | `·` |
| `&hellip;` | `…` |
| `&#N;` | code point N, decimal |
| `&#xN;` | code point N, hexadecimal |

Any other name is left in the text exactly as written. Attribute values decode the same way.

```html
<div class="page">
  <span class="label">a&nbsp;&nbsp;b</span>
  <span class="label">one   two
    three</span>
  <span class="label">joined<!-- comment -->up</span>
  <span class="label">&amp; &lt; &gt; &quot; &apos; &middot; &hellip; &#215; &#x25B3; &copy;</span>
</div>
```

```text
"a b"
"one two three"
"joinedup"
"& < > \" ' · … × △ &copy;"
```

That block is the `text` field of each text command in `build/text.json`, and the stylesheet behind it sets `white-space: pre`.

### Repeat substitution

Inside a `data-repeat` subtree, `{i}` becomes the 0-based index and `{n}` the 1-based one. Substitution runs over every attribute value and every text node in the subtree. `data-repeat` itself is consumed and never reaches the cascade. Outside a repeat, the braces stay in the text. Counts and nesting rules live on [Lists](page:authoring/lists#limits-and-errors).

### Naming focus nodes

A focus node takes its name from the element `id`. Failing that it takes the `name` attribute. Failing both it is called `box` followed by the box id, which changes whenever the document changes. Name every focusable element the runtime has to address.

## Limits and errors

Unknown `data-` attributes warn and compile. Unknown attributes without that prefix are silent, so a misspelt `focusabel` produces a screen with no navigation and no message.

```text
warning: unknown attribute: <span> line 2: data-capacity is not read by anything — did you mean data-slot-capacity?
warning: unknown attribute: <span> line 3: data-wobble is not read by anything — known: data-keep, data-nocontrast, data-repeat, data-slot, data-slot-capacity, data-tex-slot
ps2ui-layout: 2 paint commands, 0 focusables -> build/typo.json
```

Compiling the same document with and without `style`, `width`, `height` and `alt` gives two byte-identical IR files and no warning:

```sh
ps2ui-layout plain.html inert.css --fonts fonts/fonts.json -o build/plain.json
ps2ui-layout inert.html inert.css --fonts fonts/fonts.json -o build/inert.json
diff build/plain.json build/inert.json
```

```text
ps2ui-layout: 3 paint commands, 0 focusables -> build/plain.json
ps2ui-layout: 3 paint commands, 0 focusables -> build/inert.json
```

Every row below stops the compile. `ps2ui-layout` prints the message on stderr with an `error: ` prefix and exits 1. Full catalogue on [Diagnostics](page:reference/diagnostics).

| message | cause |
|---|---|
| `html: line N: unexpected end of input in tag` | Input ends between the tag name and `>`. |
| `html: line N: malformed attribute` | An attribute name came out empty, from a leading `=` or a stray `/` inside the tag. |
| `html: line N: attribute A must be quoted` | `=` is followed by something other than `"` or `'`. |
| `html: line N: unterminated attribute A` | Input ends before the closing quote. |
| `html: line N: unterminated comment` | `<!--` has no `-->`. |
| `html: line N: closing </T> with no open element` | A close tag appears with nothing open. |
| `html: line N: closing </T> but <U> (line M) is open` | The close tag does not match the innermost open element. |
| `html: line N: bare "<" in content; write &lt;` | `<` is followed by something that cannot start a tag name. |
| `html: line N: unterminated <T>` | A `head`, `style`, `script` or `title` element has no close tag. |
| `html: <T> opened on line N is never closed` | The stack is not empty at end of input. This one carries no `line N:` prefix. |
| `layout: <T> line N: data-slot needs a name` | `data-slot` is present with an empty value. |
| `layout: <T> line N: a data-slot element must contain exactly one text node (the placeholder), no child elements` | A `data-slot` element is empty or holds a child element. |

The last two come from the box builder, so they carry the `layout:` prefix rather than `html:`.

```sh
ps2ui-layout err/slot-children.html err/base.css --fonts fonts/fonts.json -o build/x.json
```

```text
error: layout: <span> line 2: a data-slot element must contain exactly one text node (the placeholder), no child elements
```

`packages/layout/src/html.js` carries an eleventh throw, `malformed tag <T>`, which no input reaches. Its attribute reader returns only when the cursor sits on `>` or `/>`, and the caller handles both cases above the throw.

## Related pages

- [CSS](page:authoring/css#what-it-is) for selectors, properties and the two hard rules.
- [Dynamic text](page:authoring/dynamic-text#what-it-is) for what a slot does at runtime.
- [Lists](page:authoring/lists#what-it-is) for `data-repeat` counts and the runtime list window.
- [Images](page:authoring/images#what-it-is) for `src`, `palettize` and streamed slots.
- [Focus and navigation](page:authoring/focus-and-navigation#what-it-is) for the solver and reachability.
- [CRT linter](page:authoring/crt-linter#what-it-is) for the contrast rule `data-nocontrast` opts out of.
- [ps2ui-layout](page:cli/ps2ui-layout#options) for the flags that compile a document.
- [ui.json](page:reference/ir-format#layout) for the IR every example above printed.
