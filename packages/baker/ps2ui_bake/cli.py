"""ps2ui-bake CLI.

    python -m ps2ui_bake ui.json -o ui.uib [--fonts fonts/fonts.json]
                                 [--preview out.png] [--montage sheet.png]
"""

import argparse
import json
import os
import sys

from .quads import Flattener
from .uib import write_uib, read_uib
from . import preview as preview_mod
from . import arena
from . import vram
from . import caps as caps_mod


def load_font_manifest(path: str) -> dict:
    """fonts.json maps face -> {ttf: [candidate paths...], metrics: path}.
    Candidates let one manifest serve machines with fonts in different
    places; the first existing path wins. Paths resolve relative to the
    manifest."""
    base = os.path.dirname(os.path.abspath(path))
    with open(path, encoding="utf-8") as fh:
        manifest = json.load(fh)
    out = {}
    for face, spec in manifest.items():
        candidates = spec["ttf"] if isinstance(spec["ttf"], list) else [spec["ttf"]]
        ttf = None
        for cand in candidates:
            resolved = cand if os.path.isabs(cand) else os.path.join(base, cand)
            if os.path.exists(resolved):
                ttf = resolved
                break
        if ttf is None:
            raise FileNotFoundError(
                f"fonts.json: no candidate TTF for '{face}' exists: {candidates}"
            )
        metrics = spec["metrics"]
        out[face] = {
            "ttf": ttf,
            "metrics": metrics if os.path.isabs(metrics) else os.path.join(base, metrics),
        }
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="ps2ui-bake")
    ap.add_argument("ir", nargs="+",
                    help="ui.json file(s) from ps2ui-layout; several files "
                         "become named screens in one blob (screen name = "
                         "file stem), sharing textures and atlases")
    ap.add_argument("-o", "--out", required=True, help="output .uib path")
    ap.add_argument("--fonts", default=None, help="fonts.json manifest (default: repo fonts/)")
    ap.add_argument("--preview", default=None, help="write a PNG replay of the initial state")
    ap.add_argument("--montage", default=None, help="write a PNG sheet of every focus state")
    ap.add_argument("--preview-display", default=None, metavar="PNG",
                    help="write the preview resampled to the panel's aspect. "
                         "The 1:1 preview matches a framebuffer capture; this "
                         "one matches a photograph of the television.")
    ap.add_argument("--palettize-images", action="store_true",
                    help="quantize every image to 8-bit indexed PSMT8+CLUT "
                         "(4x less VRAM per texel; <=256 colors per image). "
                         "Per-image opt-in: the `palettize` attribute on <img>.")
    ap.add_argument("--vram-budget", type=int, default=None, metavar="BYTES",
                    help="texture VRAM budget (default: 4 MiB minus a "
                         "double-buffered framebuffer pair + Z at canvas size)")
    args = ap.parse_args(argv)

    named_irs = []
    for path in args.ir:
        with open(path, encoding="utf-8") as fh:
            ir = json.load(fh)
        if ir.get("version") != 1:
            print(f"error: {path}: IR version {ir.get('version')}, expected 1",
                  file=sys.stderr)
            return 1
        name = os.path.splitext(os.path.basename(path))[0]
        if any(n == name for n, _ in named_irs):
            print(f"error: duplicate screen name {name!r} (file stems must be "
                  "unique)", file=sys.stderr)
            return 1
        for w in ir.get("warnings", []):
            print(f"warning (layout {name}): {w}", file=sys.stderr)
        named_irs.append((name, ir))
    ir = named_irs[0][1]  # canvas / VRAM reference

    fonts_path = args.fonts
    if fonts_path is None:
        here = os.path.dirname(os.path.abspath(__file__))
        fonts_path = os.path.join(here, "..", "..", "..", "fonts", "fonts.json")
    font_paths = load_font_manifest(fonts_path)

    flat = Flattener(ir, font_paths, palettize_all=args.palettize_images)
    try:
        flat.run_screens(named_irs)
    except ValueError as exc:
        # The bake's own diagnostics are written to be read; a traceback
        # buries them under a stack the author cannot act on. Matches
        # what ps2ui-check already does. "This indexed PNG isn't at its
        # natural size" is a routine authoring mistake, not a crash.
        print(f"ps2ui-bake: {exc}", file=sys.stderr)
        return 1

    # Runtime table caps before anything else: a blob past them loads
    # nowhere, and every host stage downstream would happily accept it
    # (backlog B10).
    cap_errors, caps = caps_mod.check(
        flat.textures, flat.cluts, flat.slots, flat.screens,
        records=flat.records)
    print(caps_mod.summary(flat.textures, flat.cluts, flat.slots,
                           flat.screens, caps), file=sys.stderr)
    if flat.dropped:
        # Silent truncation reads as "covered everything"; say what went.
        print(f"  trimmed {flat.dropped} draw command(s) that fall outside "
              f"their clip and could never draw", file=sys.stderr)
    if cap_errors:
        for e in cap_errors:
            print(f"error: {e}", file=sys.stderr)
        return 1

    # VRAM accounting before writing anything: an over-budget UI should
    # die here with a breakdown, not on the console with an alloc error.
    vlines, _vtotal, _vbudget, vok = vram.report(
        flat.textures, flat.cluts, ir["canvas"]["w"], ir["canvas"]["h"],
        args.vram_budget,
    )
    for line in vlines:
        print(line, file=sys.stderr)
    if not vok:
        print("error: texture VRAM footprint exceeds budget "
              "(see breakdown above; override with --vram-budget)", file=sys.stderr)
        return 1

    initial = flat.screens[0]["initial"]
    write_uib(
        args.out, ir["canvas"], flat.records, flat.textures, flat.cluts,
        flat.focus_nodes, initial, flat.fonts, flat.slots, flat.screens,
        tuple(ir["canvas"].get("displayAspect", (4, 3))),
    )

    n_tex_bytes = sum(len(t.data) for t in flat.textures)
    print(
        f"ps2ui-bake: {len(flat.screens)} screen(s), {len(flat.records)} records, "
        f"{len(flat.textures)} textures ({n_tex_bytes // 1024} KiB), "
        f"{len(flat.cluts)} CLUTs -> {args.out}",
        file=sys.stderr,
    )

    # The arena an integrator has to declare. Printed unconditionally
    # because ps2ui_load now takes it as an argument: without this
    # number the next step after a successful bake is a guess, and the
    # failure mode of guessing low is PS2UI_ERR_ARENA at boot.
    if True:
        uib_for_arena = read_uib(args.out)
        ee = arena.arena_size(uib_for_arena, arena.EE_PTR)
        print(
            f"ps2ui-bake: arena {ee} bytes "
            f"(static uint8_t arena[{ee}] __attribute__((aligned(16))))",
            file=sys.stderr,
        )

    if args.preview or args.montage or args.preview_display:
        uib = read_uib(args.out)  # replay what we wrote, not what we meant
        if args.preview:
            preview_mod.render(uib).save(args.preview)
            print(f"ps2ui-bake: preview -> {args.preview}", file=sys.stderr)
        if args.preview_display:
            preview_mod.to_display_space(
                preview_mod.render(uib), uib).save(args.preview_display)
            dw, dh = preview_mod.display_size(uib)
            num, den = uib.display_aspect
            print(f"ps2ui-bake: display preview {dw}x{dh} at {num}:{den} "
                  f"-> {args.preview_display}", file=sys.stderr)
        if args.montage:
            preview_mod.montage(uib).save(args.montage)
            print(f"ps2ui-bake: montage -> {args.montage}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
