# Changelog

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
