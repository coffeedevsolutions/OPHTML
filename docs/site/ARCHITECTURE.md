# OPHTML documentation library: architecture

This directory holds the documentation library for the published packages
(`ophtml` on PyPI, `@ophtml/layout` on npm) and the C runtime they ship. It
is written for the 0.6.0 release. The pages are plain markdown and are built
into the website later; nothing here depends on a site generator.

This file is the contract every page is written against. `_prompts/` holds
one self-contained brief per page. A documentation agent reads its brief,
reads this file, verifies each claim by running code, renders the screenshots
it needs, writes the page, and writes a facts file that dependent pages
consume. Nothing in a page is written from memory or copied from README.md.

## Layout

```
docs/site/
  ARCHITECTURE.md            this file
  index.md                   00 Home
  getting-started/           01 installation  02 quickstart  03 tutorial-game-browser  04 how-it-works
  authoring/                 10 project-file  11 html  12 css  13 text-and-fonts  14 images
                             15 dynamic-text  16 lists  17 focus-and-navigation  18 theming
                             19 screens-and-overlays  20 video-modes  21 crt-linter  22 vram-budget
  cli/                       30 ps2ui  31 ps2ui-layout  32 ps2ui-bake  33 ps2ui-check
                             34 ps2ui-fontgen  35 previewer
  runtime/                   40 integrating  41 frame-loop  42 api-reference  43 errors-and-constants
                             44 streaming-art  45 moving-and-hiding  46 telemetry  47 deploying  48 first-boot
  reference/                 50 ir-format  51 uib-format  52 diagnostics  53 compatibility
  examples/                  60 memcard  61 opl-env  62 channel6
  project/                   70 changelog  71 contributing  72 security-and-license  73 faq
                             74 glossary  75 internals
  assets/<page-id>/*.png     screenshots, one folder per page
  assets/assets.json         manifest: every PNG and the command that made it
  _prompts/<page-id>.md      the brief for each page
  _facts/<page-id>.md        what each page verified, for the pages that depend on it
```

A page id is its path without `docs/site/` and without `.md`, for example
`authoring/theming`. The numbers above fix the order inside a section and
are the `order` field in the frontmatter.

## Page index

| id | title | one line |
|---|---|---|
| index | OPHTML | what it is, the pipeline, where to start |
| getting-started/installation | Installation | install both packages, fonts, the Raqm refusal, checkout install |
| getting-started/quickstart | Quick start | eight commands from a TTF to a served preview |
| getting-started/tutorial-game-browser | Tutorial: a game browser | the CI-executed tutorial in the library voice |
| getting-started/how-it-works | How it works | three stages, two seams, the rules the design rests on |
| authoring/project-file | The project file | every `ps2ui.json` key and how paths resolve |
| authoring/html | HTML | what the parser accepts and every attribute the compiler reads |
| authoring/css | CSS | selectors, properties, units, colours, the two hard rules |
| authoring/text-and-fonts | Text and fonts | fonts.json, weights, charset, kerning, wrapping, ellipsis |
| authoring/images | Images | baked PNGs, palettize, intrinsic sizing |
| authoring/dynamic-text | Dynamic text | data-slot, capacity, what stays compile-time |
| authoring/lists | Lists | data-repeat and the runtime list window |
| authoring/focus-and-navigation | Focus and navigation | focusable, the solver, wrap, reachability |
| authoring/theming | Theming | :root, @theme, var(), the tint table |
| authoring/screens-and-overlays | Screens and overlays | multi-screen blobs and compositing |
| authoring/video-modes | Video modes | modes, canvas, display aspect, anamorphic pixels |
| authoring/crt-linter | CRT linter | every rule, threshold and opt-out |
| authoring/vram-budget | VRAM budget | the budget model and the breakdown table |
| cli/ps2ui | ps2ui | the umbrella command and its subcommands |
| cli/ps2ui-layout | ps2ui-layout and ps2ui-dev | the compiler and the watch loop |
| cli/ps2ui-bake | ps2ui-bake | the baker, its transcript and exit conditions |
| cli/ps2ui-check | ps2ui-check | the blob validator and its check catalogue |
| cli/ps2ui-fontgen | ps2ui-fontgen | metrics from a TTF |
| cli/previewer | Previewer | ps2ui serve: controls, routes, inspector, limits |
| runtime/integrating | Integrating the runtime | vendor-runtime, the cross toolchain, the sample Makefile |
| runtime/frame-loop | The frame loop | load, upload, render, and the guarantees |
| runtime/api-reference | C API reference | every public function, struct and scope rule |
| runtime/errors-and-constants | Errors and constants | every error code, what triggers it, every macro |
| runtime/streaming-art | Streaming art | tex_set, clut_set, host conversion |
| runtime/moving-and-hiding | Moving and hiding | visibility and the draw-time offset |
| runtime/telemetry | Telemetry | ps2ui_stats and the sample's readout |
| runtime/deploying | Deploying | from an ELF to a console |
| runtime/first-boot | First boot | the ten-step checklist |
| reference/ir-format | ui.json | the IR as emitted today |
| reference/uib-format | .uib | the blob format and the v7 pledge |
| reference/diagnostics | Diagnostics | every message, its cause and fix |
| reference/compatibility | Compatibility | versions, format, platforms |
| examples/memcard | memcard | the two-screen browser |
| examples/opl-env | opl-env | six screens, two themes, streamed covers |
| examples/channel6 | channel6 | the overlay browser and the probe screen |
| project/changelog | Changelog | 0.6.0 release notes and earlier releases |
| project/contributing | Contributing | setup, tests, the checks |
| project/security-and-license | Security and license | reporting, scope, licences |
| project/faq | FAQ | the questions the code answers |
| project/glossary | Glossary | terms |
| project/internals | Internals | the design and method documents, and where they live |

## Frontmatter

```yaml
---
id: cli/ps2ui-bake
title: ps2ui-bake
description: Bake ui.json files into one .uib blob and render previews.
section: cli
order: 32
version: 0.6.0
sources: [packages/baker/ps2ui_bake/cli.py, packages/baker/ps2ui_bake/vram.py]
---
```

`sources` lists the repository files the page was verified against. A
change to any of them marks the page for review.

## Links

- Internal: `[the project file](page:authoring/project-file#keys)`. The site
  build rewrites `page:` URLs. The id must exist in the index above.
- Repository: `[cli.py](repo:packages/baker/ps2ui_bake/cli.py#L131)`.
- External: an ordinary URL. Only for ps2dev, gsKit, PyPI, npm, the emulators.
- Headings use kebab-case anchors, so cross-page anchors are predictable.

## Voice and format

- Imperative mood for instructions, present tense for behaviour. "Run
  `ps2ui build`." Never "you can run".
- Forbidden words and phrases: let's, we, we'll, in this section, in this
  guide, simply, seamless, seamlessly, robust, leverage, powerful, note
  that, it's worth noting, it is worth noting, keep in mind, as you can
  see, of course, essentially, basically, easily, straightforward, delve,
  dive into, unlock, empower, journey, crucial, vital. No emoji. No
  exclamation marks. No rhetorical questions.
- Lead with what the thing does and how to use it. Say why only when the
  reason changes what the reader should do, in at most two sentences. A
  longer reason is a link to `project/internals` or to the repository doc.
- One fact per sentence. Under 25 words. No em dashes. Use a full stop or
  a comma.
- Flags, keys, functions, error codes and attributes live in tables. The
  column set per page type is fixed below. Prose never restates a table.
- Every code block is copied from a command that was run in the session or
  from a file in the tree. Output blocks show real output. Trim with `...`
  only where the trimmed lines are irrelevant.
- Numbers appear only when a command in the session produced them, and the
  command sits beside them.
- Do not copy README.md sentences. Re-derive from code and restate.
- A feature new in 0.6.0 opens its section with `New in 0.6.0.` Nothing else
  carries a version.
- A page is 300 to 1500 words of prose plus tables. Past that, split as the
  brief says.

## Page skeletons

| type | sections in order |
|---|---|
| guide | What it is · Minimal example · Reference table · Behaviour · Limits and errors · Related pages |
| cli | Synopsis · Options · Output · Exit codes · Files written · Related pages |
| api | Function tables by group · Structs · Constants · Ordering rules |
| format | Layout · Records · Invariants · Versioning |
| example | Screenshots · What it demonstrates · Build and check · Numbers from the blob · Source tour · Start from this |
| project | free-form, short |

Table columns:

| table | columns |
|---|---|
| options | flag · argument · default · effect |
| project keys | key · type · default · reaches |
| attributes | attribute · element · effect · page |
| properties | property · values · default · notes |
| functions | signature · returns · scope · notes |
| errors | code · value · triggered by · fix |
| diagnostics | message · stage · severity · cause · fix · page |
| lint rules | rule · threshold · message · opt-out |
| records | offset · size · type · field · meaning |

## Facts files

Each agent writes `_facts/<page-id>.md` before it writes the page. The page
is the reader's view; the facts file is the audit trail and the handoff.

```markdown
# facts: authoring/dynamic-text

| id | fact | source | verified by | status |
|---|---|---|---|---|
| slot.capacity.default | data-slot-capacity defaults to 63 | packages/layout/src/box.js:212 | compiled a slot with no capacity; ir.slots[0].capacity == 63 | verified |
| slot.lookup.global | ps2ui_slot_set resolves over the whole blob | runtime/ps2ui.c:1398 | runtime/tests/test_runtime.c "dynamic text (F2)" | verified |
```

Statuses:

| status | meaning |
|---|---|
| verified | a command or test in the session proved it |
| code-only | read in source; no executable check exists; the row says why |
| contradicts-readme | verified, and README.md says otherwise; the row cites the README line |

Fact ids are dotted, lowercase, stable. A dependent brief names the parent
facts files to read first and the ids it must not restate differently. A
child that finds a parent fact wrong appends a `## disputes` section to its
own facts file naming the id and the evidence, and stops. The orchestrator
reruns the parent, then the child.

## Screenshots

- UI renders come from the Python previewer only: `ps2ui_bake.preview.render`,
  `preview.montage`, and the `--preview`, `--montage`, `--preview-display`
  flags. The browser never draws UI pixels, in the docs as in the tool.
- Browser captures are allowed only for the `ps2ui serve` page chrome. Take
  them with Playwright against the preinstalled Chromium
  (`executablePath: '/opt/pw-browsers/chromium'`, viewport 1280x800). They
  are `checked: false` in the manifest, because browser text rendering is
  not byte-stable across versions.
- Theme rows: `preview.render(uib, screen=NAME, theme=N)`. Focus states:
  `preview.montage(uib)`. Widescreen: `--preview-display`. Offsets:
  `preview.render(uib, ..., offset=(dx, dy))`.
- Path: `assets/<page-id>/<what>.png`. Alt text states screen, theme,
  aspect and state.
- `assets/assets.json` lists every PNG:

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

  `OUT` is substituted by the checker. `tools/check-site-assets.py` re-runs
  every `checked: true` command into a temporary directory and diffs bytes.
  CI runs it after the example builds, next to `check-example-figures.py`.
  The script is written by the first agent that renders a PNG (the
  `cli/ps2ui-bake` brief owns it).

## Execution order

Briefs in one wave run in parallel. A wave starts when every facts file it
reads exists and carries no unresolved dispute.

| wave | pages | reads |
|---|---|---|
| 0 | authoring/project-file · cli/ps2ui-layout · cli/ps2ui-bake · cli/ps2ui-check · cli/ps2ui-fontgen · runtime/api-reference · runtime/errors-and-constants · reference/ir-format · reference/uib-format | code only |
| 1 | cli/ps2ui · authoring/html · authoring/css · authoring/text-and-fonts · authoring/images · authoring/dynamic-text · authoring/lists · authoring/focus-and-navigation · authoring/theming · authoring/screens-and-overlays · authoring/video-modes · authoring/crt-linter · authoring/vram-budget · runtime/frame-loop | wave 0 |
| 2 | cli/previewer · runtime/integrating · runtime/streaming-art · runtime/moving-and-hiding · runtime/telemetry · reference/diagnostics · reference/compatibility | waves 0 to 1 |
| 3 | getting-started/installation · getting-started/quickstart · getting-started/tutorial-game-browser · runtime/deploying · runtime/first-boot · examples/memcard · examples/opl-env · examples/channel6 · project/faq · project/glossary | waves 0 to 2 |
| 4 | index · getting-started/how-it-works · project/changelog · project/contributing · project/security-and-license · project/internals | everything |

Running a wave: spawn one agent per brief with the brief's path as its only
instruction. When all agents in the wave have written their facts files,
grep `_facts/` for `## disputes`. If any exist, rerun the disputed parent
with the dispute appended to its brief, then the disputing child. Then start
the next wave. After wave 4, run the verification below over the whole
tree.

## Environment

Every agent runs this first and stops if any step fails:

```sh
python3 -m pip install Pillow
pip install -e packages/baker
cd packages/layout && npm link && cd ../..
python3 tools/check-versions.py --except-tag
./examples/memcard/build.sh
```

That puts `ps2ui`, `ps2ui-bake`, `ps2ui-check`, `ps2ui-fontgen`,
`ps2ui-layout` and `ps2ui-dev` on PATH, pointed at this tree. Pages show the
installed spelling. Where a checkout spelling matters (CI, the examples'
`build.sh`), the page shows it once and links `cli/ps2ui#from-a-checkout`.

## Known drift

Every brief pastes the rows that touch its page. A page documents the
truth column; it never repeats the claim column.

| tag | where the stale claim lives | claim | truth |
|---|---|---|---|
| D1 | README.md Tests section; CONTRIBUTING.md | `make -C runtime test test-compat`; `PS2UI_GSKIT_HAS_FUNCTION=0` | No such target or macro. Targets: `test`, `test-narrow`, `syntax-check`, `timing-check`, `clean`. gsKit has no per-texture TFX field (BACKLOG.md F28). |
| D2 | README.md "Moving things at runtime"; runtime/ps2ui.h comment near `ps2ui_offset_set` | `ps2ui_focus_rect` | Not declared. Geometry is read from `ctx->focus_nodes[ctx->focus]`. |
| D3 | README.md (absent) | runtime API is what README shows | `ps2ui_theme_set`, `ps2ui_clut_set`, `ps2ui_slot_get`, `ps2ui_visible_get`, `ps2ui_list_select`, `ps2ui_list_selected_row`, `ps2ui_screen_name`, `ps2ui_arena_size`, `ps2ui_offset_get`, `ps2ui_crc32`, `ps2ui_clut_csm1` exist in `runtime/ps2ui.h` and are documented. |
| D4 | README.md "Focus and navigation", "Widescreen and video modes" | `--focus-wrap`, `--mode`, `--display-aspect` read as bake flags | They are `ps2ui-layout` flags. `--mode` is also on `ps2ui build`. `ps2ui-bake` has none of them. |
| D5 | README.md "Previewing in a browser" | the serve option list omits `--uib` | Options: project positional, `--uib`, `--port`, `--screen`, `--theme`, `--no-watch`, `--selftest`. |
| D6 | README.md C snippet under Quick start | `ps2ui_load` and `ps2ui_upload` called without checking returns | Document the checked form from `runtime/sample/main.c` (load failure and upload failure are fatal there). |
| D7 | README.md "Supported CSS" | the property list | Missing: `opacity`, `min-*`/`max-*`, `align-self`, `flex` shorthand, `row-gap`, `column-gap`, `:root` custom properties, `var()`, `@theme`, `data-nocontrast`, capacity default 63, the `name` attribute, `--min-font-size`. Overstated: `border-radius` takes one px value; named colours are eight; keyword-valued properties are unvalidated; the `:focus` geometry guard does not cover `letter-spacing`, `font-weight`, `text-align`, `text-overflow`; there is no `white-space: pre`; `&nbsp;` collapses to a space. |
| D8 | docs/format-ir.md | `canvas` is `{w, h}`; no `themes`; no theme vectors on commands and slots | The emitted IR carries `canvas.displayAspect`, `canvas.par`, `canvas.display`, a top-level `themes` array, and `fillVar`/`fillThemes`/`borderColorVar`/`borderColorThemes`/`colorVar`/`colorThemes` on commands plus `colorBaseVar`/`colorFocusVar`/`colorBaseThemes`/`colorFocusThemes` on slots. |
| D9 | packages/layout/bin/ps2ui-dev.js comment; packages/baker/ps2ui_bake/ps2ui.py `cmd_dev` | `ps2ui dev` honours `--strict` and `--min-font-size` | Both are set on `options` while `src/index.js` reads lint overrides from `options.lint` only. The flags are accepted and inert. Document as a limit until the code fix lands. |
| D10 | packages/baker/ps2ui_bake/serve.py `prog="ps2ui-serve"` | a `ps2ui-serve` command | Not installed. The command is `ps2ui serve`. |
| D11 | runtime/ps2ui.c comments near the upload loop and `list_row_name` | `PS2UI_MAX_TEXTURES`, `PS2UI_MAX_LIST_ROWS` | Neither exists. The only runtime cap is `PS2UI_MAX_SCISSOR_DEPTH` (8). Table counts are bounded by the format's uint16 fields. |
| D12 | README.md Quick start C comment | `PS2UI_VERSION` keeps baker and runtime from drifting | It is the frozen format version, 7. Baker and runtime match because `ps2ui vendor-runtime` ships both files from one package. |
| D13 | README.md Quick start C snippet | `arena[1662]` | Blob-specific and target-specific. Quote the arena line from a bake in the session, with the command. The bake prints the EE figure; `ps2ui-check` prints the EE and 64-bit host figures. |
| D14 | README.md "Multiple screens" | a second `ps2ui_render` in one frame with nothing else said | `gsKit_TexManager_nextFrame` is called once after the flip, never between the two renders; `ctx->stats` holds only the last render's counters. |

Two rows are code defects (D9, D1) and are queued as separate changes.
Pages document the current behaviour and say the limit is a defect.

## Brief template

Each `_prompts/<page-id>.md` has exactly these ten sections:

```
# Page: <id> (<title>)
## Purpose and audience
## Read first
## Sources of truth
## Claims to verify, and how
## Screenshots
## Page structure
## Cross-links
## Facts to emit
## Out of scope
## Done when
```

The brief is self-contained: it pastes the voice rules and the drift rows
it needs rather than linking them, so an agent that reads only its brief
still writes to the contract.

## Verification after wave 4

```sh
# every page exists and carries frontmatter with an id that matches its path
python3 - <<'PY'
import os, re, sys
root = "docs/site"
ids = set()
for d, _, fs in os.walk(root):
    for f in fs:
        if not f.endswith(".md") or d.endswith(("_prompts", "_facts")) or f == "ARCHITECTURE.md":
            continue
        p = os.path.join(d, f)
        text = open(p).read()
        m = re.search(r"^id: (.+)$", text, re.M)
        want = os.path.relpath(p, root)[:-3]
        if want == "index":
            want = "index"
        assert m and m.group(1).strip() == want, (p, m and m.group(1))
        ids.add(want)
bad = []
for d, _, fs in os.walk(root):
    for f in fs:
        if f.endswith(".md"):
            for link in re.findall(r"\(page:([^)#]+)", open(os.path.join(d, f)).read()):
                if link not in ids:
                    bad.append((f, link))
print("pages:", len(ids), "broken links:", bad)
sys.exit(1 if bad else 0)
PY

# forbidden phrases
grep -rniE "\b(let's|we'll|in this section|in this guide|simply|seamless|robust|leverage|powerful|note that|worth noting|keep in mind|as you can see|of course|essentially|basically|easily|straightforward|delve|dive into|unlock|empower|journey|crucial|vital)\b" docs/site --include=*.md | grep -v ARCHITECTURE.md | grep -v "Forbidden:"

# assets are current
python3 tools/check-site-assets.py

# the tutorial page still executes
python3 tools/check-tutorial.py    # pointed at getting-started/tutorial-game-browser.md once that page exists
```
