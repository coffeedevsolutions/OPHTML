"""`ps2ui` -- one front door over a toolchain that had three.

WHY THIS EXISTS. Before this, building a UI meant `ps2ui-layout` once
per screen, then `ps2ui-bake` over the results, then `ps2ui-check` over
the blob -- three tools, three argument shapes, and `--fonts` meaning
the same thing in two of them and absent from the third. Every example
in this repository wrapped that in its own `build.sh`, and all four
were the same script with different flags.

    ps2ui build          compile every screen, bake one blob, preview it
    ps2ui check          validate the blob the project builds
    ps2ui fontgen        metrics from a TTF, both faces, one command
    ps2ui dev            rebuild on every edit
    ps2ui serve          the same loop, navigable, in a browser

FINDING THE OTHER HALF. The layout compiler is a Node package, so
`build` has to reach out of this process to run it. It looks in three
places, in order, and says what to install when none of them has it:
$PS2UI_LAYOUT, then `ps2ui-layout` on PATH, then the checkout this file
might be sitting in. That last one is the same repo-relative path the
font default used, and it is a CANDIDATE for the same reason: it exists
for the people who have the repository and must not be assumed by
anyone else.
"""
import argparse
import contextlib
import json
import os
import shutil
import subprocess
import sys

from . import __version__
from .project import ProjectError, load


def layout_command():
    """How to invoke ps2ui-layout, or a message saying how to get it."""
    override = os.environ.get("PS2UI_LAYOUT")
    if override:
        return override.split()
    found = shutil.which("ps2ui-layout")
    if found:
        return [found]
    # The checkout case. Same shape as the font default: a candidate,
    # never an assumption -- `../../../packages/layout` is the repo in a
    # clone and nothing at all in an installed package.
    here = os.path.dirname(os.path.abspath(__file__))
    local = os.path.normpath(os.path.join(
        here, "..", "..", "layout", "bin", "ps2ui-layout.js"))
    if os.path.exists(local) and shutil.which("node"):
        return [shutil.which("node"), local]
    raise ProjectError(
        "cannot find ps2ui-layout, which compiles the HTML and CSS.\n"
        "  Install it:      npm install -g @ophtml/layout\n"
        "  Or point at it:  PS2UI_LAYOUT='node /path/to/ps2ui-layout.js'\n"
        "  (ps2ui-bake is the Python half and is already here; the "
        "compiler is the Node half.)")


@contextlib.contextmanager
def in_project(proj):
    """Run from the project root, so every path printed is relative to it.

    "Every path is relative to the project" has to be true of the
    OUTPUT too, or the tool answers a question nobody asked: the first
    version printed `/tmp/ps2ui-tutorial-gfzxb9v1/build/ui.uib` where
    the three tools it replaced printed `build/ui.uib`. The tutorial
    caught it, because a machine-specific absolute path is not
    something a document can quote.
    """
    prev = os.getcwd()
    os.chdir(proj.root)
    try:
        yield
    finally:
        os.chdir(prev)


def shown(path):
    """A constructed path, spelled the way every document here spells one.

    ONE DOCUMENTED STRING HAS TO BE TRUE ON THREE PLATFORMS. The
    tutorial asserts eight lines carrying a path -- three from
    `ps2ui fontgen`, four from `ps2ui build`, one from `ps2ui check`
    -- among them:

        ps2ui-fontgen: 115 glyphs, 284 kern pairs -> fonts/default.metrics.json
        ps2ui-layout: 14 paint commands, 6 focusables -> build/library.json
        ps2ui-bake: 1 screen(s), ... -> build/ui.uib

    and on Windows os.path.join and os.path.relpath spell all eight
    with a backslash. A document cannot assert both spellings, and the
    alternative -- teaching the checker to compare separator-insensitively
    -- buys a green leg for a narrower claim than the one it appears to
    certify: it would stop reading the separator anywhere, including
    where a real difference lives.

    WHY THE WRAPPER AND NOT THE TOOLS. ps2ui-layout, ps2ui-bake and
    ps2ui-check each print the path they were HANDED (`-o`, `--preview`,
    the positional blob), and echoing an argument back in a different
    spelling than it arrived in would be its own defect. So a tool
    echoes; `ps2ui` constructs, and the construction has a spelling.
    That is the whole rule, and it puts every fix in this file.

    FORWARD SLASHES ARE NOT A LIE ON WINDOWS. The Win32 API, Python's
    open() and Node's fs all take `/` as a separator, so these paths
    stay the paths -- this changes how one is written, never which file
    it names. A no-op wherever os.sep is already `/`.
    """
    return path if os.sep == "/" else path.replace(os.sep, "/")


def rel(proj, path):
    return None if path is None else shown(
        os.path.relpath(path, proj.root))


def font_args(proj):
    """Where the compiler looks for fonts. Always the manifest.

    `require_fonts` has already refused a project without one, so this
    is never the empty list in practice; it stays a function because
    two call sites need the same two words and one of them used to
    forget them.
    """
    path = project_fonts(proj)
    return ["--fonts", rel(proj, path)] if path else []


def project_fonts(proj):
    """The manifest both halves should read, or None if there is none.

    The project's own `fonts/fonts.json` first, then the baker's
    checkout default -- `default_fonts_path()`, three levels up from
    `ps2ui_bake`, which is the repository root in a clone and nothing
    at all in an installed package. Its own docstring calls it "a
    CANDIDATE, not a promise" and keeps it because every example and
    build.sh in this repository relies on it.

    READING IT HERE IS WHAT MAKES THE TWO HALVES AGREE. The baker
    already fell back to it; the compiler never knew it existed, so in
    a checkout with no project manifest the compiler measured against
    its own install-relative directory and the baker rasterized from
    the repository's -- two font configurations for one set of fonts,
    which is the defect `--fonts` was added to end and did not, because
    nothing passed it when there was no project manifest.
    """
    if proj.fonts_path:
        return proj.fonts_path
    from . import cli as bake_cli  # lazy: keeps Pillow off this path
    fallback = bake_cli.default_fonts_path()
    return fallback if os.path.exists(fallback) else None


def require_fonts(proj):
    """Refuse a project with no font manifest, and say what writes one.

    THE MESSAGE A STRANGER GOT WAS WRITTEN BY THE HALF THAT KNEW LEAST.
    With no manifest, `ps2ui build` passed no font flag, ps2ui-layout
    fell back to a default resolved against its own install, and the
    error named `lib/node_modules/fonts` -- a directory inside the npm
    package -- as where `default.metrics.json` belongs. Measured on a
    clean machine with `npm install -g @ophtml/layout`, which is what
    the documentation tells a reader to run.

    ITS ADVICE COULD NOT WORK, AND NOT ONLY BECAUSE NOTHING PASSED THE
    FLAG. "Generate the metrics and pass `--font-dir <that directory>`"
    describes a compiler-only arrangement: `--font-dir` is two fixed
    filenames and no `ttf` paths, and the BAKER rasterizes, so a bare
    directory cannot carry what the baker needs. Wiring `--font-dir`
    through was tried first and got one step further before failing
    worse -- the compile succeeded, the bake then fell back to its own
    default manifest and refused on a family mismatch between a face
    the IR was measured against and a face it was about to draw with.
    Two halves resolving fonts independently is the defect; giving them
    a second way to disagree is not the fix.

    So the only thing that works end to end is the one the tutorial
    teaches and the old message never named: `ps2ui fontgen`, which
    writes both metrics files AND the `fonts.json` that keeps the two
    halves agreeing. This says so, before either half runs, which is
    what `Project.fonts_path` always claimed to arrange.
    """
    if project_fonts(proj):
        return
    raise ProjectError(
        "no fonts for this project: %s does not exist.\n"
        "  ps2ui bakes text at build time, so it needs metrics for your\n"
        "  font before it can lay anything out. Make them from any TTF:\n"
        "\n"
        "    ps2ui fontgen <regular.ttf> <bold.ttf>\n"
        "\n"
        "  That writes fonts/default.metrics.json, fonts/default-bold.\n"
        "  metrics.json and the fonts.json above, which is the file both\n"
        "  halves read -- metrics alone are not enough, because the baker\n"
        "  rasterizes and needs the TTF paths the manifest carries.\n"
        "  Point `fonts` in %s at one you already have to share it."
        % (rel(proj, proj.fonts_path or
                     os.path.join(proj.fonts_dir, "fonts.json")),
           os.path.basename(proj.path) if getattr(proj, "path", None)
           else "ps2ui.json"))


def compile_screens(proj, argv_extra):
    """Run the layout compiler over every screen. Returns IR paths."""
    require_fonts(proj)
    base = layout_command()
    os.makedirs(proj.build_dir, exist_ok=True)
    irs = []
    for screen in proj.screens:
        out = rel(proj, proj.ir_path(screen))
        cmd = base + [rel(proj, screen.html), rel(proj, screen.css),
                      "-o", out]
        cmd += font_args(proj)
        if proj.mode:
            cmd += ["--mode", proj.mode]
        if proj.canvas:
            cmd += ["--canvas", proj.canvas]
        if proj.display_aspect:
            cmd += ["--display-aspect", proj.display_aspect]
        if proj.strict:
            cmd += ["--strict"]
        if proj.min_font_size is not None:
            cmd += ["--min-font-size", str(proj.min_font_size)]
        if screen.focus_wrap:
            cmd += ["--focus-wrap"]
        cmd += argv_extra
        rc = subprocess.call(cmd)
        if rc != 0:
            # The compiler already printed why, in its own words. Adding
            # a second summary here would bury it.
            raise ProjectError(
                "ps2ui-layout failed on %s (exit %d)"
                % (rel(proj, screen.html), rc))
        irs.append(out)
    return irs


def bake_argv(proj, irs):
    """The baker's arguments for a project, minus its preview siblings.

    ONE CONSTRUCTION, TWO CALLERS. `ps2ui serve` builds the same project
    through the same compiler, and its first version assembled this list
    itself -- passing --fonts to the compiler and not to the baker, so
    the IR was measured against the project's manifest and baked against
    the baker's default. Every other project flag was missing the same
    way and silently.

    A unit test could not see it: in a CHECKOUT the baker's default font
    directory is the repository's own fonts/, so the wrong argv produced
    a byte-identical blob and only the tutorial -- which runs from an
    empty directory -- failed. So the duplication is gone rather than
    tested around, because the test that would have caught it is one
    that cannot exist here.
    """
    argv = list(irs) + ["-o", rel(proj, proj.out_path)]
    # THE BAKER, not the compiler: it reads a manifest and has no
    # --font-dir. When there is no manifest it applies its own
    # checked default and writes its own message, which is the
    # arrangement `font_args` exists to give the compiler too.
    path = project_fonts(proj)
    if path:
        argv += ["--fonts", rel(proj, path)]
    if proj.palettize_images:
        argv += ["--palettize-images"]
    if proj.vram_budget is not None:
        argv += ["--vram-budget", str(proj.vram_budget)]
    return argv


def cmd_build(args):
    proj = load(args.project)
    extra = []
    if args.mode:
        proj.mode = args.mode
    if args.out:
        proj.set_out_override(args.out)
    for key, value in (("preview", args.preview),
                       ("montage", args.montage),
                       ("preview_display", args.preview_display)):
        if value is not None:
            setattr(proj, key, False if value == "none" else value)
    from . import cli as bake_cli
    with in_project(proj):
        irs = compile_screens(proj, extra)
        argv = bake_argv(proj, irs)
        for key, flag in (("preview", "--preview"),
                          ("montage", "--montage"),
                          ("previewDisplay", "--preview-display")):
            path = proj.preview_path(key)
            if path:
                argv += [flag, rel(proj, path)]
        return bake_cli.main(argv)


def cmd_check(args):
    proj = load(args.project)
    from . import check as check_cli
    if not os.path.exists(proj.out_path):
        raise ProjectError(
            "%s: no blob to check. Run `ps2ui build` first -- this does "
            "not build, so that a check can never report on a blob it "
            "just made and nobody has seen."
            % rel(proj, proj.out_path))
    # THE PROJECT'S BUDGET REACHES THE BAKE AND HAD TO REACH THIS TOO.
    #
    # `vramBudget` was passed to ps2ui-bake (bake_argv, above) and
    # dropped here, so at any budget other than the default the two
    # halves of one project disagreed about the same blob: the build
    # succeeded at the declared budget and the check failed at the
    # computed one, naming a number the project had already overridden.
    #
    #     build:  textures 491520 B of 1212416 B budget (40%)
    #     check:  not ok 66 - VRAM 480 KiB within budget -272 KiB
    #
    # The default is deliberately conservative -- it reserves a third
    # framebuffer for a Z buffer that this tree's own sample does not
    # allocate, because `gs->ZBuffering = GS_SETTING_OFF` and gsKit
    # only allocates Z when it is on. Overriding it is therefore an
    # ordinary thing to do rather than a corner, and it is the whole
    # reason a canvas wide enough for square pixels at 16:9 is
    # reachable at all. check.py has taken --vram-budget since it was
    # written; nothing passed it.
    argv = [rel(proj, proj.out_path)]
    if proj.vram_budget is not None:
        argv += ["--vram-budget", str(proj.vram_budget)]
    # AND `strict`, which was the same drop one flag over. Raised in
    # review of the commit that fixed the budget: check.py takes five
    # options, two of them have a project key, and this forwarded one.
    #
    # `--strict` is "treat CRT warnings as failures" (check.py:721,
    # `failed = rep.errors + (rep.warnings if args.strict else 0)`), so
    # a project declaring it -- which the tutorial's own ps2ui.json does
    # -- got strictness in the layout compiler and could not get it
    # here. The commit's whole argument is that one project must not
    # mean two things to two commands; leaving this would have been the
    # argument and not the practice.
    if proj.strict:
        argv += ["--strict"]
    with in_project(proj):
        return check_cli.main(argv)


def cmd_fontgen(args):
    """Both faces in one command, which is how a person needs them.

    ps2ui-fontgen makes ONE metrics file, and every project needs two --
    so the tutorial's font step was two near-identical lines differing
    in a weight and a filename, which is exactly the shape a typo hides
    in.
    """
    from . import fontgen
    out_dir = args.out_dir
    os.makedirs(out_dir, exist_ok=True)
    for ttf, weight, name in ((args.regular, 400, "default.metrics.json"),
                              (args.bold, 700, "default-bold.metrics.json")):
        rc = fontgen.main([ttf, "default", str(weight),
                           shown(os.path.join(out_dir, name))])
        if rc != 0:
            return rc
    manifest = shown(os.path.join(out_dir, "fonts.json"))
    # json.dump RATHER THAN A FORMAT STRING, AND THE DIFFERENCE IS A
    # PLATFORM. This wrote the file by hand -- `"ttf": ["%s"]` against
    # os.path.abspath -- which is valid JSON for exactly as long as no
    # path contains a backslash. On Windows every absolute path does:
    #
    #   "ttf": ["C:\Users\me\AppData\...\DejaVuSans.ttf"]
    #    -> Bad escaped character in JSON at position 30
    #
    # so `ps2ui fontgen` wrote a manifest that `ps2ui build` could not
    # read, one command later, with both halves working as designed.
    # The tool broke its own output on the platform it was not written
    # on, and the only symptom a reader got was the compiler exiting 1.
    #
    # A serialiser is not a style preference here. Escaping the two
    # paths and keeping the hand-rolled braces would fix this instance
    # and leave the next one -- a face name, a metrics filename -- one
    # edit away. The structure is data, so data is what writes it.
    with open(manifest, "w", encoding="utf-8") as fh:
        json.dump({
            "regular": {"ttf": [os.path.abspath(args.regular)],
                        "metrics": "default.metrics.json"},
            "bold": {"ttf": [os.path.abspath(args.bold)],
                     "metrics": "default-bold.metrics.json"},
        }, fh, indent=2)
        fh.write("\n")
    print("ps2ui-fontgen: manifest -> %s" % manifest, file=sys.stderr)
    return 0


def pick_screen(proj, name):
    """The screen `ps2ui dev` watches, or a message naming the choices.

    THE ERROR USED TO NAME A FLAG THAT DID NOT EXIST. It said
    "ps2ui dev --screen <first screen>" and the parser had no --screen,
    so the remedy it printed failed with "unrecognized arguments". Every
    example in this repository has more than one screen, so that was the
    only thing `ps2ui dev` could do with any of them.

    It also named screens[0], which is not a recommendation -- it is
    whichever screen the project happens to list first, offered as if it
    were the answer. All of them are listed now, because the caller is
    choosing and cannot choose from one name.
    """
    if name is not None:
        for screen in proj.screens:
            if screen.name == name:
                return screen
        raise ProjectError(
            "no screen named %r in %s. It has: %s"
            % (name, os.path.basename(proj.path),
               ", ".join(s.name for s in proj.screens)))
    if len(proj.screens) == 1:
        return proj.screens[0]
    raise ProjectError(
        "ps2ui dev watches one screen and this project has %d. Name one: "
        "ps2ui dev --screen <name>, where <name> is one of: %s"
        % (len(proj.screens), ", ".join(s.name for s in proj.screens)))


def cmd_dev(args):
    base = layout_command()
    dev = [c.replace("ps2ui-layout", "ps2ui-dev") for c in base]
    proj = load(args.project)
    require_fonts(proj)
    screen = pick_screen(proj, args.screen)

    # A SEPARATE OUTPUT DIRECTORY, AND NOT build/. This wrote straight
    # into the project's build directory, where `ps2ui build` and every
    # example's build.sh put the blob CI verifies -- so a watch server
    # running while a build ran clobbered ui.uib and preview.png, and
    # left a ui.json that `ps2ui build` never writes, since it names its
    # intermediates after the screen. The README's own ps2ui-dev example
    # already said `-o build/dev`; this makes the wrapper agree with it.
    out_dir = os.path.join(proj.build_dir, "dev")
    with in_project(proj):
        os.makedirs(rel(proj, out_dir), exist_ok=True)
        cmd = dev + [rel(proj, screen.html), rel(proj, screen.css),
                     "-o", rel(proj, out_dir)]
        # EVERY PROJECT SETTING, NOT JUST THE FONTS. This forwarded
        # --fonts alone, so `ps2ui dev` and `ps2ui build` compiled the
        # same project differently: opl-env sets minFontSize 11 and dev
        # printed 88 warnings the build does not, and channel6's probe
        # screen sets focusWrap so dev gave it no navigation at all.
        # Two preview paths for one project that disagree is worse than
        # one, and `ps2ui serve` reaches this through compile_screens
        # already.
        cmd += font_args(proj)
        if proj.mode:
            cmd += ["--mode", proj.mode]
        if proj.canvas:
            cmd += ["--canvas", proj.canvas]
        if proj.display_aspect:
            cmd += ["--display-aspect", proj.display_aspect]
        if proj.strict:
            cmd += ["--strict"]
        if proj.min_font_size is not None:
            cmd += ["--min-font-size", str(proj.min_font_size)]
        if screen.focus_wrap:
            cmd += ["--focus-wrap"]
        if proj.palettize_images:
            cmd += ["--palettize-images"]
        if args.once:
            cmd.append("--once")
        return subprocess.call(cmd)


def _serve(args):
    """The one place serve.py is reached from, so the import defers."""
    from . import serve
    return serve.run(args)


def _vendor_runtime(args):
    # Deferred like _serve: `ps2ui build` in a CI container should not
    # import a module it will never reach.
    from . import vendor
    return vendor.cmd_vendor_runtime(args)


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="ps2ui",
        description="Compile, bake and check a ps2ui project.")
    ap.add_argument("--version", action="version",
                    version="ps2ui %s" % __version__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("build", help="compile every screen and bake one blob")
    b.add_argument("project", nargs="?", default="ps2ui.json")
    b.add_argument("--mode", help="override the project's video mode")
    b.add_argument("-o", "--out", help="override the project's output blob; "
                   "its intermediates move with it")
    # THE SIBLINGS A SECOND BLOB NEEDS DIFFERENTLY. Without these,
    # "everything a second blob needs differently is a flag" could not
    # be applied to the one second blob in this repository: channel6's
    # 16:9 build wrote its display preview over the 4:3 one.
    for flag, key in (("--preview", "preview"),
                      ("--montage", "montage"),
                      ("--preview-display", "preview_display")):
        b.add_argument(flag, dest=key, metavar="PNG",
                       help="override the project's %s ('none' to skip it)"
                            % flag.lstrip("-"))
    b.set_defaults(fn=cmd_build)

    c = sub.add_parser("check", help="validate the blob the project builds")
    c.add_argument("project", nargs="?", default="ps2ui.json")
    c.set_defaults(fn=cmd_check)

    f = sub.add_parser("fontgen",
                       help="metrics and a manifest from two TTFs")
    f.add_argument("regular", help="the regular-weight TTF")
    f.add_argument("bold", help="the bold TTF")
    f.add_argument("-o", "--out-dir", default="fonts",
                   help="where to write them (default: fonts/)")
    f.set_defaults(fn=cmd_fontgen)

    # DECLARED HERE, NOT DELEGATED TO serve.py, AND THAT IS THE WHOLE
    # POINT. The first version called `serve.add_arguments(sv)` from an
    # import inside main() and claimed `ps2ui build` loaded no server
    # code. It did: main() builds every subparser before it dispatches,
    # so the import ran on every invocation, and `ps2ui build --help`
    # pulled in serve plus http.server, socketserver, socket, ssl and
    # email. The claim was in three places and the test that guarded it
    # never called main(), so it could not see any of that.
    #
    # Nine lines of argparse restated here buys a real deferral: serve
    # is imported by the dispatch, which only the `serve` subcommand
    # reaches. test_serve.py asserts it by running `build --help`.
    sv = sub.add_parser("serve", help="preview the project in a browser")
    sv.add_argument("project", nargs="?", default="ps2ui.json")
    sv.add_argument("--uib", metavar="BLOB",
                    help="serve a pre-baked blob: no Node, no watching")
    # THE WORDING IS serve.add_arguments's, AND IT HAS TO BE. This
    # parser is restated rather than delegated (see above), so a help
    # string fixed in one entry point stays broken in the other unless
    # somebody edits both -- and `ps2ui serve --help` is the one a
    # reader reaches first. test_serve.py compares the two texts.
    sv.add_argument("--port", type=int, default=None,
                    help="the default 8080 moves up when busy; a port "
                         "named here is used or the command fails")
    sv.add_argument("--screen", metavar="NAME", help="the screen to open")
    sv.add_argument("--theme", type=int, default=0, help="the theme row")
    sv.add_argument("--no-watch", action="store_true",
                    help="do not rebuild on edits")
    sv.add_argument("--selftest", action="store_true",
                    help="build, serve one of every route, and exit")
    sv.set_defaults(fn=_serve)

    # THE CONSOLE HALF OF THE TOOLCHAIN, WHICH USED TO NEED A CLONE.
    # `pip install ophtml` gave you everything up to the blob and then
    # README.md said "drop runtime/ps2ui.c into your project" -- a repo
    # path, in a package that shipped neither file. F26.
    #
    # The files come from THIS install, so the runtime a person compiles
    # is the one matching the baker that wrote their blob. check-
    # versions.py holds ps2ui.h's PS2UI_VERSION to the writer's, but
    # only inside the tree; handing out a runtime from anywhere else
    # puts that skew on somebody else's machine.
    vr = sub.add_parser("vendor-runtime",
                        help="write ps2ui.c and ps2ui.h into your project")
    vr.add_argument("dest", nargs="?", default=".",
                    help="where to write them (default: here)")
    vr.add_argument("--force", action="store_true",
                    help="overwrite files that are already there")
    # The runtime alone is for adding ps2ui to an app that exists. This
    # is for the other case, which had nothing: two C files and a link
    # to a 2800-line bring-up harness on GitHub.
    vr.add_argument("--starter", action="store_true",
                    help="also write a main.c and a Makefile that build "
                         "to an ELF as they stand")
    vr.set_defaults(fn=_vendor_runtime)

    d = sub.add_parser("dev", help="rebuild on every edit")
    d.add_argument("project", nargs="?", default="ps2ui.json")
    d.add_argument("--screen", metavar="NAME",
                   help="which screen to watch; required when the project "
                        "has more than one")
    d.add_argument("--once", action="store_true",
                   help="build once and exit, rather than watching")
    d.set_defaults(fn=cmd_dev)

    args = ap.parse_args(argv)
    try:
        return args.fn(args)
    except ProjectError as exc:
        # Every failure this file raises is a person's typo or a missing
        # install. A traceback buries the one line they can act on.
        print("ps2ui: %s" % exc, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
