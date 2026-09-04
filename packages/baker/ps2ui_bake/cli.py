"""ps2ui-bake CLI.

    python -m ps2ui_bake ui.json -o ui.uib [--fonts fonts/fonts.json]
                                 [--preview out.png] [--montage sheet.png]
"""

import argparse
import json
import os
import sys

from . import __version__
from .quads import Flattener
from .uib import write_uib, read_uib
from . import preview as preview_mod
from . import arena
from . import vram
from . import caps as caps_mod


def check_font_agreement(ir, font_paths):
    """The IR names the faces it was MEASURED against. Compare them.

    ps2ui-layout and ps2ui-bake take font configuration separately --
    a directory of metrics for the compiler, a manifest for the baker --
    and until this ran, nothing checked they described the same fonts.
    Compile against one face and bake with another and every glyph is
    drawn at the first font's position with the second font's shape:
    subtly wrong text on every screen, no error anywhere, and only a
    console to see it on.

    The IR has carried `fonts: {face: {family, weight}}` since v1 and
    the baker had never read it, so the information needed to catch
    this was already in the file and ignored.

    WHAT THIS DOES NOT CATCH. Two builds of the same family whose
    metrics differ -- a re-run of ps2ui-fontgen over a newer TTF, or a
    different charset -- agree on family and weight and diverge in the
    advances. Catching that wants a digest of the tables in the IR,
    which is a format-visible change and is not this. So: the loud
    case is prevented, the quiet one is still only avoidable, and
    saying which is which is the point.
    """
    declared = ir.get("fonts") or {}
    out = []
    for face, spec in sorted(declared.items()):
        paths = font_paths.get(face)
        if paths is None:
            out.append(f"the IR was compiled against a '{face}' face and "
                       f"the font manifest has none")
            continue
        with open(paths["metrics"], encoding="utf-8") as fh:
            metrics = json.load(fh)
        for key in ("family", "weight"):
            want, got = spec.get(key), metrics.get(key)
            if want is not None and got is not None and want != got:
                out.append(
                    f"{face}: the IR was compiled against {key} "
                    f"{want!r} and the manifest's metrics say {got!r} "
                    f"({paths['metrics']})")
    return out


def default_fonts_path() -> str:
    """The repository's fonts/fonts.json -- a CANDIDATE, not a promise.

    Three levels up from this file is the repository root in a
    checkout and nothing at all in an installed package: pip puts
    ps2ui_bake in site-packages, and `../../../fonts` from there is
    somewhere no font has ever been. Phase 4's exit gate reads "a
    stranger with npm, pip and a TTF"; that stranger got FileNotFound
    on a path they never chose and could not have created.

    Kept, because every example and build.sh in the repository relies
    on it. Checked before use, because outside the repository it is
    wrong, and the caller says what to do instead.
    """
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(here, "..", "..", "..", "fonts", "fonts.json")


def load_font_manifest(path: str) -> dict:
    """fonts.json maps face -> {ttf: [candidate paths...], metrics: path}.
    Candidates let one manifest serve machines with fonts in different
    places; the first existing path wins. Paths resolve relative to the
    manifest.

    `~` EXPANDS FIRST, AND IT HAS TO. os.path.isabs("~/Library/Fonts/
    DejaVuSans.ttf") is False, so before this a home-relative candidate
    was joined to the manifest's own directory and could never match --
    silently, because a candidate that does not exist is simply the
    next one tried. `~/Library/Fonts` is where macOS puts a font a
    person installs for themselves, which is where most people's fonts
    actually are, so the one spelling a Mac reader would reach for was
    the one spelling that could not work."""
    base = os.path.dirname(os.path.abspath(path))
    if not os.path.exists(path):
        # Named by the caller and not there: a traceback here buries
        # the one fact they can act on under a stack they cannot.
        raise FileNotFoundError(
            f"{path}: no such fonts.json. It maps \"regular\" and \"bold\" "
            f"to {{ttf: [...], metrics: \"...\"}}; generate the metrics "
            f"with ps2ui-fontgen, and ps2ui-layout reads the same file "
            f"via --fonts."
        )
    with open(path, encoding="utf-8") as fh:
        manifest = json.load(fh)
    out = {}
    for face, spec in manifest.items():
        candidates = spec["ttf"] if isinstance(spec["ttf"], list) else [spec["ttf"]]
        ttf = None
        for cand in candidates:
            cand = os.path.expanduser(cand)
            resolved = cand if os.path.isabs(cand) else os.path.join(base, cand)
            if os.path.exists(resolved):
                ttf = resolved
                break
        if ttf is None:
            raise FileNotFoundError(
                f"fonts.json: no candidate TTF for '{face}' exists: {candidates}"
            )
        metrics = os.path.expanduser(spec["metrics"])
        out[face] = {
            "ttf": ttf,
            "metrics": metrics if os.path.isabs(metrics) else os.path.join(base, metrics),
        }
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="ps2ui-bake")
    # THE VERSION HAS TO REACH A PERSON. Every claim in the repository
    # now agrees with every other one (tools/check-versions.py), and
    # until this flag existed none of them was reachable from the
    # command someone actually runs -- the one place a stranger with a
    # bug report would look. Sourced from __init__.py like everything
    # else, so it cannot become the next number that disagrees.
    ap.add_argument("--version", action="version",
                    version="ps2ui-bake %s" % __version__)
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
    ap.add_argument("--tints", action="store_true",
                    help="print the tint table with the var() name behind "
                         "each entry -- the half of it only the baker knows")
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

    # THREE LEVELS UP IS THE REPOSITORY ROOT, AND ONLY IN A CHECKOUT.
    # Installed from PyPI this resolves somewhere above site-packages,
    # which does not exist -- so the default font path was reachable
    # only by people who already had the repo, against an exit gate
    # that reads "a stranger with npm, pip and a TTF". Kept as the
    # default because the examples depend on it, but it is a candidate
    # now, and its absence says what to do instead of raising ENOENT on
    # a path the caller never chose.
    fonts_path = args.fonts
    if fonts_path is None:
        fonts_path = default_fonts_path()
        if not os.path.exists(fonts_path):
            print("ps2ui-bake: no font manifest. The built-in default is "
                  "the repository's fonts/fonts.json, which only exists "
                  "in a checkout.\n"
                  "  Write one naming your own TTF and its metrics:\n"
                  '    { "regular": { "ttf": ["/path/DejaVuSans.ttf"], '
                  '"metrics": "default.metrics.json" },\n'
                  '      "bold":    { "ttf": ["/path/DejaVuSans-Bold.ttf"], '
                  '"metrics": "default-bold.metrics.json" } }\n'
                  "  Generate the metrics with ps2ui-fontgen, then pass "
                  "--fonts <fonts.json>.\n"
                  "  ps2ui-layout reads the same file: --fonts <fonts.json>.",
                  file=sys.stderr)
            return 1
    try:
        font_paths = load_font_manifest(fonts_path)
    except (FileNotFoundError, KeyError, ValueError) as exc:
        # Same rule as the bake diagnostics below: a font manifest the
        # caller can fix is not a crash, and a traceback buries the one
        # line they can act on.
        print(f"ps2ui-bake: {exc}", file=sys.stderr)
        return 1

    # THE COMPILER AND THE BAKER MUST HAVE MEANT THE SAME FONTS.
    disagree = check_font_agreement(ir, font_paths)
    if disagree:
        print("ps2ui-bake: the IR and the font manifest describe "
              "different fonts:", file=sys.stderr)
        for line in disagree:
            print("  " + line, file=sys.stderr)
        print("  Text would be positioned by one font and drawn with "
              "another. Pass the same --fonts manifest to ps2ui-layout "
              "and ps2ui-bake.", file=sys.stderr)
        return 1

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
    tint_report = []
    # MAKE THE OUTPUT DIRECTORIES. `-o build/ui.uib` into a tree with
    # no build/ raised a bare FileNotFoundError traceback -- the same
    # first-command failure ps2ui-layout had, and the same reason
    # nobody here saw it: every build.sh mkdir -p's first.
    for path in (args.out, args.preview, args.montage,
                 args.preview_display):
        if path:
            parent = os.path.dirname(os.path.abspath(path))
            os.makedirs(parent, exist_ok=True)

    write_uib(
        args.out, ir["canvas"], flat.records, flat.textures, flat.cluts,
        flat.focus_nodes, initial, flat.fonts, flat.slots, flat.screens,
        tuple(ir["canvas"].get("displayAspect", (4, 3))),
        len(ir.get("themes") or ["root"]),
        tint_report=tint_report,
    )

    if args.tints:
        names = ir.get("themes") or ["root"]
        print(f"# {len(tint_report)} tint entries over {len(names)} theme(s): "
              f"{', '.join(names)}", file=sys.stderr)
        for i, var, vec in tint_report:
            cols = "  ".join("(%3d,%3d,%3d,%3d)" % tuple(c) for c in vec)
            # A LITERAL IS NOT A GAP. An entry with no name is a colour
            # the author declined to offer to a theme, which is a
            # legitimate choice -- design-p3b-theming.md 9.2 -- so it
            # is labelled rather than left blank next to the named ones.
            label = var if var else "(literal, unthemed)"
            fixed = all(c == vec[0] for c in vec)
            note = "   FIXED in every theme" if fixed and len(vec) > 1 else ""
            print(f"  {i:3d}  {cols}  {label}{note}", file=sys.stderr)

    n_tex_bytes = sum(len(t.data) for t in flat.textures)
    # Streamed slots contribute no bytes to the file, so this total is
    # honest about the blob and silent about the reservations -- which
    # read as "1 textures (0 KiB)" for a UI holding a 27 KiB slot. Name
    # them separately rather than folding them in: adding them would
    # misreport the size of the file this line is announcing, and
    # omitting them was the "reads as free" problem one line up.
    n_reserved = sum(t.reservation for t in flat.textures
                     if getattr(t, "kind", 0))
    tex_note = f"{n_tex_bytes // 1024} KiB baked"
    if n_reserved:
        tex_note += f" + {n_reserved // 1024} KiB reserved by slots"
    print(
        f"ps2ui-bake: {len(flat.screens)} screen(s), {len(flat.records)} records, "
        f"{len(flat.textures)} textures ({tex_note}), "
        f"{len(flat.cluts)} CLUTs -> {args.out}",
        file=sys.stderr,
    )

    # The arena an integrator has to declare. Printed unconditionally
    # because ps2ui_load now takes it as an argument: without this
    # number the next step after a successful bake is a guess, and the
    # failure mode of guessing low is PS2UI_ERR_ARENA at boot.
    ee = arena.arena_size(read_uib(args.out), arena.EE_PTR)
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
