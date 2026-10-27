---
name: pull
description: Add a claude.ai artifact to the gallery so it is embedded and viewable there, not just linked. Use when the user runs /pull <link-or-id> or asks to add/save/import a claude.ai artifact into the gallery.
---

# Pull a claude.ai artifact into the gallery

Input: a claude.ai artifact link (`https://claude.ai/artifact/<id>` or `https://claude.ai/code/artifact/<uuid>`)
or just the id. `claude-artifact-gallery add` accepts both forms for `--url`, so pass what the user gave.

Private artifacts can only be read by you (the Artifact tool), never by the shell, so do it in two steps:

1. Read it: `Artifact` with `action: "read"` and `url` set to the full link. For a bare id use
   `https://claude.ai/artifact/<id>`. The result names the local file that holds the page; if it only
   returns a summary (an artifact owned by someone else), say so and stop, since there is no HTML to save.
2. Save it:
   ```
   claude-artifact-gallery add <that file> --url <link or id> [--title "<title>"]
   ```
   The title defaults to the page's `<title>`. Adding the same artifact again refreshes the saved copy.
3. Rebuild and open: `claude-artifact-gallery --no-open` (or without the flag to open the browser).

Report the title, the url and the gallery path. Do not edit `artifacts.md`; a registry entry with the same
url picks up the saved copy automatically.
