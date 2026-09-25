"""The console's theme contract on the host: console.py, the `ps2ui
check` findings it adds, and `ps2ui serve --console`.

The frames are not here. hw.yml boots ophtml-mock.elf and ophtml-nav.elf
in Play! and diffs them against console/tests/mock_expected.py, which is
what holds console.py's fill and list window to the console's. What is
here is everything that can be wrong without a frame: the arithmetic,
the list the header and this module each keep, and every finding the
check can make, each provoked once.
"""
import os
import re
import sys
import unittest
from types import SimpleNamespace

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ps2ui_bake import console, serve                          # noqa: E402
from ps2ui_bake.check import Report, check_blob                # noqa: E402
# The same skip-unless-CI-says-otherwise answer test_serve uses for a
# shipped example's blob, imported rather than restated.
from test_serve import ROOT, MEMCARD, blob                     # noqa: E402

CONSOLE = os.path.join(ROOT, "examples", "console", "build", "ui.uib")
CHANNEL6 = os.path.join(ROOT, "examples", "channel6", "build", "ui.uib")
MOCK_HEADER = os.path.join(ROOT, "console", "mock_library.h")


class TestListWindow(unittest.TestCase):
    """runtime/ps2ui.c's ps2ui_list_*, as the host restates it."""

    def test_the_sequence_the_emulator_presses(self):
        """hw.yml's navigation step, in numbers: the frames it diffs are
        drawn from these."""
        w = console.ListWindow(10, 14)
        console.replay(w, ["down", "down", "down"])
        self.assertEqual((w.sel, w.top, w.selected_row()), (3, 0, 3))
        console.replay(w, ["r1"])
        # A page past the end clamps to the last item, and the window
        # slides the minimum distance to show it: top 4, not 13.
        self.assertEqual((w.sel, w.top, w.selected_row()), (13, 4, 9))
        console.replay(w, ["l1"])
        self.assertEqual((w.sel, w.top, w.selected_row()), (3, 3, 0))

    def test_a_short_list_never_scrolls(self):
        w = console.ListWindow(10, 4)
        self.assertTrue(w.move(10))
        self.assertEqual((w.sel, w.top), (3, 0))
        self.assertEqual(w.item_at(3), 3)
        self.assertEqual(w.item_at(4), -1)

    def test_the_ends_clamp_and_report_no_change(self):
        w = console.ListWindow(10, 14)
        self.assertFalse(w.move(-1))
        w.select(13)
        self.assertFalse(w.move(1))

    def test_an_empty_list_has_no_selected_row(self):
        w = console.ListWindow(10, 0)
        self.assertFalse(w.move(1))
        self.assertEqual(w.selected_row(), -1)
        self.assertEqual(w.item_at(0), -1)

    def test_unknown_keys_are_refused_rather_than_ignored(self):
        with self.assertRaises(ValueError):
            console.replay(console.ListWindow(10, 14), ["pgdn"])


class TestMockLibrary(unittest.TestCase):
    """console.py's MOCK_GAMES and console/mock_library.h are one list
    kept twice, because C cannot import Python and the wheel ships no
    header. This is what makes them one list."""

    ENUM = {"CONSOLE_MEDIA_DVD": "DVD", "CONSOLE_MEDIA_CD": "CD",
            "CONSOLE_BSD_USB": "USB", "CONSOLE_BSD_ATA": "HDD",
            "CONSOLE_BSD_MX4SIO": "SD", "CONSOLE_BSD_MMCE": "MMCE"}

    def header(self):
        if not os.path.exists(MOCK_HEADER):
            if os.environ.get("PS2UI_REQUIRE_EXAMPLES"):
                raise AssertionError("no %s in a checkout run" % MOCK_HEADER)
            raise unittest.SkipTest("no console/ beside this install")
        with open(MOCK_HEADER, encoding="utf-8") as fh:
            return fh.read()

    def test_the_header_and_the_module_list_the_same_games(self):
        src = self.header()
        rows = re.findall(r'^MOCK\("([^"]*)",\s*"([^"]*)",\s*(\w+),\s*(\w+)\)',
                          src, re.M)
        self.assertEqual(
            tuple((t, i, self.ENUM[m], self.ENUM[b]) for t, i, m, b in rows),
            console.MOCK_GAMES)

    def test_the_header_and_the_module_show_the_same_status(self):
        m = re.search(r'#define CONSOLE_MOCK_STATUS "([^"]*)"', self.header())
        self.assertEqual(m.group(1), console.MOCK_STATUS)

    def test_the_labels_are_library_cs(self):
        self.assertEqual(sorted(console.LABELS.values()),
                         ["HDD", "MMCE", "SD", "USB"])
        self.assertTrue(all(len(v) <= console.LONGEST["device"]
                            for v in console.LABELS.values()))

    def test_the_count_reads_the_way_main_c_writes_it(self):
        self.assertEqual(console.count_text(1), "1 game")
        self.assertEqual(console.count_text(14), "14 games")


def fake(screens, slots=()):
    """A blob with only what console.check reads: screens with their
    focus ranges, focus nodes and slots. screens is [(name, [nodes])]."""
    focus, table = [], []
    for name, nodes in screens:
        first = len(focus)
        for n in nodes:
            focus.append({"index": len(focus), "name": n})
        table.append({"name": name, "focus_first": first,
                      "focus_count": len(nodes), "initial": first})
    return SimpleNamespace(
        screens=table, focus=focus,
        slots=[{"name": n, "capacity": c} for n, c in slots])


def rows(n):
    return ["game-%d" % i for i in range(n)]


def row_slots(n, capacity=64):
    return [("game-%d-title" % i, capacity) for i in range(n)]


def findings(uib, force=False):
    rep = Report()
    console.check(uib, rep, force=force)
    return [(sev, label) for ok, sev, label in rep.results if not ok]


class TestContractCheck(unittest.TestCase):
    """Each finding, provoked once, and the clean case that provokes none."""

    def test_a_complete_theme_has_no_findings(self):
        uib = fake([("games", rows(3) + ["play"])],
                   row_slots(3) + [("game-0-id", 11), ("sel-device", 4),
                                   ("status", 48)])
        self.assertEqual(findings(uib), [])

    def test_a_blob_that_uses_no_console_name_gets_no_results(self):
        rep = Report()
        console.check(fake([("home", ["a", "b"])], [("title", 20)]), rep)
        self.assertEqual(rep.results, [])

    def test_sel_and_status_names_alone_do_not_make_a_console_theme(self):
        """The channel-6 example's shape: a detail panel with sel-*
        slots and no numbered rows. Ordinary names; not an opt-in."""
        uib = fake([("games", ["game-aurora", "act-launch"])],
                   [("sel-title", 40), ("sel-sub", 20), ("status", 20)])
        rep = Report()
        console.check(uib, rep)
        self.assertEqual(rep.results, [])

    def test_a_row_slot_alone_opts_a_theme_in(self):
        self.assertTrue(console.is_console_theme(
            fake([("games", ["x"])], [("game-0-title", 64)])))

    def test_a_gap_strands_the_rows_after_it(self):
        uib = fake([("games", ["game-0", "game-1", "game-3"])], row_slots(2))
        (sev, label), = findings(uib)
        self.assertEqual(sev, "error")
        self.assertIn("stops at game-2", label)
        self.assertIn("game-3", label)

    def test_rows_on_a_screen_the_console_never_opens(self):
        uib = fake([("games", rows(2)), ("detail", ["game-9"])],
                   row_slots(2))
        (sev, label), = findings(uib)
        self.assertEqual(sev, "error")
        self.assertIn("game-9", label)

    def test_without_a_games_screen_the_first_screen_is_the_one(self):
        uib = fake([("home", rows(2)), ("other", ["x"])], row_slots(2))
        self.assertEqual(findings(uib), [])
        self.assertEqual(console.games_screen(uib)["name"], "home")

    def test_a_slot_for_a_row_that_does_not_exist_is_never_filled(self):
        uib = fake([("games", rows(2))], row_slots(3))
        (sev, label), = findings(uib)
        self.assertEqual(sev, "error")
        self.assertIn("game-2-title", label)

    def test_a_misspelt_field_is_named_with_the_right_one(self):
        uib = fake([("games", rows(1))],
                   row_slots(1) + [("game-0-titel", 64), ("sel-tilte", 64)])
        (sev, label), = findings(uib)
        self.assertEqual(sev, "warning")
        self.assertIn("did you mean 'title'", label)
        self.assertIn("did you mean 'sel-title'", label)

    def test_an_id_slot_shorter_than_an_id_truncates_every_one(self):
        uib = fake([("games", rows(1))],
                   row_slots(1) + [("game-0-id", 8), ("sel-device", 3)])
        (sev, label), = findings(uib)
        self.assertEqual(sev, "warning")
        self.assertIn("game-0-id holds 8, needs 11", label)
        self.assertIn("sel-device holds 3, needs 4", label)

    def test_rows_with_no_title_say_nothing_about_their_game(self):
        uib = fake([("games", rows(2))], [("game-0-id", 11)])
        (sev, label), = findings(uib)
        self.assertEqual(sev, "warning")
        self.assertIn("game-N-title", label)

    def test_forcing_it_on_a_theme_with_no_list_is_an_error(self):
        (sev, label), = findings(fake([("home", ["a"])]), force=True)
        self.assertEqual(sev, "error")
        self.assertIn("game-0", label)

    def test_the_built_in_theme_passes_it(self):
        uib = blob(CONSOLE)
        rep = check_blob(uib)
        self.assertEqual([r for r in rep.results if not r[0]], [])
        self.assertTrue(any("console:" in r[2] for r in rep.results))

    def test_a_blob_with_no_console_names_is_checked_exactly_as_before(self):
        """The counts other blobs report are pinned in documents; this
        check must not move them by existing. Channel-6 is the one with
        sel-* slots of its own, which the first version of the opt-in
        test mistook for a console theme."""
        for path in (MEMCARD, CHANNEL6):
            rep = check_blob(blob(path))
            self.assertFalse(any("console:" in r[2] for r in rep.results),
                             path)


class TestFill(unittest.TestCase):

    def test_rows_past_the_end_are_written_blank(self):
        uib = fake([("games", rows(4))], row_slots(4))
        w = console.ListWindow(4, 2)
        text, focus = console.fill(uib, console.MOCK_GAMES[:2], w, "s")
        self.assertEqual(text["game-1-title"], "Brass Lantern")
        self.assertEqual(text["game-2-title"], "")
        self.assertEqual(text["game-count"], "2 games")
        self.assertEqual(focus, "game-0")

    def test_the_selection_panel_follows_the_selection(self):
        uib = fake([("games", rows(10))], row_slots(10))
        w = console.replay(console.ListWindow(10, 14), ["r1"])
        text, focus = console.fill(uib, console.MOCK_GAMES, w, "s")
        self.assertEqual(text["sel-title"], "Kite Season")
        self.assertEqual(text["game-9-title"], "Kite Season")
        self.assertEqual(focus, "game-9")


class TestServeConsole(unittest.TestCase):
    """`ps2ui serve --console`: main.c's loop, on the served state."""

    def server(self):
        srv = serve.Server(uib=blob(CONSOLE))
        srv.console = serve.ConsoleMock()
        srv.console.attach(srv.uib, srv.state)
        return srv

    def slots(self, srv):
        return srv.state.slots_for(srv.state.screen_name)

    def test_it_opens_on_the_first_game(self):
        srv = self.server()
        self.assertEqual(srv.state.focus_name, "game-0")
        self.assertEqual(self.slots(srv)["sel-title"], "Aurora Circuit")
        self.assertEqual(self.slots(srv)["status"], console.MOCK_STATUS)

    def test_down_and_r1_walk_the_list_as_the_console_does(self):
        srv = self.server()
        for _ in range(3):
            srv.apply({"key": "down"})
        self.assertEqual(srv.state.focus_name, "game-3")
        self.assertEqual(self.slots(srv)["sel-title"], "Deep Orchard")
        srv.apply({"key": "r1"})
        self.assertEqual(srv.state.focus_name, "game-9")
        self.assertEqual(self.slots(srv)["game-0-title"], "Echo Harbor")
        self.assertEqual(self.slots(srv)["sel-title"], "North of Nowhere")

    def test_up_at_the_top_falls_through_to_an_ordinary_move(self):
        srv = self.server()
        srv.apply({"key": "up"})
        # The built-in theme has nothing above game-0, so the fall-through
        # move is a no-op -- and the list did not wrap to the last game.
        self.assertEqual(srv.state.focus_name, "game-0")
        self.assertEqual(self.slots(srv)["sel-title"], "Aurora Circuit")

    def test_the_served_frame_is_the_one_mock_expected_draws(self):
        """The same fill through two callers: the page and the CI
        reference must not be two different pictures of one state."""
        from ps2ui_bake import preview
        srv = self.server()
        for key in ("down", "down", "r1"):
            srv.apply({"key": key})
        uib = srv.uib
        w = console.replay(console.ListWindow(console.row_count(uib), 14),
                           ["down", "down", "r1"])
        text, focus = console.fill(uib, console.MOCK_GAMES, w,
                                   console.MOCK_STATUS)
        want = preview.render(uib, screen="games", slot_text=text,
                              focus_current=console.focus_index(uib, focus))
        got = preview.render(uib, screen="games",
                             slot_text=self.slots(srv),
                             focus_current=srv.state.focus_index(uib))
        self.assertEqual(want.tobytes(), got.tobytes())


if __name__ == "__main__":
    unittest.main()
