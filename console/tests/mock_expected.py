"""What a MOCK build's frame should look like, drawn by the previewer.

usage: mock_expected.py <theme.uib> <out.png> [--keys down,down,r1,...]

The mock list, the contract names, the fill and the list window are all
packages/baker/ps2ui_bake/console.py's -- the host copy `ps2ui serve
--console` also runs -- so this script only replays keys and renders.
hw.yml boots ophtml-mock.elf (no keys) and ophtml-nav.elf (keys pressed
through Play!) and diffs each frame against one drawn here. What is
restated from C and what holds it to C is in console.py's docstring.
"""

import argparse
import os
import sys

here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(here, "..", "..", "packages", "baker"))

from ps2ui_bake import console, preview  # noqa: E402
from ps2ui_bake.uib import read_uib  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("uib")
    ap.add_argument("out")
    ap.add_argument("--keys", default="",
                    help="comma-separated up/down/l1/r1, in the order pressed")
    args = ap.parse_args(argv)

    uib = read_uib(args.uib)
    games = console.MOCK_GAMES
    rows = console.row_count(uib)
    if rows > len(games):
        sys.exit("mock_expected: the theme has %d rows and the mock list %d "
                 "games; a partly empty page hides rows, which the previewer "
                 "cannot draw" % (rows, len(games)))

    window = console.ListWindow(rows, len(games))
    keys = [k for k in args.keys.split(",") if k]
    console.replay(window, keys)
    text, focus = console.fill(uib, games, window, console.MOCK_STATUS)
    preview.render(uib, screen=console.games_screen(uib)["name"],
                   slot_text=text,
                   focus_current=console.focus_index(uib, focus)).save(args.out)
    print("mock_expected: %d rows, keys [%s] -> selection %d (row %d) -> %s"
          % (rows, ",".join(keys), window.sel, window.selected_row(), args.out),
          file=sys.stderr)


if __name__ == "__main__":
    main()
