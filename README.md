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

Optional, to also add private claude.ai artifacts from Claude Code with `/pull` (see
[Adding a claude.ai artifact](#adding-a-claudeai-artifact)):

```
claude-artifact-gallery install-skill
```

The gallery is written to `~/.cache/claude-artifact-gallery/`, never into the scanned repo.

## What it finds

| Kind | Found by | Shown as |
|------|----------|----------|
| `archify` | `.archify/<run>/*.html` | the page in an iframe |
| `registry` | `artifacts.md` | entry with a link to claude.ai (those pages are private and cannot be embedded) |
| `pulled` | `claude-artifact-gallery add` | the saved HTML of a claude.ai artifact, in an iframe, with the claude.ai link |
| `canvas` | folder with `canvas.json` and `*.dc.html` boards | the boards stacked, scaled to the pane |

A registry line looks like this; when `Copy:` names a folder that holds (or contains) a canvas, the entry
also shows that canvas's boards:

```
## Area
- [Title](https://claude.ai/artifact/<id>): purpose (YYYY-MM-DD). Copy: `path/to/folder/`.
```

Lines that do not match are skipped with a warning; a summary line prints counts per kind.

## Adding a claude.ai artifact

Private artifacts can only be read from inside Claude Code, so there it is a skill. Install it once (it
goes to `$CLAUDE_CONFIG_DIR/skills`, else `~/.claude/skills`; `--force` overwrites a different copy):

```
claude-artifact-gallery install-skill
```

Then, in any project, run
`/pull https://claude.ai/artifact/<id>` (or `/pull <id>`, or just ask "add this artifact to the gallery").
Claude reads the page and runs

```
claude-artifact-gallery add page.html --url <link-or-id> [--title T] [--group G]
```

which copies the HTML into `~/.cache/claude-artifact-gallery/pulled/`. Adding the same artifact again
refreshes it; a registry entry with the same link shows the saved copy instead of a second item.

## Update

When new code is pushed, run:

```
claude-artifact-gallery upgrade
```

It reinstalls the latest from GitHub with the tool you installed with (pipx, else pip), then refreshes the
`/pull` skill if you had installed it. It needs `git` and network access. A copy running from a local clone
is left alone (use `git pull` there). If `upgrade` cannot run, this does the same by hand:

```
pipx install --force git+https://github.com/anhkhoi/claude-artifact-gallery.git && claude-artifact-gallery install-skill --force
```

`claude-artifact-gallery --version` shows what you have, e.g. `0.1.0 (commit 54fd83b)`. If an installed
`/pull` skill is older than the package, running the gallery prints a one-line reminder to refresh it.

## Tests

```
pip install -e '.[test]' && pytest
```
