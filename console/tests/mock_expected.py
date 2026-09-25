"""What `make MOCK=1`'s first frame should look like, drawn by the previewer.

usage: mock_expected.py <theme.uib> <out.png>

Reads console/mock_library.h -- the list the MOCK build compiles in --
and fills the theme's slots with it exactly as console/main.c's fill()
does: row i from game i, the sel-* slots from game 0, "N games" and the
mock status line. hw.yml boots ophtml-mock.elf in the emulator and
diffs its frame against this one, so the check is the console's binding
of games to rows against the previewer's reading of the same list.

The labels and the count text are restated here, not imported, because
they are C (library.c's console_bsd_label, main.c's "%d games"). A
change to either shows up as that diff, which is the point of having it.
"""

import os
import re
import sys

here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(here, "..", "..", "packages", "baker"))

from ps2ui_bake import preview  # noqa: E402
from ps2ui_bake.uib import read_uib  # noqa: E402

LABEL = {"CONSOLE_BSD_USB": "USB", "CONSOLE_BSD_ATA": "HDD",
         "CONSOLE_BSD_MX4SIO": "SD", "CONSOLE_BSD_MMCE": "MMCE"}
MEDIA = {"CONSOLE_MEDIA_DVD": "DVD", "CONSOLE_MEDIA_CD": "CD"}


def mock_list():
    src = open(os.path.join(here, "..", "mock_library.h")).read()
    games = [dict(title=t, id=i, media=MEDIA[m], device=LABEL[b])
             for t, i, m, b in re.findall(
                 r'^MOCK\("([^"]*)",\s*"([^"]*)",\s*(\w+),\s*(\w+)\)', src, re.M)]
    status = re.search(r'#define CONSOLE_MOCK_STATUS "([^"]*)"', src).group(1)
    if not games:
        sys.exit("mock_expected: no MOCK(...) lines in mock_library.h")
    return games, status


def main():
    blob, out = sys.argv[1], sys.argv[2]
    uib = read_uib(blob)
    games, status = mock_list()
    names = {f["name"] for f in uib.focus}
    rows = 0
    while f"game-{rows}" in names:
        rows += 1
    if rows > len(games):
        sys.exit(f"mock_expected: the theme has {rows} rows and the mock list "
                 f"{len(games)} games; a partly empty page hides rows, which "
                 f"the previewer cannot draw")

    text = {"status": status, "game-count": f"{len(games)} games"}
    for r in range(rows):
        g = games[r]
        text[f"game-{r}-title"] = g["title"]
        text[f"game-{r}-id"] = g["id"]
        text[f"game-{r}-media"] = g["media"]
        text[f"game-{r}-device"] = g["device"]
    sel = games[0]
    text.update({"sel-title": sel["title"], "sel-id": sel["id"],
                 "sel-media": sel["media"], "sel-device": sel["device"]})

    screen = "games" if any(s["name"] == "games" for s in uib.screens) else 0
    preview.render(uib, screen=screen, slot_text=text).save(out)
    print(f"mock_expected: {rows} rows of {len(games)} games -> {out}",
          file=sys.stderr)


if __name__ == "__main__":
    main()
