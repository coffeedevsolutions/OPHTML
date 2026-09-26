# facts: authoring/dynamic-text

Session commands were run from the repository root. `<scratch>` is
`/tmp/claude-0/-home-user-OPHTML/6b0c72b8-d98f-5f58-b749-f9808bb620d6/scratchpad/authoring-dynamic-text`.
Compiles are `ps2ui-layout <html> <css> --fonts fonts/fonts.json -o <scratch>/<name>.json`.
Bakes are `ps2ui-bake <json...> -o <scratch>/<name>.uib --fonts fonts/fonts.json`.
`make -C runtime test` printed `PASS: 410 checks, 0 failure(s)`; "ok N" below is that
run's numbering. `python3 -m unittest test_baker.TestSlotCapacity test_baker.TestDynamicText
test_baker.TestSlotSpacing` from `packages/baker/tests` printed `Ran 11 tests ... OK`.

Parent facts reused without restatement: `ir.schema.slot`, `ir.schema.slot.capacity`,
`ir.schema.slot.unique`, `ir.schema.slot.single-line`, `html.slot.single-text`,
`html.slot.needs-name`, `html.attributes.capacity`, `api.functions.slot_set`,
`api.functions.slot_get`, `api.scope.rules.slot`, `api.return-conventions.one-zero`,
`api.return-conventions.null`.

| id | fact | source | verified by | status |
|---|---|---|---|---|
| slot.capacity.default | `data-slot-capacity` defaults to 63 when the attribute is absent; the value is parsed with `parseInt` and reaches the IR unchanged | packages/layout/src/box.js:220 | parent `ir.schema.slot.capacity`; re-run this session: `<scratch>/cap.html` carries `data-slot="count"` with no capacity and its IR slot printed `"capacity": 63` | verified |
| slot.capacity.uint16 | Capacity is a uint16 in the blob. The baker does not clamp it; `caps.check` refuses a capacity above 65535 with `slot '<name>': capacity <n> does not fit the format's uint16 capacity field.` and exit 1 | packages/baker/ps2ui_bake/quads.py:722-730; packages/baker/ps2ui_bake/caps.py:117-124 | baked `<scratch>/big.json` (capacity 70000): `error: slot 'count': capacity 70000 does not fit the format's uint16 capacity field.`, exit 1; `test_baker.TestSlotCapacity` both tests pass (`test_capacity_survives_the_bake` records 200, `test_a_capacity_the_format_cannot_hold_is_refused`) | verified |
| slot.capacity.bytes | Capacity is a byte count, not a character count. The runtime carves capacity+1 bytes per slot from the arena, packed end to end | runtime/ps2ui.c:1490-1494; runtime/ps2ui.h:672-673 | ok 109-112 (two slots with capacities 15 and 31 truncate at their own figure; buffers are packed at capacity+1 with no gaps) | verified |
| slot.rules | A `data-slot` element must name the slot, hold exactly one text node with no child elements, have a placeholder that fits on one line, and use a name no other slot in the blob uses | packages/layout/src/box.js:202-222; packages/layout/src/paint.js:195-202, packages/layout/src/paint.js:329-335; packages/baker/ps2ui_bake/quads.py:644-664 | the four errors triggered this session, each exit 1, see the four rows below | verified |
| slot.rules.needs-name | `data-slot=""` is a hard error `layout: <tag> line N: data-slot needs a name` | packages/layout/src/box.js:207-210 | parent `html.slot.needs-name` | verified |
| slot.rules.one-text-node | A `data-slot` element with an element child or with no child is a hard error `layout: <tag> line N: a data-slot element must contain exactly one text node (the placeholder), no child elements` | packages/layout/src/box.js:211-217 | compiled `<scratch>/err-children.html` (`6 <b>titles</b>`): `error: layout: <span> line 1: a data-slot element must contain exactly one text node (the placeholder), no child elements`, exit 1 | verified |
| slot.rules.single-line | A placeholder that wraps is a hard error `layout: data-slot "<name>" placeholder wraps to N lines — slots are single-line; add white-space: nowrap or widen the box` | packages/layout/src/paint.js:195-202 | parent `ir.schema.slot.single-line` was code-only; executed here: `<scratch>/err-wrap.html` against a 120px panel printed `error: layout: data-slot "count" placeholder wraps to 5 lines — slots are single-line; add white-space: nowrap or widen the box`, exit 1 | verified |
| slot.rules.unique-in-document | Two `data-slot` elements sharing a name in one HTML file are a compile error `layout: duplicate data-slot name "<n>"` | packages/layout/src/paint.js:329-335 | parent `ir.schema.slot.unique` | verified |
| slot.rules.unique-in-blob | The baker repeats the uniqueness check across every screen in the bake and refuses a collision with `slot name '<n>' is on screen '<a>' and screen '<b>'; slot names resolve over the whole file, so only the first would ever be reachable from the app`, exit 1 | packages/baker/ps2ui_bake/quads.py:644-664 | baked `<scratch>/library.json <scratch>/saves.json`, both carrying `data-slot="count"`: `ps2ui-bake: slot name 'count' is on screen 'library' and screen 'saves'; ...`, exit 1 | verified |
| slot.lookup.global | `ps2ui_slot_set` and `ps2ui_slot_get` resolve a name by walking slots 0 to `hdr->n_slot`, the whole blob, and take the first match. Drawing is per screen: `render_slots` walks only the current screen's slot range | runtime/ps2ui.c:1437-1448 (`slot_index_by_name`), runtime/ps2ui.c:1346-1350 (`render_slots`); runtime/sample/main.c:1756-1766 | parent `api.scope.rules.slot`; ok 110 sets `save-0`, a saves-screen slot, while `library` is current; the sample prefixes each screen's readout with the screen name for this reason | verified |
| slot.runtime.semantics | `ps2ui_slot_set(ctx, name, text)` copies `text` into the slot's own buffer, truncates at capacity bytes, then drops a trailing partial UTF-8 sequence. `NULL` reverts to the baked placeholder. `""` blanks the slot. It returns 1, or 0 when no slot has that name | runtime/ps2ui.c:1476-1497, runtime/ps2ui.c:1452-1474 (`utf8_trim_partial`), runtime/ps2ui.c:1337-1344 (`slot_current_text`); runtime/ps2ui.h:667-675 | parent `api.functions.slot_set`; ok 103, 107, 109-114, 123-125 in the `dynamic text (F2)` section of runtime/tests/test_runtime.c | verified |
| slot.runtime.get | `ps2ui_slot_get(ctx, name)` returns the runtime string when the slot has been set, else the baked placeholder, and NULL for an unknown name | runtime/ps2ui.c:1499-1505, runtime/ps2ui.c:1337-1344 | parent `api.functions.slot_get`; ok 102, 104 | verified |
| slot.baked | Geometry (`x`, `textY`, `w`), font index, size, weight, letter-spacing, alignment, ellipsis policy, base colour, focus colour and both theme vectors are compiled into the slot record. Only the string arrives at runtime | packages/layout/src/paint.js:208-238; packages/baker/ps2ui_bake/quads.py:714-741 | parent `ir.schema.slot`; `test_baker.TestDynamicText.test_slot_and_font_round_trip` asserts name, placeholder, capacity, ellipsis and the modulate-domain colours survive a write and read of the blob | verified |
| slot.pen | The runtime lays the run out with the baker's pen: letter-spacing plus the kern pair before each glyph, place at the pen, advance. No wrapping, no allocation. The previewer mirrors `render_slots` line for line | runtime/ps2ui.c:1395-1434; packages/baker/ps2ui_bake/preview.py:244-346 | ok 118-122 (an independent linear scan of the same kern and glyph tables predicts every glyph x; a kerned run is narrower than the sum of its advances); `test_preview_renders_placeholder_and_override` passes | verified |
| slot.font.charset | A slot's font entry carries every codepoint the metrics know plus U+2026, not just the glyphs static text used, because the string is unknown at bake time | packages/baker/ps2ui_bake/quads.py:693-700 | `test_baker.TestDynamicText.test_glyph_table_is_full_charset_and_sorted` asserts `A`, `z` and 0x2026 are present | verified |
| slot.overflow | Text wider than the slot box is ellipsized when the box has `text-overflow: ellipsis`, cutting at the last glyph that leaves room for U+2026 and its kern. Without it the whole run is drawn and the enclosing scissor clips the excess | runtime/ps2ui.c:1288-1334 (`slot_measure`) | code-only for the no-ellipsis branch: no runtime check asserts the clipped case; the ellipsis branch is exercised by the memcard `save-*` slots, which bake with `ellipsis` true (read from examples/memcard/build/ui.uib) | code-only |
| slot.align | `align` is 0 left, 1 center, 2 right, and centring or right-aligning only shifts the pen when the measured run is narrower than the slot box | runtime/ps2ui.c:1373-1378; packages/baker/ps2ui_bake/quads.py:720 | code-only: no runtime check asserts a centred slot's pen; read in both the runtime and the previewer mirror (preview.py:316-320), which agree | code-only |
| slot.hidden | A slot whose focus node is hidden is skipped and counted in `stats.slots_hidden`; slots sit outside the command list, so the command loop's visibility test does not reach them | runtime/ps2ui.c:1355-1362 | code-only here: the counter is asserted by the visibility tests, not by the dynamic-text section; the branch is read at ps2ui.c:1319-1321 | code-only |
| slot.spacing.i16 | Slot letter-spacing is an i16 in the blob. A value outside -32768 to 32767 is refused by name with `slot "<n>": letter-spacing <v>px does not fit the format's i16 field (-32768..32767px). ...` | packages/baker/ps2ui_bake/quads.py:754-767 | `test_baker.TestSlotSpacing` five tests pass, including `test_out_of_range_spacing_is_refused_by_name` and `test_negative_spacing_survives` | verified |
| slot.preview.no-truncate | `ps2ui_bake.preview.render(uib, slot_text=...)` draws the string it is given without applying the slot's capacity, so a programmatic preview can show text the console would truncate | packages/baker/ps2ui_bake/preview.py:251-252 | baked `<scratch>/trunc.uib` (capacity 8, 608px box) and rendered `ABCDEFGHIJKLMNOP` and `ABCDEFGH`: the two images differ | verified |
| slot.preview.empty | `preview.render` treats `slot_text={"name": ""}` as no override and draws the placeholder, where `ps2ui_slot_set(ctx, name, "")` blanks the slot. `ps2ui serve` does the same: an emptied box pops the override | packages/baker/ps2ui_bake/preview.py:252 (`.get(name) or placeholder`); packages/baker/ps2ui_bake/serve.py:210-217 | rendered `<scratch>/trunc.uib` with `slot_text={"count": ""}` and with no override: the two images are identical | verified |
| slot.preview.maxlength | The `ps2ui serve` inspector caps each slot box with `maxLength = capacity`, which counts UTF-16 code units, while the runtime truncates at capacity bytes. A two-byte character costs one unit in the box and two bytes on the console | packages/baker/ps2ui_bake/serve_page.html:610; packages/baker/ps2ui_bake/serve.py:600-604; runtime/ps2ui.c:1490-1494 | code-only: the browser side is not exercised by any test in the tree; README.md:607 says the previewer's slot box includes capacity truncation | contradicts-readme |
| slot.memcard | The memcard blob carries six slots over two screens: `count` (capacity 15) on `library`, and `save-count` (15) plus `save-0` to `save-3` (31, ellipsis on) on `saves` | examples/memcard/ui/library.html:25; examples/memcard/ui/saves.html:25-45 | read `examples/memcard/build/ui.uib` with `ps2ui_bake.uib.read_uib`: names, capacities and ellipsis flags as stated; screens `[('library', 0, 1), ('saves', 1, 5)]`; ok 100, 101 | verified |

## follow-up

Three divergences between the host previewer and `ps2ui_slot_set`, all in
the same direction: the previewer is more permissive than the console.

1. `packages/baker/ps2ui_bake/preview.py:251-252` never applies
   `slot["capacity"]`. `render_slots` in `runtime/ps2ui.c:1450-1454` does.
   A montage or a `--preview` render can therefore show a string the
   console would cut.
2. The same line reads `(slot_text or {}).get(name) or placeholder`, so an
   empty override falls back to the placeholder. `ps2ui_slot_set(ctx, name,
   "")` blanks the slot instead (backlog B12, runtime/ps2ui.c:1297-1300).
   `ps2ui serve` inherits this through `set_slots`
   (`packages/baker/ps2ui_bake/serve.py:209-216`), which pops an emptied box.
3. `packages/baker/ps2ui_bake/serve_page.html:610` sets the HTML
   `maxLength` from the capacity. `maxLength` counts UTF-16 code units;
   the capacity bounds bytes. A capacity-15 box accepts fifteen accented
   characters, thirty bytes, where the console keeps fourteen.

Fixing 1 and 2 is one change in `preview.render`: truncate `slot_text`
values at the slot capacity with the same UTF-8 trim
`runtime/ps2ui.c:1412` performs, and distinguish a missing key from an
empty value. README.md:607 claims the previewer's slot box already
includes capacity truncation, which is true only for ASCII and only in
the browser box, not for `preview.render` callers.
