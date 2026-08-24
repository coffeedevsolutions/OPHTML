"""ps2ui-check — validate a baked .uib against what the runtime assumes.

    ps2ui-check ui.uib
    PYTHONPATH=packages/baker python3 -m ps2ui_bake.check ui.uib

`read_uib` already rejects a blob with bad magic, an unknown version, a
failed CRC or unknown feature bits, so anything reaching the checks
below is structurally a v4 file. What it does not tell you is whether
the *contents* satisfy the invariants `ps2ui.c` relies on but cannot
afford to verify: the runtime indexes tables directly, in a loop, with
no allocation and no bounds reporting, so a blob that violates one of
these does not error on console. It draws the wrong thing, or hangs on
a focus cycle, or returns PS2UI_ERR_TOO_MANY with no indication why.

This is the generalized form of `examples/channel6/check.py`, which did
the same job for one specific blob and had the example's own focus and
slot names baked into it. Everything here holds for any .uib, so a
project that never touches this repository's examples still gets the
checks (backlog F22).

Two severities:

* **error** — the console will misbehave. Non-zero exit.
* **warning** — legal, but a known way to look wrong on a CRT. Exit 0
  unless `--strict`.

Output is TAP, same as the example's checker, so it reads the same in a
build log and a CI annotation.
"""
from __future__ import annotations

import argparse
import sys

from . import arena
from . import caps as caps_mod
from . import clip as clip_mod
from . import gs, vram
from .quads import (
    FOCUS_NONE, OP_QUAD, OP_SCISSOR_POP, OP_SCISSOR_PUSH, OP_TEXQUAD,
    STATE_ALWAYS, STATE_FOCUSED, STATE_UNFOCUSED, TEX_NONE,
)
from .uib import FEAT_KERNING, FEAT_SLOT_SPACING, read_uib

ERROR = "error"
WARNING = "warning"


class Report:
    """Ordered TAP results. `add` returns the verdict so callers can
    skip dependent checks when a structural one has already failed."""

    def __init__(self):
        self.results = []  # (ok, severity, label)
        self.notes = []    # diagnostics: measured, never asserted

    def add(self, ok: bool, severity: str, label: str) -> bool:
        self.results.append((bool(ok), severity, label))
        return bool(ok)

    def error(self, ok: bool, label: str) -> bool:
        return self.add(ok, ERROR, label)

    def warn(self, ok: bool, label: str) -> bool:
        return self.add(ok, WARNING, label)

    def note(self, label: str) -> None:
        """A measured number with no threshold to fail against.

        Deliberately not `add(True, ...)`: a result that cannot fail is
        not a check, and padding the count with them makes a passing
        run look better tested than it is."""
        self.notes.append(label)

    @property
    def errors(self) -> int:
        return sum(1 for ok, sev, _ in self.results if not ok and sev == ERROR)

    @property
    def warnings(self) -> int:
        return sum(1 for ok, sev, _ in self.results if not ok and sev == WARNING)

    def emit(self, out=sys.stdout) -> None:
        for label in self.notes:
            print(f"# {label}", file=out)
        for i, (ok, severity, label) in enumerate(self.results, 1):
            if ok:
                print(f"ok {i} - {label}", file=out)
            elif severity == WARNING:
                print(f"ok {i} - {label} # TODO warning", file=out)
            else:
                print(f"not ok {i} - {label}", file=out)
        print(f"1..{len(self.results)}", file=out)


def _reachable(uib, sc) -> set:
    """Names reachable from a screen's initial focus by D-pad.

    Edges that leave the screen's own range are ignored, which mirrors
    `ps2ui_move`: it only ever lands inside the current screen.
    """
    lo = sc["focus_first"]
    hi = lo + sc["focus_count"]
    if not lo <= sc["initial"] < hi:
        return set()
    seen = {sc["initial"]}
    queue = [sc["initial"]]
    while queue:
        node = uib.focus[queue.pop()]
        for edge in ("up", "down", "left", "right"):
            nxt = node[edge]
            if nxt == FOCUS_NONE or not lo <= nxt < hi or nxt in seen:
                continue
            seen.add(nxt)
            queue.append(nxt)
    return {uib.focus[i]["name"] for i in seen}


def check_tables(uib, rep: Report) -> None:
    """The four static caps ps2ui_load() enforces with PS2UI_ERR_TOO_MANY.

    Since B10 the baker refuses to write an over-cap blob, so for a blob
    this toolchain produced these cannot fail. They are here because a
    .uib is a documented format others can write, and because this reads
    the property from the far side: the baker checks what it is about to
    write, this checks what a loader will find.
    """
    c = caps_mod.parse_header()
    for count, key, what in (
        (len(uib.textures), "PS2UI_MAX_TEXTURES", "textures"),
        (len(uib.slots), "PS2UI_MAX_SLOTS", "slots"),
        (len(uib.screens), "PS2UI_MAX_SCREENS", "screens"),
    ):
        rep.error(count <= c[key], f"{count} {what} within {key} ({c[key]})")
    # Slot capacity used to be checked against the runtime's fixed
    # per-slot buffer. That buffer is gone (v6 resource model): the
    # runtime sizes each slot from the capacity declared here, so a
    # large capacity buys arena bytes instead of an unloadable blob.
    # What an integrator needs instead is the arena number itself,
    # reported rather than asserted -- there is no threshold to fail
    # against, and inventing one would be the kind of made-up limit
    # this file exists to remove.
    ee = arena.arena_size(uib, arena.EE_PTR)
    rep.note(f"arena: {ee} bytes on the EE "
             f"({arena.arena_size(uib, arena.HOST64_PTR)} on a 64-bit host; "
             f"GSTEXTURE holds pointers, so the two differ)")
    # The GIF DMA reads texture bytes in place, and DMA source addresses
    # must be qword aligned. The runtime refuses a violating blob with
    # PS2UI_ERR_ALIGN; this reads the same property at bake time, where
    # a failure names the texture instead of a red screen.
    # A GIF source-chain REF tag has no low address bits: a misaligned
    # source is truncated and the transfer starts early. bin2c places
    # the file 16-aligned, so alignment in the FILE is alignment in
    # memory -- and it takes both halves, the blob section's own offset
    # and each texture's offset within it. The first half was wrong in
    # every blob baked before 2026-08-23, shifting every texture by 4-12
    # bytes on console and emulator alike.
    ob = getattr(uib, "off_blob", 0)
    rep.error(ob % 16 == 0,
              f"blob section starts 16-aligned in the file (off_blob={ob})")
    misaligned = [i for i, t in enumerate(uib.textures) if t.data_off % 16]
    rep.error(not misaligned,
              "every texture's pixel bytes 16-aligned for in-place DMA"
              + (f"; misaligned: {misaligned}" if misaligned else ""))


def check_indices(uib, rep: Report) -> None:
    """Every table index the runtime dereferences without checking."""
    bad_tex = [i for i, r in enumerate(uib.records)
               if r.op == OP_TEXQUAD and not 0 <= r.tex < len(uib.textures)]
    rep.error(not bad_tex,
              f"every TEXQUAD names a real texture"
              + (f"; commands {bad_tex[:5]}" if bad_tex else ""))

    bad_clut = [i for i, t in enumerate(uib.textures)
                if t.clut is not None and not 0 <= t.clut < len(uib.cluts)]
    rep.error(not bad_clut,
              "every indexed texture names a real CLUT"
              + (f"; textures {bad_clut[:5]}" if bad_clut else ""))

    # A PSMT8 texel is a palette index, so an 8-bit texture with no CLUT
    # would be uploaded with whatever palette was last resident.
    no_clut = [i for i, t in enumerate(uib.textures)
               if t.fmt == gs.PSMT8 and t.clut is None]
    rep.error(not no_clut,
              "every PSMT8 texture carries a CLUT"
              + (f"; textures {no_clut[:5]}" if no_clut else ""))

    bad_font = [s["name"] for s in uib.slots
                if not 0 <= s["font"] < len(uib.fonts)]
    rep.error(not bad_font,
              "every slot names a real font table"
              + (f"; slots {', '.join(bad_font[:5])}" if bad_font else ""))

    bad_focus = [i for i, r in enumerate(uib.records)
                 if r.focus != FOCUS_NONE and not 0 <= r.focus < len(uib.focus)]
    rep.error(not bad_focus,
              "every command's focus index is in range"
              + (f"; commands {bad_focus[:5]}" if bad_focus else ""))

    bad_state = [i for i, r in enumerate(uib.records)
                 if r.state not in (STATE_ALWAYS, STATE_UNFOCUSED, STATE_FOCUSED)]
    rep.error(not bad_state, "every command carries a known state")

    # A state-dependent command with no focus index can never resolve.
    orphan = [i for i, r in enumerate(uib.records)
              if r.state != STATE_ALWAYS and r.focus == FOCUS_NONE]
    rep.error(not orphan,
              "every focus-dependent command names a focus node"
              + (f"; commands {orphan[:5]}" if orphan else ""))


def check_screens(uib, rep: Report) -> None:
    """Screens must partition the command, focus and slot tables.

    `ps2ui_screen_set` swaps ranges and replays. A gap means commands
    that no screen ever draws; an overlap means one screen drawing
    another's. Neither is detectable at runtime.
    """
    if not rep.error(len(uib.screens) >= 1, "at least one screen"):
        return

    for first, count, total, what in (
        ("cmd_first", "cmd_count", len(uib.records), "command"),
        ("focus_first", "focus_count", len(uib.focus), "focus"),
        ("slot_first", "slot_count", len(uib.slots), "slot"),
    ):
        cursor = 0
        ok = True
        for sc in uib.screens:
            if sc[first] != cursor:
                ok = False
                break
            cursor += sc[count]
        rep.error(ok and cursor == total,
                  f"screens partition the {what} table contiguously "
                  f"({cursor}/{total})")

    names = [sc["name"] for sc in uib.screens]
    rep.error(len(set(names)) == len(names),
              f"screen names are unique: {names}")

    for sc in uib.screens:
        lo, hi = sc["focus_first"], sc["focus_first"] + sc["focus_count"]
        if sc["focus_count"] == 0:
            rep.error(sc["initial"] == FOCUS_NONE,
                      f"{sc['name']}: no focusables, so no initial focus")
            continue
        rep.error(lo <= sc["initial"] < hi,
                  f"{sc['name']}: initial focus is one of its own focusables")

        # Edges that leave the screen would move focus to a node the
        # screen never draws.
        escaping = [
            uib.focus[i]["name"]
            for i in range(lo, hi)
            for edge in ("up", "down", "left", "right")
            if uib.focus[i][edge] != FOCUS_NONE
            and not lo <= uib.focus[i][edge] < hi
        ]
        rep.error(not escaping,
                  f"{sc['name']}: no D-pad edge leaves the screen"
                  + (f"; from {', '.join(sorted(set(escaping))[:5])}" if escaping else ""))

        names_in = {uib.focus[i]["name"] for i in range(lo, hi)}
        stranded = names_in - _reachable(uib, sc)
        rep.error(not stranded,
                  f"{sc['name']}: every focusable reachable by D-pad"
                  + (f"; stranded: {', '.join(sorted(stranded)[:5])}" if stranded else ""))

    if uib.screens:
        rep.error(uib.initial_focus == uib.screens[0]["initial"],
                  "header initial_focus matches screen 0")


def check_scissors(uib, rep: Report) -> None:
    """Scissor pushes and pops must balance within every screen.

    The runtime keeps a fixed stack and no error path. An unbalanced
    push leaks the clip into whatever draws next; an extra pop
    underflows.
    """
    limit = caps_mod.parse_header()["PS2UI_MAX_SCISSOR_DEPTH"]
    for sc in uib.screens:
        depth = 0
        peak = 0
        floor_hit = False
        lo = sc["cmd_first"]
        for r in uib.records[lo:lo + sc["cmd_count"]]:
            if r.op == OP_SCISSOR_PUSH:
                depth += 1
                peak = max(peak, depth)
            elif r.op == OP_SCISSOR_POP:
                depth -= 1
                if depth < 0:
                    floor_hit = True
                    break
        rep.error(peak < limit,
                  f"{sc['name']}: scissor nesting {peak} within "
                  f"PS2UI_MAX_SCISSOR_DEPTH ({limit})")
        rep.error(not floor_hit and depth == 0,
                  f"{sc['name']}: scissor pushes and pops balance"
                  + (" (underflow)" if floor_hit else
                     f" ({depth} left open)" if depth else ""))


def check_gs_domains(uib, rep: Report) -> None:
    """The two colour-domain rules that a preview cannot show you.

    Both were real defects (B1), and both look correct in the previewer
    when the previewer normalizes the same way the baker does, which is
    why they are asserted on the file rather than on a render.
    """
    bad_alpha = [i for i, r in enumerate(uib.records)
                 if r.op in (OP_QUAD, OP_TEXQUAD) and r.rgba[3] > 0x80]
    rep.error(not bad_alpha,
              "every quad's alpha is in the GS 0-128 domain"
              + (f"; commands {bad_alpha[:5]}" if bad_alpha else ""))

    bad_mod = [i for i, r in enumerate(uib.records)
               if r.op == OP_TEXQUAD and max(r.rgba[:3]) > 0x80]
    rep.error(not bad_mod,
              "TEXQUAD colors are in the 0x80 modulate-identity domain"
              + (f"; commands {bad_mod[:5]}" if bad_mod else ""))

    for name, colors in (("base", "color_base"), ("focus", "color_focus")):
        bad = [s["name"] for s in uib.slots if max(s[colors][:3]) > 0x80
               or s[colors][3] > 0x80]
        rep.error(not bad,
                  f"slot {name} colors are in the modulate domain"
                  + (f"; slots {', '.join(bad[:5])}" if bad else ""))


def check_fonts(uib, rep: Report) -> None:
    """What the runtime's glyph bsearch assumes."""
    for i, font in enumerate(uib.fonts):
        rep.error(0 <= font["tex"] < len(uib.textures),
                  f"font {i} names a real atlas texture")
        rep.error(bool(font["glyphs"]), f"font {i} has at least one glyph")
        # read_uib returns glyphs as a dict, so codepoint-sortedness in
        # the file is asserted by rebuilding the order the loader needs.
        cps = list(font["glyphs"])
        rep.error(cps == sorted(cps),
                  f"font {i} glyphs are codepoint-sorted for bsearch")

        # Same contract for the kern table, plus: a pair naming a glyph
        # the atlas does not carry can never be looked up, and a stored
        # zero is a lookup that returns what a miss would have.
        pairs = list(font["kerns"])
        rep.error(pairs == sorted(pairs),
                  f"font {i} kern pairs are sorted for bsearch")
        rep.error(all(v != 0 for v in font["kerns"].values()),
                  f"font {i} stores no zero kerns")
        orphan = [p for p in pairs
                  if p[0] not in font["glyphs"] or p[1] not in font["glyphs"]]
        rep.error(not orphan,
                  f"font {i} kerns only pairs it has glyphs for"
                  + (f"; {len(orphan)} orphaned" if orphan else ""))

    # Feature bits are a promise about the tables, and a promise the
    # runtime acts on: with the bit clear it may skip the kern lookup
    # entirely, so a blob carrying pairs it did not declare would kern
    # in the previewer and not on console.
    has_kerns = any(f["kerns"] for f in uib.fonts)
    rep.error(bool(uib.feature_flags & FEAT_KERNING) == has_kerns,
              "the kerning feature bit matches the kern tables"
              + ("" if not has_kerns else
                 f" ({sum(len(f['kerns']) for f in uib.fonts)} pairs)"))

    # Same promise for slot spacing: bit 2 says some slot carries a
    # non-zero letter-spacing.
    has_spacing = any(s_["letter_spacing"] for s_ in uib.slots)
    rep.error(bool(uib.feature_flags & FEAT_SLOT_SPACING) == has_spacing,
              "the slot-spacing feature bit matches the slot table")

    # A slot the app never sets still draws, so a placeholder that will
    # not render is a blank line on console with nothing to explain it.
    missing = []
    for s in uib.slots:
        if not 0 <= s["font"] < len(uib.fonts):
            continue
        glyphs = uib.fonts[s["font"]]["glyphs"]
        absent = {ch for ch in s["placeholder"] if ord(ch) not in glyphs}
        if absent:
            missing.append(f"{s['name']} ({''.join(sorted(absent))})")
    rep.error(not missing,
              "every slot placeholder is fully covered by its font"
              + (f"; {', '.join(missing[:5])}" if missing else ""))


def _dead_commands(uib, sc) -> list:
    """Commands whose rect cannot produce a pixel.

    Uses the same scissor model as the baker (clip.py) so the two cannot
    disagree about what "dead" means. Text is the usual source: a
    `nowrap` run inside `overflow: hidden` used to bake every glyph and
    let the GS clip, so the tail of a long string was quads the console
    submitted every frame and could never see. Since F24 the baker
    trims those, so anything reported here is either a blob from an
    older baker or a case the trim missed.
    """
    return clip_mod.dead_indices(
        uib.records, sc["cmd_first"], sc["cmd_count"],
        uib.canvas_w, uib.canvas_h)

def _declared_count(rep, n, declared, flag, noun, surplus_text, clean_text):
    """Report a count that was declared on the command line.

    A declaration is an assertion, not a ceiling. `--allow-dead 1` and
    `--allow-hairline 5` name specific instruments -- a quad parked
    outside its clip to prove the scissor works, four edge rules whose
    absence IS bring-up step 6's reading -- and the first version of
    both flags accepted "at most N", so the declaration could not
    notice its instruments leaving. Deleting the test card's red top
    edge rule left the check reporting "4 1px quad(s), 5 declared
    deliberate" and passing.

    So all three directions are verdicts: fewer than declared is an
    instrument that went missing, more is the accident the check exists
    for, and only the exact count passes.

    One function, because the second flag inherited the first flag's
    ceiling instead of its fix. A third cannot.
    """
    if declared and n == declared:
        rep.warn(True, f"{n} {noun}, {declared} declared deliberate ({flag})")
    elif declared and n < declared:
        rep.warn(False,
                 f"{n} {noun}, but {declared} declared deliberate ({flag}): "
                 f"{declared - n} of the instruments that count names is "
                 f"gone, and the check can no longer see what it measures")
    elif n:
        rep.warn(False, surplus_text
                 + (f"; {declared} declared deliberate" if declared else ""))
    else:
        rep.warn(True, clean_text)


def check_crt(uib, rep: Report, canvas, allow_dead: int = 0,
              allow_hairline: int = 0) -> None:
    """Advisory. Legal blobs that waste the GS or look wrong on a CRT."""
    # `--allow-hairline N`, for the same reason as --allow-dead below: a
    # 1px quad is usually an accident and sometimes the instrument. The
    # test card's edge rules and its interlace pair ARE the shimmer being
    # measured (bring-up step 8), and a blob cannot say so about itself.
    # Declaring the count keeps this strict -- one more still warns --
    # and turns the only remaining permanent warning in CI into a number
    # somebody chose. A linter with standing false alarms is one people
    # learn to skim.
    hairlines = [i for i, r in enumerate(uib.records)
                 if r.op == OP_QUAD and (r.w == 1 or r.h == 1)]
    _declared_count(
        rep, len(hairlines), allow_hairline, "--allow-hairline", "1px quad(s)",
        f"{len(hairlines) - allow_hairline} 1px quad(s) will shimmer on an "
        f"interlaced CRT",
        "no 1px quads to shimmer on an interlaced CRT")

    # `--allow-dead N` declares that N of these are deliberate. The flag
    # that produced them (`data-keep`) is build-time only and never
    # reaches the blob, so a validator reading the file cannot tell an
    # instrument from waste -- and it should not guess. Declaring the
    # count keeps the check strict: one more than expected still warns.
    dead = [i for sc in uib.screens for i in _dead_commands(uib, sc)]
    _declared_count(
        rep, len(dead), allow_dead, "--allow-dead", "dead command(s)",
        f"{len(dead) - allow_dead} command(s) fall entirely outside their "
        f"clip and are submitted every frame for nothing (from command "
        f"{dead[0] if dead else 0}); usually the tail of a nowrap run "
        f"inside overflow:hidden",
        "every command can produce a pixel")

    unused = sorted(set(range(len(uib.textures))) -
                    {r.tex for r in uib.records if r.op == OP_TEXQUAD}
                    - {f["tex"] for f in uib.fonts})
    rep.warn(not unused,
             f"textures {unused[:5]} are never drawn but still cost VRAM"
             if unused else
             "every texture is drawn or belongs to a font")


def check_vram(uib, rep: Report, budget=None) -> None:
    _lines, used, limit, ok = vram.report(uib.textures, uib.cluts,
                                          uib.canvas_w, uib.canvas_h, budget)
    rep.error(ok, f"VRAM {used // 1024} KiB within budget {limit // 1024} KiB")


def check_blob(uib, budget=None, allow_dead: int = 0,
               allow_hairline: int = 0) -> Report:
    """Every check, in dependency order. Returns the Report."""
    rep = Report()
    check_tables(uib, rep)
    check_indices(uib, rep)
    check_screens(uib, rep)
    check_scissors(uib, rep)
    check_gs_domains(uib, rep)
    check_fonts(uib, rep)
    check_vram(uib, rep, budget)
    check_crt(uib, rep, (uib.canvas_w, uib.canvas_h), allow_dead,
              allow_hairline)
    return rep


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        prog="ps2ui-check",
        description="Validate a baked .uib against what the C runtime assumes.")
    ap.add_argument("uib", help="path to a .uib blob")
    ap.add_argument("--vram-budget", type=int, default=None, metavar="BYTES",
                    help="override the default texture VRAM budget")
    ap.add_argument("--allow-dead", type=int, default=0, metavar="N",
                    help="N draw commands outside their clip are deliberate "
                         "(data-keep instruments); more than N still warns")
    ap.add_argument("--allow-hairline", type=int, default=0, metavar="N",
                    help="N 1px quads are deliberate (the test card's edge "
                         "rules and interlace pair); more than N still warns")
    ap.add_argument("--strict", action="store_true",
                    help="treat CRT warnings as failures")
    args = ap.parse_args(argv)

    try:
        uib = read_uib(args.uib)
    except (OSError, ValueError) as exc:
        print(f"ps2ui-check: {exc}", file=sys.stderr)
        return 2

    rep = check_blob(uib, args.vram_budget, args.allow_dead,
                     args.allow_hairline)
    rep.emit()

    aspect = f"{uib.display_aspect[0]}:{uib.display_aspect[1]}"
    print(f"# {args.uib}: {uib.canvas_w}x{uib.canvas_h} at {aspect}, "
          f"{len(uib.screens)} screen(s), {len(uib.records)} commands, "
          f"{len(uib.textures)} textures, {len(uib.slots)} slots")

    failed = rep.errors + (rep.warnings if args.strict else 0)
    verdict = "PASS" if failed == 0 else "FAIL"
    print(f"{verdict}: {len(rep.results)} checks, {rep.errors} error(s), "
          f"{rep.warnings} warning(s)")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
