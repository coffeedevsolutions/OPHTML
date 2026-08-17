#!/usr/bin/env python3
"""Pick the Linux AppImage out of a GitHub release payload.

    curl -sSfL https://api.github.com/repos/jpd002/Play-/releases \
        | python3 tools/play_release_url.py

Accepts either a single release object or the list endpoint's array,
and prints one download URL on stdout. Exits non-zero, naming what it
did see, when there is no AppImage to pick.

Use the *list* endpoint. `/releases/latest` excludes prereleases and
draft releases, and a project publishing only rolling prerelease builds
(which Play! does) has no "latest" at all, so that endpoint 404s and no
amount of getting the asset name right helps.

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


def pick(payload) -> str:
    """Return the best AppImage download URL in `payload`.

    `payload` is a release object or a list of them, newest first, as
    the two GitHub endpoints return. Drafts are skipped (their assets
    are not publicly downloadable); prereleases are not, because rolling
    prerelease builds are the only kind some projects publish.

    Raises LookupError naming what it saw when there is no candidate,
    because "no AppImage in any release" and "the AppImage was renamed"
    need different fixes and the log should say which happened.
    """
    releases = payload if isinstance(payload, list) else [payload]
    published = [r for r in releases if not r.get("draft")]
    for release in published:
        try:
            return _pick_one(release)
        except LookupError:
            continue
    seen = ", ".join(
        f"{r.get('tag_name', '?')}["
        + ", ".join(a.get("name", "?") for a in (r.get("assets") or [])) + "]"
        for r in published[:3]
    ) or "(no published releases)"
    raise LookupError(f"no .AppImage in any published release; saw: {seen}")


def _pick_one(release: dict) -> str:
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

    # The list endpoint is what the workflow actually uses, and rolling
    # prerelease builds are the case that broke /releases/latest.
    listed = [
        {"tag_name": "draft", "draft": True,
         "assets": [{"name": "Play_x86_64.AppImage",
                     "browser_download_url": "wrong"}]},
        {"tag_name": "continuous", "prerelease": True,
         "assets": [{"name": "Play_x86_64.AppImage",
                     "browser_download_url": url}]},
    ]
    got = pick(listed)
    ok = got == url
    failures += not ok
    print(f"  {'ok  ' if ok else 'FAIL'} takes a prerelease and skips a draft")

    # Newest first, and the newest release may ship no Linux build; fall
    # through rather than give up.
    got = pick([
        {"tag_name": "newest", "assets": [{"name": "Play.dmg"}]},
        {"tag_name": "older",
         "assets": [{"name": "Play.AppImage", "browser_download_url": url}]},
    ])
    ok = got == url
    failures += not ok
    print(f"  {'ok  ' if ok else 'FAIL'} falls through a release with no AppImage")

    # The whole point is a loud failure rather than a saved error page.
    for label, payload, want in [
        ("no assets at all", {"tag_name": "v4", "assets": []}, "v4"),
        ("assets but no AppImage",
         {"tag_name": "v5", "assets": [{"name": "Play.dmg"}]}, "Play.dmg"),
        ("an empty list", [], "no published releases"),
        ("only drafts",
         [{"tag_name": "d", "draft": True,
           "assets": [{"name": "Play.AppImage"}]}], "no published releases"),
    ]:
        try:
            pick(payload)
        except LookupError as exc:
            ok = want in str(exc)
        else:
            ok = False
        failures += not ok
        print(f"  {'ok  ' if ok else 'FAIL'} raises, naming what it saw: {label}")

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="play_release_url")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args(argv)
    if args.self_test:
        return self_test()

    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"release payload is not JSON: {exc}", file=sys.stderr)
        return 2
    if not isinstance(payload, (dict, list)):
        print(f"expected a release object or a list of them, got "
              f"{type(payload).__name__}", file=sys.stderr)
        return 2

    try:
        print(pick(payload))
    except LookupError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
