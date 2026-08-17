# ps2ui-bake

Second stage of the [ps2ui toolchain](../../README.md): turns the
`ui.json` IR produced by `@ps2ui/layout` into a `.uib` blob the C99
runtime replays on the PlayStation 2, plus PNG previews rendered by
replaying that same blob.

```sh
PYTHONPATH=. python3 -m ps2ui_bake ui.json -o ui.uib --preview out.png
```

See `docs/format-uib.md` at the repository root for the file format,
and `ps2ui_bake/rounding.py` for the numeric rules shared with the
layout stage.
