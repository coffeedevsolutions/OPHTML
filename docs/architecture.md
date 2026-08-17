# ps2ui — architecture and decisions

Scaffolded 2026-08-17. An open-source toolchain that compiles HTML + CSS into PlayStation 2 Graphics Synthesizer draw commands at build time, for delivery on an SD2PSX / PSxMemCard GEN2 virtual memory card.

## Shape

Three stages joined by two documented formats. Any stage can be replaced by someone who reads the format specs.

```
ui/*.html,css ──▶ @ps2ui/layout ──▶ ui.json (IR) ──▶ ps2ui-bake ──▶ ui.uib ──▶ runtime (C99 + gsKit)
                  Node, zero deps                    Python, Pillow only
```

* `packages/layout` (~3,000 lines) — HTML parser, CSS parser + cascade, flexbox solver, greedy text wrapping, spatial focus-graph solver, CRT linter.
* `packages/baker` (~2,100 lines) — font metrics + glyph atlases, GS texture formats, nine-patch generation, quad flattening, `.uib` writer/reader, PNG previewer.
* `runtime` (~1,100 lines incl. tests) — `.uib` loader, CLUT permutation, gsKit command replay, D-pad navigation.

## Decisions worth remembering

**Everything moves to build time.** The console does not parse, lay out, rasterize or allocate. This is the single rule that settles most design questions.

**Zero dependencies in the layout package.** Originally planned around Yoga (flexbox) and satori; npm was unreachable in the build sandbox, so the flexbox solver was hand-written. This turned out better for an OSS build tool aimed at a 25-year-old console — it will still install in a decade.

**Font metrics are the seam between the two host stages.** Layout needs glyph advances; rasterization lives in Python. They share a metrics JSON and the identical rounding rule `round(units * size / 1000)`, because the GS has no subpixel glyph positioning. If the two sides disagreed by half a pixel, text would drift out of its measured box.

**`:focus` is a paint-only delta.** Both states live in one command list; each command carries a `state` field (always / unfocused / focused) and a `focus_id`, and the runtime filters. No relayout, no second blob, identical draw-call cost per state. A `:focus` rule that changes geometry is a compile error, not a silent no-op.

**Alpha is converted to the GS 0–128 domain exactly once, at bake time.** The classic PS2 bug is treating 0xFF as opaque when the blend unit reads 0x80 as 1.0.

**CLUTs are stored linearly; the runtime applies the CSM1 bit-3/bit-4 swap on upload.** Keeps the file readable by tools that know nothing about the GS.

**The previewer replays the baked command list, not the HTML or the IR** — same quad order, scissor stack, CLUT lookups and alpha domain as the console. It is the verification story in the absence of hardware.

## Bugs found while building (all now regression-tested)

1. `INITIAL_STYLE.padding` was shared by reference, so one `padding-top` declaration leaked into every element compiled afterwards. Arrays are now cloned and the initial style is frozen.
2. Unitless `line-height: 1.3` parsed as `1.3px`, collapsing every line box.
3. Auto-sized flex items measured as stretched rather than content-sized, so siblings shrank to nonsense. Measurement and placement are now separate passes (`place` flag through `computeFlexLines`).
4. Anonymous text boxes inherited their parent's decoration and repainted its background and border on top of itself.
5. A single-line flex container with a definite cross size did not give its line the container's cross size, so `align-items: center` silently behaved like `flex-start`.

## Status

Host toolchain verified end to end: layout tests, baker tests, and host runtime checks (the real `ps2ui.c` compiled `-Werror` against a stub gsKit and run over a real baked blob).

The gsKit rendering path is **not hardware-verified**. The loader, focus graph, format handling and command walk are covered; the gsKit calls themselves are written against the documented API. `GSTEXTURE::Function` requires a recent gsKit — there is a `PS2UI_GSKIT_HAS_FUNCTION=0` fallback that loses text tinting. That is the first thing to check on real hardware.

## Next steps

* Run it on hardware or PCSX2; adjust the gsKit path.
* Multi-screen documents and transitions between them.
* Precompiled GIF/DMA chains instead of per-quad gsKit calls (the big performance win — near-zero CPU per frame).
* Localization: layout is frozen per build, so each locale needs its own pass.
