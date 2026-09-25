# Page: runtime/console-launcher (Console launcher)

Page type: `guide`. Section order: `49`. Wave: `3`. Model tier: `sonnet`.

The model tier is the one the orchestrator spawns this brief on: `opus` for a page whose claims are derived from source and proved by running code; `sonnet` for a page that consolidates facts parents already verified, follows a CI-executed script, or restates repository documents.

## Purpose and audience

For someone who has a theme, or wants one, and a PlayStation 2, and does not want to write C. The page gets `ophtml.elf` onto a console with Neutrino and a game library, names what the launcher fills in a theme, and says plainly that the launcher has not yet been run on a console.

## Read first

1. `docs/site/ARCHITECTURE.md`, all of it. Its voice, format and link rules are binding.
2. Parent facts files: `_facts/cli/ps2ui-check.md` (the console checks), `_facts/cli/previewer.md` (`serve --console`), `_facts/runtime/deploying.md` (getting an ELF onto a console). Reuse their ids; do not restate them differently.
3. `console/README.md`, all of it, and its bench table. The page restates it for a reader who has not cloned the repository; it does not copy its sentences.

## Sources of truth

Authority order: code, then tests, then `console/README.md`.

- `console/main.c`: `choose_theme`, `count_rows`, `fill`, `wait_for_drives`, `scan_all`, `launch_selected`, `wants_mx4sio`, `main`'s three `hold` calls and its input loop.
- `console/launch.c`: `console_find_neutrino`.
- `console/library.c`: `console_bsd_from_driver`, `console_bsd_label`.
- `console/scan.c`, `console/storage.c`: the folders scanned and the module table.
- `.github/workflows/console-release.yml`: what a tag attaches to a release.
- `console/tests/mock_expected.py`, `packages/baker/ps2ui_bake/console.py`: the mock frame.

## Claims to verify, and how

- Each status string, the three hold colours, the theme order and the Neutrino order, by reading the function named above and citing it.
- The labels and the scan, by `make -C console/tests test`.
- The screenshot, by running the command recorded in `assets/assets.json`.
- Whether any GitHub Release carries `ophtml.elf` yet, from the repository's release list. Word the download step so it is true either way.
- That nothing has run on a console, from the bench table's `[open]` markers. Re-read them when regenerating: a case a sitting has reported changes what the page may claim.

## Screenshots

One: `assets/runtime/console-launcher/mock-filled.png`, from `python3 console/tests/mock_expected.py examples/console/build/ui.uib OUT --keys down,down,down` after `./examples/console/build.sh`. It is the frame hw.yml compares the emulator against, so the caption says it is the previewer's drawing, not a photograph of a console.

## Page structure

guide: What it is · Minimal example · Reference table · Behaviour · Limits and errors · Related pages. Tables: the contract names (name · element · filled with), the drives (drive · attached · label), the controls (button · action), the two search orders, the status strings (status · cause · fix), the start-up colours (screen · meaning).

## Cross-links

`cli/ps2ui-check#options`, `cli/previewer#options`, `authoring/lists`, `runtime/deploying`, `runtime/errors-and-constants`. Repository links to `console/README.md` for the bench cases, the build line and the loader's colours.

## Facts to emit

`launcher.*` rows: release assets, untested on hardware, the mock frame, theme order, screen, rows, names, scan, drives, exFAT, the wait, Neutrino order, MX4SIO, controls, status strings, colours.

## Out of scope

The C behind the launcher beyond what a reader acts on (module order, elf-loader, `-qb`); `console/README.md` and the source carry it. Building the launcher, beyond one link to the Docker line. Cover art and per-game settings, which do not exist yet: the page says so in one sentence.
