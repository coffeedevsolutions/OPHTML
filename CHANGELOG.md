# Changelog

## Unreleased — 0.3.0.dev0

`.uib` format **version 7**. v3 through v6 files are rejected; re-bake.
Four format moves have landed since 0.2.0 — v4 display aspect, v5
kerning, v6 texture kinds, v7 the tint table — so a blob baked against
that release will not load.

There is no 0.2.0 tag and there never was one, and there is no 0.3.0
yet. Both packages therefore carry a prerelease: `0.3.0.dev0` for
`ps2ui-bake`, `0.3.0-dev.0` for `@ps2ui/layout`. That is the true
statement — past 0.2.0, not yet the next release — and it is the one
pip and npm act on, since neither installs a prerelease unless asked
for it by name. Until Phase 4 publishes, building on this tree means
building on an unverified renderer, and the version says so.

These numbers used to drift because nothing read them: the baker
shipped `__version__ = "0.1.0"` beside `version = "0.2.0"` in its own
`pyproject.toml`, and this section said "format version 5" through two
further format breaks. `pyproject.toml` now derives its version from
`__init__.py` instead of restating it, and `tools/check-versions.py`
reads the package versions, `PS2UI_VERSION`, `uib.VERSION`, the
paragraph above, `docs/format-uib.md`, `docs/PLAN.md`'s format history
and the README's Quick start note against each other on every push.

### Breaking — authoring

- **`flex-direction` is now required on any container laying out two or
  more children.** Omitting it is a compile error listing every
  offending container with its line. Containers with one child or none
  are unaffected.

  **Migrating:** compile once and add `flex-direction: row` or
  `column` to each container the error names. If your document was
  written against a ps2ui release, it relied on the old implicit
  `column`, so `column` restores exactly what you had — adding it to
  both shipped examples left their previews *and* their `.uib` files
  byte-identical.

  Why: the implicit default was `column`, undocumented, where CSS's
  initial value is `row`. Switching to `row` would have silently
  relaid out every existing document; keeping `column` would teach a
  permanent exception to CSS. Requiring the answer is the only version
  with no silent victims.

  No format change. Existing `.uib` blobs are unaffected; only source
  documents need edits.

### Breaking — runtime

- **`ps2ui_load` takes an arena.** The context no longer carries
  fixed-size tables; it points into caller memory sized from the blob
  by `ps2ui_arena_size(data, size)`, which reads the header only and
  returns 0 when the blob is not worth loading at all. The arena must
  be `PS2UI_ARENA_ALIGN`-aligned and must outlive every render, not
  just the load, because nothing is copied — a blob that fails
  validation never touches it.

  **Migrating:** call `ps2ui_arena_size` first and hand `ps2ui_load`
  the buffer. `PS2UI_ERR_ARENA` is the new failure for one that is too
  small.

  Why it matters: the fixed tables charged roughly 36 KiB to every
  blob, a two-slot overlay included. The six-screen UC-3 environment
  asks for 7,319 bytes.

- **Texture entries grew 16 → 20 bytes (`.uib` v6).** The `pad` byte at
  offset 1 became `kind` and a `name_off` was added, which is what
  makes **streamed textures** expressible: an entry carrying geometry
  and a VRAM reservation but no texel data, pointed at the app's own
  buffer on the console by `ps2ui_tex_set`. Cover art off a disc, an
  HDD or a network cannot be baked, because nothing at bake time knows
  what it is.

  A v5 reader would have walked the texture table at the wrong stride,
  so this is a version bump rather than a feature bit alone. Feature
  bit 3 additionally says the blob declares a streamed texture, so a
  reader that cannot fill one refuses the file instead of drawing an
  empty slot.

  **Migrating:** re-bake. Every writer before v6 wrote zero in the byte
  that became `kind`, which is `PS2UI_TEXKIND_BAKED` — the meaning the
  zeros already had.

- **Commands and slots hold tint indices, not colours (`.uib` v7).**
  Where they carried rgba bytes they carry a u16 index into a **tint
  table**: `n_theme × n_tint` entries, theme-major, so one theme's
  colours are contiguous and selecting a theme is a pointer add rather
  than a strided walk. `ps2ui_theme_set` moves which row is live, with
  no `GSGLOBAL` and no upload — it is the cheap half of theming, beside
  `ps2ui_clut_set` for the palettes.

  The command entry did not change size (four colour bytes became two
  indices; the two that freed went into `tint_focus`, inside padding
  that already existed). The slot entry shrank, 32 → 28. Neither the
  stride nor the meaning of a field survives a v6 reader, which is
  exactly the case a version bump exists for.

  **Migrating:** re-bake. A one-theme blob draws what v6 drew.
  `PS2UI_FEAT_ROLE_TINTS` gates more than one row: it says the indices
  are keyed on the authored *declaration* rather than the resolved
  colour, and `ps2ui_load` refuses `n_theme > 1` without it, because
  two declarations that happen to share a colour would otherwise
  collapse into one entry no theme could tell apart.

- **`PS2UI_MAX_TEXTURES`, `PS2UI_MAX_SLOTS` and `PS2UI_MAX_SCREENS` are
  deleted.** A UI is no longer limited to 32 textures, 16 slots or 8
  screens. The v6 arena already sizes the context from the blob, and
  once it did those constants bounded nothing the blob's own size did
  not already bound — every table is checked as
  `off + n * sizeof(entry) <= size` on the way in.

  **Migrating:** nothing to do unless you referenced the constants.
  Code that read them (to size a buffer, or to assert a count) will no
  longer compile, which is the intended outcome — the number it wanted
  is the arena figure `ps2ui-bake` and `ps2ui-check` print.
  `PS2UI_MAX_SCISSOR_DEPTH` stays; it is a real stack in
  `ps2ui_render`, not a validation limit.

  `PS2UI_ERR_TOO_MANY` keeps its number and changes meaning: it now
  says the arena this blob demands does not fit the target's address
  space, not that a count passed a threshold ps2ui.h picked. A blob
  with zero screens returns `PS2UI_ERR_BOUNDS` rather than
  `PS2UI_ERR_TOO_MANY`.

  Why it matters: the UC-3 scoping fixture — a five-screen OPL-class
  environment — measures 121 slots and could not be baked at all
  without hand-editing a vendored header. It now bakes on a stock
  checkout and asks for roughly 8 KiB of arena — the measured figure
  lives in `fixtures/opl-scope/README.md`, where `figures.py` now reads
  it back out of the blob — against roughly 36 KiB that the
  fixed-maxima context charged every blob including a two-slot
  overlay.

### Added
- **Compositing two screens in one frame is a contract**, not an
  accident. `ps2ui_render` never clears — stated as a guarantee on the
  function, in the README with a worked frame loop, and in
  `format-uib.md` — so `screen_set` + `render` twice in a frame draws
  the second over the first. That is the dialog and modal technique,
  with no format flag and no new API: an overlay screen is an ordinary
  screen with a translucent scrim.

  Input follows the **last** `screen_set`, so an overlay drawn last
  owns the D-pad and dismissing it is one call back, restoring the
  focus the user left on the base. Visibility resolves in the current
  screen, so an overlay cannot reach into the base by naming one of
  its nodes.

  Two traps, documented and fenced: `ctx->stats` describes one render
  and is reset at the top of every call, so a composited frame ends
  holding the overlay's counters; and `gsKit_TexManager_nextFrame`
  belongs once per frame after the flip, not between the two renders,
  or an open dialog re-uploads the base's atlases every frame. The
  host stub now counts frame clears and residency ageing ticks, so a
  render that takes over either fails by name rather than silently —
  the primitive count notices neither.

  There is deliberately no `ps2ui_overlay_push`. The one thing it
  would buy is a dialog drawn over a base that still receives input,
  and nothing has asked for that.
- **Kerning** — `ps2ui-fontgen` measures pairs out of the face (with
  ligature substitution disabled, so a ligature's width is never
  mistaken for a kern) and every pen applies them: layout's
  `Font.layout`, the baker's `_flatten_text`, and the runtime's
  `render_slots`. Pairs reach the console pre-resolved to pixels at
  each font's size, in a per-font table sorted for binary search, so a
  frame costs one lookup per glyph and no arithmetic. Feature bit 1;
  the font entry grew 16 → 24 bytes, which is what forces v5.
- **Widescreen** — anamorphic 16:9 authoring, `--mode ntsc16x9`, the
  display aspect recorded in the header, and `ps2ui_pixel_aspect_x1000`
  so a mismatch is detectable rather than merely ugly (`.uib` v4).
- **Lists** — `data-repeat` template expansion at build time plus a
  runtime window over more items than fit: `ps2ui_list_init`,
  `_move`, `_select`, `_set_count`, `_item_at`, `_selected_row`,
  `_apply_visibility`.
- **Runtime visibility** — `ps2ui_visible_set` / `_get` / `_reset`,
  so an app can hide a row it has no data for instead of blanking
  every slot in it and leaving the panel drawn.
- **`ps2ui-check`** — a standalone `.uib` validator (TAP output) that
  reads a blob the way the loader does and reports what would go
  wrong on console: table caps, VRAM budget, scissor balance and
  nesting depth, glyph and kern table sortedness, feature bits that
  do not match the tables they describe.
- `fonts/regen.sh` regenerates the committed metrics in one command.

### Changed
- `arena_compute` accumulates the carve in 64 bits and refuses it
  before narrowing. Counts and slot capacity are all `uint16`, so a
  well-formed header can legally demand 65535 x 65536 bytes of slot
  text; that total wraps a 32-bit `size_t`, which is what the EE has,
  and a wrapped total carves a small arena for a huge blob. The
  ceilings used to make this unreachable as a side effect.
  `make -C runtime test-narrow` compiles the runtime at a 32-bit
  address width and proves both halves: the oversized blob is refused,
  and an ordinary one still loads.
- The bake's table line prints counts instead of fractions
  (`15 slots`, not `15/16 slots`). A fraction of 65535 is a number
  with a decorative second half; the figure that constrains a UI is
  the arena, printed on its own line.
- The baker drops draw records that cannot produce a pixel (geometry
  fully outside its clip), shrinking the command list on exactly the
  data-heavy screens where it matters.
- The contrast lint composites the full containing chain including
  alpha; a translucent scrim no longer lints as an opaque fill.
- Example builds refresh the committed screenshots, so a preview
  cannot drift from the renderer that produced it.

### Fixed
- Slots dropped `letter-spacing`: layout measured and centered the box
  with it while the runtime and previewer drew without it — 44px of
  divergence over 12 glyphs at 4px spacing. The value now travels in
  the slot entry (feature bit 2, stride unchanged) and every pen
  applies it, kern included, ellipsis junction included.
- The scissor stack could desynchronise: a `SCISSOR_PUSH` refused for
  want of stack was still being popped, leaving every *later* clip in
  the frame wrong rather than only the too-deep subtree. The bake now
  refuses a blob that deep as well.
- `render_slots` ignored the visibility bit, so hiding a row removed
  its panel and left its glyphs floating.
- Focus and slot name lookups were blob-global, so hiding a row on one
  screen could blank an identically-named row on another.
- `ps2ui_list_set_count` did not move focus with a shrinking list.

## 0.2.0 — 2026-08-17

The "real apps" release: the toolchain now covers what an actual
SD2PSX memory-card browser needs, with the format hardened for third
parties. `.uib` format version 3 (v1/v2 files are rejected; re-bake).

### Added
- **Dynamic text** — `data-slot` elements whose strings the console
  sets at runtime (`ps2ui_slot_set`), composed per frame from baked,
  codepoint-sorted glyph tables. Same advances and baseline as static
  text; fixed per-slot buffers, zero allocation, UTF-8, ellipsis,
  alignment, focus-aware colors.
- **Multiple screens** — several IR files bake into one blob as named
  screens sharing textures/atlases/fonts; `ps2ui_screen_set` switches
  with per-screen focus memory. The example is now two screens.
- **Images** — `<img src="assets/...png">` baked to PSMCT32 textures,
  pre-scaled at build time; opt-in **palettization** to PSMT8+CLUT
  (`palettize` attribute or `--palettize-images`), 4× less VRAM/texel.
- **Format integrity** — CRC-32 over the whole file (validated by the
  C loader and the Python reader) and feature flags that reject
  unknown capabilities loudly.
- Focus API: `ps2ui_focus_set(name)`, build-time `--focus-wrap`.
- `--mode ntsc|pal` presets; CRT-linter safe areas derive from canvas.
- `ps2ui-dev` watch mode (~200 ms edit-to-preview).
- Bake-time VRAM budget with per-texture page-rounded breakdown.
- Hardware bring-up checklist (docs/bringup.md), CI-built PS2 ELF
  (ps2dev container), texel-alignment test card, frame-diff tool.
- CONTRIBUTING.md, SECURITY.md, issue templates, Dependabot, hardened
  workflows (read-only tokens, concurrency groups).

### Fixed
- **GS modulate color domain**: TEXQUAD tints now bake in the
  0x80-identity domain; previously every tinted glyph/nine-patch would
  render up to 2× overbright on hardware while the previewer hid it.
  The previewer now mirrors the hardware `>>7` multiply.
- **Baseline seam**: glyph ink hangs from the metrics ascent layout
  measured with, not Pillow's per-size ascent (was ±1 px drift).
- **Space width**: an invisible U+00A0 in the fontgen charset shadowed
  the real space, so every space measured at `?` width on both hosts.
  Metrics regenerated; text is now correctly (and visibly) tighter.
- `GSTEXTURE::Function` is autodetected; older gsKit (including the
  ps2dev container's) builds cleanly with untinted text.
- `<img>` elements error/warn instead of silently vanishing.

## 0.1.0 — 2026-08-17

Initial scaffold: layout (HTML/CSS → IR), baker (IR → .uib + PNG
previews), C99 runtime (loader, CSM1 CLUT permutation, focus-filtered
replay, D-pad navigation), memcard example, format documentation.
