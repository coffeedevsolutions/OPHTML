---
id: cli/ps2ui-check
title: ps2ui-check
description: Validate a baked .uib against the invariants the C runtime indexes by without checking.
section: cli
order: 33
version: 0.7.0
sources: [packages/baker/ps2ui_bake/check.py, packages/baker/ps2ui_bake/uib.py, packages/baker/ps2ui_bake/ps2ui.py, packages/baker/ps2ui_bake/vram.py, packages/baker/ps2ui_bake/caps.py, packages/baker/ps2ui_bake/clip.py, packages/baker/ps2ui_bake/cli.py, packages/baker/tests/test_baker.py, tools/check-blobs.sh, runtime/ps2ui.h, .github/workflows/ci.yml, .github/workflows/hw.yml, examples/memcard/build.sh, examples/memcard/ps2ui.json, README.md, CHANGELOG.md]
---

# ps2ui-check

`ps2ui-check` reads one `.uib` blob and reports, in TAP, every invariant the runtime relies on but does not verify. The loader refuses a blob with bad magic, a wrong version, a failed CRC or unknown feature bits. Everything past that point is indexed directly, so a wrong index or an unbalanced scissor draws the wrong thing on console with no diagnostic. This command finds those cases on the host. The loader's own refusals are on [Errors and constants](page:runtime/errors-and-constants#constants); the file layout it walks is on [.uib](page:reference/uib-format#invariants).

## Synopsis

```sh
ps2ui-check build/ui.uib
ps2ui-check build/ui.uib --strict
ps2ui-check build/ui.uib --allow-dead 1 --strict
ps2ui-check build/ui.uib --tints
```

`ps2ui check` runs the same code on a project's output blob and forwards the project's `vramBudget` and `strict` keys. See [ps2ui](page:cli/ps2ui#synopsis). The checkout spelling is `PYTHONPATH=packages/baker python3 -m ps2ui_bake.check`, which is what [tools/check-blobs.sh](repo:tools/check-blobs.sh#L83) uses.

## Options

Output of `ps2ui-check --help`:

```
usage: ps2ui-check [-h] [--version] [--vram-budget BYTES] [--allow-dead N]
                   [--allow-hairline N] [--strict] [--tints]
                   uib

Validate a baked .uib against what the C runtime assumes.

positional arguments:
  uib                  path to a .uib blob

options:
  -h, --help           show this help message and exit
  --version            show program's version number and exit
  --vram-budget BYTES  override the default texture VRAM budget
  --allow-dead N       N draw commands outside their clip are deliberate
                       (data-keep instruments); more than N still warns
  --allow-hairline N   N 1px quads are deliberate (the test card's edge rules
                       and interlace pair); more than N still warns
  --strict             treat CRT warnings as failures
  --tints              print the tint table, one row per entry and one column
                       per theme, then exit
```

| flag | argument | default | effect |
|---|---|---|---|
| `uib` | path | required | the blob to read; positional |
| `--version` | none | | print `ps2ui-check <version>` and exit 0 |
| `--vram-budget` | `BYTES` | 4 MiB minus three framebuffers at the canvas | the limit the VRAM check compares against; see [VRAM budget](page:authoring/vram-budget#behaviour) |
| `--allow-dead` | `N` | 0 | declare that exactly N commands fall outside their clip on purpose |
| `--allow-hairline` | `N` | 0 | declare that exactly N quads are 1px wide or tall on purpose |
| `--strict` | none | off | count failed warnings as failures in the exit code |
| `--tints` | none | off | print the tint table and exit 0 without running any check |

## Output

### TAP shape

Note lines come first, then one result per check, then the plan, a summary line, and the verdict. Run on the memcard example:

```
$ ps2ui-check examples/memcard/build/ui.uib
# arena: 1662 bytes on the EE (1750 on a 64-bit host; GSTEXTURE holds pointers, so the two differ)
# font 0 (size 13): 113 inked glyphs, 74 of non-power-of-two width, 99 of non-power-of-two height
# font 1 (size 14): 113 inked glyphs, 82 of non-power-of-two width, 83 of non-power-of-two height
ok 1 - 11 textures fit the format's uint16 count field
ok 2 - 1 CLUTs fit the format's uint16 count field
ok 3 - 6 slots fit the format's uint16 count field
ok 4 - 2 screens fit the format's uint16 count field
ok 5 - at least one screen -- a UI with none has nothing to draw and ps2ui_load refuses it
...
ok 60 - VRAM 160 KiB within budget 736 KiB
ok 61 - no 1px quads to shimmer on an interlaced CRT
ok 62 - every command can produce a pixel
ok 63 - every texture is drawn or belongs to a font
1..63
# examples/memcard/build/ui.uib: 640x448 at 4:3, 2 screen(s), 1062 commands, 11 textures, 6 slots
PASS: 63 checks, 0 error(s), 0 warning(s)
```

| line | form | meaning |
|---|---|---|
| note | `# <text>` | a measured number with no threshold; not counted in the plan |
| passed check | `ok N - <label>` | the invariant holds |
| failed warning | `ok N - <label> # TODO warning` | legal blob, known to look wrong or waste the GS on a CRT |
| failed error | `not ok N - <label>` | the console will misbehave |
| plan | `1..N` | N is the number of checks, notes excluded |
| summary | `# <path>: WxH at A:B, S screen(s), C commands, T textures, L slots` | the blob's headline figures |
| verdict | `PASS: N checks, E error(s), W warning(s)` or `FAIL: ...` | PASS when E is 0, and W is 0 under `--strict` |

A failed warning still starts with `ok`, which is TAP's TODO convention. Grep for `TODO` to find warnings and for `^not ok` to find errors. The check count varies by blob: two fonts and two screens give memcard 63 checks, channel6 has 75 and opl-env 107.

### The arena note

The first note is the arena size the integrator declares. `ps2ui-check` prints two figures because `GSTEXTURE` holds pointers, so the same blob needs a different arena on a 64-bit host than on the EE. The bake prints only the EE figure. Both come from the same blob and the same function, [arena.py](repo:packages/baker/ps2ui_bake/arena.py):

```
$ ps2ui-bake examples/memcard/build/library.json examples/memcard/build/saves.json -o /tmp/memcard.uib
...
ps2ui-bake: arena 1662 bytes (static uint8_t arena[1662] __attribute__((aligned(16))))
```

The figure belongs to that blob. The channel6 blob prints `10624 bytes on the EE (10824 on a 64-bit host ...)`, and opl-env prints `7319` and `7487`. Take the number from the check or bake of the blob you ship, never from a snippet.

### The catalogue

Checks run in nine groups, in the order below. A label pattern in braces is filled from the blob. A bracketed suffix appears only on failure and names the first five offenders. Groups are the functions in [check.py](repo:packages/baker/ps2ui_bake/check.py#L629).

| label pattern | severity | meaning | change |
|---|---|---|---|
| `{n} textures/CLUTs/slots/screens fit the format's uint16 count field` | error | a table count exceeds 65535 | fewer entries of that kind |
| `at least one screen -- a UI with none has nothing to draw and ps2ui_load refuses it` | error | the screen table is empty | give the project at least one screen |
| `the streamed-texture feature bit matches the texture table ({n} streamed)` | error | feature bit and table disagree | rebake; a hand-written blob must set the bit when it streams |
| `every streamed texture is named, so something can fill it` | error | a streamed slot has no name for `ps2ui_tex_set` to find | name the `<img>` that streams |
| `every streamed texture states a nonzero reservation` | error | a streamed slot reserves no VRAM | give the streamed image a width and height |
| `no streamed texture carries texels in the blob` | error | a streamed entry also carries pixel bytes | rebake; the writer emitted both |
| `texture names are unique, so a name identifies one slot` | error | two textures share a name | rename one image |
| `no font points at a streamed texture` | error | an atlas is marked streamed | rebake; the writer mislabelled an atlas |
| `blob section starts 16-aligned in the file (off_blob={n})` | error | the pixel section is not qword aligned | rebake with the current baker |
| `every baked texture's pixel bytes 16-aligned for in-place DMA[; misaligned: [...]]` | error | a texture's bytes start unaligned; the GIF DMA would read early | rebake with the current baker |
| `every TEXQUAD names a real texture[; commands [...]]` | error | a textured quad indexes past the texture table | rebake; a hand-written blob fixes the index |
| `every indexed texture names a real CLUT[; textures [...]]` | error | a palette index is out of range | rebake |
| `every PSMT8 texture carries a CLUT[; textures [...]]` | error | an 8-bit texture has no palette, so the last resident one would be used | palettize with a CLUT or bake as 32-bit |
| `every slot names a real font table[; slots ...]` | error | a `data-slot` points at a missing font | check `fonts.json` covers the slot's weight and size |
| `every command's focus index is in range[; commands [...]]` | error | a command's focus index is past the focus table | rebake |
| `every command carries a known state` | error | a state byte is not always, focused or unfocused | rebake |
| `every focus-dependent command names a focus node[; commands [...]]` | error | a `:focus` styled command has no focus index, so it can never resolve | rebake; a hand-written blob sets the index |
| `at least one screen` | error | same as above; the remaining screen checks are skipped when it fails | as above |
| `screens partition the command/focus/slot table contiguously ({cursor}/{total})` | error | a gap or overlap between screen ranges; commands no screen draws, or one screen drawing another's | rebake; a hand-written blob makes ranges adjacent |
| `screen names are unique: [...]` | error | two screens share a name | rename a screen file |
| `{screen}: no focusables, so no initial focus` | error | a screen without focusables names an initial focus | rebake |
| `{screen}: initial focus is one of its own focusables` | error | the initial focus lies outside the screen's range | rebake |
| `{screen}: no D-pad edge leaves the screen[; from ...]` | error | a focus edge points at a node another screen draws | rebake; the compiler never emits this |
| `{screen}: every focusable reachable by D-pad[; stranded: ...]` | error | a control the D-pad can never reach from the initial focus | move the control, or add a neighbour; see [Focus and navigation](page:authoring/focus-and-navigation#behaviour) |
| `header initial_focus matches screen 0` | error | the header and the first screen disagree | rebake |
| `{screen}: scissor nesting {n} within PS2UI_MAX_SCISSOR_DEPTH (8)` | error | `overflow: hidden` nests 8 deep or more; the runtime's stack is fixed | flatten the nesting; the cap is on [Errors and constants](page:runtime/errors-and-constants#constants) |
| `{screen}: scissor pushes and pops balance[ (underflow)/ ({n} left open)]` | error | a clip leaks into the next draw, or a pop underflows | rebake; the compiler always balances |
| `every quad's alpha is in the GS 0-128 domain[; commands [...]]` | error | an alpha above 0x80 is more than opaque on the GS | rebake; the baker halves CSS alpha |
| `TEXQUAD colors are in the 0x80 modulate-identity domain[; commands [...]]` | error | a texture tint above 0x80 brightens texels | rebake |
| `slot base/focus colors are in the modulate domain[; slots ...]` | error | a slot colour above 0x80 | rebake |
| `the blob has at least one theme row -- a themeless UI is one row, not zero` | error | the theme table is empty | rebake |
| `{n} tints fit the format's uint16 count field` | error | more than 65535 tint entries | fewer distinct colours |
| `{n} tints over {p} painting commands: the palette is a small repeated set, which is what makes a theme a table swap` | error | tint entries times four reach the paint count; asserted only when p is 100 or more, otherwise a note | the baker stopped deduplicating colours; see [Theming](page:authoring/theming#behaviour) |
| `{t} theme(s) with FEAT_ROLE_TINTS set/clear: more than one row needs the bit, or ps2ui_load refuses the blob` | error | several themes with value-keyed tints | rebake |
| `font {i} names a real atlas texture` | error | the font's atlas index is out of range | rebake |
| `font {i} has at least one glyph` | error | an empty glyph table | check the charset in `fonts.json` |
| `font {i} glyphs are codepoint-sorted for bsearch` | error | the runtime's binary search would miss glyphs | rebake |
| `font {i} kern pairs are sorted for bsearch` | error | same, for kerning | rebake |
| `font {i} stores no zero kerns` | error | a zero pair is a lookup that returns a miss | rebake |
| `font {i} kerns only pairs it has glyphs for[; {n} orphaned]` | error | a pair names a glyph outside the charset | rebake |
| `the kerning feature bit matches the kern tables[ ({n} pairs)]` | error | pairs present with the bit clear, or the reverse; the runtime may skip the lookup | rebake |
| `the slot-spacing feature bit matches the slot table` | error | a slot has `letter-spacing` with the bit clear, or the reverse | rebake |
| `every slot placeholder is fully covered by its font[; {slot} ({chars}), ...]` | error | placeholder text uses a codepoint the font lacks; blank on console | add the character to the charset or change the placeholder |
| `VRAM {used} KiB within budget {limit} KiB[ -- the default budget is unusable at this canvas, see notes]` | error | textures and CLUTs, charged in pages, exceed the budget | shrink or palettize images, or declare the real budget |
| `no 1px quads to shimmer on an interlaced CRT` / `{n} 1px quad(s) will shimmer on an interlaced CRT[; {N} declared deliberate]` | warning | a quad 1px wide or tall flickers on an interlaced field | make rules 2px, or declare the count |
| `every command can produce a pixel` / `{n} command(s) fall entirely outside their clip and are submitted every frame for nothing (from command {i}); usually the tail of a nowrap run inside overflow:hidden[; {N} declared deliberate]` | warning | a command outside its clip and the canvas, submitted every frame | shorten the text, or declare the count |
| `every texture is drawn or belongs to a font` / `textures [...] are never drawn but still cost VRAM` | warning | an image no command references | remove the `<img>` |

Three notes join the arena note. Each font prints its inked glyph count and how many are not power-of-two sized, because the GS drops the last texel row of such a quad. A blob under 100 painting commands prints the tint ratio instead of asserting it. The VRAM check prints two explanatory lines when the default budget cannot exist at the canvas.

### VRAM

New in 0.6.0. When no `--vram-budget` is given and three framebuffers at the canvas do not fit in 4 MiB, the VRAM label ends with `-- the default budget is unusable at this canvas, see notes`. Two note lines then state the arithmetic and the budget to declare with Z buffering off. A budget passed on the command line suppresses both. The same function feeds `ps2ui build`, so the two commands print the same explanation. Passing a tiny budget shows the error form:

```
$ ps2ui-check examples/memcard/build/ui.uib --vram-budget 1
...
not ok 60 - VRAM 160 KiB within budget 0 KiB
# examples/memcard/build/ui.uib: 640x448 at 4:3, 2 screen(s), 1062 commands, 11 textures, 6 slots
FAIL: 63 checks, 1 error(s), 0 warning(s)
```

The budget model and the page-charging rule are on [VRAM budget](page:authoring/vram-budget#behaviour).

### Declared counts

`--allow-dead N` and `--allow-hairline N` are assertions, not ceilings. Only the exact count passes. Fewer than N means an instrument the count names has gone missing. More than N is the accident the check exists for. The channel6 probe screen parks one quad outside its clip on purpose, so its CI rule declares 1:

```
$ ps2ui-check examples/channel6/build/ui.uib --allow-dead 1 --strict
...
ok 74 - 1 dead command(s), 1 declared deliberate (--allow-dead)
...
PASS: 75 checks, 0 error(s), 0 warning(s)
```

Declare one more than the blob carries and the check warns in the other direction:

```
$ ps2ui-check examples/channel6/build/ui.uib --allow-dead 2 --strict
...
ok 74 - 1 dead command(s), but 2 declared deliberate (--allow-dead): 1 of the instruments that count names is gone, and the check can no longer see what it measures # TODO warning
...
FAIL: 75 checks, 0 error(s), 1 warning(s)
```

The hairline flag has the same three verdicts. memcard has no 1px quads, so declaring one warns:

```
$ ps2ui-check examples/memcard/build/ui.uib --allow-hairline 1
...
ok 61 - 0 1px quad(s), but 1 declared deliberate (--allow-hairline): 1 of the instruments that count names is gone, and the check can no longer see what it measures # TODO warning
...
PASS: 63 checks, 0 error(s), 1 warning(s)
```

The CRT rules the compiler applies before the bake are on [CRT linter](page:authoring/crt-linter#reference-table); the three warnings here are the ones only a finished blob can show.

### The tint table

`--tints` prints the theme table a loader finds and exits without running checks. One row per entry, one colour column per theme, and a `where` column: `cmd`, `slot`, `UNREFERENCED` when nothing points at the entry, and `fixed in every theme` when every theme holds the same value. The blob carries no `var()` names, so `ps2ui-bake --tints` prints the other half; see [ps2ui-bake](page:cli/ps2ui-bake#output) and [Theming](page:authoring/theming#reference-table). The opl-env blob has two themes:

```
$ ps2ui-check examples/opl-env/build/ui.uib --tints
# 28 tint entries over 2 theme(s)
  idx  theme 0               theme 1               where
    0  ( 11, 15, 22,128)     (244,246,250,128)     cmd
    1  (121,123,125,128)     (  8, 11, 18,128)     cmd, slot
...
    9  (128,128,128,128)     (128,128,128,128)     cmd, fixed in every theme
...
```

## Exit codes

| code | value | triggered by | fix |
|---|---|---|---|
| unreadable | 2 | `read_uib` refuses the file: truncated header, bad magic, wrong version, unknown feature bits, CRC mismatch, blob past EOF, zero themes, or an index past a table. One line on stderr, no TAP | rebake; the blob is not a v7 file the loader would open |
| fail | 1 | at least one error, or under `--strict` at least one warning | change what the failed label names |
| pass | 0 | no errors, and no warnings under `--strict`; also every `--tints` run | none |

A flipped byte in a copy of the memcard blob:

```
$ ps2ui-check corrupt.uib
ps2ui-check: corrupt.uib: crc mismatch (file 0x4d8c37e4, computed 0x5dc0fb31)
```

Exit code 2. The verdict line prints the warning count whether or not `--strict` counts it. channel6 with no flags prints `PASS: 75 checks, 0 error(s), 1 warning(s)` and exits 0; with `--strict` alone it prints `FAIL` and exits 1.

### The CI wrapper

[tools/check-blobs.sh](repo:tools/check-blobs.sh#L28) is the only place the per-blob flags live. Both `ci.yml` and `hw.yml` call it, so one blob cannot pass under one workflow and fail under the other. Every blob runs `--strict`; anything deliberate is declared by exact count.

| blob | flags |
|---|---|
| `examples/memcard/build/ui.uib` | `--strict` |
| `examples/opl-env/build/ui.uib` | `--strict` |
| `examples/memcard/build/testcard.uib` | `--allow-hairline 5 --strict` |
| `examples/channel6/build/ui.uib` | `--allow-dead 1 --strict` |
| `examples/channel6/build/ui-16x9.uib` | `--allow-dead 1 --strict` |

With no arguments the script checks every known blob that exists. A named blob must exist and must be in the table; an unknown path exits 2 with `check-blobs: no rules for <blob>`. Zero blobs checked also exits 2. In this tree the test card is not built, so the script reports four:

```
$ sh tools/check-blobs.sh
...
check-blobs: 4 blob(s) validated
```

## Files written

None. Results go to stdout and refusal messages to stderr. The input blob is only read.

## Related pages

- [ps2ui](page:cli/ps2ui#synopsis), the `ps2ui check` subcommand and the project keys it forwards.
- [ps2ui-bake](page:cli/ps2ui-bake#output), which prints the EE arena figure and the named tint table.
- [Previewer](page:cli/previewer#options), whose `--uib` flag opens the same blob after it passes; check first, then look.
- [.uib](page:reference/uib-format#invariants), the tables and feature bits the catalogue reads.
- [Errors and constants](page:runtime/errors-and-constants#constants), what `ps2ui_load` refuses on its own and `PS2UI_MAX_SCISSOR_DEPTH`.
- [VRAM budget](page:authoring/vram-budget#behaviour), [Theming](page:authoring/theming#reference-table), [CRT linter](page:authoring/crt-linter#reference-table).
