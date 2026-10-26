import json

from claude_artifact_gallery.sources.canvas import find_canvases


def make(tmp_path, canvas_json, files=("Main.dc.html", "Proposed.dc.html")):
    d = tmp_path / "ai-review" / "design" / "type-scale"
    d.mkdir(parents=True)
    for f in files:
        (d / f).write_text("<div>x</div>")
    text = canvas_json if isinstance(canvas_json, str) else json.dumps(canvas_json)
    (d / "canvas.json").write_text(text, encoding="utf-8")
    return d


CJ = {"title": "Type Review", "order": ["Proposed.dc.html", "Main.dc.html"],
      "boards": {"Main.dc.html": {"w": 1000, "h": 820, "title": "Hiện tại"},
                 "Proposed.dc.html": {"w": 900, "h": 700}}}


def test_boards_follow_order_with_titles_and_sizes(tmp_path):
    d = make(tmp_path, CJ)
    [c] = find_canvases(tmp_path)
    assert (c.kind, c.title, c.group) == ("canvas", "Type Review", "design")
    assert c.meta["dir"] == d.resolve()
    assert [b["title"] for b in c.boards] == ["Proposed", "Hiện tại"]
    assert (c.boards[1]["w"], c.boards[1]["h"]) == (1000, 820)
    assert c.boards[0]["href"].startswith("file://")


def test_missing_board_file_is_skipped(tmp_path):
    make(tmp_path, CJ, files=("Main.dc.html",))
    [c] = find_canvases(tmp_path)
    assert [b["title"] for b in c.boards] == ["Hiện tại"]


def test_malformed_canvas_json_is_skipped_with_warning(tmp_path):
    make(tmp_path, "{not json")
    warned = []
    assert find_canvases(tmp_path, warn=warned.append) == []
    assert len(warned) == 1


def test_canvas_without_boards_yields_empty_boards(tmp_path):
    make(tmp_path, {"title": "Empty"}, files=())
    [c] = find_canvases(tmp_path)
    assert c.boards == []


def test_non_integer_board_size_falls_back_without_dropping_canvas(tmp_path):
    make(tmp_path, {"title": "S", "order": ["Main.dc.html"], "boards": {"Main.dc.html": {"w": "500px", "h": 300}}})
    [c] = find_canvases(tmp_path)
    assert (c.boards[0]["w"], c.boards[0]["h"]) == (1000, 300)
