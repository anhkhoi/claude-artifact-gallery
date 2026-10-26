import json
from pathlib import Path

from claude_artifact_gallery.model import Item, merge


def reg(title="Type scale", **kw):
    return Item(kind="registry", title=title, group="Design system",
                purpose="scale", date="2026-10-17", url="https://claude.ai/artifact/x", **kw)


def canvas(d: Path, title="Lesson Preview Type Review"):
    boards = [{"title": "Main", "href": "file:///m.html", "w": 1000, "h": 820}]
    return Item(kind="canvas", title=title, group="design", boards=boards, meta={"dir": d})


def test_merge_joins_registry_with_canvas(tmp_path):
    out = merge([reg()], [canvas(tmp_path)], {"https://claude.ai/artifact/x": tmp_path})
    assert len(out) == 1
    assert out[0].kind == "registry"
    assert out[0].title == "Type scale"
    assert out[0].url == "https://claude.ai/artifact/x"
    assert out[0].boards[0]["title"] == "Main"


def test_merge_keeps_unreferenced_canvas(tmp_path):
    out = merge([reg()], [canvas(tmp_path)], {})
    assert sorted(i.kind for i in out) == ["canvas", "registry"]


def test_merge_registry_without_copy_passes_through():
    out = merge([reg()], [], {})
    assert len(out) == 1 and out[0].boards == []


def test_to_dict_is_json_serialisable(tmp_path):
    d = canvas(tmp_path).to_dict()
    assert json.loads(json.dumps(d))["meta"]["dir"] == str(tmp_path)


def test_merge_matches_canvas_in_subfolder_of_copy_dir(tmp_path):
    sub = tmp_path / "canvas"
    sub.mkdir()
    out = merge([reg()], [canvas(sub)], {"https://claude.ai/artifact/x": tmp_path})
    assert len(out) == 1 and out[0].boards[0]["title"] == "Main"


def test_to_dict_key_distinguishes_canvases_with_same_title_and_group(tmp_path):
    a, b = tmp_path / "x", tmp_path / "y"
    assert canvas(a, "S").to_dict()["key"] != canvas(b, "S").to_dict()["key"]


def test_merge_takes_canvas_date_when_registry_has_none(tmp_path):
    c = canvas(tmp_path)
    c.date = "2026-10-20"
    undated = reg()
    undated.date = ""
    assert merge([undated], [c], {"https://claude.ai/artifact/x": tmp_path})[0].date == "2026-10-20"
    assert merge([reg()], [c], {"https://claude.ai/artifact/x": tmp_path})[0].date == "2026-10-17"


def test_merge_copies_canvas_notes(tmp_path):
    c = canvas(tmp_path)
    c.notes = [{"x": 0, "y": 0, "w": 100, "kind": "title1", "fill": "", "text": "T"}]
    out = merge([reg()], [c], {"https://claude.ai/artifact/x": tmp_path})
    assert out[0].notes == c.notes and out[0].to_dict()["notes"] == c.notes
