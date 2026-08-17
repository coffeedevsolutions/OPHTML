#!/usr/bin/env python3
"""Pick the Linux AppImage out of a GitHub release payload.

    curl -sSfL https://api.github.com/repos/jpd002/Play-/releases/latest \
        | python3 tools/play_release_url.py

Prints one download URL on stdout, or exits non-zero with the asset
names it did see.

Why this exists: `hw.yml` used to fetch a hardcoded
`releases/latest/download/Play_x86_64.AppImage`. That path 404s, and
because the download had no `--fail`, curl happily wrote the nine-byte
string "Not Found" to `Play.AppImage`, which the next step then ran:

    ./Play.AppImage: line 1: Not: command not found

A wrong filename should be one clear error, not an executed error page.
The asset name is release metadata and has changed before, so read it
rather than guess it.

Self-test: python3 tools/play_release_url.py --self-test
"""
from __future__ import annotations

import argparse
import json
import sys

# Preferred first. A release usually ships several AppImages (and on
# some tags, none at all), so rank rather than take the first match.
PREFERRED = ("x86_64", "amd64")


def pick(release: dict) -> str:
    """Return the best AppImage download URL in `release`.

    Raises LookupError naming every asset when there is no candidate,
    because "no AppImage" and "renamed AppImage" need different fixes
    and the log should say which one happened.
    """
    assets = release.get("assets") or []
    appimages = [a for a in assets if a.get("name", "").endswith(".AppImage")]
    if not appimages:
        names = ", ".join(a.get("name", "?") for a in assets) or "(none)"
        raise LookupError(
            f"no .AppImage asset in release {release.get('tag_name', '?')}; "
            f"assets were: {names}"
        )

    def rank(asset: dict) -> tuple[int, str]:
        name = asset["name"].lower()
        for i, token in enumerate(PREFERRED):
            if token in name:
                return (i, name)
        return (len(PREFERRED), name)

    return min(appimages, key=rank)["browser_download_url"]


def self_test() -> int:
    url = "https://example.invalid/Play_x86_64.AppImage"
    cases = [
        (
            "prefers x86_64 over an unqualified build",
            {
                "tag_name": "v1",
                "assets": [
                    {"name": "Play.AppImage", "browser_download_url": "wrong"},
                    {"name": "Play_x86_64.AppImage", "browser_download_url": url},
                ],
            },
            url,
        ),
        (
            "falls back to any AppImage",
            {
                "tag_name": "v2",
                "assets": [{"name": "Play.AppImage", "browser_download_url": url}],
            },
            url,
        ),
        (
            "ignores non-AppImage assets",
            {
                "tag_name": "v3",
                "assets": [
                    {"name": "Play.dmg", "browser_download_url": "wrong"},
                    {"name": "Play_amd64.AppImage", "browser_download_url": url},
                ],
            },
            url,
        ),
    ]
    failures = 0
    for label, release, want in cases:
        got = pick(release)
        ok = got == want
        failures += not ok
        print(f"  {'ok  ' if ok else 'FAIL'} {label}")

    # The whole point is a loud failure rather than a saved error page.
    for label, release in [
        ("no assets at all", {"tag_name": "v4", "assets": []}),
        (
            "assets but no AppImage",
            {"tag_name": "v5", "assets": [{"name": "Play.dmg"}]},
        ),
    ]:
        try:
            pick(release)
        except LookupError as exc:
            ok = "assets were" in str(exc)
        else:
            ok = False
        failures += not ok
        print(f"  {'ok  ' if ok else 'FAIL'} raises with the asset list: {label}")

    print(f"play_release_url self-test: {'PASS' if not failures else f'{failures} FAILURE(S)'}")
    return 1 if failures else 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="play_release_url")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args(argv)
    if args.self_test:
        return self_test()

    try:
        release = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"release payload is not JSON: {exc}", file=sys.stderr)
        return 2
    if not isinstance(release, dict):
        print(f"expected a release object, got {type(release).__name__}", file=sys.stderr)
        return 2

    try:
        print(pick(release))
    except LookupError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
