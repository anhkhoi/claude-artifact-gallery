import json
import re

from claude_artifact_gallery.cli import default_out, main


def embedded(out):
    text = out.read_text(encoding="utf-8")
    return json.loads(re.search(r"const ITEMS=(.*?);\n", text).group(1)), text


def build_tree(tmp_path, title="Type scale"):
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


def test_cli_smoke_writes_page_with_registry_and_canvas_kinds(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    build_tree(root)
    # an unreferenced canvas so both kinds survive the merge
    other = root / "docs" / "other"
    other.mkdir(parents=True)
    (other / "canvas.json").write_text(json.dumps({"title": "Loose canvas"}))
    code, out = run(tmp_path, root)
    items, _ = embedded(out)
    assert code == 0
    assert sorted(i["kind"] for i in items) == ["canvas", "registry", "registry"]
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
