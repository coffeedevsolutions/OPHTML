"""MkDocs hooks that adapt docs/site/ to the site generator.

docs/site/ARCHITECTURE.md fixes three things the generator cannot read on
its own, and this file supplies each of them at build time so the pages
stay generator-neutral:

  1. Navigation. Every page carries `section` and `order` in its
     frontmatter. on_config scans the pages and builds the nav from those
     fields, ordered as the architecture's page index lists them.
  2. `page:<id>#<anchor>` links. on_page_markdown rewrites each to a
     relative link to the target page's markdown file, which MkDocs then
     resolves, so a link to a missing page fails a --strict build. The
     heading half is not this build's to catch: MkDocs reports a missing
     anchor at INFO, which --strict does not escalate. That is
     tools/check-site-pages.py's job, and ci.yml runs it on every pull
     request with no paths filter.
  3. `repo:<path>#L<n>[-L<m>]` links. on_page_markdown rewrites each to a
     GitHub blob URL pinned to the commit being built (OPHTML_DOCS_REF,
     else git HEAD, else main). A line citation is verified by
     tools/check-site-pages.py against the tree at that commit, so the
     pin keeps it pointing at the cited line after main moves on.

on_files also publishes website/static/ under static/ in the built site,
so the favicon and stylesheet need not live inside docs/site/.

The two link regexes are the ones tools/check-site-pages.py uses, so the
checker and the build agree on what a link is.
"""

import logging
import os
import posixpath
import re
import subprocess

from mkdocs.structure.files import File

log = logging.getLogger("mkdocs.hooks.ophtml")

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
STATIC_DIR = os.path.join(HERE, "static")
GITHUB_REPO = "https://github.com/coffeedevsolutions/OPHTML"

# Section titles, in the order the architecture's page index lists them.
# A section that is not here still appears, after these, title-cased.
SECTIONS = {
    "getting-started": "Getting started",
    "authoring": "Authoring",
    "cli": "CLI",
    "runtime": "Runtime",
    "reference": "Reference",
    "examples": "Examples",
    "project": "Project",
}

PAGE_LINK = re.compile(r"\(page:([^)#\s]+)(?:#([^)\s]+))?\)")
REPO_LINK = re.compile(r"\(repo:([^)#\s]+)(?:#L(\d+)(?:-L?(\d+))?)?\)")
FRONTMATTER = re.compile(r"\A---[ \t]*\n(.*?\n)---[ \t]*\n", re.S)

# page id -> source path relative to docs_dir, filled by on_config.
PAGES = {}
REF = "main"


def _parse_frontmatter(text):
    """The flat `key: value` parse tools/check-site-pages.py uses.

    Not YAML on purpose. A page's `description` is a sentence, and three
    of them contain an unquoted colon that a YAML parser rejects. MkDocs
    swallows that error, returns no metadata, and leaves the block in
    the page body, so the site would show the frontmatter as text. The
    fields the build needs (id, title, section, order, description) are
    one line each, and this reads exactly those.
    """
    m = FRONTMATTER.match(text)
    if not m:
        return {}, text
    fm = {}
    for line in m.group(1).splitlines():
        if ":" in line and not line.startswith((" ", "\t")):
            k, v = line.split(":", 1)
            fm[k.strip()] = v.strip()
    return fm, text[m.end():]


def _frontmatter(path):
    with open(path, encoding="utf-8") as f:
        return _parse_frontmatter(f.read())[0]


def _excluded(rel, spec):
    """Whether MkDocs excludes this path, asked of MkDocs itself.

    `exclude_docs` is gitignore syntax, and MkDocs resolves it into a
    pathspec matcher before any hook runs. Reusing that matcher is what
    keeps this walk and MkDocs' own file collection from disagreeing: a
    second implementation here would silently diverge the first time a
    pattern is respelled (`_facts/**` for `_facts/`), and the build would
    then fail naming the files rather than the pattern.
    """
    if spec is None:
        return False
    return spec.match_file(rel)


def _git_ref():
    ref = os.environ.get("OPHTML_DOCS_REF")
    if ref:
        return ref
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, check=True,
            capture_output=True, text=True,
        )
        return out.stdout.strip() or "main"
    except (OSError, subprocess.CalledProcessError):
        return "main"


def _site_version(docs_dir):
    arch = os.path.join(docs_dir, "ARCHITECTURE.md")
    try:
        with open(arch, encoding="utf-8") as f:
            for line in f:
                if line.startswith("Site version:"):
                    return line.split(":", 1)[1].strip()
    except OSError:
        pass
    return None


def on_config(config):
    global REF
    REF = _git_ref()

    docs_dir = config["docs_dir"]
    spec = config.get("exclude_docs")

    PAGES.clear()
    pages = []
    for root, dirs, names in os.walk(docs_dir):
        dirs.sort()
        for name in sorted(names):
            if not name.endswith(".md"):
                continue
            path = os.path.join(root, name)
            rel = os.path.relpath(path, docs_dir).replace(os.sep, "/")
            if _excluded(rel, spec):
                continue
            meta = _frontmatter(path)
            pid = meta.get("id")
            if not pid:
                log.warning("%s has no id in its frontmatter, so it is "
                            "neither a page nor excluded; give it one or "
                            "add it to exclude_docs in mkdocs.yml", rel)
                continue
            if pid in PAGES:
                log.warning("page id %s is claimed by %s and %s", pid,
                            PAGES[pid], rel)
                continue
            PAGES[pid] = rel
            pages.append((meta.get("section", ""), int(meta.get("order", 0)),
                          pid, meta.get("title", pid), rel))

    # Sections in architecture order, then any unknown section by the
    # order of its first page. Pages inside a section by order, then id.
    by_section = {}
    for section, order, pid, title, rel in sorted(pages, key=lambda p: (p[1], p[2])):
        by_section.setdefault(section, []).append((order, pid, title, rel))

    nav = []
    home = PAGES.get("index")
    if home:
        nav.append({"Home": home})
    known = [s for s in SECTIONS if s in by_section]
    unknown = sorted((s for s in by_section if s not in SECTIONS and s != "root"),
                     key=lambda s: by_section[s][0][0])
    for section in known + unknown:
        title = SECTIONS.get(section, section.replace("-", " ").capitalize())
        entries = [{t: rel} for (_, pid, t, rel) in by_section[section]
                   if pid != "index"]
        nav.append({title: entries})
    config["nav"] = nav

    version = _site_version(docs_dir)
    if version:
        config["copyright"] = "OPHTML %s. MIT License." % version
    log.info("ophtml: %d pages in %d sections, repo links pinned to %s",
             len(PAGES), len(nav) - 1, REF)
    return config


def on_files(files, config):
    for root, _, names in os.walk(STATIC_DIR):
        for name in sorted(names):
            path = os.path.join(root, name)
            rel = os.path.relpath(path, STATIC_DIR).replace(os.sep, "/")
            files.append(File.generated(config, "static/" + rel,
                                        abs_src_path=path))
    return files


def on_page_markdown(markdown, page, config, files):
    src = page.file.src_uri
    base = posixpath.dirname(src) or "."

    # MkDocs strips the frontmatter only when its YAML parse succeeds;
    # see _parse_frontmatter. Strip it here regardless, and fill in the
    # metadata the theme reads (description, for the <meta> tag).
    meta, markdown = _parse_frontmatter(markdown)
    for key, value in meta.items():
        page.meta.setdefault(key, value)

    def page_link(m):
        pid, anchor = m.group(1), m.group(2)
        target = PAGES.get(pid)
        if target is None:
            log.warning("%s: page:%s is not a page", src, pid)
            return m.group(0)
        href = posixpath.relpath(target, base)
        if anchor:
            href += "#" + anchor
        return "(%s)" % href

    def repo_link(m):
        path, first, last = m.group(1), m.group(2), m.group(3)
        if not os.path.isfile(os.path.join(REPO_ROOT, path)):
            log.warning("%s: repo:%s is not a file in the tree", src, path)
        href = "%s/blob/%s/%s" % (GITHUB_REPO, REF, path)
        if first:
            href += "#L" + first
            if last:
                href += "-L" + last
        return "(%s)" % href

    markdown = PAGE_LINK.sub(page_link, markdown)
    markdown = REPO_LINK.sub(repo_link, markdown)
    return markdown
