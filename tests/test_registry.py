from claude_artifact_gallery.sources.registry import find_registries, parse_registry

HEAD = "# Artifacts\n\nintro line\n\n"


def write(tmp_path, body):
    p = tmp_path / "ai-review" / "artifacts.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(HEAD + body, encoding="utf-8")
    return p


def test_parses_title_url_purpose_date_group(tmp_path):
    p = write(tmp_path, "## Reading\n\n- [Reading · Workspace · Design](https://claude.ai/artifact/abc): workspace desktop and mobile (2026-10-25). Copy: `ai-review/design/x/`.\n")
    items, _ = parse_registry(p, tmp_path)
    assert len(items) == 1
    i = items[0]
    assert (i.kind, i.group) == ("registry", "Reading")
    assert i.title == "Reading · Workspace · Design"
    assert i.url == "https://claude.ai/artifact/abc"
    assert i.purpose == "workspace desktop and mobile"
    assert i.date == "2026-10-25"


def test_extracts_copy_path_when_dir_exists(tmp_path):
    (tmp_path / "ai-review/design/x").mkdir(parents=True)
    p = write(tmp_path, "## A\n- [T](https://claude.ai/artifact/a): p (2026-10-01). Copy: `ai-review/design/x/`.\n")
    _, copies = parse_registry(p, tmp_path)
    assert copies == {"https://claude.ai/artifact/a": (tmp_path / "ai-review/design/x").resolve()}


def test_copy_path_missing_dir_is_ignored(tmp_path):
    p = write(tmp_path, "## A\n- [T](https://claude.ai/artifact/a): p (2026-10-01). Copy: `nope/`.\n")
    items, copies = parse_registry(p, tmp_path)
    assert len(items) == 1 and copies == {}


def test_multiple_copy_paths_uses_first_existing(tmp_path):
    (tmp_path / "b").mkdir()
    p = write(tmp_path, "## A\n- [T](https://claude.ai/artifact/a): p (2026-10-01). Copy: `a/`, `b/`. Rename to `Other · Title`.\n")
    _, copies = parse_registry(p, tmp_path)
    assert copies == {"https://claude.ai/artifact/a": (tmp_path / "b").resolve()}


def test_no_repo_copy_line_has_no_preview(tmp_path):
    p = write(tmp_path, "## A\n- [T](https://claude.ai/artifact/a): p (2026-10-01). No repo copy (plain page).\n")
    items, copies = parse_registry(p, tmp_path)
    assert len(items) == 1 and copies == {}


def test_malformed_line_is_skipped_with_warning(tmp_path):
    p = write(tmp_path, "## A\n- [Broken]: no url here\n- [Ok](https://claude.ai/artifact/a): fine (2026-10-01)\n")
    warned = []
    items, _ = parse_registry(p, tmp_path, warn=warned.append)
    assert [i.title for i in items] == ["Ok"]
    assert len(warned) == 1


def test_find_registries_skips_node_modules(tmp_path):
    write(tmp_path, "")
    nm = tmp_path / "node_modules" / "pkg"
    nm.mkdir(parents=True)
    (nm / "artifacts.md").write_text("x")
    assert find_registries(tmp_path) == [tmp_path / "ai-review" / "artifacts.md"]


def test_non_utf8_registry_is_skipped_with_warning(tmp_path):
    p = tmp_path / "artifacts.md"
    p.write_bytes(b"## A\n- [T](https://claude.ai/artifact/a): caf\xff\n")
    warned = []
    assert parse_registry(p, tmp_path, warn=warned.append) == ([], {})
    assert len(warned) == 1


def test_duplicate_titles_get_their_own_copy_paths(tmp_path):
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    p = write(tmp_path, "## A\n- [Dup](https://claude.ai/artifact/1): p (2026-01-01). Copy: `a`\n"
                        "## B\n- [Dup](https://claude.ai/artifact/2): q (2026-01-02). Copy: `b`\n")
    _, copies = parse_registry(p, tmp_path)
    assert copies == {"https://claude.ai/artifact/1": (tmp_path / "a").resolve(),
                      "https://claude.ai/artifact/2": (tmp_path / "b").resolve()}


def test_copy_path_resolves_when_root_is_a_subfolder(tmp_path):
    (tmp_path / "ai-review/design/x").mkdir(parents=True)
    p = write(tmp_path, "## A\n- [T](https://claude.ai/artifact/a): p (2026-10-01). Copy: `ai-review/design/x/`.\n")
    _, copies = parse_registry(p, tmp_path / "ai-review")
    assert copies == {"https://claude.ai/artifact/a": (tmp_path / "ai-review/design/x").resolve()}


def test_copy_path_without_backticks(tmp_path):
    (tmp_path / "d/x").mkdir(parents=True)
    p = write(tmp_path, "## A\n- [T](https://claude.ai/artifact/a): p (2026-10-01). Copy: d/x/.\n")
    _, copies = parse_registry(p, tmp_path)
    assert copies == {"https://claude.ai/artifact/a": (tmp_path / "d/x").resolve()}
