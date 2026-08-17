#!/usr/bin/env python3
"""Find the newest Play! Linux AppImage on purei.org.

Two parse-only modes, so the network calls stay in the workflow and the
logic stays testable:

    curl -sSfL https://purei.org/downloads/play/stable/ \
        | python3 tools/play_appimage_url.py --latest-version
    # -> 0.72

    curl -sSfL https://purei.org/downloads/play/stable/0.72/ \
        | python3 tools/play_appimage_url.py --appimage
    # -> Play!-8de4a71f-x86_64.AppImage

Both read an Apache-style directory index on stdin.

## Why not GitHub

`hw.yml` originally fetched
`github.com/jpd002/Play-/releases/latest/download/Play_x86_64.AppImage`.
Three things were wrong with that, and they only became visible one at
a time because each failure hid the next:

1. No `--fail`, so curl wrote the 404 body ("Not Found", nine bytes) to
   `Play.AppImage` and the next step executed it:
   `./Play.AppImage: line 1: Not: command not found`.
2. With `--fail`, the 404 turned out to be on `/releases/latest`, which
   excludes prereleases.
3. Querying the releases *list* instead returned an empty array:
   `jpd002/Play-` publishes no GitHub releases at all.

Play! is distributed from purei.org, not from GitHub. No filename guess
could ever have worked. The continuous-build API the downloads page
references (`services.purei.org/api/builds`) is commented out in the
served HTML, so the stable tree is the supported path.

Self-test: python3 tools/play_appimage_url.py --self-test
"""
from __future__ import annotations

import argparse
import re
import sys

# Apache's index: href="0.72/" for directories, href="Play!-...AppImage"
# for files. Deliberately narrow, so a redesigned page fails loudly here
# rather than yielding a plausible wrong URL.
_VERSION_DIR = re.compile(r'href="(\d+)\.(\d+)/"')
_HREF = re.compile(r'href="([^"]+)"')

# The 64-bit desktop build. 32-bit and other-arch AppImages would still
# match ".AppImage", so require the arch rather than take the first hit.
PREFERRED_ARCH = ("x86_64", "amd64")


def latest_version(index_html: str) -> str:
    """Newest version directory, compared numerically.

    String order would put 0.9 above 0.70 and 0.100 below 0.99, and this
    tree is already past 0.70.
    """
    found = [(int(a), int(b)) for a, b in _VERSION_DIR.findall(index_html)]
    if not found:
        raise LookupError(
            "no version directories in the index; expected entries like "
            'href="0.72/". The stable tree may have moved.'
        )
    major, minor = max(found)
    return f"{major}.{minor}"


def appimage(index_html: str) -> str:
    """The 64-bit AppImage filename in a version directory index."""
    names = [h for h in _HREF.findall(index_html) if h.endswith(".AppImage")]
    if not names:
        raise LookupError(
            "no .AppImage in this version directory; it ships "
            + (", ".join(h for h in _HREF.findall(index_html)
                         if "?" not in h and not h.startswith("/")) or "nothing")
        )
    for token in PREFERRED_ARCH:
        for name in names:
            if token in name.lower():
                return name
    raise LookupError(
        f"no 64-bit AppImage; found {', '.join(names)}. Check whether the "
        f"build is published under a different architecture name."
    )


def self_test() -> int:
    # Shaped like the real pages, which is the point: these are the
    # strings the workflow will actually parse.
    stable_index = """
      <a href="?C=N;O=D">Name</a>
      <a href="/downloads/play/">Parent Directory</a>
      <a href="0.68/">0.68/</a>
      <a href="0.69/">0.69/</a>
      <a href="0.70/">0.70/</a>
      <a href="0.72/">0.72/</a>
    """
    version_index = """
      <a href="?C=N;O=D">Name</a>
      <a href="/downloads/play/stable/">Parent Directory</a>
      <a href="Play!-8de4a71f-x86_64.AppImage">Play!-8de4a71f-x86_64.AppImage</a>
      <a href="Play-release.apk">Play-release.apk</a>
      <a href="Play.dmg">Play.dmg</a>
    """
    failures = 0

    def expect(label, fn, want):
        nonlocal failures
        try:
            got = fn()
        except Exception as exc:  # noqa: BLE001 - the assertion is the point
            got = f"raised {exc!r}"
        ok = got == want
        failures += not ok
        print(f"  {'ok  ' if ok else 'FAIL'} {label}"
              + ("" if ok else f" (got {got!r}, want {want!r})"))

    expect("newest version directory",
           lambda: latest_version(stable_index), "0.72")
    expect("the 64-bit AppImage",
           lambda: appimage(version_index), "Play!-8de4a71f-x86_64.AppImage")

    # 0.9 must not beat 0.70, and 0.100 must beat 0.99.
    expect("versions compare numerically, not as strings",
           lambda: latest_version('href="0.9/" href="0.70/"'), "0.70")
    expect("three-digit minors sort above two-digit",
           lambda: latest_version('href="0.99/" href="0.100/"'), "0.100")

    def raises(fn, needle):
        try:
            fn()
        except LookupError as exc:
            return needle in str(exc)
        return False

    for label, ok in [
        ("empty index names the expected shape",
         raises(lambda: latest_version("<html>nothing here</html>"),
                "no version directories")),
        ("a directory with no AppImage says what it does ship",
         raises(lambda: appimage('href="Play.dmg"'), "no .AppImage")),
        ("a 32-bit-only build is refused, not silently taken",
         raises(lambda: appimage('href="Play!-x86-32.AppImage"'),
                "no 64-bit AppImage")),
    ]:
        failures += not ok
        print(f"  {'ok  ' if ok else 'FAIL'} {label}")

    print("play_appimage_url self-test: "
          + ("PASS" if not failures else f"{failures} FAILURE(S)"))
    return 1 if failures else 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="play_appimage_url")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--latest-version", action="store_true",
                      help="read the stable index, print the newest version")
    mode.add_argument("--appimage", action="store_true",
                      help="read a version directory, print the AppImage name")
    mode.add_argument("--self-test", action="store_true")
    args = ap.parse_args(argv)

    if args.self_test:
        return self_test()
    if not (args.latest_version or args.appimage):
        ap.error("one of --latest-version, --appimage or --self-test")

    html = sys.stdin.read()
    try:
        print(latest_version(html) if args.latest_version else appimage(html))
    except LookupError as exc:
        print(f"play_appimage_url: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
