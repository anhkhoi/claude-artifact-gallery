import json
import re

from claude_artifact_gallery.cli import default_out, main


def embedded(out):
    text = out.read_text(encoding="utf-8")
    return json.loads(re.search(r"const ITEMS=(.*?);\n", text).group(1)), text


def build_tree(tmp_path, title="Type scale"):
    run = tmp_path / ".archify" / "workflow-x-20261024-000000"
    run.mkdir(parents=True)
    (run / "x.html").write_text("<html></html>")
    canvas = tmp_path / "ai-review" / "design" / "type-scale"
    canvas.mkdir(parents=True)
    (canvas / "Main.dc.html").write_text("<div></div>")
    (canvas / "canvas.json").write_text(json.dumps(
        {"title": "Review", "order": ["Main.dc.html"], "boards": {"Main.dc.html": {"w": 800, "h": 600}}}))
    (tmp_path / "ai-review" / "artifacts.md").write_text(
        f"## Design system\n- [{title}](https://claude.ai/artifact/a): scale (2026-10-17). Copy: `ai-review/design/type-scale/`.\n"
        "- [Only link](https://claude.ai/artifact/b): private page (2026-10-18). No repo copy.\n",
        encoding="utf-8")


def run(tmp_path, root=None):
    out = tmp_path / "out.html"
    code = main([str(root or tmp_path), "-o", str(out), "--no-open"])
    return code, out


def test_cli_smoke_writes_page_with_all_three_kinds(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    build_tree(root)
    # an unreferenced canvas so all three kinds survive the merge
    other = root / "docs" / "other"
    other.mkdir(parents=True)
    (other / "canvas.json").write_text(json.dumps({"title": "Loose canvas"}))
    code, out = run(tmp_path, root)
    items, _ = embedded(out)
    assert code == 0
    assert sorted(i["kind"] for i in items) == ["archify", "canvas", "registry", "registry"]
    merged = next(i for i in items if i["title"] == "Type scale")
    assert merged["url"] and merged["boards"][0]["w"] == 800


def test_empty_root_renders_and_exits_zero(tmp_path):
    root = tmp_path / "empty"
    root.mkdir()
    code, out = run(tmp_path, root)
    items, text = embedded(out)
    assert code == 0 and items == [] and "No artifacts" in text


def test_script_end_tag_in_title_is_escaped(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    build_tree(root, title="x</script>y")
    _, out = run(tmp_path, root)
    items, text = embedded(out)
    assert "</script>y" not in text
    assert any(i["title"] == "x</script>y" for i in items)


def test_vietnamese_text_roundtrips(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    build_tree(root, title="Bài học · Ngữ pháp")
    _, out = run(tmp_path, root)
    items, _ = embedded(out)
    assert any(i["title"] == "Bài học · Ngữ pháp" for i in items)


def test_default_out_is_outside_root(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    root = tmp_path / "repo"
    root.mkdir()
    out = default_out(root)
    assert out.parent == tmp_path / "cache" / "claude-artifact-gallery"
    assert out.name.startswith("repo-") and out.suffix == ".html"


def test_canvas_without_boards_gets_no_private_page_message(tmp_path):
    from claude_artifact_gallery.page import PAGE
    assert "has no boards" in PAGE


def test_empty_or_relative_xdg_cache_home_falls_back_to_home_cache(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    root = tmp_path / "repo"
    root.mkdir()
    for bad in ("", "relative/cache"):
        monkeypatch.setenv("XDG_CACHE_HOME", bad)
        assert default_out(root).parent == tmp_path / "home" / ".cache" / "claude-artifact-gallery"


def test_page_guards_bad_hash_and_refits_on_pane_resize():
    from claude_artifact_gallery.page import PAGE
    assert "try{return decodeURIComponent" in PAGE
    assert "new ResizeObserver(fit)" in PAGE


def test_kind_tags_have_distinct_colours_in_light_and_dark():
    from claude_artifact_gallery.page import PAGE
    for kind in ("archify", "registry", "canvas"):
        assert PAGE.count(f"--k-{kind}:") == 2  # light + dark theme
        assert f".tag.k-{kind}" in PAGE
    assert 'class="tag k-${esc(i.kind)}"' in PAGE


def test_page_embeds_scanned_root_name_and_path(tmp_path):
    root = tmp_path / "my-project"
    root.mkdir()
    _, out = run(tmp_path, root)
    text = out.read_text(encoding="utf-8")
    info = json.loads(re.search(r"const ROOT=(.*?);\n", text).group(1))
    assert info == {"name": "my-project", "path": str(root.resolve())}


def test_root_name_is_a_button_that_copies_the_folder_path():
    from claude_artifact_gallery.page import PAGE
    assert '<button class="root" id="root"' in PAGE
    assert "navigator.clipboard.writeText(t)" in PAGE
    assert "copy(ROOT.path)" in PAGE
    assert 'execCommand("copy")' in PAGE  # fallback when the Clipboard API is unavailable
