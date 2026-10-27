# claude-artifact-gallery

Python CLI (`src/claude_artifact_gallery/`), tests in `tests/` (`.venv/bin/python -m pytest -q`).

## Versioning

Every time you commit and push, bump the version in the same commit. Pick the level yourself; do not ask.
The only place the version lives is `version` in `pyproject.toml` (`--version` and `upgrade` read it from there).

- **major** (X.0.0): a breaking change for users: a command, flag, skill name or output people script against is
  renamed or removed, or the on-disk cache layout changes so old data stops working.
- **minor** (0.X.0): new behaviour that stays compatible: a new command, flag, artifact kind or skill capability.
- **patch** (0.0.X): fixes, docs, wording, output formatting, tests and refactors with no behaviour change.

While the major version is 0, a breaking change bumps minor instead. When one push mixes levels, use the highest.

Do it as part of the commit and push, not as a separate step:

1. Run the tests first; do not bump on a red run.
2. Edit `version` in `pyproject.toml`.
3. Put the new version in the commit subject or body (e.g. `feat: ... (v0.3.0)`).
4. In your reply, state the old and new version and the one-line reason for the level you chose.

Commit and push only when the user asks, as before; this rule only says what a commit must contain.
