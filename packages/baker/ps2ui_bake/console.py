"""The console's theme contract, on the host.

console/ (the OPHTML console, `ophtml.elf`) fills any theme that uses a
set of names -- `game-{i}` rows, `game-{i}-title`, `sel-title`, `status`
and the rest in console/README.md. Three things on the host need to know
that contract the same way the console does, and this module is the one
place they read it from:

* `ps2ui check` (check.py), which says when a theme's names would leave
  the console with rows it never fills or slots it never reaches;
* `ps2ui serve --console`, which fills a theme with the mock library so
  an author sees it populated before owning a console;
* console/tests/mock_expected.py, which draws the frames hw.yml diffs the
  emulator against.

WHAT IS RESTATED FROM C, AND WHAT HOLDS IT THERE. None of it can be
imported from Python, so each piece is fenced where it can be:

* the mock list is console/mock_library.h's, and tests/test_console.py's
  TestMockLibrary parses the header and compares;
* the four device labels are library.c's console_bsd_label, the media
  words and both count strings are main.c's, and TestRestatedFromC
  parses those out of the C source and compares;
* the list window (`ListWindow`) is runtime/ps2ui.c's ps2ui_list_*
  arithmetic, line for line, and is held to it by frames: hw.yml boots
  the console in Play!, presses keys, and diffs what it drew against
  what this module draws. That is the one piece held by behaviour
  rather than by text, so a change to ps2ui.c's list that keeps its
  frames for Down x3 / R1 / L1 is not caught here.
"""
from __future__ import annotations

import difflib
import re

# ------------------------------------------------------------ the names

SCREEN = "games"
ROW = re.compile(r"^game-(\d+)$")
ROW_SLOT = re.compile(r"^game-(\d+)-(.+)$")
ROW_FIELDS = ("title", "id", "media", "device")
SEL_SLOTS = tuple("sel-" + f for f in ROW_FIELDS)
GLOBAL_SLOTS = SEL_SLOTS + ("game-count", "status")

# The longest value the console writes into each field, in bytes. A
# slot shorter than this is truncated on every game that reaches the
# length -- which for the ID is every game: "SLUS_200.02" is always 11.
LONGEST = {"id": 11, "media": 3, "device": 4}

# console_bsd_label, by the -bsd= name Neutrino takes.
LABELS = {"usb": "USB", "ata": "HDD", "mx4sio": "SD", "mmce": "MMCE"}

# console/mock_library.h, in the same order and with the same labels.
# test_console.py's TestMockLibrary parses the header and fails if
# these drift.
MOCK_STATUS = "MOCK build: sample games, no drive read"
MOCK_GAMES = (
    ("Aurora Circuit", "SLUS_900.01", "DVD", "USB"),
    ("Brass Lantern", "SLUS_900.02", "DVD", "HDD"),
    ("Cinder Road", "SLUS_900.03", "CD", "USB"),
    ("Deep Orchard", "SLUS_900.04", "DVD", "SD"),
    ("Echo Harbor", "SLUS_900.05", "DVD", "MMCE"),
    ("Fable of the Long Winter and the Seven Bells", "SLUS_900.06", "DVD", "HDD"),
    ("Glass Meridian", "SLUS_900.07", "DVD", "USB"),
    ("Hollow Signal", "SLUS_900.08", "CD", "USB"),
    ("Iron Tide", "SLUS_900.09", "DVD", "HDD"),
    ("Juniper Line", "SLUS_900.10", "DVD", "MMCE"),
    ("Kite Season", "SLUS_900.11", "DVD", "USB"),
    ("Lumen Vale", "SLUS_900.12", "DVD", "SD"),
    ("Moth and Mirror", "SLUS_900.13", "CD", "HDD"),
    ("North of Nowhere", "SLUS_900.14", "DVD", "USB"),
)


def count_text(n: int) -> str:
    """main.c's game-count line."""
    return "%d game" % n if n == 1 else "%d games" % n


# ------------------------------------------------------- the list window

class ListWindow:
    """ps2ui_list, for the host. runtime/ps2ui.c:1665-1760 is the
    source; each method names the function it mirrors."""

    def __init__(self, rows: int, count: int = 0):
        self.rows, self.count, self.top, self.sel = rows, 0, 0, 0
        self.set_count(count)

    def _scroll_into_view(self):            # list_scroll_into_view
        if self.rows == 0 or self.count == 0:
            self.top = 0
            return
        if self.sel < self.top:
            self.top = self.sel
        elif self.sel >= self.top + self.rows:
            self.top = self.sel - self.rows + 1
        if self.count > self.rows:
            self.top = min(self.top, self.count - self.rows)
        else:
            self.top = 0

    def set_count(self, count: int):        # ps2ui_list_set_count
        self.count = count
        if count == 0:
            self.sel = self.top = 0
            return
        self.sel = min(self.sel, count - 1)
        self._scroll_into_view()

    def select(self, item: int) -> bool:    # ps2ui_list_select
        if self.count == 0:
            return False
        old = (self.sel, self.top)
        self.sel = min(item, self.count - 1)
        self._scroll_into_view()
        return (self.sel, self.top) != old

    def move(self, delta: int) -> bool:     # ps2ui_list_move
        if self.count == 0:
            return False
        return self.select(max(0, min(self.sel + delta, self.count - 1)))

    def item_at(self, row: int) -> int:     # ps2ui_list_item_at
        if row >= self.rows or self.top + row >= self.count:
            return -1
        return self.top + row

    def selected_row(self) -> int:          # ps2ui_list_selected_row
        if self.count == 0 or self.rows == 0:
            return -1
        row = self.sel - self.top
        return row if 0 <= row < self.rows else -1


# -------------------------------------------------------- blob questions

def games_screen(uib) -> dict:
    """The screen the console opens on: `games` if the theme has one,
    else its first (main.c's ps2ui_screen_set("games"))."""
    for sc in uib.screens:
        if sc["name"] == SCREEN:
            return sc
    return uib.screens[0]


def _nodes(uib, sc):
    return uib.focus[sc["focus_first"]:sc["focus_first"] + sc["focus_count"]]


def row_count(uib) -> int:
    """How many rows the console binds: game-0, game-1, ... on its
    screen, counted until the first name that is missing -- main.c's
    count_rows, which stops the same way."""
    names = {n["name"] for n in _nodes(uib, games_screen(uib))}
    r = 0
    while "game-%d" % r in names:
        r += 1
    return r


def is_console_theme(uib) -> bool:
    """Whether a blob uses the contract at all: a numbered game-N row,
    or a game-N-* slot. The check only speaks to blobs that opted in.

    NOT sel-*, status or game-count, although the console fills them.
    Those are ordinary names for ordinary panels, and the channel-6
    example -- a PS2 browser, not a console theme -- has `sel-title`,
    `sel-id` and three other sel-* slots of its own. Keying on them
    reported it as a console theme with three "unknown" names and moved
    its check count, which the promise in check_blob's docstring rules
    out. Numbered rows are what a list the console drives looks like;
    `ps2ui-check --console` covers a theme with none."""
    for n in uib.focus:
        if ROW.match(n["name"] or ""):
            return True
    return any(ROW_SLOT.match(s["name"]) for s in uib.slots)


# ---------------------------------------------------------------- filling

def fill(uib, games, window: ListWindow, status: str):
    """What the console writes, after a fill(): (slot_text, focus_name).

    main.c's fill() and scan_all(), and add_mock() for the count. Rows
    past the end are written "" as the console writes them; hiding them
    is ps2ui_list_apply_visibility's, which the previewer cannot do, so a
    caller that needs an exact frame keeps the window full."""
    text = {"status": status, "game-count": count_text(len(games))}
    for r in range(window.rows):
        item = window.item_at(r)
        g = games[item] if item >= 0 else None
        for i, field in enumerate(ROW_FIELDS):
            text["game-%d-%s" % (r, field)] = g[i] if g else ""
    sel = games[window.sel] if games else None
    for i, name in enumerate(SEL_SLOTS):
        text[name] = sel[i] if sel else ""
    row = window.selected_row()
    return text, ("game-%d" % row if row >= 0 else None)


def focus_index(uib, name):
    """The blob-wide focus index of a node on the games screen."""
    for n in _nodes(uib, games_screen(uib)):
        if n["name"] == name:
            return n["index"]
    return games_screen(uib)["initial"]


# Keys as main.c's loop reads them, for anything that replays a session.
KEYS = {"up": -1, "down": 1}


def replay(window: ListWindow, keys) -> ListWindow:
    """Apply main.c's list keys: up/down one item, l1/r1 a page."""
    for k in keys:
        if k in KEYS:
            window.move(KEYS[k])
        elif k == "l1":
            window.move(-window.rows)
        elif k == "r1":
            window.move(window.rows)
        else:
            raise ValueError("unknown key %r (up, down, l1, r1)" % k)
    return window


# ------------------------------------------------------------- checking

def _suggest(word, choices):
    hit = difflib.get_close_matches(word, choices, n=1, cutoff=0.6)
    return " (did you mean %r?)" % hit[0] if hit else ""


def check(uib, rep, force: bool = False) -> None:
    """The contract, as `ps2ui check` findings. Errors are names the
    console will leave showing their placeholder; warnings are names it
    never looks up, and slots too short for what it writes."""
    if not (force or is_console_theme(uib)):
        return
    sc = games_screen(uib)
    rows = row_count(uib)
    rep.note("console: %d row(s) on screen %r" % (rows, sc["name"]))

    if force:
        # Asked for by --console, so a theme with no list is a finding
        # rather than a blob this check has nothing to say about.
        rep.error(rows > 0,
                  "console: the theme has a game-0 row on the screen the "
                  "console opens (%r)" % sc["name"])

    # Offender suffixes follow the rest of the catalogue: "; <what>:
    # <first five>", present only on failure (ps2ui-check.md, "The
    # catalogue").
    def first5(names):
        return ", ".join(names[:5])

    # Rows past a gap are drawn with their placeholder forever: the
    # console stops counting at the first missing name.
    here = {n["name"] for n in _nodes(uib, sc)}
    stranded = sorted(int(m.group(1)) for m in
                      (ROW.match(n) for n in here) if m and int(m.group(1)) >= rows)
    rep.error(not stranded,
              "console: every game-N row is reachable from game-0 without a gap"
              + ("" if not stranded else "; the console stops at game-%d: %s"
                 % (rows, first5(["game-%d" % i for i in stranded]))))

    # Rows on another screen: the console never opens that screen.
    elsewhere = sorted({n["name"] for s in uib.screens if s is not sc
                        for n in _nodes(uib, s) if ROW.match(n["name"] or "")})
    rep.error(not elsewhere,
              "console: game-N rows are all on the screen the console opens (%r)"
              % sc["name"] + ("" if not elsewhere else
                              "; elsewhere: " + first5(elsewhere)))

    fields = set()
    unreached, unknown, short = [], [], []
    for s in uib.slots:
        name = s["name"]
        m = ROW_SLOT.match(name)
        if m:
            i, field = int(m.group(1)), m.group(2)
            if field not in ROW_FIELDS:
                unknown.append(name + _suggest(field, ROW_FIELDS))
                continue
            fields.add(field)
            if i >= rows:
                unreached.append(name)
        elif name.startswith("sel-"):
            if name not in SEL_SLOTS:
                unknown.append(name + _suggest(name, SEL_SLOTS))
                continue
            field = name[4:]
        else:
            continue
        if s["capacity"] < LONGEST.get(field, 0):
            short.append("%s (%d of %d)" % (name, s["capacity"], LONGEST[field]))

    rep.error(not unreached,
              "console: every game-N-field slot belongs to a row the console fills"
              + ("" if not unreached else "; never filled: " + first5(unreached)))
    rep.warn(not unknown,
             "console: every game-N-* and sel-* slot is a name the console fills"
             + ("" if not unknown else "; unknown: " + first5(unknown)))
    rep.warn(not short,
             "console: slots are long enough for what the console writes"
             + ("" if not short else "; short: " + first5(short)))
    rep.warn(rows == 0 or "title" in fields,
             "console: the rows carry a game-N-title slot, so a row shows "
             "which game it is")
