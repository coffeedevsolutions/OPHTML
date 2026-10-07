#!/usr/bin/env python3
"""No tracked file names the machine it was written on.

WHY THIS EXISTS. An exposure audit of this public repository found two
findings of exactly one shape, and both got there the same way: this
project's documented practice is to paste real command output into the
fact tables, because a transcript nobody ran is a document that was true
on the day it was written. Real output carries real paths.

  * THE AGENT SESSION. 362 occurrences across 21 tracked files of
    `/tmp/claude-0/-home-user-OPHTML/<uuid>/scratchpad/...`, which
    discloses the container's scratchpad layout, the instance slot and a
    stable per-session UUID. Two of the 21 were PUBLISHED pages rather
    than `_facts/` files the site excludes. The `<scratch>` token was
    already the convention in 29 files; only its own definition line
    still spelled the literal out.

  * THE BUILD HOST. `/opt/node22/...` and `/opt/pw-browsers/chromium` in
    15 lines across 6 files, principally the stored screenshot commands
    in `docs/site/assets/assets.json`. Non-standard install locations,
    so an environment fingerprint -- and the commands were less
    reproducible for it, since nobody else's machine has those paths.

Neither was ever going to be caught by review: the literal is one field
inside a pasted transcript that is otherwise exactly what a reader
wants. So it is checked instead, and the check runs over the tree rather
than over a diff, because the question is what the repository CONTAINS.

A THIRD RULE COVERS IMAGES, for the same reason one layer over.
`docs/assets/`'s logo carried a PNG `iTXt` packet from the editor that
drew it, holding `XML:com.adobe.xmp` with create and modify timestamps.
Nothing in a PNG viewer shows that. All 86 tracked PNGs are clean now,
and a future one exported from a design tool will not be.

WHAT IS DELIBERATELY NOT FENCED, so nobody reads its absence as an
oversight:

  * `/home/user/OPHTML`, the container's checkout root, in 32 lines. It
    is the working directory a reader needs in order to read a relative
    path in the same transcript, and it names no person and no machine.
  * `HOME=/root` and `/root/...` in pasted output, which says the doc
    runs were done as root and nothing else.
  * `/Users/` and `C:\\Users\\` ARE fenced, but four placeholder
    segments are allowed, because this repository documents Windows and
    macOS path handling and has to be able to write an example. Every
    hit is either one of those or a failure -- there is no third
    outcome, which is the property that makes the rule worth having.

Run by ci.yml. Exits 0 with one `ok -` line per rule, or 1 naming every
file and line.
"""
import os
import re
import struct
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# This file names every pattern it looks for, so it cannot be its own
# corpus. It is the ONLY exception, and the count is asserted below.
SELF = "tools/check-host-paths.py"

UUID = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"

# The four user segments this repository is allowed to write, and what
# each is for. A fifth is a finding until someone adds it here.
HOME_SEGMENTS = {
    "you": "the placeholder in the relative-path examples "
           "(`../../../../Users/you/repo/fonts.json`)",
    "runner": "GitHub's own macOS runner, in a pasted brew transcript",
    "me": "the placeholder in the Windows `ttf` example",
    "O'Brien": "the worked example about a quote in a path breaking eval",
}

RULES = [
    ("the agent container's scratchpad",
     re.compile(r"/tmp/claude-[0-9]+/"),
     "Use the `<scratch>` token, which 29 fact files already define."),
    ("a session UUID",
     re.compile(UUID),
     "The only UUIDs this tree has ever held were agent session ids. If a "
     "real one is needed, name it here with its reason."),
    ("a build-host install location",
     re.compile(r"/opt/(?:node22|pw-browsers)"),
     "Parameterise it: `$(npm root -g)` for NODE_PATH and "
     "`$PLAYWRIGHT_BROWSERS_PATH` for the browser, so the recorded command "
     "runs on a machine that is not this one."),
]

HOME_RE = re.compile(r"(?:/Users/|C:\\Users\\)([^/\\\"` )\n]+)")

TEXTY_CHUNKS = {b"iTXt", b"tEXt", b"zTXt", b"eXIf", b"tIME"}

problems = []
oks = []


def tracked():
    out = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT,
                         capture_output=True, text=True)
    if out.returncode != 0:
        print("check-host-paths cannot run `git ls-files`, so it cannot say "
              "what the repository contains:\n" + out.stderr, file=sys.stderr)
        sys.exit(1)
    return [f for f in out.stdout.split("\0") if f]


files = tracked()
skipped = [f for f in files if f == SELF]
if len(skipped) != 1:
    problems.append(
        "this checker excludes %r from its own corpus and git lists %d file(s) "
        "by that name. If it was renamed, rename SELF with it -- otherwise the "
        "patterns below are being searched for in the file that defines them, "
        "or nothing is being excluded and the exclusion is a lie."
        % (SELF, len(skipped)))
corpus = [f for f in files if f != SELF]

text, pngs = [], []
for f in corpus:
    path = os.path.join(ROOT, f)
    if f.lower().endswith(".png"):
        pngs.append(f)
        continue
    try:
        with open(path, encoding="utf-8") as fh:
            text.append((f, fh.read().split("\n")))
    except (UnicodeDecodeError, IsADirectoryError, FileNotFoundError):
        continue      # a binary or a submodule: no lines to read

for label, pattern, remedy in RULES:
    hits = ["%s:%d: %s" % (f, n, pattern.search(ln).group(0))
            for f, lines in text
            for n, ln in enumerate(lines, 1) if pattern.search(ln)]
    check_ok = not hits
    if check_ok:
        oks.append("no tracked file names %s (%d file(s) read)"
                   % (label, len(text)))
    else:
        problems.append(
            "%d line(s) name %s. %s\n      %s"
            % (len(hits), label, remedy, "\n      ".join(hits[:40])))

# THE HOME-DIRECTORY RULE, which is an allowlist rather than a ban.
bad_home, allowed_home = [], 0
for f, lines in text:
    for n, ln in enumerate(lines, 1):
        for m in HOME_RE.finditer(ln):
            seg = m.group(1)
            if seg in HOME_SEGMENTS:
                allowed_home += 1
            else:
                bad_home.append("%s:%d: %s" % (f, n, m.group(0)))
if bad_home:
    problems.append(
        "%d home-directory path(s) name a user segment this file does not "
        "declare. The declared ones are %s. If the new one is a placeholder "
        "too, add it to HOME_SEGMENTS with what it is for; if it is a real "
        "account name, take it out.\n      %s"
        % (len(bad_home), ", ".join(sorted(HOME_SEGMENTS)),
           "\n      ".join(bad_home[:40])))
else:
    oks.append("every /Users/ and C:\\Users\\ path is one of the %d declared "
               "placeholders (%d occurrence(s))"
               % (len(HOME_SEGMENTS), allowed_home))

# AND THE IMAGES. Read as chunks rather than through an image library,
# because the point is the metadata a decoder throws away.
meta = []
for f in pngs:
    d = open(os.path.join(ROOT, f), "rb").read()
    if d[:8] != b"\x89PNG\r\n\x1a\n":
        problems.append("%s is named .png and has no PNG signature" % f)
        continue
    i = 8
    while i + 8 <= len(d):
        ln = struct.unpack(">I", d[i:i+4])[0]
        typ = d[i+4:i+8]
        if typ in TEXTY_CHUNKS:
            key = d[i+8:i+8+40].split(b"\0")[0].decode("latin1", "replace")
            meta.append("%s: %s chunk, %d bytes, %r"
                        % (f, typ.decode("latin1"), ln, key))
        i += 12 + ln
        if typ == b"IEND":
            break
if meta:
    problems.append(
        "%d PNG metadata chunk(s) in tracked images. A design tool writes an "
        "XMP packet with create and modify timestamps and nothing in a viewer "
        "shows it. Strip it -- `exiftool -all=`, or drop the chunk and keep "
        "the IDAT bytes so the pixels do not "
        "change.\n      %s" % (len(meta), "\n      ".join(meta[:40])))
else:
    oks.append("no tracked PNG carries a text, time or EXIF chunk (%d image(s))"
               % len(pngs))

for line in oks:
    print("ok - " + line)
if problems:
    print("\nFAIL: %d problem(s)\n" % len(problems), file=sys.stderr)
    for p in problems:
        print("  * " + p + "\n", file=sys.stderr)
    sys.exit(1)
print("\nPASS: %d rule(s) over %d tracked file(s)" % (len(oks), len(corpus)))
