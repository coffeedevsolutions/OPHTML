# website/

The MkDocs build for the documentation site. The pages themselves live in
`docs/site/` and are written against `docs/site/ARCHITECTURE.md`, which
keeps them free of any site generator. This directory is the generator:
delete it and the pages are unchanged.

| file | role |
|---|---|
| `mkdocs.yml` | site configuration. `docs_dir` points at `../docs/site`, output goes to `website/build/` (gitignored). |
| `hooks.py` | builds the navigation from each page's `section` and `order` frontmatter, rewrites `page:` links to site paths and `repo:` links to GitHub blob URLs pinned to the commit being built, and publishes `static/`. |
| `static/` | the favicon and the stylesheet, served at `/static/`. |
| `requirements.txt` | pinned MkDocs and Material versions. |

The deploy workflow is `.github/workflows/docs.yml`. It runs
`tools/check-site-pages.py`, then `mkdocs build --strict`, on every pull
request that touches the site, and deploys to GitHub Pages on pushes to
`main`. The published site is
<https://coffeedevsolutions.github.io/OPHTML/>.

## Run it locally

```
pip install -r website/requirements.txt
mkdocs serve -f website/mkdocs.yml
```

`mkdocs build --strict -f website/mkdocs.yml` is what the workflow runs. A
`page:` link to a missing page, a missing image, or a page absent from the
nav fails it. A same-page `#anchor` that names no heading is reported as
an INFO line and does not fail the build; fix it in the page.

Locally, `repo:` links pin to `git rev-parse HEAD`. Set `OPHTML_DOCS_REF`
to pin to something else, as the workflow does with the pushed commit.

## One-time setup

GitHub Pages must be set to deploy from a workflow before the first run of
`docs.yml` can publish: repository Settings, Pages, Source, "GitHub
Actions". Until then the deploy job fails with a message saying Pages is
not configured, and the build job still runs as a check.

## Adding a page

Follow `docs/site/ARCHITECTURE.md`. Nothing here needs editing: the nav
comes from the frontmatter. A new section key needs a title in the
`SECTIONS` table in `hooks.py`, or it appears after the known sections
with its key capitalised.

## Customising

Colours, fonts, the header icon, and the navigation features are the
`theme:` block in `mkdocs.yml`; the Material reference at
<https://squidfunk.github.io/mkdocs-material/setup/> documents each key.
Page styling goes in `static/extra.css`. Template overrides, if ever
needed, are a `custom_dir` under `theme:` pointing at a directory here,
not inside `docs/site/`.

`requirements.txt` pins MkDocs 1.6. Material prints a notice about MkDocs
2.0 on every build; the pin is why it does not apply.
