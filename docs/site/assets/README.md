# Assets

Screenshots, one folder per page: `assets/<page-id>/<what>.png`.

Every file is registered in `assets.json`:

```json
[
  {
    "path": "assets/authoring/theming/library-theme-1.png",
    "page": "authoring/theming",
    "command": "PYTHONPATH=packages/baker python3 -c \"from ps2ui_bake.uib import read_uib; from ps2ui_bake import preview; preview.render(read_uib('examples/opl-env/build/ui.uib'), screen='library', theme=1).save('OUT')\"",
    "checked": true
  }
]
```

- `command` runs from the repository root with `OUT` replaced by the output
  path. It must be reproducible from a clean build of the examples.
- `checked: true` means `tools/check-site-assets.py` re-runs the command and
  diffs bytes against the committed file. Previewer renders are checked.
- `checked: false` is for Playwright captures of the `ps2ui serve` page,
  whose text rendering is not byte-stable across browser versions. The
  command is still recorded so the capture can be redone.
- UI pixels come from the Python previewer only. The browser never draws
  the UI, in the documentation as in the tool.

`tools/check-site-assets.py` is written by the `cli/ps2ui-bake` brief, the
first to render a PNG, and is added to CI once pages exist.
