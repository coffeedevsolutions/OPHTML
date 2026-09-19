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
# THE SAME FONT ANSWER test_baker USES, IMPORTED RATHER THAN
# RESTATED. These build- and dev-driving tests hand the CLI a
# project whose fonts come from fonts/fonts.json, so on a
# machine with no DejaVu they fail exactly as test_baker's did.
from fonts_available import TTF, require_ttf  # noqa: E402,F401

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))
MEMCARD = os.path.join(ROOT, "examples", "memcard", "build", "ui.uib")
OPLENV = os.path.join(ROOT, "examples", "opl-env", "build", "ui.uib")


def blob(path):
    """A shipped example's blob, or a skip -- unless CI says otherwise.

    A SKIP THAT NOBODY SEES IS NOT COVERAGE, AND THIS FILE HAD IT.
    ci.yml ran the baker suite BEFORE the three example builds, so
    twenty of this file's twenty-one tests skipped there: every
    navigation, focus-name, screen, theme, frame and route test -- all
    of the state machine this module's docstring calls the thing worth
    fencing. They passed locally and executed nowhere.

    The step has moved below the builds. This variable is the guard on
    that ordering: with it set, a missing blob is a FAILURE naming the
    step that should have produced it, so putting the suite back above
    the builds breaks CI loudly instead of quietly going green. The
    same tripwire, and the same wording, as PS2UI_REQUIRE_CROSSCHECK --
    which exists because this exact thing happened once before.
    """
    if not os.path.exists(path):
        rel = os.path.relpath(path, ROOT)
        if os.environ.get("PS2UI_REQUIRE_EXAMPLES"):
            raise AssertionError(
                "no blob at %s, and PS2UI_REQUIRE_EXAMPLES is set. This "
                "suite must run AFTER the example builds; if it did not, "
                "twenty tests in this file just checked nothing." % rel)
        raise unittest.SkipTest("no blob at %s; run its build.sh" % rel)
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

    def test_every_part_of_the_cache_key_discriminates(self):
        """IDEMPOTENCE IS NOT DISCRIMINATION, and the test above only
        checks the first.

        It calls frame() twice with nothing changed in between, so it
        passes for ANY key -- including a constant. Four of the five key
        components could be dropped with the whole suite green: the page
        would serve the wrong screen's frame, the wrong focus highlight,
        the wrong theme or stale slot text, and nothing would say so.
        The one that was covered was covered incidentally, by a test
        written to check that the forced aspects differ.

        So each component gets a mutation of its own: change exactly
        one, and the frame must change with it.
        """
        u = blob(OPLENV)
        srv = serve.Server(uib=u)
        srv.apply({"screen": "library"})
        base = srv.frame()

        def differs(what, mutate, undo):
            mutate()
            try:
                self.assertNotEqual(
                    srv.frame(), base,
                    "changing %s did not change the frame -- the cache "
                    "key does not include it" % what)
            finally:
                undo()

        first = srv.state.focus_name
        moved = srv.state.move(u, "down") or srv.state.move(u, "right")
        self.assertTrue(moved, "library has no edge to move along")
        after = srv.state.focus_name
        srv.state.focus_name = first
        differs("the focus", lambda: setattr(srv.state, "focus_name", after),
                lambda: setattr(srv.state, "focus_name", first))

        differs("the screen", lambda: srv.apply({"screen": "confirm"}),
                lambda: srv.apply({"screen": "library"}))

        # AND THE ONE COMPONENT THIS CANNOT FALSIFY, SAID OUT LOUD.
        # Replacing the screen name in the key with a constant leaves
        # the suite green, and the reason is not a missing assertion:
        # focus indices are BLOB-GLOBAL, so the focus component already
        # names the screen. The screen name is kept anyway, because a
        # key that is correct only via an invariant nobody stated is a
        # key that breaks when the invariant does -- two screens with
        # no focusables at all would share `initial` and collide.
        #
        # So assert the invariant instead of pretending to a fence.
        seen = {}
        for sc in u.screens:
            for n in serve.nodes_of(u, sc):
                seen.setdefault(n["index"], []).append(sc["name"])
        shared = {i: names for i, names in seen.items() if len(names) > 1}
        self.assertEqual(shared, {},
                         "focus indices are no longer blob-unique, so the "
                         "screen name in the cache key is now load-bearing "
                         "and needs a mutation test of its own")

        n_theme = max(1, len(u.themes or ()))
        if n_theme > 1:
            differs("the theme", lambda: srv.apply({"theme": 1}),
                    lambda: srv.apply({"theme": 0}))

        slot = srv.snapshot()["slots"][0]["name"]
        differs("slot text",
                lambda: srv.apply({"slot": {slot: "A DIFFERENT STRING"}}),
                lambda: srv.apply({"slot": {slot: ""}}))

        differs("the aspect", lambda: srv.apply({"aspect": "force-16:9"}),
                lambda: srv.apply({"aspect": "authored"}))

    def test_the_warm_thread_cannot_file_a_frame_under_a_stale_key(self):
        """THE PROBE'S SNAPSHOT HAS TO BE ONE.

        `probe.__dict__.update(base.__dict__)` copies slot_text by
        REFERENCE, so key() and render() became two reads of a dict the
        request thread mutates -- and a slot edit landing between them
        files a frame under the key of text it was not rendered with.
        Under --uib nothing ever drops the cache, so it stays wrong.
        """
        u = blob(OPLENV)
        srv = serve.Server(uib=u)
        srv.apply({"screen": "library"})
        slot = srv.snapshot()["slots"][0]["name"]
        srv.apply({"slot": {slot: "BEFORE"}})

        # What _warm_now does, with a mutation in the window between
        # taking the key and rendering the frame.
        with srv.lock:
            base = srv.state
        frozen = {k: dict(v) for k, v in base.slot_text.items()}
        probe = serve.PreviewState()
        probe.__dict__.update(base.__dict__)
        probe.slot_text = frozen
        key = probe.key(u)
        srv.apply({"slot": {slot: "AFTER"}})       # the racing edit
        png = serve.render_png(u, probe)

        srv.apply({"slot": {slot: "BEFORE"}})
        self.assertEqual(key, srv.state.key(u))
        self.assertEqual(png, srv.frame(),
                         "the warm thread rendered text other than the "
                         "one its key names")

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

    def test_a_busy_explicit_port_is_a_message_and_the_default_wanders(self):
        """B18: the refusal was right; the traceback was not.

        Naming a port means that port, so a busy one has to fail --
        but it failed as a bare OSError out of ThreadingHTTPServer,
        "[Errno 98] Address already in use" and a stack, which names
        neither the port nor the fact that the refusal is deliberate.
        The second half of this test is the behaviour that must NOT
        change with the reporting: with no --port, a busy 8080 still
        moves up.

        NO BLOB, DELIBERATELY. Every other test in this file takes one
        of the shipped examples and SKIPS when it has not been built,
        which is right for them and wrong for this one: `bind` takes a
        handler class and never asks what it serves, so requiring a
        blob here would make B18's only unit fence disappear in a
        fresh clone -- silently, inside an `OK`. Review of #157 found
        it that way round, reading a skipped fence as a sabotage that
        got through.
        """
        import socket
        from http.server import BaseHTTPRequestHandler
        handler = BaseHTTPRequestHandler

        held = socket.socket()
        self.addCleanup(held.close)
        held.bind(("127.0.0.1", 0))
        held.listen(1)
        busy = held.getsockname()[1]

        with self.assertRaises(serve.ProjectError) as cm:
            serve.bind(handler, busy, False)
        msg = str(cm.exception)
        self.assertIn("port %d is already in use" % busy, msg)
        self.assertIn("not moved", msg)

        # And the wandering default steps over the same busy port
        # rather than refusing -- the deliberate difference between
        # the two, which the help text now words as the DEFAULT's
        # property rather than the flag's.
        httpd = serve.bind(handler, busy, True)
        self.addCleanup(httpd.server_close)
        self.assertNotEqual(httpd.server_address[1], busy)

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


@unittest.skipIf(TTF is None, "no DejaVu; fonts/fonts.json lists the paths looked in")
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


class TestPackaging(unittest.TestCase):

    def test_the_page_is_in_the_wheel(self):
        """THE COMMENT BESIDE package-data WAS RIGHT AND UNENFORCED.

        It says removing the declaration leaves `ps2ui serve` working in
        a checkout and raising FileNotFoundError for anyone who
        installed the package, "and nothing in the tree would have said
        so". That was still true of removing the declaration: the whole
        suite stayed green. Six lines make it a fact.
        """
        import shutil
        import subprocess
        pkg = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if not os.path.exists(os.path.join(pkg, "pyproject.toml")):
            raise unittest.SkipTest("not a source checkout")

        # `build_py` rather than a whole wheel: it is the step that
        # decides what package DATA gets copied, which is the thing
        # under test, and this container's setuptools cannot complete a
        # wheel at all (a Debian install_layout patch). A fence that
        # skips is the same nothing as no fence, so it runs the step it
        # can run rather than the one that reads better.
        with tempfile.TemporaryDirectory() as tmp:
            work = os.path.join(tmp, "baker")
            out = os.path.join(tmp, "lib")
            shutil.copytree(pkg, work,
                            ignore=shutil.ignore_patterns(
                                "build", "dist", "*.egg-info", "__pycache__"))
            done = subprocess.run(
                [sys.executable, "-c", "import setuptools; setuptools.setup()",
                 "build_py", "--build-lib", out],
                cwd=work, capture_output=True, text=True)
            self.assertEqual(done.returncode, 0,
                             "build_py failed: %s" % done.stderr[-400:])
            staged = os.path.join(out, "ps2ui_bake")
            self.assertTrue(os.path.exists(os.path.join(staged, "serve.py")),
                            "build_py staged no package at all, so the "
                            "assertion below would pass vacuously")
            self.assertTrue(
                os.path.exists(os.path.join(staged, "serve_page.html")),
                "serve_page.html is not staged into the distribution; "
                "`ps2ui serve` would raise FileNotFoundError once "
                "installed, and only for people who installed it")

    def test_watch_mode_refuses_without_node(self):
        """require_node() is called, not merely defined.

        Deleting the call left everything green: the failure would then
        be a layout subprocess that cannot spawn, minutes later and in
        someone else's words.
        """
        import argparse
        saved_path = os.environ.get("PATH")
        saved_layout = os.environ.pop("PS2UI_LAYOUT", None)
        os.environ["PATH"] = tempfile.gettempdir()
        try:
            args = argparse.Namespace(uib=None, project="ps2ui.json",
                                      screen=None, theme=0)
            with self.assertRaises(serve.ProjectError) as cm:
                serve.build_server(args)
            self.assertIn("Node", str(cm.exception))
            self.assertIn("--uib", str(cm.exception),
                          "the error must name the path that still works")
        finally:
            os.environ["PATH"] = saved_path
            if saved_layout is not None:
                os.environ["PS2UI_LAYOUT"] = saved_layout


@unittest.skipIf(TTF is None, "no DejaVu; fonts/fonts.json lists the paths looked in")
class TestDevAgreesWithBuild(unittest.TestCase):

    def test_dev_compiles_a_screen_the_way_build_does(self):
        """TWO PREVIEW PATHS FOR ONE PROJECT MUST NOT DISAGREE.

        `ps2ui serve` reaches compile_screens, so it forwards every
        project setting. `cmd_dev` forwarded --fonts alone, so on
        channel6 -- whose probe screen sets focusWrap -- dev produced a
        screen with no navigation at all, and on opl-env, which sets
        minFontSize 11, it printed 88 warnings the build does not.
        """
        import shutil
        import subprocess
        from ps2ui_bake import ps2ui as front
        src = os.path.join(ROOT, "examples", "channel6")
        if not os.path.exists(os.path.join(src, "ps2ui.json")):
            raise unittest.SkipTest("no channel6 project")
        if not (os.environ.get("PS2UI_LAYOUT") or shutil.which("node")):
            raise unittest.SkipTest("no node for the layout stage")

        with tempfile.TemporaryDirectory() as tmp:
            work = os.path.join(tmp, "channel6")
            shutil.copytree(src, work,
                            ignore=shutil.ignore_patterns("build"))
            cfg = os.path.join(work, "ps2ui.json")
            self.assertEqual(front.main(["build", cfg]), 0)
            rc = subprocess.run(
                [sys.executable, "-m", "ps2ui_bake.ps2ui", "dev", cfg,
                 "--screen", "probe", "--once"],
                capture_output=True, text=True,
                env=dict(os.environ, PYTHONPATH=os.path.dirname(
                    os.path.dirname(os.path.abspath(__file__)))))
            self.assertEqual(rc.returncode, 0, rc.stderr)

            def nodes(path):
                with open(path, encoding="utf-8") as fh:
                    return [n.get("name")
                            for n in json.load(fh)["focus"]["nodes"]]

            built = nodes(os.path.join(work, "build", "probe.json"))
            deved = nodes(os.path.join(work, "build", "dev", "probe.json"))
            self.assertTrue(built, "the build produced no focusables")
            self.assertEqual(deved, built,
                             "ps2ui dev compiled the screen differently "
                             "from ps2ui build")

    def test_dev_applies_strict_and_min_font_size_like_build(self):
        """THE FORWARDED FLAGS HAVE TO LAND, NOT JUST BE SENT.

        cmd_dev forwarded --strict and --min-font-size, and ps2ui-dev
        accepted both and read neither: it set options.strict and
        options.minFontSize while the compiler takes lint overrides
        from options.lint only. So `ps2ui dev` on opl-env, which sets
        minFontSize 11 and strict, printed 44 warnings at the 14px
        floor and exited 0 where `ps2ui build` printed none. The
        warning count on the `built in` line is the observable.
        """
        import re
        import shutil
        import subprocess
        from ps2ui_bake import ps2ui as front
        src = os.path.join(ROOT, "examples", "opl-env")
        if not os.path.exists(os.path.join(src, "ps2ui.json")):
            raise unittest.SkipTest("no opl-env project")
        if not (os.environ.get("PS2UI_LAYOUT") or shutil.which("node")):
            raise unittest.SkipTest("no node for the layout stage")

        with tempfile.TemporaryDirectory() as tmp:
            # Two screens borrow a cover from channel6 by a path that
            # climbs to the repository root, so the copy keeps the
            # examples/<name> shape and brings that one asset directory.
            work = os.path.join(tmp, "examples", "opl-env")
            shutil.copytree(src, work,
                            ignore=shutil.ignore_patterns("build"))
            shutil.copytree(
                os.path.join(ROOT, "examples", "channel6", "ui", "assets"),
                os.path.join(tmp, "examples", "channel6", "ui", "assets"))
            cfg = os.path.join(work, "ps2ui.json")
            with open(cfg, encoding="utf-8") as fh:
                project = json.load(fh)
            self.assertTrue(project.get("strict"),
                            "opl-env must set strict for this to mean anything")
            self.assertEqual(project.get("minFontSize"), 11)
            self.assertEqual(front.main(["build", cfg]), 0)
            rc = subprocess.run(
                [sys.executable, "-m", "ps2ui_bake.ps2ui", "dev", cfg,
                 "--screen", "library", "--once"],
                capture_output=True, text=True,
                env=dict(os.environ, PYTHONPATH=os.path.dirname(
                    os.path.dirname(os.path.abspath(__file__)))))
            self.assertEqual(rc.returncode, 0, rc.stderr)
            plain = re.sub(r"\x1b\[[0-9;]*m", "", rc.stderr)
            m = re.search(r"built in \d+ms .*?, (\d+) warnings?", plain)
            self.assertIsNotNone(m, rc.stderr)
            self.assertEqual(int(m.group(1)), 0,
                             "ps2ui dev warned where ps2ui build did not:\n"
                             + rc.stderr)


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
            "import ps2ui_bake.ps2ui, contextlib, io\n"
            # CALLING main() IS THE POINT. It builds every subparser
            # before it dispatches, so an import there runs on every
            # invocation -- which is exactly how `ps2ui build --help`
            # came to pull in serve, http.server, socketserver, socket,
            # ssl and email while three places in the tree claimed it
            # loaded no server code. Importing the module and stopping
            # reported nothing and passed.
            "try:\n"
            "    with contextlib.redirect_stdout(io.StringIO()):\n"
            "        ps2ui_bake.ps2ui.main(['build', '--help'])\n"
            "except SystemExit:\n"
            "    pass\n"
            "bad = [m for m in sys.modules if m.endswith('.serve')]\n"
            "bad += [m for m in ('http.server', 'socketserver', 'ssl')\n"
            "        if m in sys.modules]\n"
            "print(','.join(bad))\n")
        env = dict(os.environ, PYTHONPATH=pkg_root)
        out = subprocess.run([sys.executable, "-c", code], env=env,
                             capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(out.stdout.strip(), "",
                         "importing the baker pulled in serve.py")


class TestHelpAgreement(unittest.TestCase):

    def help_from(self, parser_help):
        """The part of a --help that is not the program's own name."""
        return parser_help[parser_help.index("positional arguments:"):]

    def test_both_ways_of_saying_serve_print_the_same_help(self):
        """ps2ui.py RESTATES this parser instead of importing serve.

        That buys the deferred import TestImportRule fences, and it
        costs a second copy of every help string. B18's wording fix
        landed on serve.add_arguments first and `ps2ui serve --help`
        -- the spelling the documentation teaches, and the one the
        report came from -- went on printing the old sentence, so the
        flag still promised what it does not do. The duplication is
        deliberate; drifting apart is not.
        """
        import argparse
        import contextlib
        from ps2ui_bake import ps2ui

        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            with self.assertRaises(SystemExit):
                ps2ui.main(["serve", "--help"])
        umbrella = self.help_from(out.getvalue())

        standalone = self.help_from(serve.add_arguments(
            argparse.ArgumentParser(prog="ps2ui-serve")).format_help())

        self.assertEqual(umbrella, standalone,
                         "`ps2ui serve --help` and `ps2ui-serve --help` "
                         "describe the same command differently")


class TestBusyPortIsAMessage(unittest.TestCase):

    def refuse_on(self, module, port):
        """Run one entry point against a held port and hand back the run.

        `ps2ui_bake.ps2ui` takes the subcommand; `ps2ui_bake.serve` is
        the command. Everything after that is the same command line.
        """
        import subprocess
        pkg_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        argv = [sys.executable, "-m", module]
        if module.endswith(".ps2ui"):
            argv.append("serve")
        argv += ["--uib", OPLENV, "--port", str(port), "--no-watch"]
        return subprocess.run(argv,
                              env=dict(os.environ, PYTHONPATH=pkg_root),
                              capture_output=True, text=True, timeout=120)

    def test_neither_entry_point_prints_a_traceback_for_a_busy_port(self):
        """B18, END TO END, because bind() alone was not the whole path.

        run() wrapped build_server in the `ps2ui serve: ` handler and
        left the bind call outside it, so both of bind's refusals
        escaped: under `ps2ui serve` the umbrella caught them and
        printed `ps2ui: `, against a Diagnostics page that has always
        said `ps2ui serve: ports <a>-<b> are all busy`, and under
        `python -m ps2ui_bake.serve` there is no handler at all and
        they reached the terminal as a traceback. A ProjectError
        raised where nothing catches it is still a traceback, which
        is what this row was about.
        """
        import socket
        blob(OPLENV)                       # skip like the rest of the file

        held = socket.socket()
        self.addCleanup(held.close)
        held.bind(("127.0.0.1", 0))
        held.listen(1)
        port = held.getsockname()[1]

        for module in ("ps2ui_bake.ps2ui", "ps2ui_bake.serve"):
            out = self.refuse_on(module, port)
            self.assertEqual(out.returncode, 1, out.stderr)
            self.assertNotIn("Traceback", out.stderr, module)
            self.assertIn("ps2ui serve: port %d is already in use" % port,
                          out.stderr, module)


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
