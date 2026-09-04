"""`ps2ui serve`: the state machine and the routes.

NOT PIXELS. `preview.render()` already has its own tests and its own
goldens, and duplicating them here would be a second set to keep in
step. What is new and therefore worth fencing is the state machine --
which screen, which focus, which theme, and what survives a rebuild --
plus the fact that the routes answer at all.

The one pixel assertion that IS here is the one that makes the tool
honest: the frame the server serves must be byte-identical to what
`--preview` writes for the same state. If it is not, the server has
started diverging from the CLI, and a previewer that disagrees with the
thing it previews is worse than none.
"""
import io
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))

from ps2ui_bake import preview, serve                          # noqa: E402
from ps2ui_bake.uib import read_uib                            # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))
MEMCARD = os.path.join(ROOT, "examples", "memcard", "build", "ui.uib")
OPLENV = os.path.join(ROOT, "examples", "opl-env", "build", "ui.uib")


def blob(path):
    if not os.path.exists(path):
        raise unittest.SkipTest("no blob at %s; run its build.sh"
                                % os.path.relpath(path, ROOT))
    return read_uib(path)


class TestFocusNames(unittest.TestCase):
    """Names, not indices, and scoped to a screen."""

    def test_the_same_name_on_two_screens_stays_on_its_own(self):
        """THE REGRESSION A SYNTHETIC TEST CANNOT PRODUCE.

        `nav-games`, `nav-saves` and `nav-settings` exist on BOTH of the
        memcard example's screens, because a nav bar is on every screen
        and `data-repeat` makes two screens each using `row-{i}` the
        natural thing to author. A blob-global name lookup passes every
        made-up fixture and selects the wrong screen's node on the first
        real example, which is why this test uses the shipped one.
        """
        u = blob(MEMCARD)
        shared = set()
        for sc in u.screens:
            names = {n["name"] for n in serve.nodes_of(u, sc)}
            shared = names if not shared else (shared & names)
        self.assertIn("nav-saves", shared,
                      "the example stopped sharing focus names, so this "
                      "test no longer covers what it was written for")

        st = serve.PreviewState()
        st.set_screen(u, "saves")
        st.focus_name = "nav-saves"
        got = st.focus_index(u)

        saves = serve.screen_of(u, "saves")
        lib = serve.screen_of(u, "library")
        in_saves = {n["index"] for n in serve.nodes_of(u, saves)}
        in_lib = {n["index"] for n in serve.nodes_of(u, lib)}
        self.assertIn(got, in_saves)
        self.assertNotIn(got, in_lib,
                         "resolved a name to the OTHER screen's node")

    def test_focus_survives_a_rebuild_that_renumbers(self):
        """A CSS edit must not move the selection.

        Indices are global, so adding one focusable to an earlier screen
        shifts every index after it. The state is a (screen, name) pair
        for exactly this.
        """
        u = blob(MEMCARD)
        st = serve.PreviewState()
        st.set_screen(u, "saves")
        st.focus_name = "save-gt4"
        before = st.focus_index(u)

        # A different blob, whose indices for the same names differ.
        v = blob(OPLENV)
        st2 = serve.PreviewState()
        st2.set_screen(v, "library")
        st2.focus_name = "row-0"
        self.assertIsNotNone(st2.focus_index(v))

        # And the original still resolves to the same node by name.
        self.assertEqual(st.focus_index(u), before)
        self.assertEqual(st.focus_name, "save-gt4")

    def test_a_vanished_name_falls_back_to_the_screens_initial(self):
        u = blob(MEMCARD)
        st = serve.PreviewState()
        st.set_screen(u, "saves")
        st.focus_name = "a-focusable-that-was-deleted"
        sc = serve.screen_of(u, "saves")
        self.assertEqual(st.focus_index(u), sc["initial"],
                         "a name that is gone must fall back, not raise")
        st.reconcile(u)
        self.assertIn(st.focus_name,
                      {n["name"] for n in serve.nodes_of(u, sc)})

    def test_a_vanished_screen_falls_back_to_the_first(self):
        u = blob(MEMCARD)
        st = serve.PreviewState()
        st.screen_name = "a-screen-that-was-deleted"
        st.reconcile(u)
        self.assertEqual(st.screen_name, u.screens[0]["name"])


class TestNavigation(unittest.TestCase):
    """Every move is the blob's own edge, or no move at all."""

    def test_a_move_lands_on_exactly_the_baked_neighbour(self):
        u = blob(MEMCARD)
        sc = serve.screen_of(u, "library")
        nodes = serve.nodes_of(u, sc)
        by_i = {n["index"]: n for n in nodes}
        moved = 0
        for node in nodes:
            for d in ("up", "down", "left", "right"):
                nxt = node[d]
                st = serve.PreviewState()
                st.set_screen(u, "library")
                st.focus_name = node["name"]
                ok = st.move(u, d)
                if nxt == serve.PS2UI_NONE or nxt == node["index"]:
                    # ps2ui_move returns 0 for both: no neighbour, and a
                    # self-edge. Neither may move the selection.
                    self.assertFalse(ok, "%s %s moved with no neighbour"
                                         % (node["name"], d))
                    self.assertEqual(st.focus_name, node["name"])
                else:
                    self.assertTrue(ok)
                    self.assertEqual(st.focus_name, by_i[nxt]["name"],
                                     "%s %s did not land on the baked edge"
                                     % (node["name"], d))
                    moved += 1
        self.assertGreater(moved, 0, "no edge in the example moved at all; "
                                     "this test asserted nothing")

    def test_no_wrap_is_invented(self):
        """Wrapping is a bake-time property of --focus-wrap.

        A previewer that wrapped on its own would show navigation the
        console does not have, which is the one thing it must never do.
        """
        u = blob(MEMCARD)
        sc = serve.screen_of(u, "library")
        edges = [n for n in serve.nodes_of(u, sc)
                 if n["up"] == serve.PS2UI_NONE]
        self.assertTrue(edges, "the example has no edge node to test")
        st = serve.PreviewState()
        st.set_screen(u, "library")
        st.focus_name = edges[0]["name"]
        self.assertFalse(st.move(u, "up"))
        self.assertEqual(st.focus_name, edges[0]["name"])


class TestScreensAndThemes(unittest.TestCase):

    def test_switching_screens_by_name_and_refusing_an_unknown_one(self):
        u = blob(MEMCARD)
        st = serve.PreviewState()
        st.set_screen(u, "saves")
        self.assertEqual(st.screen(u)["name"], "saves")
        with self.assertRaises(KeyError):
            st.set_screen(u, "nope")

    def test_focus_is_remembered_per_screen(self):
        u = blob(MEMCARD)
        srv = serve.Server(uib=u)
        srv.apply({"screen": "library"})
        srv.apply({"key": "down"})
        lib_focus = srv.state.focus_name
        srv.apply({"screen": "saves"})
        srv.apply({"screen": "library"})
        self.assertEqual(srv.state.focus_name, lib_focus,
                         "switching away and back lost the selection")

    def test_theme_clamps_rather_than_rendering_out_of_range(self):
        u = blob(OPLENV)
        n = max(1, len(u.themes or ()))
        self.assertGreater(n, 1, "the example lost its second theme, so "
                                 "this test no longer covers a switch")
        st = serve.PreviewState()
        st.set_theme(u, n - 1)
        with self.assertRaises(ValueError):
            st.set_theme(u, n)
        # A rebuild that drops a theme row must not leave the state
        # pointing past the end of the table.
        st.theme = 99
        st.reconcile(u)
        self.assertEqual(st.theme, 0)


class TestFrames(unittest.TestCase):

    def test_the_served_frame_is_what_preview_writes(self):
        """THE ASSERTION THIS WHOLE TOOL RESTS ON.

        The page shows a PNG and claims it is what the baker produces.
        If the two ever differ, every judgement made at the browser is
        about something the console will not draw.
        """
        u = blob(OPLENV)
        sc = u.screens[0]
        buf = io.BytesIO()
        preview.render(u, focus_current=sc["initial"],
                       screen=sc["name"]).save(buf, "PNG")

        srv = serve.Server(uib=u)
        srv.apply({"aspect": "framebuffer"})
        self.assertEqual(srv.frame(), buf.getvalue(),
                         "the server has diverged from --preview")

    def test_a_cached_frame_is_the_frame(self):
        """A cache that changes the answer is not a cache."""
        u = blob(OPLENV)
        srv = serve.Server(uib=u)
        cold = srv.frame()
        warm = srv.frame()
        self.assertEqual(cold, warm)
        srv.cache.clear()
        self.assertEqual(srv.frame(), cold)

    def test_every_aspect_mode_renders_and_they_differ(self):
        u = blob(OPLENV)
        srv = serve.Server(uib=u)
        sizes = {}
        for mode in serve.ASPECTS:
            srv.apply({"aspect": mode})
            png = srv.frame()
            self.assertEqual(png[:8], b"\x89PNG\r\n\x1a\n")
            sizes[mode] = len(png)
        self.assertNotEqual(sizes["force-4:3"], sizes["force-16:9"],
                            "the forced aspects produced the same image, so "
                            "the toggle is not doing anything")


class TestRoutes(unittest.TestCase):

    def serve_on_a_free_port(self, u):
        import threading
        page = "<!doctype html><title>t</title>"
        httpd = serve.bind(serve.make_handler(serve.Server(uib=u), page),
                           0, False)
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        self.addCleanup(httpd.shutdown)
        return httpd.server_address[1]

    def test_the_routes_answer(self):
        import http.client
        port = self.serve_on_a_free_port(blob(OPLENV))
        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=30)
        self.addCleanup(conn.close)

        for route, ctype in (("/", "text/html"),
                             ("/frame.png", "image/png"),
                             ("/state", "application/json"),
                             ("/rev", "application/json")):
            conn.request("GET", route)
            r = conn.getresponse()
            body = r.read()
            self.assertEqual(r.status, 200, route)
            self.assertIn(ctype, r.getheader("Content-Type", ""), route)
            if route == "/frame.png":
                self.assertEqual(body[:8], b"\x89PNG\r\n\x1a\n")
            if ctype == "application/json":
                json.loads(body)

        conn.request("GET", "/nope")
        r = conn.getresponse()
        r.read()
        self.assertEqual(r.status, 404)

    def test_binding_is_loopback_only(self):
        """An unauthenticated dev tool must not be on the network."""
        page = "<!doctype html><title>t</title>"
        httpd = serve.bind(serve.make_handler(serve.Server(uib=blob(OPLENV)),
                                              page), 0, False)
        self.addCleanup(httpd.server_close)
        self.assertEqual(httpd.server_address[0], "127.0.0.1")

    def test_input_reports_a_bad_field_rather_than_crashing(self):
        srv = serve.Server(uib=blob(OPLENV))
        with self.assertRaises(KeyError):
            srv.apply({"nonsense": 1})
        with self.assertRaises(KeyError):
            srv.apply({"screen": "no-such-screen"})


class TestState(unittest.TestCase):

    def test_state_names_the_current_screens_focusables_only(self):
        u = blob(MEMCARD)
        srv = serve.Server(uib=u)
        srv.apply({"screen": "saves"})
        got = srv.snapshot()
        saves = serve.screen_of(u, "saves")
        self.assertEqual([f["name"] for f in got["focusables"]],
                         [n["name"] for n in serve.nodes_of(u, saves)])
        self.assertEqual(got["screen"], "saves")
        self.assertEqual(len(got["commands"]), saves["cmd_count"])
        # Neighbours are names, and every one either names a focusable
        # of THIS screen or is null.
        here = {f["name"] for f in got["focusables"]} | {None}
        for f in got["focusables"]:
            for d in ("up", "down", "left", "right"):
                self.assertIn(f[d], here,
                              "%s.%s names something off this screen"
                              % (f["name"], d))

    def test_slot_text_is_per_screen(self):
        u = blob(MEMCARD)
        srv = serve.Server(uib=u)
        srv.apply({"screen": "library"})
        first = srv.snapshot()["slots"][0]["name"]
        srv.apply({"slot": {first: "OVERRIDDEN"}})
        self.assertEqual(srv.snapshot()["slots"][0]["text"], "OVERRIDDEN")
        srv.apply({"screen": "saves"})
        for s in srv.snapshot()["slots"]:
            self.assertNotEqual(s["text"], "OVERRIDDEN",
                                "slot text leaked across screens")


class TestNoNodeNeeded(unittest.TestCase):

    def test_uib_mode_needs_no_node_on_path(self):
        """THE TEST THAT KEEPS THE OPTIONAL DEPENDENCY OPTIONAL.

        The baker has no Node dependency and this feature must not
        quietly give it one. `--uib` skips the compiler entirely, so it
        has to work with node nowhere on PATH.
        """
        import argparse
        if not os.path.exists(OPLENV):
            raise unittest.SkipTest("no blob")
        saved = os.environ.get("PATH")
        saved_layout = os.environ.pop("PS2UI_LAYOUT", None)
        os.environ["PATH"] = tempfile.gettempdir()
        try:
            args = argparse.Namespace(uib=OPLENV, project=None, screen=None,
                                      theme=0)
            srv = serve.build_server(args)
            self.assertIsNotNone(srv.uib)
            self.assertEqual(srv.frame()[:8], b"\x89PNG\r\n\x1a\n")
        finally:
            os.environ["PATH"] = saved
            if saved_layout is not None:
                os.environ["PS2UI_LAYOUT"] = saved_layout


class TestPipelineMatchesTheBuild(unittest.TestCase):

    def test_the_served_blob_is_the_built_blob(self):
        """THE FENCE THAT CAUGHT THE FIRST VERSION OF THE PIPELINE.

        That version assembled the layout argv itself and passed
        --fonts to the compiler but not to the baker, so the IR was
        measured against one font configuration and baked against
        another. check-tutorial.py found it; nothing in this file would
        have. Every other project flag -- mode, canvas, display aspect,
        strict, min-font-size, palettize, the VRAM budget -- was missing
        the same way and silently.

        So the pipeline calls `compile_screens` now, and this asserts
        the only property that keeps it honest: the blob the server
        serves is byte-for-byte the blob `ps2ui build` writes.
        """
        import shutil
        from ps2ui_bake import project
        from ps2ui_bake import ps2ui as front
        src = os.path.join(ROOT, "examples", "memcard")
        if not os.path.exists(os.path.join(src, "ps2ui.json")):
            raise unittest.SkipTest("no memcard project")
        if not (os.environ.get("PS2UI_LAYOUT") or shutil.which("node")):
            raise unittest.SkipTest("no node for the layout stage")

        with tempfile.TemporaryDirectory() as tmp:
            work = os.path.join(tmp, "memcard")
            shutil.copytree(src, work,
                            ignore=shutil.ignore_patterns("build"))
            cfg = os.path.join(work, "ps2ui.json")

            rc = front.main(["build", cfg])
            self.assertEqual(rc, 0)
            with open(os.path.join(work, "build", "ui.uib"), "rb") as fh:
                built = fh.read()

            pipe = serve.BuildPipeline(project.load(cfg))
            result = pipe.build()
            self.assertIsNone(result.error, result.error)
            with open(pipe.uib_path, "rb") as fh:
                served = fh.read()

            self.assertEqual(
                served, built,
                "the server's build diverged from `ps2ui build` -- a "
                "project flag reaches one and not the other")
            self.assertNotEqual(
                os.path.dirname(pipe.uib_path),
                os.path.join(work, "build"),
                "the server built into build/, where a real build's "
                "artifacts live")


class TestImportRule(unittest.TestCase):

    def test_nothing_pulls_serve_in(self):
        """IMPORTS GO ONE WAY, AND THIS IS WHY IT IS A TEST.

        serve.py binds a port and holds an HTTP server. `ps2ui bake` in
        a CI container has no business loading any of that, and the way
        that stops being true is a convenience import somebody adds
        later without thinking about it. Run in a subprocess so this
        test's own import of serve, at the top of this file, cannot
        make it pass.
        """
        import subprocess
        pkg_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        code = (
            "import sys\n"
            "import ps2ui_bake, ps2ui_bake.cli, ps2ui_bake.check\n"
            "import ps2ui_bake.uib, ps2ui_bake.preview, ps2ui_bake.project\n"
            "import ps2ui_bake.ps2ui\n"
            "bad = [m for m in sys.modules if m.endswith('.serve')]\n"
            "print(','.join(bad))\n")
        env = dict(os.environ, PYTHONPATH=pkg_root)
        out = subprocess.run([sys.executable, "-c", code], env=env,
                             capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(out.stdout.strip(), "",
                         "importing the baker pulled in serve.py")


class TestBuildFailure(unittest.TestCase):

    def test_a_broken_build_keeps_the_last_good_blob(self):
        """A watch server that dies on a typo is worse than none."""
        u = blob(OPLENV)
        srv = serve.Server(uib=u)
        good = srv.frame()

        class Failing:
            def build(self):
                return serve.BuildResult(error="layout failed: bad CSS")

            def inputs(self):
                return []

        srv.pipeline = Failing()
        srv.rebuild()
        self.assertIn("bad CSS", srv.snapshot()["error"])
        self.assertEqual(srv.frame(), good,
                         "a failed build blanked the frame")


if __name__ == "__main__":
    unittest.main()
