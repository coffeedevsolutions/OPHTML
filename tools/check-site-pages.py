#!/usr/bin/env python3
"""Check the documentation site's pages: links, citations, voice, stamps.

WHY THIS EXISTS. docs/site/ carries 46 pages with about 780 `page:`
links, 214 `repo:` links and 183 of those pinned to a line number. The
review of the pull request that added them found eight line pins that
had gone stale while the branch was open (two other pull requests
inserted lines above the cited ones) and one that was wrong when
written, and nothing in the tree could see any of the nine: the only
committed checker compared PNG bytes, and the page verification lived
as a shell snippet in docs/site/ARCHITECTURE.md that nobody ran.

WHAT IT CHECKS, over every page under docs/site/ except _prompts/,
_facts/, ARCHITECTURE.md and the READMEs:

  1. Frontmatter: `id` equals the page's path, `version` equals the
     one site version declared in ARCHITECTURE.md, and the page's
     facts file exists under _facts/.
  2. `page:<id>#<anchor>` links name a written page and a real heading
     on it (headings inside fenced code do not count).
  3. `repo:<path>#L<n>[-L<m>]` links name a file in the tree with the
     line numbers inside it.
  4. Citation drift. docs/site/_citations.tsv records, for every
     line-pinned citation, the text of the cited line when it was
     pinned, plus the lines before and after it. A cited line whose
     text has changed is reported as drifted. `--pin` rewrites the
     record from the tree as it stands; `--fix` relocates a drifted
     citation when the recorded line now occurs exactly once in the
     file, or when several copies exist and exactly one sits between
     the recorded neighbours (a bare `return PS2UI_ERR_RANGE;` repeats,
     its neighbours do not), rewriting the page and the record. The
     ones it cannot place are reported for a hand fix. A citation with
     no record, or a record with no citation, fails until `--pin` is
     run, so the record stays exact.
  5. Voice: the forbidden words and phrases from ARCHITECTURE.md, em
     dashes and exclamation marks, all outside code, backticks and
     table rows. `Play!` is the emulator's name and is allowed.
  6. Every embedded image exists.
  7. Prose word count: at most 1500 on every page, at least 300 on
     every page outside the project section and the home page.

OUTPUT is TAP-shaped like the other tools/check-*.py: one `ok -` or
`not ok -` line per finding class per page, a summary, exit 1 on any
`not ok`.
"""

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(ROOT, "docs", "site")
ARCH = os.path.join(SITE, "ARCHITECTURE.md")
PIN = os.path.join(SITE, "_citations.tsv")

FORBIDDEN = [
    "let's", "we", "we'll", "in this section", "in this guide", "simply",
    "seamless", "seamlessly", "robust", "leverage", "powerful",
    "note that", "it's worth noting", "it is worth noting", "keep in mind",
    "as you can see", "of course", "essentially", "basically", "easily",
    "straightforward", "delve", "dive into", "unlock", "empower",
    "journey", "crucial", "vital",
]
FORBIDDEN_RE = re.compile(
    r"\b(" + "|".join(re.escape(p) for p in FORBIDDEN) + r")\b", re.I)

PAGE_LINK = re.compile(r"\(page:([^)#\s]+)(?:#([^)\s]+))?\)")
REPO_LINK = re.compile(r"\(repo:([^)#\s]+)(?:#L(\d+)(?:-L?(\d+))?)?\)")
IMAGE = re.compile(r"!\[[^\]]*\]\(([^)\s]+)\)")
HEADING = re.compile(r"^#{1,6}\s+(.*?)\s*#*\s*$")


def pages():
    out = []
    for d, dirs, files in os.walk(SITE):
        dirs[:] = [x for x in dirs if x not in ("_prompts", "_facts")]
        for f in files:
            if not f.endswith(".md") or f in ("ARCHITECTURE.md", "README.md"):
                continue
            path = os.path.join(d, f)
            out.append((os.path.relpath(path, SITE)[:-3], path))
    return sorted(out)


def site_version():
    text = open(ARCH, encoding="utf-8").read()
    m = re.search(r"^Site version: `?([0-9][^`\s]*)`?", text, re.M)
    if not m:
        raise SystemExit("not ok - ARCHITECTURE.md does not declare "
                         "`Site version: <x.y.z>`; every page's version "
                         "stamp is checked against that one line")
    return m.group(1)


def frontmatter(text):
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---", 4)
    if end < 0:
        return {}
    fm = {}
    for line in text[4:end].splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            fm[k.strip()] = v.strip()
    return fm


def slug(heading):
    h = heading.replace("`", "").strip().lower()
    h = re.sub(r"[^a-z0-9 _-]", "", h)
    return re.sub(r"\s+", "-", h).strip("-")


def prose_lines(text):
    """Lines that are prose: no fenced code, no table rows, no
    frontmatter, no headings, no image-only lines; backtick spans
    removed from what remains."""
    out = []
    fence = False
    body = text
    if body.startswith("---\n"):
        end = body.find("\n---", 4)
        body = body[end + 4:] if end >= 0 else body
    for line in body.splitlines():
        if line.startswith("```") or line.startswith("~~~"):
            fence = not fence
            continue
        if fence:
            continue
        s = line.strip()
        if s.startswith("|") or s.startswith("#") or s.startswith("!["):
            continue
        out.append(re.sub(r"`[^`]*`", "", line))
    return out


def headings(text):
    out = set()
    fence = False
    for line in text.splitlines():
        if line.startswith("```") or line.startswith("~~~"):
            fence = not fence
            continue
        if fence:
            continue
        m = HEADING.match(line)
        if m:
            out.add(slug(m.group(1)))
    return out


def file_lines(path):
    with open(os.path.join(ROOT, path), encoding="utf-8",
              errors="replace") as fh:
        return fh.read().split("\n")


def escape(text):
    return text.replace("\\", "\\\\").replace("\t", "\\t")


def unescape(text):
    return re.sub(r"\\(.)", lambda m: "\t" if m.group(1) == "t" else m.group(1),
                  text)


def read_pin():
    records = {}
    if not os.path.exists(PIN):
        return records
    for raw in open(PIN, encoding="utf-8"):
        raw = raw.rstrip("\n")
        if not raw or raw.startswith("#"):
            continue
        page, path, line, text, before, after = raw.split("\t", 5)
        records[(page, path, int(line))] = (
            unescape(text), unescape(before), unescape(after))
    return records


def write_pin(records):
    with open(PIN, "w", encoding="utf-8") as fh:
        fh.write("# page\trepo path\tline\ttext of that line when pinned"
                 "\tline before\tline after\n"
                 "# Written by tools/check-site-pages.py --pin. Do not "
                 "edit by hand.\n")
        for (page, path, line), (text, before, after) in sorted(records.items()):
            fh.write("%s\t%s\t%d\t%s\t%s\t%s\n"
                     % (page, path, line, escape(text), escape(before),
                        escape(after)))


def window(lines, n):
    """(text, line before, line after) for 1-based line n."""
    return (lines[n - 1],
            lines[n - 2] if n >= 2 else "",
            lines[n] if n < len(lines) else "")


def main(argv):
    mode = "check"
    for a in argv:
        if a in ("--pin", "--fix"):
            mode = a[2:]
        else:
            raise SystemExit("not ok - check-site-pages: unknown argument %r; "
                             "the flags are --pin and --fix" % a)

    version = site_version()
    site = dict(pages())
    texts = {pid: open(p, encoding="utf-8").read() for pid, p in site.items()}
    heads = {pid: headings(t) for pid, t in texts.items()}
    fails = []
    oks = []

    def bad(msg):
        fails.append("not ok - " + msg)

    # 1. frontmatter, facts file
    for pid, text in texts.items():
        fm = frontmatter(text)
        if fm.get("id") != pid:
            bad("%s: frontmatter id is %r, path says %r"
                % (pid, fm.get("id"), pid))
        if fm.get("version") != version:
            bad("%s: version stamp %r, ARCHITECTURE.md says %s"
                % (pid, fm.get("version"), version))
        if not os.path.exists(os.path.join(SITE, "_facts", pid + ".md")):
            bad("%s: no facts file under docs/site/_facts/" % pid)
    oks.append("ok - %d pages carry their own id, version %s, and a facts "
               "file" % (len(site), version))

    # 2. page links
    n_page = 0
    for pid, text in texts.items():
        for m in PAGE_LINK.finditer(text):
            n_page += 1
            target, anchor = m.group(1), m.group(2)
            if target not in site:
                bad("%s: page:%s is not a page" % (pid, target))
            elif anchor and anchor not in heads[target]:
                bad("%s: page:%s#%s names no heading on that page"
                    % (pid, target, anchor))
    oks.append("ok - %d page: links resolve to a page and a heading" % n_page)

    # 3. repo links, and 4. citation drift
    records = read_pin() if mode != "pin" else {}
    seen = set()
    n_repo = n_pinned = 0
    drifted = []
    for pid, text in texts.items():
        for m in REPO_LINK.finditer(text):
            n_repo += 1
            path = m.group(1)
            full = os.path.join(ROOT, path)
            if not os.path.isfile(full):
                bad("%s: repo:%s is not a file in the tree" % (pid, path))
                continue
            if not m.group(2):
                continue
            n_pinned += 1
            lines = file_lines(path)
            first = int(m.group(2))
            last = int(m.group(3)) if m.group(3) else first
            if not (1 <= first <= last <= len(lines)):
                bad("%s: repo:%s#L%d%s is outside the file (%d lines)"
                    % (pid, path, first,
                       "-L%d" % last if last != first else "", len(lines)))
                continue
            key = (pid, path, first)
            seen.add(key)
            current = window(lines, first)
            if mode == "pin":
                records[key] = current
            elif key not in records:
                bad("%s: repo:%s#L%d has no record in _citations.tsv; run "
                    "tools/check-site-pages.py --pin" % (pid, path, first))
            elif records[key][0] != current[0]:
                drifted.append((pid, path, first, last, records[key], current,
                                m.group(0)[1:-1]))
    if mode == "pin":
        records = {k: v for k, v in records.items() if k in seen}
        write_pin(records)
        oks.append("ok - pinned %d line citations into docs/site/_citations.tsv"
                   % len(records))
    else:
        for key in sorted(set(records) - seen):
            bad("%s: _citations.tsv records repo:%s#L%d, which the page no "
                "longer cites; run --pin" % key)
    # Relocation is one pass per page keyed by the exact reference text,
    # never a sequence of text.replace calls: a page that cites L357 and
    # L358 shifts both by one, and replacing "#L357)" then "#L358)" in
    # turn moves the first citation twice.
    moves = {}
    removed, added = set(), {}
    for pid, path, first, last, want, got, ref in drifted:
        if mode != "fix":
            bad("%s: repo:%s#L%d cites a line that changed since it was "
                "pinned\n    pinned: %s\n    now:    %s"
                % (pid, path, first, want[0].strip(), got[0].strip()))
            continue
        lines = file_lines(path)
        where = [i + 1 for i, ln in enumerate(lines) if ln == want[0]]
        if len(where) > 1:
            narrowed = [n for n in where if window(lines, n) == want]
            if len(narrowed) == 1:
                where = narrowed
        if len(where) != 1:
            bad("%s: repo:%s#L%d drifted and its text occurs %d times now; "
                "fix by hand, then --pin\n    pinned: %s\n    now:    %s"
                % (pid, path, first, len(where), want[0].strip(),
                   got[0].strip()))
            continue
        new = where[0]
        new_ref = "repo:%s#L%d" % (path, new)
        if last != first:
            # keep the page's own spelling of the range end
            new_ref += ("-L%d" if "-L" in ref else "-%d") % (last + new - first)
        moves.setdefault(pid, {})[ref] = new_ref
        removed.add((pid, path, first))
        added[(pid, path, new)] = window(lines, new)
        oks.append("ok - %s: moved repo:%s#L%d to #L%d" % (pid, path, first, new))
    if moves:
        for pid, table in moves.items():
            text = open(site[pid], encoding="utf-8").read()
            text = REPO_LINK.sub(
                lambda m: "(" + table.get(m.group(0)[1:-1], m.group(0)[1:-1]) + ")",
                text)
            open(site[pid], "w", encoding="utf-8").write(text)
        for key in removed:
            records.pop(key, None)
        records.update(added)
        write_pin(records)
    if mode != "pin":
        oks.append("ok - %d repo: links name files in the tree; %d line "
                   "citations checked against _citations.tsv"
                   % (n_repo, n_pinned))

    # 5. voice, 6. images, 7. word budget
    for pid, text in texts.items():
        prose = prose_lines(text)
        joined = "\n".join(prose)
        hits = sorted(set(h.lower() for h in FORBIDDEN_RE.findall(joined)))
        if hits:
            bad("%s: forbidden phrase(s) in prose: %s" % (pid, ", ".join(hits)))
        if "—" in joined:
            bad("%s: em dash in prose" % pid)
        bangs = [ln for ln in prose if "!" in ln.replace("Play!", "")]
        if bangs:
            bad("%s: exclamation mark in prose: %s" % (pid, bangs[0].strip()))
        page_dir = os.path.dirname(site[pid])
        for m in IMAGE.finditer(text):
            src = m.group(1)
            if src.startswith("http"):
                continue
            if not (os.path.exists(os.path.join(page_dir, src))
                    or os.path.exists(os.path.join(SITE, src))):
                bad("%s: image %s does not exist" % (pid, src))
        words = len(joined.split())
        if words > 1500:
            bad("%s: %d prose words, budget is 1500" % (pid, words))
        section = pid.split("/")[0]
        if words < 300 and section not in ("project", "index"):
            bad("%s: %d prose words, budget is at least 300" % (pid, words))
    oks.append("ok - voice, images and word budgets hold on every page")

    for line in oks:
        print(line)
    for line in fails:
        print(line)
    print("%s - %d page(s), %d finding(s)"
          % ("not ok" if fails else "ok", len(site), len(fails)))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
