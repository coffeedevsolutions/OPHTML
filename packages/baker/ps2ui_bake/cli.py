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
    ap.add_argument("ir", help="ui.json from ps2ui-layout")
    ap.add_argument("-o", "--out", required=True, help="output .uib path")
    ap.add_argument("--fonts", default=None, help="fonts.json manifest (default: repo fonts/)")
    ap.add_argument("--preview", default=None, help="write a PNG replay of the initial state")
    ap.add_argument("--montage", default=None, help="write a PNG sheet of every focus state")
    args = ap.parse_args(argv)

    with open(args.ir, encoding="utf-8") as fh:
        ir = json.load(fh)
    if ir.get("version") != 1:
        print(f"error: IR version {ir.get('version')}, expected 1", file=sys.stderr)
        return 1
    for w in ir.get("warnings", []):
        print(f"warning (layout): {w}", file=sys.stderr)

    fonts_path = args.fonts
    if fonts_path is None:
        here = os.path.dirname(os.path.abspath(__file__))
        fonts_path = os.path.join(here, "..", "..", "..", "fonts", "fonts.json")
    font_paths = load_font_manifest(fonts_path)

    flat = Flattener(ir, font_paths)
    flat.run()

    initial = None
    if ir["focus"]["initial"] is not None:
        initial = flat.focus_index.get(ir["focus"]["initial"])
    write_uib(
        args.out, ir["canvas"], flat.records, flat.textures, flat.cluts,
        ir["focus"]["nodes"], initial,
    )

    n_tex_bytes = sum(len(t.data) for t in flat.textures)
    print(
        f"ps2ui-bake: {len(flat.records)} records, {len(flat.textures)} textures "
        f"({n_tex_bytes // 1024} KiB), {len(flat.cluts)} CLUTs -> {args.out}",
        file=sys.stderr,
    )

    if args.preview or args.montage:
        uib = read_uib(args.out)  # replay what we wrote, not what we meant
        if args.preview:
            preview_mod.render(uib).save(args.preview)
            print(f"ps2ui-bake: preview -> {args.preview}", file=sys.stderr)
        if args.montage:
            preview_mod.montage(uib).save(args.montage)
            print(f"ps2ui-bake: montage -> {args.montage}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
