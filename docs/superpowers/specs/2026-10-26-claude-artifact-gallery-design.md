# claude-artifact-gallery — design

Date: 2026-10-26. Status: approved in chat, pending spec review.

## Purpose

A stdlib-only Python CLI that scans a project folder for Claude artifacts and writes one
self-contained, browsable HTML gallery page (sidebar, search, embedded viewer).

```
claude-artifact-gallery [ROOT] [-o OUT] [--no-open]
```

ROOT defaults to the git root of the cwd, else the cwd. OUT defaults to
`~/.cache/claude-artifact-gallery/<root>-<hash>.html`; nothing is written into the scanned repo.

## Artifact sources

| Kind | Found by | Metadata |
|------|----------|----------|
| `registry` | `**/artifacts.md` | `- [title](url): purpose (YYYY-MM-DD). Copy: path`, grouped under `## Area` headings |
| `canvas` | folders containing `canvas.json` | board order, titles, `x/y/w/h`; boards are `*.dc.html` |

A registry entry whose `Copy:` path resolves to a canvas folder is merged with it into one item:
claude.ai link plus local preview. Registry URLs are private to the owner's account and cannot be embedded.

## Modules

- `sources/registry.py` — parse `artifacts.md`; skip and warn on lines that do not match.
- `sources/canvas.py` — read `canvas.json`, list `*.dc.html` boards in `order`.
- `model.py` — single `Item` type; merge registry + canvas.
- `page.py` — HTML template and rendering of items into the page.
- `cli.py` — arguments, root detection, write and open.

## Page behaviour

- Sidebar: search, kind filter, area/project filter; items grouped by area.
- Selection lives in the URL hash.
- `canvas`: boards stacked vertically, each in an iframe of its `w×h` scaled to the pane, title above.
  `.dc.html` files reference a `support.js` that is absent from repo copies; the unknown `<x-dc>` tag
  is ignored by the browser and the styled content still lays out.
- `registry`-only: card with purpose, date and "Open on claude.ai ↗", with a note that the page is private.
- Dark/light follows the system.

## Errors

A missing or unreadable file or malformed JSON never aborts the run: the item is skipped or shown
without that metadata. A summary line prints counts per kind and the number skipped.

## Testing

pytest with miniature fixtures taken from `learnig`: registry parser (normal line, line with `Copy:`,
malformed line), canvas board ordering, registry + canvas merge, and a CLI smoke test that checks the
embedded JSON of the output file. Manual check: open the real `learnig` gallery in a browser.

## Out of scope

Fetching claude.ai pages, a live server or file watching, editing the registry.
