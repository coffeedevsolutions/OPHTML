# facts: runtime/console-launcher

Session commands, all run from the repository root.

- `./examples/console/build.sh`: exit 0, blob at `examples/console/build/ui.uib`.
- `python3 console/tests/mock_expected.py examples/console/build/ui.uib OUT --keys down,down,down`:
  `mock_expected: 10 rows, keys [down,down,down] -> selection 3 (row 3)`,
  which is the page's screenshot and the command in `assets/assets.json`.
- `actionlint .github/workflows/console-release.yml`: no findings.
- `grep -n` over `console/main.c`, `console/launch.c`, `console/library.c`,
  `console/scan.c` and `console/storage.c` for each symbol cited below.

No row here was run on a console. Every hardware claim on the page is stated
as untested, and `console/README.md`'s bench cases C1 to C8 are the checks.

| id | fact | source | verified by | status |
|---|---|---|---|---|
| launcher.release.assets | Pushing a tag matching `v[0-9]*` or `N.N.N` runs `console-release.yml`, which bakes `examples/console`, builds `ophtml.elf` and `ophtml-mock.elf` in the ps2dev container, and attaches both with `SHA256SUMS` to the tag's GitHub Release, creating it as a draft when it does not exist | .github/workflows/console-release.yml:24, .github/workflows/console-release.yml:98-99, .github/workflows/console-release.yml:127, .github/workflows/console-release.yml:134-135 | read the workflow; actionlint clean. Not yet run: no tag has been pushed since it was added | code-only |
| launcher.release.none-before | No GitHub Release in the repository carries `ophtml.elf` when this page was written, so the page tells a reader to build from a checkout when a release has none | .github/workflows/console-release.yml:127 | the GitHub API's release list for the repository returned no releases | verified |
| launcher.hardware.untested | The launcher has booted only in Play!, which has no USB, HDD or memory card slot; no drive has been read and no game started | console/README.md:225 | `console/README.md`'s bench table lists C1 to C8 all `[open]` | verified |
| launcher.mock.frame | The page's screenshot is the frame hw.yml compares a MOCK build against, drawn by the previewer through `console.py` after three presses of Down | console/tests/mock_expected.py:24-49 | ran the command above; hw.yml's two console steps call the same script | verified |
| launcher.theme.order | The theme is `theme.uib` in the ELF's folder, then `OPHTML/theme.uib` on each drive, then the built-in one; a refused blob falls back and `status` reads `<path> refused (<code>); built-in theme` | console/main.c:200-223 | read `choose_theme` | code-only |
| launcher.screen | The launcher opens on a screen named `games`, and a theme without one stays on its first screen | console/main.c:463 | `ps2ui_screen_set` leaves the screen unchanged on an unknown name | code-only |
| launcher.rows | Rows are counted from `game-0` up to the first missing number | console/main.c:286-295 | read `count_rows` | code-only |
| launcher.names | The launcher fills `game-{i}-title`, `-id`, `-media`, `-device`, the four `sel-*` slots, `game-count` and `status` | console/main.c:255-263, console/main.c:342 | read `fill`; `TestRestatedFromC` in `packages/baker/tests/test_console.py` parses the same names | verified |
| launcher.scan | Each drive's `DVD/` and `CD/` are scanned and the games sorted by title; the ID comes from the file name or the disc | console/scan.c:29, console/scan.c:50, console/scan.c:70-71, console/main.c:339 | `make -C console/tests test` covers the name and disc paths | verified |
| launcher.drives | Labels are `USB`, `HDD`, `SD` and `MMCE`, from the BDM driver name or the MMCE device | console/library.c:9-19, console/library.c:33-42 | `make -C console/tests test` | verified |
| launcher.exfat | The HDD is read through `ata_bd` and FatFs with exFAT, so an APA drive is not read | console/storage.c:67-68 | read the module table | code-only |
| launcher.wait | The wait ends when the mounts stop changing, capped at 300 frames, which is 5 s at 60 Hz and 6 s on a PAL console | console/main.c:303, console/main.c:308 | read `wait_for_drives` | code-only |
| launcher.neutrino.order | Neutrino is looked for beside the ELF, then at each drive's root, then under `APPS/neutrino/` on `mc0:` and `mc1:` | console/launch.c:52-66, console/launch.c:67-69, console/launch.c:70-71 | read `console_find_neutrino`; the drive loop and the card loop are cited on their own first lines, so swapping them drifts a pinned line (F49: a range is checked on its first line only) | code-only |
| launcher.mx4sio | MX4SIO loads instead of MMCE when the ELF's name contains `m4s` or `M4S`, or it is passed `-mx4sio` | console/main.c:428-439 | read `wants_mx4sio` | code-only |
| launcher.controls | Up and Down move the list, Left and Right move focus, L1 and R1 page, and ✕ launches | console/main.c:483-505 | hw.yml's pad step proves Down, R1 and L1 in Play! on the ROM pad modules | verified |
| launcher.status | The status strings the page lists: `No drives found`, `No ISOs in DVD/ or CD/`, `Neutrino not found: put neutrino/ at a drive's root`, `Could not start Neutrino (<code>)` and `This theme has no game-0 row to list games in` | console/main.c:347, console/main.c:349, console/main.c:393, console/main.c:405, console/main.c:474 | read `scan_all`, `launch_selected` and `main`; each string cited on its own line, so a changed string drifts a pinned line | code-only |
| launcher.colours | Grey is a module failure, red the built-in theme failing, yellow a VRAM failure; yellow holds, with no fallback to the built-in theme, because the upload is after the theme is chosen | console/main.c:222, console/main.c:453, console/main.c:459 | read the three `hold` calls | code-only |
