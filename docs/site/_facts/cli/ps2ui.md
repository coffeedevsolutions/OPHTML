# facts: cli/ps2ui

Session: every `ps2ui` run below used a scratch copy of an example, made with
`cp -r examples/<name> <scratch>/` and `rm -rf <scratch>/<name>/build`. Nothing
under `examples/*/build/` was written. `opl-env` and `channel6` were copied into
`<scratch>/tree/examples/` so that `../../../examples/channel6/ui/assets/...` in
`opl-env/ui/landing.html` still resolves. The server run used `--port 8433` and
was stopped with `kill` before the `find build` listing that follows it.

Line numbers were re-located by symbol in this session.

| id | fact | source | verified by | status |
|---|---|---|---|---|
| cli.ps2ui.version | `ps2ui --version` prints `ps2ui <ps2ui_bake.__version__>` on stdout and exits 0. This tree prints `ps2ui 0.6.0.dev0`. | packages/baker/ps2ui_bake/ps2ui.py:340-341; packages/baker/ps2ui_bake/__init__.py:39 | `ps2ui --version` printed `ps2ui 0.6.0.dev0`, exit 0; `TestConsoleScriptVersions` in `packages/baker/tests/test_baker.py:3891` asserts the string against `__version__` | verified |
| cli.ps2ui.entry-point | `ps2ui` is the console script for `ps2ui_bake.ps2ui:main`. `ps2ui-layout` and `ps2ui-dev` are npm bins of `@ophtml/layout`, not Python entry points. | packages/baker/pyproject.toml:21-24; packages/layout/package.json `bin` | `python3 -c` over `packages/layout/package.json` printed `{'ps2ui-layout': 'bin/ps2ui-layout.js', 'ps2ui-dev': 'bin/ps2ui-dev.js'}`; `which ps2ui` gave `/usr/local/bin/ps2ui`, `which ps2ui-layout` gave `/opt/node22/bin/ps2ui-layout` | verified |
| cli.ps2ui.subcommands | Six subcommands: `build`, `check`, `fontgen`, `serve`, `vendor-runtime`, `dev`. The subparser is `required=True`, so a bare `ps2ui` prints the usage line and exits 2. Options per subcommand are in the table under `## cli.ps2ui.subcommands`. | ps2ui.py:342 (`required=True`), 344-424 | `ps2ui` printed `ps2ui: error: the following arguments are required: cmd`, exit 2; `ps2ui --help` and `ps2ui <sub> --help` for all six pasted on the page; `ps2ui nope` printed `invalid choice: 'nope' (choose from 'build', 'check', 'fontgen', 'serve', 'vendor-runtime', 'dev')`, exit 2 | verified |
| cli.ps2ui.forwarding | Project keys reach each tool as the flags in the table under `## cli.ps2ui.forwarding`. build: layout gets `--fonts --mode --canvas --display-aspect --strict --min-font-size --focus-wrap`, bake gets `-o --fonts --palettize-images --vram-budget --preview --montage --preview-display`. check gets `--vram-budget --strict`. dev gets the layout set plus `--palettize-images` and `--once`. | ps2ui.py:92-105 (`compile_screens`), 135-141 (`bake_argv`), 161-166 (`cmd_build`), 198-213 (`cmd_check`), 302-319 (`cmd_dev`) | a scratch project setting every key: `PS2UI_LAYOUT=/bin/echo ps2ui build` printed the layout argv, `PS2UI_LAYOUT=/bin/echo ps2ui dev --once` printed the dev argv, and a python run with `cli.main`/`check.main` replaced by printers gave the bake and check argv. All four pasted on the page | verified |
| cli.ps2ui.forwarding.build-overrides | `ps2ui build` takes `--mode`, `-o/--out`, `--preview`, `--montage`, `--preview-display`. Each replaces the project key; `none` for the three PNG flags suppresses that output. | ps2ui.py:346-358, 148-156 | `ps2ui build <scratch>/memcard -o build/ui-16x9.uib --mode ntsc16x9 --preview none --montage none` exited 0 and wrote `build/ui-16x9.uib`, `build/library-16x9.json`, `build/saves-16x9.json` and no new PNG | verified |
| cli.ps2ui.files | `ps2ui build` writes `<build>/<screen><suffix>.json` per screen, the blob at `out`, and the PNGs named by `preview`, `montage` and `previewDisplay`. `ps2ui dev` writes `<build>/dev/`. `ps2ui serve` writes `<build>/serve/`. `ps2ui check` writes nothing. The full table is under `## cli.ps2ui.files`. | ps2ui.py:89 (`ir_path`), 135, 161-166, 289 (`dev`); packages/baker/ps2ui_bake/serve.py:332 (`set_out_override` to `build/serve/ui.uib`); packages/baker/ps2ui_bake/check.py (no write) | `find build` on the scratch memcard after `ps2ui build`, after `ps2ui dev --screen library --once`, and while `ps2ui serve --port 8433` ran; all three listings pasted on the page | verified |
| cli.ps2ui.files.serve-no-pngs | The serve pipeline sets `preview`, `montage` and `previewDisplay` to `False`, so `build/serve/` holds only the IR files and `ui.uib`. | serve.py:331-336 | the serve listing shows `build/serve/library.json`, `build/serve/saves.json`, `build/serve/ui.uib` and no PNG | verified |
| cli.ps2ui.check-never-builds | `ps2ui check` does not compile or bake. A missing blob is refused with `<out>: no blob to check. Run \`ps2ui build\` first ...`, exit 1, and no file is written. | ps2ui.py:173-178 | moved `build/ui.uib` aside on the scratch memcard; `ps2ui check` printed that line, exit 1, and `find build` showed the remaining files unchanged and no new blob | verified |
| cli.ps2ui.out-override | `-o NEW` on `ps2ui build` moves the blob and its intermediates; the suffix rule is parent fact `project.out-override`. The previews do not move; use `--preview`, `--montage`, `--preview-display`. | packages/baker/ps2ui_bake/project.py:156-176; ps2ui.py:150-156 | the `-o build/ui-16x9.uib` run above | verified |
| cli.ps2ui.layout-discovery | `layout_command()` returns, in order: `$PS2UI_LAYOUT` split on spaces; `shutil.which("ps2ui-layout")`; `[node, <pkg>/../../layout/bin/ps2ui-layout.js]` when both that file and `node` exist; otherwise it raises the `cannot find ps2ui-layout` message naming `npm install -g @ophtml/layout` and `PS2UI_LAYOUT`. | ps2ui.py:36-57 | `PS2UI_LAYOUT=/bin/echo ps2ui build` ran `/bin/echo` with the layout argv; `PS2UI_LAYOUT=/bin/false ps2ui build` printed `ps2ui: ps2ui-layout failed on ui/library.html (exit 1)`, exit 1; with a PATH holding only `node` the function returned the checkout pair; with `env -i PATH=/usr/bin:/bin` it printed the four-line install message, exit 1 | verified |
| cli.ps2ui.layout-discovery.dev | `cmd_dev` derives the watcher command from the same list, replacing `ps2ui-layout` with `ps2ui-dev` in every element. An override that does not contain that substring is used unchanged. | ps2ui.py:277-278 | `PS2UI_LAYOUT=/bin/echo ps2ui dev ... --once` ran `/bin/echo`, which proves the substring replace left a path without `ps2ui-layout` in it alone | verified |
| cli.ps2ui.exit-codes | `main` returns 1 and prints `ps2ui: <message>` for every `ProjectError`. Otherwise the subcommand's own return value is the exit code: the baker's, the checker's, the fontgen tool's, or `subprocess.call`'s for `dev`. argparse errors exit 2. | ps2ui.py:426-433, 167, 215, 234, 320 | `ps2ui` bare, exit 2; `ps2ui nope`, exit 2; unknown project key, `ps2ui: ... unknown key(s) 'colour'.`, exit 1; missing blob, exit 1; `vramBudget` 100000 on one memcard screen, baker printed `error: texture VRAM footprint exceeds budget`, exit 1; a crc-corrupted blob, `ps2ui-check: build/ui.uib: crc mismatch (...)`, exit 2. A failing layout stage is the exception: `compile_screens` raises `ProjectError`, so `--mode vga` exited 1 while the compiler exited 2 | verified |
| cli.ps2ui.exit-codes.serve | `serve` is the exception: `serve.run` catches `ProjectError` itself and prints `ps2ui serve: <message>` before returning 1, so the prefix differs from every other subcommand. | serve.py:803-808 | `ps2ui serve <missing> --selftest` printed `ps2ui serve: <path>: no such project file.`, exit 1; `ps2ui build <missing>` printed the same message behind `ps2ui: `, exit 1 | verified |
| cli.ps2ui.dev.screen | `ps2ui dev` watches one screen. With no `--screen` and more than one screen it refuses and lists every screen name. An unknown name is refused and lists them too. | ps2ui.py:246-273 (`pick_screen`) | `ps2ui dev <scratch>/memcard --once` printed `ps2ui dev watches one screen and this project has 2. Name one: ps2ui dev --screen <name>, where <name> is one of: library, saves`, exit 1; `--screen nope` printed `no screen named 'nope' in ps2ui.json. It has: library, saves`, exit 1 | verified |
| cli.ps2ui.dev.inert-flags | `ps2ui dev` forwards `--strict` and `--min-font-size` from the project and both are inert in `ps2ui-dev`, which sets them on `options` while the compiler reads lint overrides from `options.lint` only (D9). | ps2ui.py:310-313; packages/layout/bin/ps2ui-dev.js:88-89; packages/layout/src/index.js:219 | opl-env sets `strict: true` and `minFontSize: 11`. `PS2UI_LAYOUT=/bin/echo ps2ui dev ... --screen landing --once` printed `ui/landing.html ui/opl.css -o build/dev --strict --min-font-size 11 --once`. The real run printed 9 warnings reading `is 11px; below 14px is unreadable from a couch` and exited 0. `ps2ui build` on the same project printed 0 warnings and exited 0. Restates parent `cli.dev.inert-flags` and `project.keys.dev` | verified |
| cli.ps2ui.fontgen | `ps2ui fontgen <regular> <bold> [-o DIR]` writes `default.metrics.json`, `default-bold.metrics.json` and `fonts.json` into `DIR` (default `fonts/`), one stderr line each. | ps2ui.py:218-243, 365-371 | `ps2ui fontgen fonts/vendor/DejaVuSans.ttf fonts/vendor/DejaVuSans-Bold.ttf -o <scratch>/fonts` printed `115 glyphs, 284 kern pairs`, `115 glyphs, 163 kern pairs` and `manifest -> .../fonts.json`, exit 0; `ls` showed exactly three files. Restates parent `fontgen.outputs` | verified |
| cli.ps2ui.vendor-runtime | `ps2ui vendor-runtime [dest] [--force]` copies `ps2ui.c` and `ps2ui.h` into `dest` (default `.`) and prints the toolchain notes. An unchanged file prints `already up to date`. A file that differs from the shipped runtime refuses the whole command with exit 1 unless `--force` is given. | packages/baker/ps2ui_bake/vendor.py:131, 198-225; ps2ui.py:329-333, 409-415 | wrote both files into a scratch directory (exit 0); a second run printed `ps2ui.c, ps2ui.h already up to date.` (exit 0); after appending a line to `ps2ui.c` the run printed `ps2ui: ps2ui.c in <dir> differs from the runtime this toolchain ships, so nothing was written.`, exit 1; `--force` then rewrote it, exit 0 | verified |
| cli.ps2ui.serve.options | `ps2ui serve` takes the project positional plus `--uib BLOB`, `--port PORT`, `--screen NAME`, `--theme N`, `--no-watch`, `--selftest`. The subparser is declared in `ps2ui.py`, not delegated to `serve.py`, so `ps2ui build --help` never imports the server. | ps2ui.py:385-397; serve.py:726-739 | `ps2ui serve --help` printed exactly that list; `TestImportRule.test_nothing_pulls_serve_in` in `packages/baker/tests/test_serve.py` passed. README.md:590 calls `[--port 8080] [--screen NAME] [--theme N] [--no-watch] [--selftest]` "the whole option list" and omits `--uib` (D5) | contradicts-readme |
| cli.ps2ui.serve.no-standalone | There is no `ps2ui-serve` command. `serve.py` declares `prog="ps2ui-serve"` in its own `main`, which no entry point reaches. | packages/baker/ps2ui_bake/serve.py:836-841; packages/baker/pyproject.toml:21-24 | `pyproject.toml` lists four console scripts and `ps2ui-serve` is not among them; `which ps2ui-serve` found nothing (D10) | verified |
| cli.ps2ui.serve.selftest | `--selftest` binds port 0, requests `/`, `/frame.png`, `/state`, `/rev` and one unknown route, asserts the served frame is byte-identical to what `--preview` writes, prints `PASS: N route(s)` and exits 0. It ignores `--port`. | serve.py:741-799, 815-817 | `ps2ui serve <scratch>/memcard --selftest` printed six `ok -` lines and `PASS: 6 route(s)`, exit 0; `ps2ui serve --uib <scratch>/memcard/build/ui.uib --selftest` printed the same six lines, exit 0 | verified |
| cli.ps2ui.serve.port | With no `--port` the server tries 8080 and walks up to 8099. An explicit `--port` is tried once. | serve.py:651-666, 820-823 | `ps2ui serve <scratch>/memcard --port 8433` printed `ps2ui serve: http://127.0.0.1:8433/ -- ctrl-c to stop`; a `curl` to that URL answered 200; the wander range is read from `range(port, port + (20 if wander else 1))` and was not driven to exhaustion | verified (explicit port); code-only (the walk-up branch) |
| cli.ps2ui.checkout | Checkout spellings for every installed command; the table is under `## cli.ps2ui.checkout`. `examples/*/build.sh` uses `PYTHONPATH="$repo/packages/baker" python3 -m ps2ui_bake.ps2ui build`. | packages/baker/pyproject.toml:21-24; packages/baker/ps2ui_bake/__main__.py; packages/layout/package.json `bin`; examples/memcard/build.sh:18; examples/channel6/build.sh:23-29 | ran `--version` through every spelling in this session: `python3 -m ps2ui_bake.ps2ui`, `-m ps2ui_bake`, `-m ps2ui_bake.cli`, `-m ps2ui_bake.check`, `-m ps2ui_bake.fontgen`, `node packages/layout/bin/ps2ui-layout.js`, `node packages/layout/bin/ps2ui-dev.js`; each printed its own name and version | verified |
| cli.ps2ui.cwd | Every subcommand except `fontgen` and `vendor-runtime` chdirs into the project root for the duration and restores the previous directory. Paths printed by the tools are therefore relative to the project file, not to the shell's directory. | ps2ui.py:60-76 (`in_project`), 79-80 (`rel`), 158, 214, 290 | `ps2ui build <scratch>/memcard` run from `/home/user/OPHTML` printed `-> build/ui.uib`, `preview -> build/preview.png`, `montage -> build/states.png`. Restates parent `project.resolution` | verified |

## cli.ps2ui.subcommands

| subcommand | positional | options |
|---|---|---|
| build | `project` (default `ps2ui.json`) | `--mode MODE`, `-o/--out OUT`, `--preview PNG`, `--montage PNG`, `--preview-display PNG` |
| check | `project` (default `ps2ui.json`) | none beyond `-h` |
| fontgen | `regular`, `bold` | `-o/--out-dir DIR` (default `fonts`) |
| serve | `project` (default `ps2ui.json`) | `--uib BLOB`, `--port PORT`, `--screen NAME`, `--theme N`, `--no-watch`, `--selftest` |
| vendor-runtime | `dest` (default `.`) | `--force` |
| dev | `project` (default `ps2ui.json`) | `--screen NAME`, `--once` |

Source: ps2ui.py:344-424. Verified by `ps2ui <sub> --help` for all six.

## cli.ps2ui.forwarding

`key` is the project key (parent fact `project.keys`). A blank cell means the key
does not reach that tool.

| key | build: ps2ui-layout | build: ps2ui-bake | check: ps2ui-check | dev: ps2ui-dev |
|---|---|---|---|---|
| screens | the two positionals | the IR positionals | | the two positionals |
| css | the second positional | | | the second positional |
| fonts | `--fonts` | `--fonts` | | `--fonts` |
| out | `-o <build>/<screen>.json` | `-o` | the positional | `-o <build>/dev` |
| preview | | `--preview` | | |
| montage | | `--montage` | | |
| previewDisplay | | `--preview-display` | | |
| mode | `--mode` | | | `--mode` |
| canvas | `--canvas` | | | `--canvas` |
| displayAspect | `--display-aspect` | | | `--display-aspect` |
| strict | `--strict` | | `--strict` | `--strict` (inert, D9) |
| minFontSize | `--min-font-size` | | | `--min-font-size` (inert, D9) |
| focusWrap | `--focus-wrap` (per screen) | | | `--focus-wrap` (chosen screen) |
| palettizeImages | | `--palettize-images` | | `--palettize-images` |
| vramBudget | | `--vram-budget` | `--vram-budget` | |

Source: ps2ui.py:89-105, 135-141, 161-166, 198-213, 292-319.

## cli.ps2ui.files

| subcommand | writes | source |
|---|---|---|
| build | `<build>/<screen><suffix>.json` per screen | ps2ui.py:89; project.py:156-176 |
| build | the blob at `out`, default `build/ui.uib` | ps2ui.py:135 |
| build | `preview`, `montage`, `previewDisplay` PNGs when set | ps2ui.py:161-166 |
| check | nothing | check.py (no write) |
| fontgen | `<out-dir>/default.metrics.json`, `default-bold.metrics.json`, `fonts.json` | ps2ui.py:229-242 |
| serve | `<build>/serve/<screen>.json`, `<build>/serve/ui.uib` | serve.py:332 |
| vendor-runtime | `<dest>/ps2ui.c`, `<dest>/ps2ui.h` | vendor.py:212-216 |
| dev | `<build>/dev/<screen>.json`, `<build>/dev/ui.uib`, `<build>/dev/preview.png` | ps2ui.py:289; packages/layout/bin/ps2ui-dev.js:122-138 |

## cli.ps2ui.checkout

| installed command | checkout spelling |
|---|---|
| `ps2ui` | `PYTHONPATH=packages/baker python3 -m ps2ui_bake.ps2ui` |
| `ps2ui-bake` | `PYTHONPATH=packages/baker python3 -m ps2ui_bake` |
| `ps2ui-check` | `PYTHONPATH=packages/baker python3 -m ps2ui_bake.check` |
| `ps2ui-fontgen` | `PYTHONPATH=packages/baker python3 -m ps2ui_bake.fontgen` |
| `ps2ui-layout` | `node packages/layout/bin/ps2ui-layout.js` |
| `ps2ui-dev` | `node packages/layout/bin/ps2ui-dev.js` |

`python3 -m ps2ui_bake.cli` is the same program as `python3 -m ps2ui_bake`
(`__main__.py` imports `cli.main`). Both were run.

## findings

- `ps2ui serve --uib <missing file>` raises an uncaught `FileNotFoundError` and
  exits 1 with a traceback. `build_server` calls `read_uib(args.uib)` outside the
  `ProjectError` handler (serve.py:698-701, 803-808). Every other missing-input
  path in this file prints one line.
- `ps2ui serve --port <busy>` raises an uncaught `OSError: [Errno 98] Address
  already in use` and exits 1 with a traceback. `bind` re-raises when `wander` is
  false (serve.py:660-664). The docstring above it argues an explicit port should
  fail hard, which it does, but the failure is a traceback rather than a message.
  Verified by holding 127.0.0.1:8434 open and running `ps2ui serve --uib ...
  --port 8434`.
- A failing layout stage is reported as `ProjectError`, so `ps2ui build` exits 1
  even when `ps2ui-layout` exited 2. `ps2ui build <scratch>/memcard --mode vga`
  printed the compiler's usage line, then `ps2ui: ps2ui-layout failed on
  ui/library.html (exit 2)`, and exited 1 (ps2ui.py:107-113).
