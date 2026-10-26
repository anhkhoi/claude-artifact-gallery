"""Behaviour tests for the page script, run in Node against a small DOM stub (skipped without Node)."""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from claude_artifact_gallery.model import Item
from claude_artifact_gallery.page import render

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")

HARNESS = r"""
const els = {}, H = {view: {}, doc: {}};
const board = {on: false, classList: {add(c) { if (c === "on") board.on = true }, remove(c) { if (c === "on") board.on = false }}};
const shield = {parentElement: board};
function el(id) {
  return els[id] || (els[id] = {innerHTML: "", textContent: "", value: "", className: "", hidden: false, title: "", style: {},
    clientWidth: 1000, scrollLeft: 0, scrollTop: 0, classList: {add() {}, remove() {}},
    getBoundingClientRect: () => ({left: 0, top: 0}),
    set onclick(f) { if (id === "#view") H.viewClick = f }, set oninput(f) {},
    addEventListener(t, f) { if (id === "#view") H.view[t] = f }, closest() { return null }});
}
global.document = {querySelector: s => el(s), title: "",
  querySelectorAll: s => (s === ".bd.on" && board.on ? [board] : []),
  addEventListener(t, f) { H.doc[t] = f }};
global.location = {hash: "#" + encodeURIComponent(KEY)};
global.addEventListener = () => {};
global.ResizeObserver = class { constructor() {} observe() {} };
eval(SRC + ";globalThis.Z=Z");
const out = v => console.log(JSON.stringify(v));
const stage = el("#stage");
const onStage = {closest: s => (s === "#stage" ? stage : null)};
"""


def run_js(tmp_path: Path, scenario: str):
    item = Item(kind="canvas", title="C", group="g",
                boards=[{"title": "B", "href": "file:///b.html", "x": 0, "y": 0, "w": 1000, "h": 800}])
    html = render([item], Path("/proj"))
    src = re.search(r"<script>\n(.*)</script>", html, re.S).group(1)
    script = f"const KEY={json.dumps(item.to_dict()['key'])};\nconst SRC={json.dumps(src)};\n{HARNESS}\n{scenario}"
    f = tmp_path / "scenario.js"
    f.write_text(script, encoding="utf-8")
    done = subprocess.run(["node", str(f)], capture_output=True, text=True)
    assert done.returncode == 0, done.stderr
    return json.loads(done.stdout.strip().splitlines()[-1])


def test_ctrl_wheel_zooms_around_the_pointer(tmp_path):
    r = run_js(tmp_path, """
const s0 = Z.cur, wx = 500 / Z.cur, wy = 300 / Z.cur;
let prevented = false;
H.view.wheel({ctrlKey: true, metaKey: false, deltaY: -100, clientX: 500, clientY: 300, preventDefault() { prevented = true }});
out({grew: Z.cur > s0, mode: Z.mode, prevented, dl: stage.scrollLeft - (wx * Z.cur - 500), dt: stage.scrollTop - (wy * Z.cur - 300)});
""")
    assert r["grew"] and r["prevented"] and r["mode"] == "z"
    assert abs(r["dl"]) < 1e-6 and abs(r["dt"]) < 1e-6  # the world point under the pointer stays put


def test_plain_wheel_is_left_to_native_scrolling(tmp_path):
    r = run_js(tmp_path, """
let prevented = false;
H.view.wheel({ctrlKey: false, metaKey: false, deltaY: 120, clientX: 10, clientY: 10, preventDefault() { prevented = true }});
out({prevented, mode: Z.mode});
""")
    assert r == {"prevented": False, "mode": "fit"}


def test_dragging_the_canvas_pans_it_until_mouse_up(tmp_path):
    r = run_js(tmp_path, """
stage.scrollLeft = 200; stage.scrollTop = 100;
H.view.mousedown({button: 0, clientX: 100, clientY: 100, target: onStage, preventDefault() {}});
H.doc.mousemove({clientX: 60, clientY: 70});
const moved = [stage.scrollLeft, stage.scrollTop];
H.doc.mouseup({});
H.doc.mousemove({clientX: 0, clientY: 0});
out({moved, after: [stage.scrollLeft, stage.scrollTop]});
""")
    assert r["moved"] == [240, 130] and r["after"] == [240, 130]


def test_zero_key_refits_but_not_while_typing(tmp_path):
    r = run_js(tmp_path, """
H.viewClick({target: {closest: () => ({dataset: {z: "1"}})}});
const zoomed = Z.mode;
H.doc.keydown({key: "0", target: {tagName: "INPUT"}});
const typing = Z.mode;
H.doc.keydown({key: "0", target: {tagName: "BODY"}});
out({zoomed, typing, after: Z.mode});
""")
    assert r == {"zoomed": "z", "typing": "z", "after": "fit"}


def test_double_click_activates_a_board_and_outside_press_or_escape_deactivates(tmp_path):
    r = run_js(tmp_path, """
H.view.dblclick({target: {closest: s => (s === ".sh" ? shield : null)}});
const active = board.on;
H.view.mousedown({button: 0, clientX: 1, clientY: 1, target: {closest: () => null}, preventDefault() {}});
const afterPress = board.on;
H.view.dblclick({target: {closest: s => (s === ".sh" ? shield : null)}});
H.doc.keydown({key: "Escape", target: {tagName: "BODY"}});
out({active, afterPress, afterEscape: board.on});
""")
    assert r == {"active": True, "afterPress": False, "afterEscape": False}
