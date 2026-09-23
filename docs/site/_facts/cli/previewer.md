# facts: cli/previewer

Session: every `ps2ui serve` below ran against a scratch copy of
`examples/memcard`, made with `cp -r examples/memcard <scratch>/memcard` and
`rm -rf <scratch>/memcard/build`. `<scratch>` is
`/tmp/claude-0/-home-user-OPHTML/6b0c72b8-d98f-5f58-b749-f9808bb620d6/scratchpad/cli/previewer`.
Nothing under `examples/*/build/` or `examples/*/screenshots/` was written or read
for a render. The watch server ran on `--port 8501` and was stopped with `pkill`;
port 8501 was confirmed bindable afterwards. Two extra servers ran on the default
port for the walk-up row and were stopped the same way.

Suite: `cd packages/baker && env -u PS2UI_REQUIRE_EXAMPLES PYTHONPATH=tests python3
-m unittest tests.test_serve -v` printed `Ran 26 tests in 14.751s` / `OK`.
`python3 -m unittest tests.test_serve` alone fails to import: `test_serve.py:31`
imports `fonts_available`, which lives in `packages/baker/tests/` and is not on
`sys.path` under that spelling. Recorded under `## follow-up`.

Line numbers were re-located by symbol in this session.

Parent facts reused without restatement: `cli.ps2ui.serve.options`,
`cli.ps2ui.serve.no-standalone`, `cli.ps2ui.serve.selftest`,
`cli.ps2ui.serve.port`, `cli.ps2ui.exit-codes.serve`, `cli.ps2ui.files`,
`cli.ps2ui.files.serve-no-pngs`, `cli.ps2ui.cwd`, `project.resolution`,
`project.out-override`, `focus.solver`, `focus.scope`, `focus.previewer`,
`focus.runtime`, `theme.index`, `theme.seeing.preview`, `lint.serve.no-jump`,
`lint.serve.safe-area-inset`.

| id | fact | source | verified by | status |
|---|---|---|---|---|
| serve.options | `ps2ui serve [project] [--uib BLOB] [--port PORT] [--screen NAME] [--theme THEME] [--no-watch] [--selftest]`. The table is under `## serve.options`. Parent fact `cli.ps2ui.serve.options` owns the list; this row adds the per-flag effects. | packages/baker/ps2ui_bake/ps2ui.py:531-543; serve.py:726-739 | `ps2ui serve --help` pasted on the page. README.md:591 calls its shorter list "the whole option list" and omits `--uib` (D5) | contradicts-readme |
| serve.routes | Six routes. GET `/` (text/html), `/frame.png` (image/png), `/montage.png` (image/png), `/state` (application/json), `/rev` (application/json); POST `/input` (application/json). Every other path is 404 with a JSON body. Every response carries `Cache-Control: no-store`. The table is under `## serve.routes`. | serve.py:615-634 (`do_GET`), serve.py:636-648 (`do_POST`), serve.py:601-613 (`send`, `json`) | a server on `--port 8501`: the six-line status table pasted on the page; `GET /input` answered 404; `curl -D -` showed `Cache-Control: no-store` on `/` and `/state`; `TestRoutes.test_the_routes_answer` passed | verified |
| serve.routes.input | `/input` takes one field per request: `key` (`up`/`down`/`left`/`right`), `screen`, `theme`, `aspect` or `slot` (a name-to-text object). It answers with the whole `/state` payload. A body with no recognised field, an unknown screen, an out-of-range theme, an unknown aspect or unparseable JSON is 400 with `{"error": ...}`. | serve.py:527-545 (`apply`), serve.py:644-645 | `{"key":"down"}` answered 200 and moved the focus; `{"nonsense":1}`, `{"screen":"nope"}`, `{"theme":9}` and `not json` each answered 400, the four bodies pasted on the page; `TestRoutes.test_input_reports_a_bad_field_rather_than_crashing` passed | verified |
| serve.routes.state | `/state` is one object with 16 keys: `revision`, `error`, `screens`, `screen`, `themes`, `theme`, `aspect`, `aspects`, `canvas`, `display`, `display_aspect`, `focus`, `focusables`, `commands`, `slots`, `warnings`. `commands`, `focusables` and `slots` cover the current screen only. | serve.py:481-525 (`snapshot`) | `curl /state` on the scratch memcard printed exactly those keys, `screens ['library','saves']`, `canvas {'w':640,'h':448}`, `display {'w':597,'h':448}`, 686 commands, 9 focusables, 1 slot, 45 warnings; `TestState.test_state_names_the_current_screens_focusables_only` passed | verified |
| serve.routes.rev | `/rev` is `{"revision": N}` and nothing else. The counter rises on every build attempt, failed builds included. | serve.py:628-630, serve.py:412-425 (`rebuild`) | `curl /rev` printed `{"revision": 1}`; a broken CSS edit took it to 2 and the repair to 3 | verified |
| serve.controls | Every control in the page and what it drives. The table is under `## serve.controls`. Focus moves by arrow key only; `/input` has no set-focus verb, so clicking a focusable walks the baked graph and posts those arrows. | packages/baker/ps2ui_bake/serve_page.html:121-138 (toolbar), packages/baker/ps2ui_bake/serve_page.html:624-647 (handlers), packages/baker/ps2ui_bake/serve_page.html:681-706 (keys), packages/baker/ps2ui_bake/serve_page.html:447-479 (`pathTo`, `focusTo`) | one Playwright run against the `--port 8501` server pressed every key and read the result back from `#status` and the DOM; the transcript is under `## serve.controls` | verified |
| serve.controls.arrows | An arrow key posts `{"key": <dir>}`, which is `ps2ui_move`'s edge semantics exactly: the baked neighbour or nothing. No wrap is invented in the previewer. | serve.py:161-187 (`move`); serve_page.html:681-691 | the probe pressed Down, Right, Up, Left from `nav-settings` and landed on `tile-gt4`, `tile-ffx`, `tile-sotc`, `tile-ico`; `TestNavigation.test_no_wrap_is_invented` and `test_a_move_lands_on_exactly_the_baked_neighbour` passed | verified |
| serve.controls.slots | A slot box posts `{"slot": {name: text}}` on change. Its `maxLength` is the slot's baked capacity and its tooltip is `capacity N`. Empty text drops the override and the placeholder returns. Slot text is kept per screen. | serve_page.html:595-622, serve_page.html:610; serve.py:209-221 (`set_slots`, `slots_for`) | the memcard `count` box reported `maxLength 15`, `title "capacity 15"`, value `6 titles`; typing `THE LONGEST TITLE THAT FITS AND MORE` left `THE LONGEST TIT`; `TestState.test_slot_text_is_per_screen` passed | verified |
| serve.controls.overlays | Four overlays, all off by default, all SVG over the `<img>`: `Grid` an 8 px lattice, `Safe area` a 10 percent dashed inset, `Focus boxes` one magenta rectangle per focusable with the current one dashed wider, `Focus graph` one arrow per solved D-pad edge. Hover and selection draw their own rectangle unconditionally. | serve_page.html:305-359 (`drawOverlay`), serve_page.html:193-197 (the `S` defaults) | the probe toggled each by keyboard and counted `#ov` children: grid 1, safe 2, focus boxes 11, graph 65, and 0 after toggling all four off; parent facts `focus.previewer` and `lint.serve.safe-area-inset` | verified |
| serve.inspector | Clicking the frame hit-tests front to back to the topmost drawn command and selects it. A command row in the left list selects the same way. The Inspector lists index, op, position, size, rgba, tex, state and focus, plus `drawn now`, and the Selected record pane holds the raw JSON. | serve_page.html:649-679 (`hit`, the click handlers), serve_page.html:481-515 (`select`, `buildInspector`) | the probe clicked the frame and read back `index 0 · op quad · position 0, 0 · size 640 x 448 · rgba #0a0e1a · a128/128 · tex — · state 0 always · focus — · drawn now yes`; `assets/cli/previewer/inspector.png` shows command 14 selected from the list | verified |
| serve.inspector.alpha | The Inspector reads alpha in the GS domain, 0 to 128, and a swatch divides by 128 rather than 255. | serve_page.html:200-203, serve_page.html:508 | the capture shows `#0a0d16 · a128/128` for command 14 of the memcard library screen | verified |
| serve.aspects | Four aspect modes: `framebuffer` (the 1:1 render, what `--preview` writes), `authored` (resampled through the blob's own display aspect, the default), `force-4:3` and `force-16:9` (the same framebuffer resampled to a ratio the header did not ask for). **The default is therefore not the size `--preview` writes**: a 4:3 blob is 640x448 in the file and 597x448 on the page, and 796x448 under `force-16:9`. Both are right; the difference is the pixel aspect the television applies (F39). | serve.py:66 (`ASPECTS`), serve.py:233-248 (`render_png`), serve.py:203-207 | `/state` printed `aspect authored` and `aspects ['framebuffer','authored','force-4:3','force-16:9']`; the Playwright capture `assets/cli/previewer/aspect-16x9.png` shows the memcard library screen under `force-16:9`; `TestFrames.test_every_aspect_mode_renders_and_they_differ` passed; the four sizes were measured for F39 on `examples/opl-env/build/ui.uib` by opening each frame with PIL: framebuffer 640x448, authored 597x448, force-4:3 597x448, force-16:9 796x448, and `preview.render(u)` 640x448; `TestFrames.test_the_frame_on_screen_is_not_the_frame_that_was_compared` passed | verified |
| serve.ports | With no `--port` the server binds 127.0.0.1:8080 and walks up one port at a time to 8099, then refuses with `ports 8080-8099 are all busy`. An explicit `--port` is tried once and refused by name: `ps2ui serve: port <n> is already in use.` plus two lines saying a named port is not moved. Both refusals print with the `ps2ui serve: ` prefix from `ps2ui serve` and from `python -m ps2ui_bake.serve` alike; before B18 the bind call sat outside `run`'s handler, so they printed `ps2ui: ` under the first and a traceback under the second. It never binds an address other than 127.0.0.1. Extends parent fact `cli.ps2ui.serve.port`, whose walk-up half was `code-only`. | serve.py:651-678 (`bind`), serve.py:840-852 (`run`) | two servers started with no `--port` printed `ps2ui serve: http://127.0.0.1:8080/ -- ctrl-c to stop` and `... http://127.0.0.1:8081/ ...`, both pasted on the page; `TestRoutes.test_binding_is_loopback_only` passed; in the B17/B18 session both refusals were driven on a scratch memcard, a held ephemeral port printing the three-line message at exit 1 from both entry points and 8080-8099 all held printing `ps2ui serve: ports 8080-8099 are all busy` at exit 1; `TestBusyPortIsAMessage.test_neither_entry_point_prints_a_traceback_for_a_busy_port` and `TestRoutes.test_a_busy_explicit_port_is_a_message_and_the_default_wanders` passed, each falsified against the line it fences | verified |
| serve.output | `ps2ui serve` prints the compiler's per-screen line and its warnings, then one URL line on stderr. `--no-watch` adds `  (not watching)`. Ctrl-C prints a blank line and exits 0. | serve.py:819-834 | the `--port 8501` run printed `ps2ui-layout: 89 paint commands, 9 focusables -> build/serve/library.json`, the `saves` twin and the URL line; `ps2ui serve --port 8502 --no-watch` added `  (not watching)` | verified |
| serve.files | A project-mode server writes `<build>/serve/<screen>.json` and `<build>/serve/ui.uib`, and no PNG. `--uib` writes nothing at all. Restates parent facts `cli.ps2ui.files` and `cli.ps2ui.files.serve-no-pngs`. | serve.py:330-337 (`BuildPipeline.__init__`), serve.py:698-701 (`build_server`) | `find build -type f` on the scratch memcard after the run printed exactly `build/serve/library.json`, `build/serve/saves.json`, `build/serve/ui.uib`; `ps2ui serve --uib ... --selftest` run in an empty directory left 0 entries | verified |
| serve.uib | `--uib BLOB` reads the blob and serves it: no project file, no Node, no watching, no warnings panel. It makes the page an inspector for any `.uib`. | serve.py:698-701, serve.py:678-696 (`require_node`, which `--uib` skips) | `env -i PATH=/usr/local/bin:/usr/bin:/bin ps2ui serve --uib build/serve/ui.uib --selftest` printed `PASS: 6 route(s)`, exit 0, with `node` only on `/opt/node22/bin`; `serve.Server(uib=...)` reported `pipeline None` and `warnings []`; `TestNoNodeNeeded.test_uib_mode_needs_no_node_on_path` passed | verified |
| serve.screen-theme-validated | `--screen` and `--theme` are checked against the blob before the server binds. An unknown screen is `no screen named 'X'. The blob has: <names>`; an out-of-range theme is `no theme N; the blob has M`. Both exit 1 behind the `ps2ui serve: ` prefix. | serve.py:702-720 (`build_server`) | `ps2ui serve --uib build/serve/ui.uib --screen nope --selftest` printed `ps2ui serve: no screen named 'nope'. The blob has: library, saves`, exit 1; `--theme 3` printed `ps2ui serve: no theme 3; the blob has 1`, exit 1; `--screen saves --selftest` printed `PASS: 6 route(s)`, exit 0 | verified |
| serve.selftest | `--selftest` binds an ephemeral port, fetches `/`, `/frame.png`, `/state`, `/rev` and one unknown route, asserts the served frame is byte-identical to what `preview.render` writes, prints `PASS: 6 route(s)` and exits 0. **It forces `framebuffer` for that comparison and restores the mode afterwards**, so the frame it compares is not the one the page is showing; its line names the framebuffer since F39. It ignores `--port` and `--no-watch`. `/montage.png` is not among the routes it checks. | serve.py:741-800, serve.py:815-817 | `ps2ui serve --selftest` in the scratch project printed the six `ok -` lines and `PASS: 6 route(s)`, exit 0, pasted on the page; `TestFrames.test_the_served_frame_is_what_preview_writes` passed; re-run for F39 the line reads `ok - the framebuffer frame is byte-identical to --preview`, and restoring the old wording fails `check-tutorial.py` on two documents. Restates parent fact `cli.ps2ui.serve.selftest` | verified |
| serve.build-error | A failed rebuild keeps the last good blob on screen and puts the build's message in a banner above the frame. The revision still rises, so the page repaints. The next clean build clears the banner. | serve.py:412-425 (`rebuild` keeps `self.uib`), serve.py:359-391 (`build` returns an error rather than raising); serve_page.html:152, serve_page.html:286-287 | appended `.tile { background: #12g4f6; }` to the scratch `ui/library.css` while the server watched: `/state` went to revision 2 with `error "ps2ui-layout failed on ui/library.html (exit 1)"` and still 686 commands; `assets/cli/previewer/error-banner.png` is that state; restoring the file took it to revision 3 with `error None`; `TestBuildFailure.test_a_broken_build_keeps_the_last_good_blob` passed | verified |
| serve.watch | The watcher polls every 0.2 s, debounces a burst for 0.12 s, then rebuilds. It stats the project file, every screen's HTML and CSS, and every `.html`, `.css` and `.png` under each screen's directory. `--no-watch` and `--uib` start no watcher. | serve.py:547-591 (`Watcher`), serve.py:346-357 (`inputs`), serve.py:806-809 | `serve.Watcher.INTERVAL` printed 0.2 and `DEBOUNCE` 0.12; the CSS edit above was picked up and rebuilt without any further command | verified |
| serve.poll | The page polls `/rev` every 250 ms and refetches `/state` only when the revision changed or the connection came back. A failed poll greys the frame and shows `Server stopped — reconnecting…`; polling continues. | serve_page.html:714 (`setInterval(poll, 250)`), serve_page.html:227-241, serve_page.html:218-225 (`setOnline`), serve_page.html:151 | read in source; the 250 ms interval and the offline banner were not driven by a command here, because stopping the server ends the session that would observe it | code-only |
| serve.frames | Frames are rendered by `preview.render` server-side and reach the page as PNG bytes. The cache is keyed on screen, focus index, theme, aspect and a digest of the slot text, and holds 96 frames. After each build and each screen switch a background thread renders that screen's every focus state. | serve.py:233-248, serve.py:223-231 (`key`), serve.py:72 (`CACHE_MAX`), serve.py:427-467 (`warm`, `_warm_now`) | `serve.CACHE_MAX` printed 96; `TestFrames.test_every_part_of_the_cache_key_discriminates`, `test_a_cached_frame_is_the_frame` and `test_the_warm_thread_cannot_file_a_frame_under_a_stale_key` passed | verified |
| serve.montage | `/montage.png` is `preview.montage` of the current screen: one tile per focusable, three per row, that focusable current. Nothing in the page requests it. | serve.py:474-479 (`montage`); serve_page.html (no `/montage.png` reference) | `curl /montage.png` answered 200 `image/png`, 133306 bytes, 1984x1408 for the 9-focusable memcard library screen; `grep -c montage.png packages/baker/ps2ui_bake/serve_page.html` printed 0 | verified |
| serve.limits | Four things the previewer cannot show: runtime visibility and list windowing, a hardware fault the command list is innocent of, a composite of two screens in one frame, and a streamed texture's pixels. The table is under `## serve.limits`. | serve.py:36-45 (the module docstring); packages/baker/ps2ui_bake/preview.py:126-134 (`render` takes one screen and optional `tex_fills`); README.md:719-725; docs/tutorial-uc3.md:294-311 | the first two are restated from the sources named; the third and fourth are read from `render`'s signature and from `render_png`, which passes no `tex_fills` (`grep -n tex_fills packages/baker/ps2ui_bake/serve.py` printed nothing) | code-only |
| serve.limits.no-jump | A warning row in the previewer never jumps to a command, because `serve.py` publishes `{screen, text}` and no command index. Restates parent fact `lint.serve.no-jump`. docs/tutorial-uc3.md:268 says "warnings jump to the command they name". | serve.py:375-381; serve_page.html:517-536 | `/state` on the scratch memcard returned 45 warnings, every one of them with the two keys only | verified |
| serve.focus-not-per-screen | Focus is one name in one `PreviewState`, reconciled against the screen in view. Leaving a screen and returning restores the old node only when that name still resolves. A name the other screen also carries follows the reader across. docs/tutorial-uc3.md:264 says each screen remembers its own focus. | serve.py:115-126 (one `focus_name`, a per-screen `slot_text`), serve.py:144-159 (`reconcile`), serve.py:189-194 (`set_screen`) | on the scratch memcard: focus `tile-okami` on `library`, then `{"screen":"saves"}` gave `nav-saves`, then `{"screen":"library"}` gave `nav-saves`, not `tile-okami`. `TestScreensAndThemes.test_focus_is_remembered_per_screen` passes only because it moves to `nav-saves`, a name both memcard screens carry | verified |
| serve.banner-loses-the-diagnostic | The banner shows the one-line summary of a failed build, not the compiler's diagnostic. `build` redirects Python-level stderr into a buffer, and the compiler is a subprocess writing to the inherited file descriptor, so its line reaches the terminal instead. | serve.py:359-372 (`contextlib.redirect_stderr(err)`); ps2ui.py:83-113 (`compile_screens` runs the compiler at ps2ui.py:107 with `subprocess.call`) | the broken-CSS run put `ps2ui-layout failed on ui/library.html (exit 1)` in `/state.error` with an empty second line, while `error: css: line 195: background: bad color "#12g4f6" ...` went to the server's terminal | verified |
| serve.no-standalone | There is no `ps2ui-serve` command; `serve.py`'s own `prog="ps2ui-serve"` reaches no entry point (D10). Restates parent fact `cli.ps2ui.serve.no-standalone`. | serve.py:836-841; packages/baker/pyproject.toml:21-24 | parent fact `cli.ps2ui.serve.no-standalone`; re-checked here with `which ps2ui-serve`, which found nothing | verified |
| serve.exit-codes | 0 for a clean run, a clean `--selftest` and Ctrl-C. 1 for every refusal, printed as `ps2ui serve: <message>`. 2 for an argparse error. Restates parent facts `cli.ps2ui.exit-codes.serve` and `cli.ps2ui.exit-codes.argparse`. | serve.py:803-834; ps2ui.py:426-433 | `--selftest` exit 0; `--screen nope` and `--theme 3` exit 1; parent fact covers `ps2ui serve --nope` exit 2 | verified |

## serve.options

| flag | argument | default | effect |
|---|---|---|---|
| (positional) | `project` | `ps2ui.json` | the project to build and watch; a directory means the `ps2ui.json` inside it |
| `--uib` | `BLOB` | none | serve a pre-baked blob: no project, no Node, no watching, no warnings |
| `--port` | `PORT` | 8080, walking up to 8099 | bind this port once, and say which port is busy and fail |
| `--screen` | `NAME` | the blob's first screen | open on this screen; an unknown name is refused |
| `--theme` | `THEME` | 0 | open on this theme row; a row past the end is refused |
| `--no-watch` | none | off | serve the first build and never rebuild |
| `--selftest` | none | off | fetch every route on an ephemeral port, assert the frame, exit |

Source: ps2ui.py:385-397. Verified by `ps2ui serve --help`.

## serve.routes

| route | method | type | purpose |
|---|---|---|---|
| `/` | GET | `text/html; charset=utf-8` | the previewer page, 29569 bytes |
| `/frame.png` | GET | `image/png` | the current state rendered by `preview.render` |
| `/montage.png` | GET | `image/png` | `preview.montage` of the current screen |
| `/state` | GET | `application/json` | the whole payload the page draws from |
| `/rev` | GET | `application/json` | `{"revision": N}`, the poll target |
| `/input` | POST | `application/json` | one state change, answered with `/state` |
| anything else | GET or POST | `application/json` | `{"error": "no route '/x'"}`, 404 |

Source: serve.py:615-648. Verified by `curl -i` against a server on port 8501.

## serve.controls

| control | drives |
|---|---|
| arrow keys | `{"key": dir}`, one `ps2ui_move` along the baked focus graph |
| Screen menu, `[` and `]` | `{"screen": name}`, the same switch `ps2ui_screen_set` makes |
| Theme menu | `{"theme": n}`, the tint-table row; disabled below two themes |
| Aspect menu | `{"aspect": mode}`, one of the four resamplings |
| a slot's text box | `{"slot": {name: text}}`, the host mirror of `ps2ui_slot_set` |
| Zoom menu | client-side scale: Fit, 1x, 2x, 3x |
| Smooth | client-side upscaling filter, nearest-neighbour by default |
| Focus boxes, `b` | magenta rectangle per focusable |
| Focus graph, `n` | one arrow per solved D-pad edge |
| Grid, `g` | an 8 px lattice |
| Safe area, `s` | a dashed 10 percent inset |
| Full screen, `f`, Esc to leave | hides both panels and the toolbar |
| clicking the frame | selects the topmost command drawn there |
| clicking a command row | selects that command |
| clicking a focusable row | walks the D-pad to that node, or says there is no path |

Source: serve_page.html:121-138, :447-479, :595-647, :649-706.

Probe transcript (one Playwright run against the port 8501 server, viewport
1280x800, `executablePath: '/opt/pw-browsers/chromium'`):

```
start                        rev 3 · library · theme 0 · 686 cmds · focus nav-settings
after ArrowDown              rev 3 · library · theme 0 · 686 cmds · focus tile-gt4
after ArrowRight             rev 3 · library · theme 0 · 686 cmds · focus tile-ffx
after ArrowUp                rev 3 · library · theme 0 · 686 cmds · focus tile-sotc
after ArrowLeft              rev 3 · library · theme 0 · 686 cmds · focus tile-ico
key g -> #btnGrid            on=true overlay shapes=1
key s -> #btnSafe            on=true overlay shapes=2
key b -> #btnFocus           on=true overlay shapes=11
key n -> #btnGraph           on=true overlay shapes=65
overlay after toggling off   0
after ]                      rev 3 · saves · theme 0 · 376 cmds · focus nav-saves
after [                      rev 3 · library · theme 0 · 686 cmds · focus nav-saves
key f -> body.fullscreen   true
Esc -> body.fullscreen     false
zoom fit vs 2x width       664 1194
Smooth -> image-rendering  auto
again -> image-rendering   pixelated
slot inputs                [["count",15,"6 titles","capacity 15"]]
slot value after typing    ["THE LONGEST TIT"]
click frame -> inspector   index0opquadposition0, 0size640 x 448rgba#0a0e1a · a128/128tex—state0 alwaysfocus—drawn nowyes
before focus row click       rev 3 · library · theme 0 · 686 cmds · focus nav-saves
after focus row click        rev 3 · library · theme 0 · 686 cmds · focus tile-okami
```

The script is `<scratch>/probe.js`.

## serve.limits

| cannot show | why |
|---|---|
| `ps2ui_visible_set` and the list window | `preview.render` has no visibility parameter, so the page draws the baked state |
| a hardware fault the command list is innocent of | the previewer replays the list faithfully; F-048 lived in a GS register the runtime never writes |
| two screens composited in one frame | `preview.render` takes one screen, and `/state` publishes one screen's records |
| a streamed texture's pixels | `render_png` passes no `tex_fills`, so a streamed slot draws nothing |
| the rectangle the overscan lint enforces | the `Safe area` overlay insets 10 percent and the lint tests 5 percent (parent fact `lint.serve.safe-area-inset`) |
| which command a warning is about | warnings carry a screen and no command index (parent fact `lint.serve.no-jump`) |

## follow-up

Not in the drift table, found while verifying:

1. `python3 -m unittest tests.test_serve` from `packages/baker` fails at import:
   `tests/test_serve.py:31` does `from fonts_available import ...` and
   `packages/baker/tests` is not on `sys.path` under that spelling. The file
   inserts `packages/baker` at `sys.path[0]` (lines 22-23) but not its own
   directory. `PYTHONPATH=tests` or running from inside `tests/` works. Adding
   `os.path.dirname(os.path.abspath(__file__))` to the same insert would make
   both spellings work.
2. The build banner never carries the compiler's diagnostic. `BuildPipeline.build`
   wraps the compile in `contextlib.redirect_stderr(err)` (serve.py:365), which
   rebinds `sys.stderr` only; `compile_screens` runs `ps2ui-layout` with
   `subprocess`, which inherits the real file descriptor. So the page shows
   `ps2ui-layout failed on ui/library.html (exit 1)` with an empty second line
   while `error: css: line 195: background: bad color "#12g4f6" ...` goes to the
   terminal the server was started from. Row `serve.banner-loses-the-diagnostic`.
3. Focus is not remembered per screen, which docs/tutorial-uc3.md:264 says it is.
   `PreviewState` holds one `focus_name` for the whole session and `reconcile`
   re-resolves it against whichever screen is in view. `slot_text` is keyed by
   screen; `focus_name` is not. The existing test passes because it moves to
   `nav-saves`, a name both memcard screens carry. Row
   `serve.focus-not-per-screen`.
4. `/input` reports a rejected screen, theme or aspect as the bare repr of the
   offending value: `{"error": "'nope'"}` and `{"error": "9"}`. `apply` lets
   `KeyError(name)` and `ValueError(n)` out of `PreviewState` and the handler
   stringifies whatever it caught (serve.py:189-208, :644-645). The messages
   `build_server` prints for the same two mistakes name the blob's screens and
   theme count; the route could raise those.
5. `ps2ui serve` answers `HEAD /rev` with `501 Unsupported method ('HEAD')`,
   the `BaseHTTPRequestHandler` default. Harmless for a dev tool, but `curl -I`
   against the server looks like a failure.
