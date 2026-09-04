# @ophtml/layout

The Node half of the OPHTML toolchain, published to npm as
`@ophtml/layout`. It provides the `ps2ui-layout` and `ps2ui-dev`
commands. OPHTML is the product, ps2ui is the format and the tools
that speak it.

First stage of the [ps2ui toolchain](https://github.com/coffeedevsolutions/OPHTML/blob/main/README.md): parses HTML and
CSS and produces the `ui.json` intermediate representation that
`ophtml` (PyPI) bakes into a `.uib` blob the C99 runtime replays on the
PlayStation 2. **Zero runtime dependencies**, Node >= 18.

```sh
npx --package @ophtml/layout ps2ui-layout page.html page.css -o ui.json
```

Everything expensive happens here and in the baker: parsing, the
flexbox pass, text measurement and wrapping, D-pad edge solving, and
the paint order. The console never does any of it.

## What it decides

- **Layout.** A flexbox subset. `flex-direction` is required on any
  container with two or more children, because the old implicit default
  was `column` where CSS's initial value is `row`, and requiring the
  answer is the only version with no silent victims.
- **Text.** Measured against the same font metrics the baker and the C
  runtime use, including kerning. The three implementations are held to
  pixel agreement by a cross-language test, which is why a fourth one
  is not welcome.
- **Focus.** `up`/`down`/`left`/`right` edges solved per screen from the
  geometry, so the runtime's D-pad walk is a table lookup.
- **Warnings.** Contrast, overflow, title-safe margins and font size,
  reported per screen. `--strict` turns them into errors.

`ps2ui-dev` watches one screen's HTML and CSS, recompiles and re-bakes
on change, and writes a preview PNG to `build/dev/`. For an interactive
version with arrow-key navigation, screen and theme switching and
aspect toggles, see `ps2ui serve` in the Python package, which renders
through the previewer rather than in the browser.

## Numbers, not opinions

The IR this emits is the contract with the baker, and both halves ship
as one version: `@ophtml/layout` and `ophtml` carry the same number in
the two spellings their ecosystems use, and CI reads them against each
other on every push. See [docs/format-ir.md](https://github.com/coffeedevsolutions/OPHTML/blob/main/docs/format-ir.md)
for the IR and [docs/format-uib.md](https://github.com/coffeedevsolutions/OPHTML/blob/main/docs/format-uib.md) for what
it becomes.
