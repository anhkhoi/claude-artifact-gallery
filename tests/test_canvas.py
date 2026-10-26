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


def test_boards_carry_their_canvas_position(tmp_path):
    make(tmp_path, {"title": "S", "order": ["Main.dc.html"],
                    "boards": {"Main.dc.html": {"x": 1080, "y": -40, "w": 900, "h": 700}}})
    [c] = find_canvases(tmp_path)
    assert (c.boards[0]["x"], c.boards[0]["y"]) == (1080, -40)


def test_boards_without_positions_are_stacked_with_a_gap(tmp_path):
    make(tmp_path, {"title": "S", "order": ["Main.dc.html", "Proposed.dc.html"],
                    "boards": {"Main.dc.html": {"w": 1000, "h": 600}, "Proposed.dc.html": {"w": 1000, "h": 400}}})
    [c] = find_canvases(tmp_path)
    assert [(b["x"], b["y"]) for b in c.boards] == [(0, 0), (0, 680)]


def test_notes_are_read_with_defaults_and_tolerate_bad_values(tmp_path):
    make(tmp_path, {"title": "S", "notes": {
        "t1": {"x": 0, "y": -260, "text": "Title", "kind": "title1", "maxW": 2080},
        "s1": {"x": 10, "y": 20, "w": 420, "fill": "blue", "text": "hi"},
        "bad": {"x": "left", "text": 123}}})
    [c] = find_canvases(tmp_path)
    assert c.notes == [
        {"x": 0, "y": -260, "w": 2080, "kind": "title1", "fill": "", "text": "Title"},
        {"x": 10, "y": 20, "w": 420, "kind": "", "fill": "blue", "text": "hi"},
        {"x": 0, "y": 0, "w": 0, "kind": "", "fill": "", "text": "123"}]
