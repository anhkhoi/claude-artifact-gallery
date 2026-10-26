# claude-artifact-gallery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A stdlib-only CLI that scans a folder for Claude artifacts (archify HTML, claude.ai registry entries, design canvases) and writes one self-contained gallery page.

**Architecture:** Three source scanners each return `Item`s; `model.merge` joins registry entries with the canvas folder they point to; `page.render` embeds the items as JSON in an HTML template; `cli` wires root detection, output path and opening the browser.

**Tech Stack:** Python >=3.8, stdlib only at runtime; pytest for tests; setuptools with `src/` layout.

> **Scope change after execution:** the `.archify` source (Task 4) was dropped; the tool covers claude.ai registry entries and design canvases only.

**Spec:** `docs/superpowers/specs/2026-10-26-claude-artifact-gallery-design.md`

## Global Constraints

- Package `claude_artifact_gallery` under `src/`; console script `claude-artifact-gallery = claude_artifact_gallery.cli:main`.
- Python `>=3.8`, `dependencies = []`.
- CLI: `claude-artifact-gallery [ROOT] [-o OUT] [--no-open]`; ROOT defaults to git root of cwd else cwd.
- Default OUT `~/.cache/claude-artifact-gallery/<root-name>-<sha1(root)[:8]>.html` (honour `XDG_CACHE_HOME`); never write into the scanned repo.
- Skip dirs while walking: `node_modules`, `.git`, `.venv`, `venv`, `__pycache__`, `.next`.
- Registry line format: `- [title](url): purpose (YYYY-MM-DD). Copy: path`, under `## Area` headings; unmatched lines are skipped with a warning.
- A bad file or malformed JSON never aborts the run; print a summary of counts per kind and skipped count.
- Item kinds are exactly `archify`, `registry`, `canvas`.

## Review Focus

- ROOT with no artifacts at all: page still renders with an empty-state message, exit code 0.
- `Copy:` path in the registry that does not exist, or lists several paths (`Copy: \`a\`, \`b\``): entry stays a registry-only item; with several, the first existing one is used.
- Registry line saying `No repo copy` or with no URL-bearing link: no crash, no local preview.
- Title or purpose containing `</script>`, quotes or Vietnamese text: embedded JSON must not break the page.
- `canvas.json` whose `order` names a board file that is missing, or lists no boards: missing boards are skipped, the rest still show.

---

### Task 1: Scaffold, `Item` model and merge

**Files:**
- Create: `pyproject.toml`, `.gitignore`, `src/claude_artifact_gallery/__init__.py`, `src/claude_artifact_gallery/model.py`, `src/claude_artifact_gallery/sources/__init__.py`, `tests/test_model.py`

**Interfaces:**
- Produces:
  - `@dataclass Item(kind: str, title: str, group: str, purpose: str = "", date: str = "", url: str = "", href: str = "", boards: list = field(default_factory=list), tags: list = field(default_factory=list), meta: dict = field(default_factory=dict))` with `.to_dict() -> dict`. `boards` entries are `{"title": str, "href": str, "w": int, "h": int}`; `href` is a `file://` URI or `""`; `url` is the claude.ai URL or `""`.
  - `merge(registry: list[Item], canvases: list[Item], copy_paths: dict[str, Path]) -> list[Item]` where `copy_paths` maps a registry item's `title` to its resolved existing Copy folder. A registry item whose folder equals a canvas item's folder (`canvas.meta["dir"]`) becomes one item: registry's title/purpose/date/url/group plus the canvas's `boards`; that canvas is dropped from the output. Other items pass through unchanged.

- [ ] **Step 1: Write failing tests** in `tests/test_model.py`: `test_merge_joins_registry_with_canvas` (registry item + canvas with `meta["dir"]` equal to the mapped path → one item, `url` kept, `boards` from canvas, kind `registry`), `test_merge_keeps_unreferenced_canvas` (canvas not mapped stays kind `canvas`), `test_merge_registry_without_copy_passes_through`, `test_to_dict_is_json_serialisable` (`json.dumps(item.to_dict())` works with a `Path` in `meta` converted to `str`).
- [ ] **Step 2: Run `pytest tests/test_model.py -v`**; expected: FAIL (import error).
- [ ] **Step 3: Create the scaffold** (`pyproject.toml` with `[project.optional-dependencies] test = ["pytest"]`; `.gitignore` for `__pycache__`, `*.egg-info`, `.venv`) and implement `Item`/`merge` in `model.py`.
- [ ] **Step 4: Run `pytest tests/test_model.py -v`**; expected: PASS.
- [ ] **Step 5: Commit** `feat: scaffold package, Item model and merge`.

### Task 2: Registry parser

**Files:**
- Create: `src/claude_artifact_gallery/sources/registry.py`, `tests/test_registry.py`

**Interfaces:**
- Consumes: `Item` from Task 1.
- Produces: `parse_registry(path: Path, root: Path, warn=print) -> tuple[list[Item], dict[str, Path]]`. Returns kind `registry` items (`group` = nearest `## ` heading, `""` if none) and the `copy_paths` map for `merge` (paths resolved against `root`, only if they exist as directories). `find_registries(root: Path) -> list[Path]` returns every `artifacts.md` under `root`, skipping the Global Constraints dirs.

- [ ] **Step 1: Write failing tests**, using an inline registry text written to `tmp_path`: `test_parses_title_url_purpose_date_group`, `test_extracts_copy_path_when_dir_exists`, `test_copy_path_missing_dir_is_ignored`, `test_multiple_copy_paths_uses_first_existing`, `test_no_repo_copy_line_has_no_preview`, `test_malformed_line_is_skipped_with_warning` (`warn` called once, other lines still parsed), `test_find_registries_skips_node_modules`.
- [ ] **Step 2: Run `pytest tests/test_registry.py -v`**; expected: FAIL.
- [ ] **Step 3: Implement** with one compiled regex for the bullet line and a second for `Copy:` backticked paths; the trailing `(YYYY-MM-DD)` may also be `(YYYY-MM-DD, cập nhật …)`, so take the first date.
- [ ] **Step 4: Run `pytest tests/test_registry.py -v`**; expected: PASS.
- [ ] **Step 5: Commit** `feat: parse artifacts.md registry`.

### Task 3: Canvas scanner

**Files:**
- Create: `src/claude_artifact_gallery/sources/canvas.py`, `tests/test_canvas.py`

**Interfaces:**
- Consumes: `Item`.
- Produces: `find_canvases(root: Path, warn=print) -> list[Item]`: one kind `canvas` item per folder containing `canvas.json`; `title` from `canvas.json["title"]` else folder name; `group` = folder's parent name; `meta["dir"]` = resolved folder `Path`; `boards` in `order` (fall back to the `boards` dict keys), each `{"title": boards[f]["title"] or stem, "href": file URI, "w": …, "h": …}`; boards whose file is missing are skipped; `date` from the newest board mtime (`YYYY-MM-DD`).

- [ ] **Step 1: Write failing tests**: `test_boards_follow_order_with_titles_and_sizes`, `test_missing_board_file_is_skipped`, `test_malformed_canvas_json_is_skipped_with_warning`, `test_canvas_without_boards_yields_empty_boards`.
- [ ] **Step 2: Run `pytest tests/test_canvas.py -v`**; expected: FAIL.
- [ ] **Step 3: Implement** with `os.walk`, pruning the Global Constraints dirs.
- [ ] **Step 4: Run `pytest tests/test_canvas.py -v`**; expected: PASS.
- [ ] **Step 5: Commit** `feat: scan design canvases`.

### Task 4: Archify scanner

**Files:**
- Create: `src/claude_artifact_gallery/sources/archify.py`, `tests/test_archify.py`

**Interfaces:**
- Consumes: `Item`.
- Produces: `find_archify(root: Path) -> list[Item]`: kind `archify`, `group` = project path relative to root (`"."` for root), `title` from `candidate.json` `meta.title` else html stem, `tags=[diagram_type or run-name prefix]`, `href` file URI, `date` from mtime (`YYYY-MM-DD HH:MM`), `meta` = `{"size": bytes, "check": status}` where check is `browser-check.json["status"]` else `"ok"` if `finalize-summary.json["ok"]` else `""`.

- [ ] **Step 1: Write failing tests** building a fake `.archify/<run>/` tree: `test_reads_title_type_and_check`, `test_falls_back_to_stem_when_candidate_missing`, `test_ignores_archify_dirs_inside_node_modules`.
- [ ] **Step 2: Run `pytest tests/test_archify.py -v`**; expected: FAIL.
- [ ] **Step 3: Implement** by walking the tree for `.archify` dirs (pruning the Global Constraints dirs) and reading the JSON files tolerantly.
- [ ] **Step 4: Run `pytest tests/test_archify.py -v`**; expected: PASS.
- [ ] **Step 5: Commit** `feat: scan .archify outputs`.

### Task 5: Page renderer and CLI

**Files:**
- Create: `src/claude_artifact_gallery/page.py`, `src/claude_artifact_gallery/cli.py`, `tests/test_cli.py`

**Interfaces:**
- Consumes: `find_archify`, `find_canvases`, `find_registries`, `parse_registry`, `merge`, `Item.to_dict`.
- Produces: `collect(root: Path) -> tuple[list[Item], dict]` (items sorted newest first; dict is `{"archify": n, "registry": n, "canvas": n, "skipped": n}`); `render(items: list[Item]) -> str` (full HTML; embeds `json.dumps(..., ensure_ascii=False)` with `</` replaced by `<\/`); `main(argv=None) -> int`.
- Page behaviour per spec: sidebar with search, kind filter, group filter; grouped list; URL-hash selection; viewer per kind (archify iframe; canvas boards stacked, each iframe at `w×h` scaled to pane width via CSS `transform: scale`; registry-only card with "Open on claude.ai ↗" and the private-page note; merged items show boards plus the claude.ai link); empty-state message; system dark/light.

- [ ] **Step 1: Write failing tests**: `test_cli_smoke_writes_page_with_all_three_kinds` (fixture tree with one `.archify` run, one canvas folder, one `artifacts.md`; run `main([str(root), "-o", str(out), "--no-open"])`, extract the embedded JSON by regex `const ITEMS=(.*?);\n`, assert kinds and exit code 0), `test_empty_root_renders_and_exits_zero`, `test_script_end_tag_in_title_is_escaped` (title `x</script>y`; the output contains no raw `</script>y`), `test_vietnamese_text_roundtrips`, `test_default_out_is_outside_root` (with `XDG_CACHE_HOME=tmp`).
- [ ] **Step 2: Run `pytest tests/test_cli.py -v`**; expected: FAIL.
- [ ] **Step 3: Implement** `page.py` (template string plus `render`) and `cli.py` (`default_root`, `default_out`, `collect`, `main`, summary line like `N artifact(s): archify A, registry R, canvas C, skipped S -> OUT`).
- [ ] **Step 4: Run `pytest -v`**; expected: all tests PASS.
- [ ] **Step 5: Commit** `feat: render gallery page and CLI`.

### Task 6: Real-data check and README

**Files:**
- Create: `README.md`

- [ ] **Step 1: Install editable** with `pip install -e '.[test]'` (or `pipx install -e .`) and run `claude-artifact-gallery <sample-project> --no-open`; expected: summary line with 4 archify, the registry entries from `ai-review/artifacts.md`, and the canvas folders under `ai-review/design/`, with skipped count printed.
- [ ] **Step 2: Open the output in a browser** (Claude in Chrome or `open`) and confirm: an archify item renders in the iframe, a merged registry item (for example `Type scale`) shows three boards stacked with titles and its claude.ai link, a registry-only item (for example `Reading · Student workspace · Security and grading fixes`) shows the private-page card. Fix any rendering defect found, with a regression test where it is testable.
- [ ] **Step 3: Write `README.md`**: install, usage line, the three sources and the registry line format, output location.
- [ ] **Step 4: Run `pytest -v`**; expected: all PASS.
- [ ] **Step 5: Commit** `docs: README and real-data verification`.
