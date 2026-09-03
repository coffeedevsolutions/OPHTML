"""`ps2ui.json` -- what a project is, so a build is one command.

WHY THIS EXISTS. Every example in this repository carried its own
`build.sh`, and all four were the same shape written four times:
compile each screen against a shared stylesheet, bake the results into
one blob, write a preview. The differences were flags. A newcomer
following the tutorial ran seven commands and had to know that
`--fonts` means the same thing in two tools and does not exist in the
third.

So the shape becomes a file, and the file is deliberately small. The
only required keys are the ones with no sensible default:

    {
      "screens": ["ui/library.html", "ui/detail.html"],
      "css": "ui/app.css"
    }

Everything else has one: the blob lands in `build/ui.uib`, a preview
beside it, fonts from `fonts/fonts.json` next to the project file.

WHAT IS DELIBERATELY NOT HERE. Build variants. channel6 bakes a second
blob at 16:9 from the same sources, and the obvious move is a
`variants` block -- but a second blob is a second build, and
`ps2ui build --mode ntsc16x9 -o build/ui-16x9.uib` says so in one line
without a nested dialect anyone has to learn. The file describes ONE
blob. Everything a second blob needs differently is a flag.

Paths resolve relative to the project file, not the working directory,
so `ps2ui build path/to/ps2ui.json` behaves the same from anywhere.
"""
import json
import os

# Keys a project may set, with their defaults. Anything else is a typo
# and is refused by name -- the same rule the layout compiler now
# applies to `data-` attributes, for the same reason: a silently
# ignored key is a setting the author believes is in effect.
DEFAULTS = {
    "screens": None,          # required
    "css": None,              # required
    "fonts": None,            # default: fonts/fonts.json beside the project
    "out": "build/ui.uib",
    "preview": "build/preview.png",
    "montage": None,
    "previewDisplay": None,
    "mode": None,
    "canvas": None,
    "displayAspect": None,
    "strict": False,
    "minFontSize": None,
    "focusWrap": False,
    "palettizeImages": False,
    "vramBudget": None,
}

# Per-screen keys. A screen is usually just a path; an object is for
# the one screen that needs something the others do not.
SCREEN_DEFAULTS = {"html": None, "css": None, "focusWrap": None}


class ProjectError(Exception):
    """Something a person can fix, reported without a traceback."""


class Screen:
    __slots__ = ("html", "css", "focus_wrap", "name")

    def __init__(self, html, css, focus_wrap, name):
        self.html, self.css = html, css
        self.focus_wrap, self.name = focus_wrap, name


class Project:
    """A loaded ps2ui.json, with every path already absolute."""

    def __init__(self, path, data):
        self.path = path
        self.root = os.path.dirname(os.path.abspath(path))
        for key, default in DEFAULTS.items():
            setattr(self, _attr(key), data.get(key, default))
        self.screens = [self._screen(s, i)
                        for i, s in enumerate(data["screens"])]

    def _abs(self, rel):
        return None if rel is None else os.path.join(self.root, rel)

    def _screen(self, spec, index):
        if isinstance(spec, str):
            spec = {"html": spec}
        if not isinstance(spec, dict):
            raise ProjectError(
                "screens[%d] is %r; a screen is a path, or an object with "
                "\"html\" and optionally \"css\" or \"focusWrap\""
                % (index, spec))
        unknown = sorted(set(spec) - set(SCREEN_DEFAULTS))
        if unknown:
            raise ProjectError(
                "screens[%d] has unknown key(s) %s; a screen takes %s"
                % (index, ", ".join(repr(k) for k in unknown),
                   ", ".join(sorted(SCREEN_DEFAULTS))))
        html = spec.get("html")
        if not html:
            raise ProjectError("screens[%d] has no \"html\"" % index)
        css = spec.get("css", self.css)
        if not css:
            raise ProjectError(
                "screens[%d] (%s) has no stylesheet: set \"css\" at the top "
                "level for every screen, or on this one" % (index, html))
        focus_wrap = spec.get("focusWrap")
        return Screen(
            self._abs(html), self._abs(css),
            self.focus_wrap if focus_wrap is None else focus_wrap,
            os.path.splitext(os.path.basename(html))[0])

    # Absolute paths for everything the build writes or reads.
    @property
    def out_path(self):
        return self._abs(self.out)

    @property
    def build_dir(self):
        return os.path.dirname(self.out_path)

    @property
    def fonts_path(self):
        """Explicit, else fonts/fonts.json beside the project, else None.

        None means "let the baker apply its own default and say its own
        thing if that is missing too" -- one message about fonts, in the
        place that already knows how to write it.
        """
        if self.fonts:
            return self._abs(self.fonts)
        beside = self._abs(os.path.join("fonts", "fonts.json"))
        return beside if os.path.exists(beside) else None

    def preview_path(self, key):
        value = getattr(self, _attr(key))
        return None if value in (None, False) else self._abs(value)

    # A SECOND BUILD OF ONE PROJECT MOVES ITS WHOLE BUILD, not just the
    # blob. Treating `-o` as "the blob moves, everything else stays"
    # made channel6's 16:9 build overwrite the 4:3 build's intermediate
    # JSON and its display preview, and -- because a blob's screen
    # names are the IR file stems -- silently renamed its screens from
    # games-16x9/probe-16x9 to games/probe.
    #
    # So an overridden output carries its suffix down to the
    # intermediates: `-o build/ui-16x9.uib` writes build/games-16x9.json,
    # which is what the hand-written build.sh did before there was a
    # project file, and what keeps the two builds from standing on each
    # other. The previews take the same treatment through explicit
    # flags, because their names are documented and a derived one would
    # have to guess where the suffix goes.
    ir_suffix = ""

    def ir_path(self, screen):
        return os.path.join(self.build_dir,
                            screen.name + self.ir_suffix + ".json")

    def set_out_override(self, out):
        """Point the build at a different blob, and move its
        intermediates with it."""
        base = os.path.splitext(os.path.basename(self.out))[0]
        new = os.path.splitext(os.path.basename(out))[0]
        self.out = out
        if new == base:
            self.ir_suffix = ""
        elif new.startswith(base):
            self.ir_suffix = new[len(base):]
        else:
            # No shared stem to extend, so there is no suffix to infer.
            # Use the whole name rather than guess: two builds that
            # share nothing must still not share intermediates.
            self.ir_suffix = "-" + new


def _attr(key):
    """previewDisplay -> preview_display, so JSON reads as JSON."""
    out = []
    for ch in key:
        if ch.isupper():
            out.append("_")
        out.append(ch.lower())
    return "".join(out)


def load(path):
    """Read and validate a ps2ui.json. Raises ProjectError, never a
    traceback: every failure here is a person's typo."""
    if os.path.isdir(path):
        path = os.path.join(path, "ps2ui.json")
    if not os.path.exists(path):
        raise ProjectError(
            "%s: no such project file.\n"
            "  A ps2ui.json needs two keys:\n"
            "    { \"screens\": [\"ui/library.html\"], \"css\": \"ui/app.css\" }\n"
            "  Everything else has a default: the blob lands in "
            "build/ui.uib with a preview beside it." % path)
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except json.JSONDecodeError as exc:
        raise ProjectError("%s: not valid JSON -- %s" % (path, exc))
    if not isinstance(data, dict):
        raise ProjectError("%s: the top level must be an object" % path)

    unknown = sorted(set(data) - set(DEFAULTS))
    if unknown:
        raise ProjectError(
            "%s: unknown key(s) %s.\n  A project takes: %s"
            % (path, ", ".join(repr(k) for k in unknown),
               ", ".join(sorted(DEFAULTS))))
    for required in ("screens", "css"):
        if required == "css":
            # Satisfied per-screen too; _screen says so if neither.
            continue
        if not data.get(required):
            raise ProjectError(
                "%s: \"%s\" is required and must not be empty" % (path, required))
    if not isinstance(data["screens"], list):
        raise ProjectError("%s: \"screens\" must be a list" % path)
    return Project(path, data)
