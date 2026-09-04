"""`ps2ui serve` -- the edit loop, in a browser, driven by arrow keys.

WHY THIS EXISTS. `ps2ui dev` recompiles on every edit and writes a PNG.
Looking at a PNG tells you whether the first frame is right and nothing
else: there is no way to move the focus, no way to reach a second
screen, no way to see the light theme, and no way to try a longer
string in a slot. Everything past "does the initial frame look right"
meant baking to a memory card and booting a console, which is a
twenty-minute loop for a one-line CSS change.

Nothing in this repository bound a port before this file.

THE BROWSER DRAWS NO UI CONTENT, AND THAT IS NOT NEGOTIABLE. Every
pixel comes from `preview.render()` here and reaches the page as PNG
bytes in an <img>. The repository holds three text-layout
implementations to pixel agreement -- a Node measurer, this package's
baker pen and the C runtime's -- and `TestCrossLanguagePen` exists
because keeping them equal is hard. A canvas renderer in the page would
be a fourth pen and an unvalidated one, and `preview.render()` is the
implementation that has been image-diffed against hardware. It is also
the only one that already knows about CLUT quantisation, nine-patch
rasterisation, the baker's glyph advance rounding, streamed textures
and the v7 tint table.

The page may draw dev chrome over the frame -- a dashed magenta focus
rectangle, the title-safe box, a grid -- because none of that is UI
content and all of it is off by default or visually unmistakable.

IMPORTS GO ONE WAY. This module imports `cli`, `project`, `preview` and
`uib`. Nothing imports this module: not `cli`, not `check`, not `uib`,
not the other `ps2ui` subcommands. So `ps2ui build` in a CI container
never loads a line of server code, and the published package gains a
subcommand rather than becoming a thing that ships a web server. Do not
wire them together later.

WHAT THIS DOES NOT DO. It replays the command list faithfully, so it
cannot catch the console diverging from that list. F-048 -- the GS
clear not paying the blended fill rate despite ABE being set -- lived
in a register `runtime/` never writes, and no previewer of any accuracy
would have found it. Nor is runtime visibility previewable:
`preview.render()` has no visibility parameter, so `ps2ui_visible_set`
and the list-windowing APIs are outside what this shows. Both are
stated boundaries rather than oversights.
"""
import argparse
import contextlib
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import threading
import time

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from . import cli
from . import preview
from .project import ProjectError, load, _attr
from .uib import read_uib

PS2UI_NONE = 0xFFFF
OPS = {0: "quad", 1: "texquad", 2: "scissor_push", 3: "scissor_pop"}
ASPECTS = ("framebuffer", "authored", "force-4:3", "force-16:9")

# The frame cache's ceiling. A screen's every focus state is what the
# background warmer fills, and the largest screen in the shipped
# examples has 17 -- so this holds a few screens' worth without ever
# being the reason a rebuild is slow.
CACHE_MAX = 96


# ---------------------------------------------------------------- state

def screen_of(uib, name):
    """The screen record by name, or None."""
    for sc in uib.screens:
        if sc["name"] == name:
            return sc
    return None


def nodes_of(uib, sc):
    """A screen's focus nodes, and nothing else's.

    FOCUS NAMES ARE UNIQUE ONLY WITHIN A SCREEN. `runtime/ps2ui.c` says
    so at the ps2ui_visible_set comment, and the shipped memcard example
    proves it: `nav-games`, `nav-saves` and `nav-settings` are on BOTH
    of its screens, and `data-repeat` makes two screens each using
    `row-{i}` the natural thing to author. A blob-global name scan
    passes every synthetic test and selects the wrong screen's node on
    the first real example, so every lookup in this file goes through
    here.
    """
    return uib.focus[sc["focus_first"]:sc["focus_first"] + sc["focus_count"]]


def slots_of(uib, sc):
    return uib.slots[sc["slot_first"]:sc["slot_first"] + sc["slot_count"]]


class PreviewState:
    """What the page is looking at, in names rather than indices.

    INDICES ARE GLOBAL AND A REBUILD RENUMBERS THEM. Focus indices span
    the whole blob, so a CSS edit that adds one focusable to an earlier
    screen shifts every index after it. State held as an index would
    teleport the selection on every keystroke of an edit; state held as
    a (screen, name) pair survives, and falls back explicitly when the
    name really is gone.
    """

    def __init__(self):
        self.screen_name = None
        self.focus_name = None
        self.theme = 0
        self.aspect = "authored"
        # Keyed per screen, for the same reason focus is: two screens
        # can each have a `row-0-title`.
        self.slot_text = {}
        self.revision = 0

    # -- resolution against a blob -------------------------------------

    def screen(self, uib):
        sc = screen_of(uib, self.screen_name) if self.screen_name else None
        return sc or uib.screens[0]

    def focus_index(self, uib):
        """The current focus as a blob index, resolved within the screen.

        name still present  -> that node
        name gone           -> the screen's own `initial`
        """
        sc = self.screen(uib)
        if self.focus_name:
            for n in nodes_of(uib, sc):
                if n["name"] == self.focus_name:
                    return n["index"]
        return sc["initial"]

    def reconcile(self, uib):
        """Re-anchor to a freshly built blob, keeping what still exists."""
        sc = screen_of(uib, self.screen_name) if self.screen_name else None
        if sc is None:
            sc = uib.screens[0]
            self.screen_name = sc["name"]
        names = {n["name"] for n in nodes_of(uib, sc)}
        if self.focus_name not in names:
            init = [n["name"] for n in nodes_of(uib, sc)
                    if n["index"] == sc["initial"]]
            self.focus_name = init[0] if init else None
        n_theme = max(1, len(uib.themes or ()))
        if not 0 <= self.theme < n_theme:
            self.theme = 0

    # -- mutation -------------------------------------------------------

    def move(self, uib, direction):
        """One D-pad step, with `ps2ui_move`'s edge semantics exactly.

        A move is a no-op when the neighbour is PS2UI_NONE, and also
        when it resolves back to the current node -- both cases are
        `return 0` in runtime/ps2ui.c. Wrap-around is NOT invented here:
        wrapping is a bake-time property of --focus-wrap and is already
        in the edges, so a previewer that wrapped on its own would show
        navigation the console does not have.
        """
        sc = self.screen(uib)
        cur = self.focus_index(uib)
        node = None
        for n in nodes_of(uib, sc):
            if n["index"] == cur:
                node = n
                break
        if node is None:
            return False
        nxt = node.get(direction, PS2UI_NONE)
        if nxt == PS2UI_NONE or nxt == cur:
            return False
        for n in nodes_of(uib, sc):
            if n["index"] == nxt:
                self.focus_name = n["name"]
                return True
        return False

    def set_screen(self, uib, name):
        if screen_of(uib, name) is None:
            raise KeyError(name)
        self.screen_name = name
        self.reconcile(uib)
        return True

    def set_theme(self, uib, n):
        n_theme = max(1, len(uib.themes or ()))
        if not 0 <= n < n_theme:
            raise ValueError(n)
        self.theme = n
        return True

    def set_aspect(self, mode):
        if mode not in ASPECTS:
            raise ValueError(mode)
        self.aspect = mode
        return True

    def set_slots(self, mapping):
        per = self.slot_text.setdefault(self.screen_name, {})
        for k, v in mapping.items():
            if v == "":
                per.pop(k, None)
            else:
                per[str(k)] = str(v)
        return True

    def slots_for(self, screen_name):
        return dict(self.slot_text.get(screen_name) or {})

    # -- the cache key --------------------------------------------------

    def key(self, uib):
        text = self.slots_for(self.screen_name)
        digest = hashlib.sha1(
            json.dumps(text, sort_keys=True).encode("utf-8")).hexdigest()[:12]
        return (self.screen(uib)["name"], self.focus_index(uib), self.theme,
                self.aspect, digest)


# ---------------------------------------------------------------- frames

def render_png(uib, state):
    """One frame, as PNG bytes, in the state's aspect mode."""
    img = preview.render(uib,
                         focus_current=state.focus_index(uib),
                         screen=state.screen(uib)["name"],
                         slot_text=state.slots_for(state.screen_name) or None,
                         theme=state.theme)
    if state.aspect == "authored":
        img = preview.to_display_space(img, uib)
    elif state.aspect in ("force-4:3", "force-16:9"):
        w, h = (4, 3) if state.aspect == "force-4:3" else (16, 9)
        img = img.resize((int(round(img.height * w / h)), img.height))
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


class FrameCache:
    """Rendered frames, keyed by everything that changes one.

    RENDERING IS NOT FAST ENOUGH TO DO PER KEYPRESS. Measured on the
    shipped opl-env blob: 66 ms for the 110-command screen and 218 ms
    for the 694-command one, plus a round trip. 218 ms is past the point
    where arrow keys stop feeling like navigation.

    So the current screen's every focus state is rendered in the
    background after each build -- 3.4 s for the largest screen -- and
    navigation within it is a dict lookup. This is a cache of a pure
    function of (blob, state), so it is dropped wholesale on a rebuild
    and there is no coherence problem to get wrong.
    """

    def __init__(self, limit=CACHE_MAX):
        self.limit = limit
        self.lock = threading.Lock()
        self.frames = {}
        self.order = []

    def clear(self):
        with self.lock:
            self.frames.clear()
            del self.order[:]

    def get_or_render(self, uib, state):
        key = state.key(uib)
        with self.lock:
            hit = self.frames.get(key)
        if hit is not None:
            return hit
        png = render_png(uib, state)
        self.put(key, png)
        return png

    def put(self, key, png):
        with self.lock:
            if key not in self.frames and len(self.order) >= self.limit:
                self.frames.pop(self.order.pop(0), None)
            if key not in self.frames:
                self.order.append(key)
            self.frames[key] = png


# ------------------------------------------------------------- building

class BuildResult:
    def __init__(self, uib=None, warnings=(), error=None):
        self.uib = uib
        self.warnings = list(warnings)
        self.error = error


class BuildPipeline:
    """Sources to a blob, using the same compiler call `ps2ui build` uses.

    NOT A SECOND COPY OF THE BUILD. The first version of this walked
    the screens and assembled the layout argv itself, and immediately
    got it wrong: it passed --fonts to the compiler and not to the
    baker, so the IR was measured against the project's manifest and
    baked against the baker's default, and `check-tutorial.py` caught it
    on the first run with "text would be positioned by one font and
    drawn with another". Every other project flag -- mode, canvas,
    display aspect, strict, min-font-size, palettize, the VRAM budget --
    was missing too, silently.

    So it calls `compile_screens` and mirrors `cmd_build`'s bake argv.
    A flag added to the project cannot now reach the build and miss the
    server.

    OUTPUT GOES TO build/serve/, NEVER build/. `ps2ui build` and every
    example's build.sh write build/, and that is the blob CI verifies. A
    server writing there clobbers artifacts a build just produced, and a
    build clobbers the blob under a live server. `ps2ui dev` already
    took build/dev/ for the same reason. `set_out_override` is what
    moves the intermediates along with the blob -- the same mechanism
    channel6's second build needed.
    """

    def __init__(self, proj):
        self.proj = proj
        proj.set_out_override(os.path.join(proj.build_dir, "serve", "ui.uib"))
        # The server renders its own frames; the build does not need to
        # write PNG siblings nobody reads.
        for key in ("preview", "montage", "previewDisplay"):
            setattr(proj, _attr(key), False)

    @property
    def out_dir(self):
        return self.proj.build_dir

    @property
    def uib_path(self):
        return self.proj.out_path

    def inputs(self):
        """Every file whose mtime should trigger a rebuild."""
        seen = [self.proj.path]
        for screen in self.proj.screens:
            seen.append(screen.html)
            seen.append(screen.css)
            root = os.path.dirname(screen.html)
            for dirpath, _dirs, files in os.walk(root):
                for f in files:
                    if f.endswith((".html", ".css", ".png")):
                        seen.append(os.path.join(dirpath, f))
        return sorted(set(seen))

    def build(self):
        """One full build. Never raises: a failure is a displayable state."""
        from .ps2ui import bake_argv, compile_screens, in_project
        proj = self.proj
        err = io.StringIO()
        try:
            with in_project(proj), contextlib.redirect_stderr(err):
                irs = compile_screens(proj, [])
                rc = cli.main(bake_argv(proj, irs))
        except ProjectError as exc:
            return BuildResult(error="%s\n%s" % (exc, err.getvalue().strip()))
        except Exception as exc:                       # noqa: BLE001
            return BuildResult(error="%s\n%s" % (exc, err.getvalue().strip()))
        if rc != 0:
            return BuildResult(error=err.getvalue().strip() or "bake failed")

        warnings = []
        for screen in proj.screens:
            try:
                with open(proj.ir_path(screen), encoding="utf-8") as fh:
                    for w in json.load(fh).get("warnings", ()):
                        warnings.append({"screen": screen.name, "text": w})
            except (OSError, ValueError):
                pass

        # REPLAY WHAT WE WROTE, NOT WHAT WE MEANT. cli.py does exactly
        # this after baking, and the server inherits the property for
        # free: what the page shows came out of the file the console
        # would load, not out of the IR that produced it.
        try:
            return BuildResult(uib=read_uib(proj.out_path), warnings=warnings)
        except Exception as exc:                       # noqa: BLE001
            return BuildResult(error="the blob did not read back: %s" % exc)


class Server:
    """Everything the routes need, behind one lock."""

    def __init__(self, pipeline=None, uib=None):
        self.pipeline = pipeline
        self.state = PreviewState()
        self.cache = FrameCache()
        self.lock = threading.Lock()
        self.uib = uib
        self.warnings = []
        self.error = None
        self.revision = 0
        self._warm = None
        if uib is not None:
            self.state.reconcile(uib)

    # -- builds ---------------------------------------------------------

    def rebuild(self):
        """Build, and keep the last good blob if it fails."""
        result = self.pipeline.build()
        with self.lock:
            self.error = result.error
            if result.uib is not None:
                self.uib = result.uib
                self.warnings = result.warnings
                self.state.reconcile(result.uib)
                self.cache.clear()
            self.revision += 1
        if result.uib is not None:
            self.warm()
        return result

    def warm(self):
        """Render the current screen's every focus state, off the path."""
        if self._warm is not None and self._warm.is_alive():
            return
        self._warm = threading.Thread(target=self._warm_now, daemon=True)
        self._warm.start()

    def _warm_now(self):
        with self.lock:
            uib, base = self.uib, self.state
        if uib is None:
            return
        sc = base.screen(uib)
        # A REAL SNAPSHOT, NOT A SHARED REFERENCE. `__dict__.update`
        # copies `slot_text` by reference, so the probe's key() and its
        # render() were two separate reads of a dict the request thread
        # mutates -- and a `set_slots` landing between them filed a
        # frame under the key of the text it was NOT rendered with. The
        # window is one render (66-218 ms) inside a warm pass that runs
        # for seconds after every build and every screen switch, and
        # typing in a slot box during it is ordinary use. Under --uib
        # there is no rebuild to drop the cache, so a wrong frame stays
        # wrong for the life of the process. FrameCache's docstring
        # claims a pure function of (blob, state); this is what makes
        # that true.
        frozen = {k: dict(v) for k, v in base.slot_text.items()}
        for node in nodes_of(uib, sc):
            probe = PreviewState()
            probe.__dict__.update(base.__dict__)
            probe.slot_text = frozen
            probe.focus_name = node["name"]
            key = probe.key(uib)
            with self.cache.lock:
                if key in self.cache.frames:
                    continue
            try:
                self.cache.put(key, render_png(uib, probe))
            except Exception:                          # noqa: BLE001
                return

    # -- reads ----------------------------------------------------------

    def frame(self):
        with self.lock:
            uib, st = self.uib, self.state
        return self.cache.get_or_render(uib, st)

    def montage(self):
        with self.lock:
            uib, st = self.uib, self.state
        buf = io.BytesIO()
        preview.montage(uib, screen=st.screen(uib)["name"]).save(buf, "PNG")
        return buf.getvalue()

    def snapshot(self):
        with self.lock:
            uib, st = self.uib, self.state
            err, warn, rev = self.error, list(self.warnings), self.revision
        sc = st.screen(uib)
        nodes = nodes_of(uib, sc)
        by_i = {n["index"]: n["name"] for n in nodes}
        nb = lambda v: (None if v == PS2UI_NONE else by_i.get(v))  # noqa: E731
        recs = uib.records[sc["cmd_first"]:sc["cmd_first"] + sc["cmd_count"]]
        text = st.slots_for(sc["name"])
        dw, dh = preview.display_size(uib)
        cur = st.focus_index(uib)
        return {
            "revision": rev,
            "error": err,
            "screens": [s["name"] for s in uib.screens],
            "screen": sc["name"],
            "themes": max(1, len(uib.themes or ())),
            "theme": st.theme,
            "aspect": st.aspect,
            "aspects": list(ASPECTS),
            "canvas": {"w": uib.canvas_w, "h": uib.canvas_h},
            "display": {"w": dw, "h": dh},
            "display_aspect": list(uib.display_aspect or (4, 3)),
            "focus": by_i.get(cur),
            "focusables": [
                {"name": n["name"], "rect": list(n["rect"]),
                 "up": nb(n["up"]), "down": nb(n["down"]),
                 "left": nb(n["left"]), "right": nb(n["right"])}
                for n in nodes],
            "commands": [
                {"i": i, "op": OPS.get(r.op, r.op), "state": r.state,
                 "focus": nb(r.focus), "rect": [r.x, r.y, r.w, r.h],
                 "rgba": list(r.rgba),
                 "tex": None if r.tex == PS2UI_NONE else r.tex}
                for i, r in enumerate(recs)],
            "slots": [
                {"name": s["name"],
                 "text": text.get(s["name"], s["placeholder"]),
                 "placeholder": s["placeholder"], "capacity": s["capacity"]}
                for s in slots_of(uib, sc)],
            "warnings": warn,
        }

    # -- writes ---------------------------------------------------------

    def apply(self, body):
        with self.lock:
            uib, st = self.uib, self.state
            if "key" in body:
                st.move(uib, str(body["key"]))
            elif "screen" in body:
                st.set_screen(uib, str(body["screen"]))
            elif "theme" in body:
                st.set_theme(uib, int(body["theme"]))
            elif "aspect" in body:
                st.set_aspect(str(body["aspect"]))
            elif "slot" in body:
                st.set_slots(dict(body["slot"]))
            else:
                raise KeyError("no recognised field in %r" % sorted(body))
        if "screen" in body:
            self.warm()
        return self.snapshot()


class Watcher(threading.Thread):
    """Poll mtimes and rebuild.

    Python's stdlib has no fs.watch, so polling is the correct call
    rather than a compromise -- and a new dependency for it (watchdog)
    would be a dependency on every `pip install` of a package whose job
    is IR to blob. The walk is restricted to .html/.css/.png so a large
    assets/ tree stays cheap.
    """

    INTERVAL = 0.2
    DEBOUNCE = 0.12

    def __init__(self, server):
        super().__init__(daemon=True)
        self.server = server
        self.stop = threading.Event()

    def stamps(self):
        out = {}
        for path in self.server.pipeline.inputs():
            try:
                out[path] = os.stat(path).st_mtime_ns
            except OSError:
                out[path] = None
        return out

    def run(self):
        last = self.stamps()
        while not self.stop.wait(self.INTERVAL):
            now = self.stamps()
            if now == last:
                continue
            # Coalesce the burst an editor's save produces before
            # building, the same 120 ms ps2ui-dev.js uses.
            time.sleep(self.DEBOUNCE)
            last = self.stamps()
            try:
                self.server.rebuild()
            except Exception as exc:                   # noqa: BLE001
                with self.server.lock:
                    self.server.error = "watcher: %s" % exc
                    self.server.revision += 1


# ------------------------------------------------------------------ HTTP

def make_handler(server, page):
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *args):                  # noqa: A003
            pass                                       # one line per key is noise

        def send(self, code, body, ctype, cache=True):
            if isinstance(body, str):
                body = body.encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            if not cache:
                self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def json(self, code, obj):
            self.send(code, json.dumps(obj), "application/json", cache=False)

        def do_GET(self):                              # noqa: N802
            route = self.path.split("?", 1)[0]
            try:
                if route == "/":
                    return self.send(200, page, "text/html; charset=utf-8",
                                     cache=False)
                if route == "/frame.png":
                    return self.send(200, server.frame(), "image/png",
                                     cache=False)
                if route == "/montage.png":
                    return self.send(200, server.montage(), "image/png",
                                     cache=False)
                if route == "/state":
                    return self.json(200, server.snapshot())
                if route == "/rev":
                    with server.lock:
                        return self.json(200, {"revision": server.revision})
            except Exception as exc:                   # noqa: BLE001
                return self.json(500, {"error": str(exc)})
            self.json(404, {"error": "no route %r" % route})

        def do_POST(self):                             # noqa: N802
            if self.path.split("?", 1)[0] != "/input":
                return self.json(404, {"error": "no route %r" % self.path})
            try:
                n = int(self.headers.get("Content-Length") or 0)
                body = json.loads(self.rfile.read(n) or b"{}")
                return self.json(200, server.apply(body))
            except (KeyError, ValueError) as exc:
                return self.json(400, {"error": str(exc)})
            except Exception as exc:                   # noqa: BLE001
                return self.json(500, {"error": str(exc)})

    return Handler


def bind(handler, port, wander):
    """127.0.0.1 only, and take the next port when one is busy.

    UNAUTHENTICATED DEV TOOL: it must never listen on 0.0.0.0. Running
    two projects side by side is a normal thing to want, so a busy
    default port moves up rather than printing a traceback -- but an
    EXPLICIT --port fails hard, because a person who named a port meant
    that port.
    """
    for candidate in range(port, port + (20 if wander else 1)):
        try:
            return ThreadingHTTPServer(("127.0.0.1", candidate), handler)
        except OSError:
            if not wander:
                raise
    raise ProjectError("ports %d-%d are all busy" % (port, port + 19))


# ------------------------------------------------------------ entry point

def page_html():
    """The page, from the file beside this module."""
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "serve_page.html"), encoding="utf-8") as fh:
        return fh.read()


def require_node():
    """Probe at STARTUP, not at the first rebuild.

    The baker has no Node dependency and this feature must not quietly
    give it one. A person who installed only the Python half should
    learn that here, in one sentence, rather than after editing a file
    and waiting for a build that cannot happen -- and --uib does not
    probe at all, because it needs no compiler.
    """
    if os.environ.get("PS2UI_LAYOUT") or shutil.which("ps2ui-layout"):
        return
    if shutil.which("node"):
        return
    raise ProjectError(
        "watch mode compiles HTML and CSS, which needs the Node half.\n"
        "  Install it:  npm install -g @ophtml/layout\n"
        "  Or serve a blob you already have, which needs no Node:\n"
        "      ps2ui serve --uib build/ui.uib")


def build_server(args):
    """A Server ready to answer, plus its watcher (or None)."""
    if args.uib:
        srv = Server(uib=read_uib(args.uib))
    else:
        require_node()
        proj = load(args.project)
        srv = Server(pipeline=BuildPipeline(proj))
        result = srv.rebuild()
        if srv.uib is None:
            raise ProjectError("the first build failed, so there is nothing "
                               "to serve:\n%s" % result.error)
    if args.screen:
        try:
            srv.state.set_screen(srv.uib, args.screen)
        except KeyError:
            raise ProjectError(
                "no screen named %r. The blob has: %s"
                % (args.screen, ", ".join(s["name"] for s in srv.uib.screens)))
    if args.theme:
        try:
            srv.state.set_theme(srv.uib, args.theme)
        except ValueError:
            raise ProjectError("no theme %d; the blob has %d"
                               % (args.theme, max(1, len(srv.uib.themes or ()))))
    return srv


def add_arguments(parser):
    parser.add_argument("project", nargs="?", default="ps2ui.json")
    parser.add_argument("--uib", metavar="BLOB",
                        help="serve a pre-baked blob: no Node, no watching")
    parser.add_argument("--port", type=int, default=None,
                        help="default 8080, moving up when it is busy")
    parser.add_argument("--screen", metavar="NAME", help="the screen to open")
    parser.add_argument("--theme", type=int, default=0, help="the theme row")
    parser.add_argument("--no-watch", action="store_true",
                        help="do not rebuild on edits")
    parser.add_argument("--selftest", action="store_true",
                        help="build, serve one of every route, and exit")
    return parser


def selftest(srv, page):
    """Every route once, headless. What CI runs."""
    import http.client
    httpd = bind(make_handler(srv, page), 0, False)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    port = httpd.server_address[1]
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=30)
    ok = 0
    try:
        for route, ctype in (("/", "text/html"), ("/frame.png", "image/png"),
                             ("/state", "application/json"),
                             ("/rev", "application/json")):
            conn.request("GET", route)
            r = conn.getresponse()
            body = r.read()
            assert r.status == 200, "%s -> %d" % (route, r.status)
            assert ctype in r.getheader("Content-Type", ""), route
            if route == "/frame.png":
                assert body[:8] == b"\x89PNG\r\n\x1a\n", "not a PNG"
            if ctype == "application/json":
                json.loads(body)
            print("ok - %s %d bytes" % (route, len(body)), file=sys.stderr)
            ok += 1
        conn.request("GET", "/nope")
        r = conn.getresponse()
        r.read()
        assert r.status == 404, "an unknown route answered %d" % r.status
        print("ok - an unknown route is 404", file=sys.stderr)
        ok += 1

        # THE ASSERTION THIS WHOLE TOOL RESTS ON, and the reason it is
        # in the CLI rather than only in the test suite: a person who
        # doubts the page can run one command and find out. The frame
        # the server serves must be the frame `--preview` writes. If
        # they ever differ, every judgement made at the browser is about
        # something the console will not draw.
        with srv.lock:
            uib, st = srv.uib, srv.state
        was = st.aspect
        st.aspect = "framebuffer"
        try:
            served = srv.frame()
        finally:
            st.aspect = was
        sc = st.screen(uib)
        buf = io.BytesIO()
        preview.render(uib, focus_current=st.focus_index(uib),
                       screen=sc["name"],
                       slot_text=st.slots_for(sc["name"]) or None,
                       theme=st.theme).save(buf, "PNG")
        assert served == buf.getvalue(), (
            "the served frame is NOT what --preview writes; the server "
            "has diverged from the baker")
        print("ok - the frame is byte-identical to --preview", file=sys.stderr)
        ok += 1
    finally:
        conn.close()
        httpd.shutdown()
    print("PASS: %d route(s)" % ok, file=sys.stderr)
    return 0


def run(args):
    """Serve, given already-parsed arguments. `ps2ui serve` calls this."""
    try:
        srv = build_server(args)
    except ProjectError as exc:
        print("ps2ui serve: %s" % exc, file=sys.stderr)
        return 1
    page = page_html()
    if args.selftest:
        return selftest(srv, page)

    watcher = None
    if srv.pipeline is not None and not args.no_watch:
        watcher = Watcher(srv)
        watcher.start()
    srv.warm()

    wander = args.port is None
    httpd = bind(make_handler(srv, page), args.port or 8080, wander)
    url = "http://127.0.0.1:%d/" % httpd.server_address[1]
    print("ps2ui serve: %s -- ctrl-c to stop" % url, file=sys.stderr)
    if watcher is None and srv.pipeline is not None:
        print("  (not watching)", file=sys.stderr)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("", file=sys.stderr)
    finally:
        if watcher is not None:
            watcher.stop.set()
    return 0


def main(argv=None):
    ap = add_arguments(argparse.ArgumentParser(
        prog="ps2ui-serve",
        description="Preview a ps2ui project in a browser."))
    return run(ap.parse_args(argv))


if __name__ == "__main__":
    sys.exit(main())
