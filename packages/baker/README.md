# ophtml

The Python half of the OPHTML toolchain, published to PyPI as
`ophtml`. It provides the `ps2ui`, `ps2ui-bake`, `ps2ui-check` and
`ps2ui-fontgen` commands, and `ps2ui vendor-runtime`, which hands you
the C runtime. OPHTML is the product, ps2ui is the format
and the tools that speak it.

Second stage of the [ps2ui toolchain](https://github.com/coffeedevsolutions/OPHTML/blob/main/README.md): turns the
`ui.json` IR produced by `@ophtml/layout` into a `.uib` blob the C99
runtime replays on the PlayStation 2, plus PNG previews rendered by
replaying that same blob.

```sh
PYTHONPATH=. python3 -m ps2ui_bake ui.json -o ui.uib --preview out.png
```

`ps2ui serve` puts that same replay behind a localhost page with
arrow-key navigation, screen and theme switching, four aspect modes and
click-to-inspect over the command list. `--uib blob.uib` serves any
`.uib` with no project and no Node. It renders through the previewer
rather than in the browser, so it shows what the console draws; it is
not a substitute for running on one. See the repository README.

## Getting it onto a console

`ps2ui vendor-runtime src/` writes `ps2ui.c` and `ps2ui.h` out of this
package, so the console half needs no clone — the runtime you compile is
the one matching the baker that wrote your blob.

**Compiling them is a separate toolchain, and this package cannot
provide it.** The PlayStation 2 is a MIPS target and never the build
host, so the two files have to be cross-compiled:

```sh
docker run --rm -v "$PWD:/src" ghcr.io/ps2dev/ps2dev make -C /src
```

or install [ps2dev](https://github.com/ps2dev/ps2dev) natively. The
authoring half above needs none of this: `pip install ophtml`, a TTF and
Node are enough to build, check and preview a real blob.
[docs/deploying.md](https://github.com/coffeedevsolutions/OPHTML/blob/main/docs/deploying.md)
is the path from an ELF onto hardware.

## Working from a checkout

`pip install -e .` from this directory puts `ps2ui`, `ps2ui-bake`,
`ps2ui-check` and `ps2ui-fontgen` on `PATH` as bare commands, pointed at
the checkout, so the `PYTHONPATH=` prefix is only needed when nothing is
installed, which is the case CI runs in.

See [docs/format-uib.md](https://github.com/coffeedevsolutions/OPHTML/blob/main/docs/format-uib.md)
for the file format, and `ps2ui_bake/rounding.py` for the numeric rules
shared with the layout stage.
