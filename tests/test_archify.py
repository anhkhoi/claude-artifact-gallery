import json

from claude_artifact_gallery.sources.archify import find_archify


def run_dir(tmp_path, project=".", name="workflow-tts-20261024-214016"):
    base = tmp_path if project == "." else tmp_path / project
    d = base / ".archify" / name
    d.mkdir(parents=True)
    return d


def test_reads_title_type_and_check(tmp_path):
    d = run_dir(tmp_path, project="apps/web")
    (d / "candidate.json").write_text(json.dumps({"diagram_type": "workflow", "meta": {"title": "TTS audio"}}))
    (d / "tts.html").write_text("<html></html>")
    (d / "tts.browser-check.json").write_text(json.dumps({"status": "pass"}))
    [i] = find_archify(tmp_path)
    assert (i.kind, i.title, i.group) == ("archify", "TTS audio", "apps/web")
    assert i.tags == ["workflow"] and i.meta["check"] == "pass"
    assert i.href.startswith("file://") and i.meta["size"] == len("<html></html>")


def test_falls_back_to_stem_when_candidate_missing(tmp_path):
    d = run_dir(tmp_path)
    (d / "overview.html").write_text("x")
    (d / "overview.finalize-summary.json").write_text(json.dumps({"ok": True}))
    [i] = find_archify(tmp_path)
    assert (i.title, i.group, i.tags, i.meta["check"]) == ("overview", ".", ["workflow"], "ok")


def test_ignores_archify_dirs_inside_node_modules(tmp_path):
    d = run_dir(tmp_path, project="node_modules/pkg")
    (d / "a.html").write_text("x")
    assert find_archify(tmp_path) == []


def test_bad_candidate_meta_does_not_abort(tmp_path):
    d = run_dir(tmp_path)
    (d / "candidate.json").write_text(json.dumps({"meta": "oops"}))
    (d / "a.html").write_text("x")
    [i] = find_archify(tmp_path)
    assert i.title == "a"


def test_broken_html_symlink_is_skipped(tmp_path):
    d = run_dir(tmp_path)
    (d / "ok.html").write_text("x")
    (d / "dead.html").symlink_to(tmp_path / "missing.html")
    assert [i.title for i in find_archify(tmp_path)] == ["ok"]
