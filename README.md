# claude-artifact-gallery

Browse your Claude artifacts in one page: a searchable gallery of published claude.ai artifacts, local
design canvases and archify diagrams, found by scanning a project folder.

```
pipx install git+https://github.com/anhkhoi/claude-artifact-gallery.git
# or from a local clone: pipx install -e .
cd <any repo>
claude-artifact-gallery            # scans git root, opens the gallery
claude-artifact-gallery [ROOT] [-o OUT] [--no-open]
```

The gallery is written to `~/.cache/claude-artifact-gallery/`, never into the scanned repo.

## What it finds

| Kind | Found by | Shown as |
|------|----------|----------|
| `archify` | `.archify/<run>/*.html` | the page in an iframe |
| `registry` | `artifacts.md` | entry with a link to claude.ai (those pages are private and cannot be embedded) |
| `canvas` | folder with `canvas.json` and `*.dc.html` boards | the boards stacked, scaled to the pane |

A registry line looks like this; when `Copy:` names a folder that holds (or contains) a canvas, the entry
also shows that canvas's boards:

```
## Area
- [Title](https://claude.ai/artifact/<id>): purpose (YYYY-MM-DD). Copy: `path/to/folder/`.
```

Lines that do not match are skipped with a warning; a summary line prints counts per kind.

## Tests

```
pip install -e '.[test]' && pytest
```
