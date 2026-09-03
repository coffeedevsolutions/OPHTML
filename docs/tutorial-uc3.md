# Tutorial: an OPL-class game browser

The use case this toolchain was scoped against (UC-3) is a game
launcher: a list of titles on a CRT, driven by a D-pad, with the row
text filled in at runtime from whatever is on the disc. This builds a
working one from an empty directory.

You will need **Node 18+**, **Python 3 with Pillow**, and **a TTF**.
Nothing else — no clone, no build system, no C compiler until you want
the ELF.

> **Every command below is executed by CI**, in order, in a scratch
> directory, and the output blocks are matched against what actually
> happens (`tools/check-tutorial.py`). A tutorial nobody re-runs is a
> tutorial that was true once. If a number here looks wrong, it is not.

> **The packages are not published yet.** `ps2ui-layout` and
> `ps2ui-bake` below are the names they will have; today they come from
> a checkout — see [Running it before publication](#running-it-before-publication)
> at the end, which is also what CI does. `docs/releasing.md` says what
> is left.

## 1. A place to work, and fonts of your own

ps2ui bakes text at build time: glyphs are rasterized into an atlas and
positions are solved on the host, so the console never measures a
string. That means the toolchain needs *metrics* for your font, and
`ps2ui-fontgen` makes them from any TTF.

```sh
mkdir -p browser/ui && cd browser
ps2ui fontgen "$TTF_REGULAR" "$TTF_BOLD"
```

```text
ps2ui-fontgen: 115 glyphs, 284 kern pairs -> fonts/default.metrics.json
ps2ui-fontgen: 115 glyphs, 163 kern pairs -> fonts/default-bold.metrics.json
ps2ui-fontgen: manifest -> fonts/fonts.json
```

Two faces, not a weight axis: the PS2 does not have the VRAM for one.
Anything with `font-weight: 600` or more resolves to bold.

That wrote `fonts/fonts.json` as well, which names both TTFs and both
metrics files. Everything downstream reads it and you will not have to
mention fonts again. `ttf` takes a list of candidates and the first one
that exists wins, so one manifest can serve machines that keep their
fonts in different places.

## 2. The screen

```sh
cat > ui/library.html <<'EOF'
<screen name="library">
  <div class="page">
    <div class="header">
      <span class="title">Game Library</span>
      <span class="count" data-slot="count" data-slot-capacity="16">0 titles</span>
    </div>
    <div class="row" data-repeat="6" id="row-{i}" focusable>
      <span class="name" data-slot="name-{i}" data-slot-capacity="40">--</span>
      <span class="size" data-slot="size-{i}" data-slot-capacity="12">--</span>
    </div>
  </div>
</screen>
EOF
```

Three things are doing the work:

- **`data-repeat="6"`** stamps out six copies at compile time. `{i}` is
  the 0-based index, substituted in attributes and in text. The rows are
  fixed; how many *titles* you have is a runtime concern, handled by the
  list window in step 6.
- **`data-slot`** marks text the console will replace. `data-slot-capacity`
  is how many bytes to reserve — the runtime copies into that, so a
  40-byte name cannot overrun into the row below. Get it wrong and the
  text is truncated at a UTF-8 boundary, never split mid-character.
- **`focusable`** puts the row in the navigation graph. The compiler
  solves D-pad adjacency at build time; the runtime walks a table.

## 3. The style

Ordinary CSS, and `var()` is real — those custom properties become a
*tint table* in the blob, which is what makes runtime theming a table
swap rather than a re-bake.

```sh
cat > ui/library.css <<'EOF'
:root {
  --bg: #10141f; --panel: #1a2030;
  --text: #e8ecf4; --dim: #a8b2c4; --accent: #2f6fd0;
}
.page   { display: flex; flex-direction: column; padding: 32px 40px; background: var(--bg); }
.header { display: flex; flex-direction: row; padding-bottom: 12px; }
.title  { font-size: 20px; font-weight: 700; color: var(--text); flex-grow: 1; }
.count  { font-size: 14px; color: var(--dim); }
.row    { display: flex; flex-direction: row; padding: 7px 10px; background: var(--panel); margin-bottom: 3px; }
.row:focus { background: var(--accent); }
.name   { font-size: 14px; color: var(--text); flex-grow: 1; }
.size   { font-size: 14px; color: var(--dim); }
.row:focus .size { color: var(--text); }
EOF
```

`flex-direction` is **required** on any container with two or more
children. CSS's initial value is `row`; an earlier ps2ui defaulted to
`column`, and rather than teach a permanent exception or silently
relayout every existing document, the compiler asks.

That last rule is not decoration. Without it the dim `--dim` text sits
on the focused row's `--accent` blue at 2.33:1, and `--strict` refuses
the build: **CRTs crush shadows much harder than the monitor you are
designing on.** The linter checks contrast, minimum font size and the
action-safe margin, and it reads the *resolved* colour of every focus
state, not just the base one.

## 4. Say what the project is

One file, and the only two keys with no sensible default:

```sh
cat > ps2ui.json <<'EOF'
{
  "screens": ["ui/library.html"],
  "css": "ui/library.css",
  "strict": true,
  "montage": "build/states.png"
}
EOF
```

`strict` and `montage` are already optional. Without them the blob still
lands in `build/ui.uib` with a preview beside it, fonts come from
`fonts/fonts.json` next to this file, and every path is relative to the
project rather than to wherever you happen to be standing.

A key nothing reads is an **error**, not a shrug — misspell
`minFontSize` and the message names it and lists what a project takes.
The whole set: `screens`, `css`, `fonts`, `out`, `preview`, `montage`,
`previewDisplay`, `mode`, `canvas`, `displayAspect`, `strict`,
`minFontSize`, `focusWrap`, `palettizeImages`, `vramBudget`.

A screen is usually a path. When one needs something the others do not,
it becomes an object — `{ "html": "ui/probe.html", "focusWrap": true }`.

## 5. Build

```sh
ps2ui build
```

```text
ps2ui-layout: 14 paint commands, 6 focusables -> build/library.json
ps2ui-bake: 1 screen(s), 24 records, 2 textures (32 KiB baked), 1 CLUTs -> build/ui.uib
ps2ui-bake: arena 1516 bytes (static uint8_t arena[1516] __attribute__((aligned(16))))
ps2ui-bake: preview -> build/preview.png
ps2ui-bake: montage -> build/states.png
```

Two stages ran. `build/library.json` is the **intermediate
representation**: a flat display list with the flexbox already solved,
every string already measured and kerned, and the focus graph resolved.
It is a documented format (`docs/format-ir.md`), so you can generate it
from something other than HTML. `build/ui.uib` is what ships.

`ui.uib` is what ships to the console: quads, texture atlases, palettes,
the slot table, the focus graph and the tint table, in one file the
runtime validates and points into without copying.

**The arena line is the number to keep.** The runtime allocates nothing;
you give it that many bytes and it carves them. Paste the declaration
into your program. Six rows and thirteen slots cost 1,516 bytes, and the
whole six-screen environment `examples/opl-env` builds asks for 7,319.

`preview.png` replays the blob on the host with the same pen the console
uses — so it shows what the PS2 will draw, not what a browser thinks the
CSS means. `states.png` is every focus state as a contact sheet.

## 6. Check it

```sh
ps2ui check
```

```text
# build/ui.uib: 640x448 at 4:3, 1 screen(s), 24 commands, 2 textures, 13 slots
PASS: 51 checks, 0 error(s), 0 warning(s)
```

`ps2ui-check` validates the blob against what the C runtime assumes —
table bounds, texture residency, scissor depth, VRAM budget, palette
ratios, dead commands outside their clip. It is the same contract the
runtime enforces at load, run offline so a bad blob never reaches a
console.

## 7. Drive it from C

The runtime is one `.c` and one `.h` you compile with your project
against [gsKit]. The whole surface is small enough to list:

```c
static uint8_t arena[1516] __attribute__((aligned(16)));   /* from the bake */
ps2ui_ctx ui;

ps2ui_load(&ui, blob, blob_len, arena, sizeof arena);
ps2ui_upload(&ui, gs);                       /* atlases and palettes to VRAM */

ps2ui_list list;
ps2ui_list_init(&list, "row-", 6);           /* the six baked rows */
ps2ui_list_set_count(&ui, &list, n_games);   /* however many you found */

for (;;) {
    if (pad_down)  ps2ui_list_move(&ui, &list, +1);
    if (pad_up)    ps2ui_list_move(&ui, &list, -1);

    for (uint16_t r = 0; r < list.rows; r++) {
        int item = ps2ui_list_item_at(&list, r);
        char name[8];
        sprintf(name, "name-%u", r);
        ps2ui_slot_set(&ui, name, item < 0 ? "" : titles[item]);
    }
    ps2ui_slot_set(&ui, "count", count_text);

    ps2ui_render(&ui, gs);                   /* never clears: see below */
    gsKit_queue_exec(gs); gsKit_sync_flip(gs);
    gsKit_TexManager_nextFrame(gs);
}
```

`ps2ui_render` **never clears the frame**, and that is a guarantee, not
an omission: call `ps2ui_screen_set` and render twice and the second
screen composites over the first. That is the whole dialog and overlay
technique — no format flag, no new API, an overlay is an ordinary screen
with a translucent scrim.

`docs/bringup.md` is the ordered procedure for the first run on real
hardware, each step with its expected result and failure symptom.

## Running it before publication

`ps2ui-layout` and friends are not on npm and PyPI yet. From a checkout,
these are the same commands:

```
ps2ui         ->  PYTHONPATH=<repo>/packages/baker python3 -m ps2ui_bake.ps2ui
ps2ui-layout  ->  node <repo>/packages/layout/bin/ps2ui-layout.js
ps2ui-dev     ->  node <repo>/packages/layout/bin/ps2ui-dev.js
ps2ui-bake    ->  PYTHONPATH=<repo>/packages/baker python3 -m ps2ui_bake
ps2ui-check   ->  PYTHONPATH=<repo>/packages/baker python3 -m ps2ui_bake.check
ps2ui-fontgen ->  PYTHONPATH=<repo>/packages/baker python3 -m ps2ui_bake.fontgen
```

`ps2ui build` runs the compiler as a subprocess, so it has to find it.
It looks at `$PS2UI_LAYOUT`, then `ps2ui-layout` on `PATH`, then the
checkout it might be sitting in — and when none of those has it, says
`npm install -g @ps2ui/layout` rather than failing on a path you never
chose.

`tools/check-tutorial.py` puts exactly those on `PATH` as shims and runs
this document, which is how the commands above stay true: they are
written for the stranger the exit gate names, and executed today.

[gsKit]: https://github.com/ps2dev/gsKit
