import pytest

from claude_artifact_gallery.cli import collect, install_method, main
from claude_artifact_gallery.sources.pulled import add_pulled, artifact_url, find_pulled
from test_cli import embedded


@pytest.mark.parametrize("ref,want", [
    ("abc123", "https://claude.ai/artifact/abc123"),
    ("  abc-123_X \n", "https://claude.ai/artifact/abc-123_X"),
    ("https://claude.ai/artifact/abc123", "https://claude.ai/artifact/abc123"),
    ("https://claude.ai/artifact/abc123/?utm=1#x", "https://claude.ai/artifact/abc123"),
    ("https://claude.ai/code/artifact/0f1e-22", "https://claude.ai/code/artifact/0f1e-22"),
])
def test_artifact_url_accepts_id_or_link(ref, want):
    assert artifact_url(ref) == want


@pytest.mark.parametrize("ref", ["", "https://example.com/artifact/a", "https://claude.ai/chat/a", "a b"])
def test_artifact_url_rejects_other_input(ref):
    with pytest.raises(ValueError):
        artifact_url(ref)


def page(tmp_path, body="<html><title>Hello</title></html>"):
    f = tmp_path / "in.html"
    f.write_text(body)
    return f


def test_add_pulled_then_find(tmp_path):
    add_pulled(page(tmp_path), "https://claude.ai/artifact/a", "Hello")
    [item] = find_pulled()
    assert (item.kind, item.title, item.url) == ("pulled", "Hello", "https://claude.ai/artifact/a")
    assert item.href.startswith("file://") and item.href.endswith(".html")


def test_adding_same_url_refreshes_instead_of_duplicating(tmp_path):
    add_pulled(page(tmp_path, "<p>v1</p>"), "https://claude.ai/artifact/a", "T")
    add_pulled(page(tmp_path, "<p>v2</p>"), "https://claude.ai/artifact/a", "T")
    [item] = find_pulled()
    assert "v2" in open(item.href[len("file://"):]).read()


def test_cli_add_takes_a_bare_id_and_uses_html_title(tmp_path, capsys):
    assert main(["add", str(page(tmp_path)), "--url", "abc123"]) == 0
    [item] = find_pulled()
    assert item.url == "https://claude.ai/artifact/abc123" and item.title == "Hello"
    assert "abc123" in capsys.readouterr().out


def test_cli_add_rejects_bad_ref_and_missing_file(tmp_path):
    assert main(["add", str(page(tmp_path)), "--url", "not a ref"]) == 1
    assert main(["add", str(tmp_path / "nope.html"), "--url", "abc"]) == 1
    assert find_pulled() == []


def test_pulled_shows_in_gallery(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    add_pulled(page(tmp_path), "https://claude.ai/artifact/a", "Hello")
    out = tmp_path / "out.html"
    assert main([str(root), "-o", str(out), "--no-open"]) == 0
    items, _ = embedded(out)
    assert [(i["kind"], i["title"]) for i in items] == [("pulled", "Hello")]


def test_pulled_copy_attaches_to_matching_registry_entry(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    (root / "artifacts.md").write_text("## G\n- [Reg](https://claude.ai/artifact/a): p (2026-10-17).\n")
    add_pulled(page(tmp_path), "https://claude.ai/artifact/a", "Hello")
    items, counts = collect(root)
    assert [(i.kind, i.title) for i in items] == [("registry", "Reg")]
    assert items[0].href.startswith("file://") and counts["pulled"] == 0


def test_install_skill_copies_then_is_idempotent(tmp_path, capsys):
    skills = tmp_path / "skills"
    assert main(["install-skill", "--dir", str(skills)]) == 0
    dest = skills / "pull" / "SKILL.md"
    assert dest.read_text().startswith("---\nname: pull\n")
    assert main(["install-skill", "--dir", str(skills)]) == 0
    assert "up to date" in capsys.readouterr().out


def test_install_skill_keeps_a_different_copy_unless_forced(tmp_path):
    dest = tmp_path / "pull" / "SKILL.md"
    dest.parent.mkdir()
    dest.write_text("mine")
    assert main(["install-skill", "--dir", str(tmp_path)]) == 1 and dest.read_text() == "mine"
    assert main(["install-skill", "--dir", str(tmp_path), "--force"]) == 0
    assert dest.read_text().startswith("---")


def test_install_skill_defaults_to_claude_config_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path / "cfg"))
    assert main(["install-skill"]) == 0
    assert (tmp_path / "cfg" / "skills" / "pull" / "SKILL.md").exists()


def test_version_flag(capsys):
    with pytest.raises(SystemExit) as e:
        main(["--version"])
    assert e.value.code == 0 and "claude-artifact-gallery 0." in capsys.readouterr().out


def test_gallery_run_hints_when_installed_skill_is_stale(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path / "cfg"))
    root = tmp_path / "repo"
    root.mkdir()
    args = [str(root), "-o", str(tmp_path / "o.html"), "--no-open"]
    main(args)
    assert "out of date" not in capsys.readouterr().err        # nothing installed
    main(["install-skill"])
    main(args)
    assert "out of date" not in capsys.readouterr().err        # installed and current
    (tmp_path / "cfg" / "skills" / "pull" / "SKILL.md").write_text("old")
    main(args)
    assert "install-skill --force" in capsys.readouterr().err


class FakeRun:
    def __init__(self, code=0):
        self.calls, self.code = [], code

    def __call__(self, cmd, **kw):
        self.calls.append(cmd)
        return type("R", (), {"returncode": self.code, "stdout": "claude-artifact-gallery 9.9\n"})()


@pytest.fixture
def fake_run(monkeypatch):
    fake = FakeRun()
    monkeypatch.setattr("claude_artifact_gallery.cli.subprocess.run", fake)
    return fake


def test_upgrade_with_pipx_reinstalls_from_github(monkeypatch, fake_run, capsys):
    monkeypatch.setattr("claude_artifact_gallery.cli.install_method", lambda: ("pipx", ""))
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", "/nonexistent")  # no skill installed
    assert main(["upgrade"]) == 0
    assert fake_run.calls[0][:3] == ["pipx", "install", "--force"] and fake_run.calls[0][3].startswith("git+https://")
    assert not any("install-skill" in c for c in fake_run.calls)
    assert "Upgraded: claude-artifact-gallery 9.9" in capsys.readouterr().out


def test_upgrade_with_pip_uses_this_interpreter(monkeypatch, fake_run):
    monkeypatch.setattr("claude_artifact_gallery.cli.install_method", lambda: ("pip", ""))
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", "/nonexistent")
    assert main(["upgrade"]) == 0
    assert fake_run.calls[0][1:4] == ["-m", "pip", "install"] and "--force-reinstall" in fake_run.calls[0]


def test_upgrade_refreshes_an_installed_skill(monkeypatch, fake_run, tmp_path):
    monkeypatch.setattr("claude_artifact_gallery.cli.install_method", lambda: ("pipx", ""))
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path / "cfg"))
    main(["install-skill"])
    assert main(["upgrade"]) == 0
    assert any(c[-2:] == ["install-skill", "--force"] for c in fake_run.calls)


def test_upgrade_leaves_a_local_clone_alone(monkeypatch, fake_run, capsys):
    monkeypatch.setattr("claude_artifact_gallery.cli.install_method", lambda: ("local", "file:///src/x"))
    assert main(["upgrade"]) == 0
    assert fake_run.calls == [] and "git pull" in capsys.readouterr().out


def test_upgrade_unknown_install_prints_the_manual_command(monkeypatch, fake_run, capsys):
    monkeypatch.setattr("claude_artifact_gallery.cli.install_method", lambda: ("unknown", ""))
    assert main(["upgrade"]) == 1
    assert fake_run.calls == [] and "pipx install --force" in capsys.readouterr().err


def test_upgrade_reports_failure_and_missing_tool(monkeypatch, fake_run, capsys):
    monkeypatch.setattr("claude_artifact_gallery.cli.install_method", lambda: ("pipx", ""))
    fake_run.code = 3
    assert main(["upgrade"]) == 3 and "failed" in capsys.readouterr().err

    def missing(cmd, **kw):
        raise FileNotFoundError(2, "No such file or directory")
    monkeypatch.setattr("claude_artifact_gallery.cli.subprocess.run", missing)
    assert main(["upgrade"]) == 1 and "cannot run pipx" in capsys.readouterr().err


@pytest.mark.parametrize("direct,prefix,want", [
    ('{"url": "file:///src/x", "dir_info": {"editable": true}}', "/venv", ("local", "file:///src/x")),
    ('{"url": "https://github.com/a/b", "vcs_info": {"vcs": "git"}}', "/home/u/.local/pipx/venvs/x", ("pipx", "")),
    ('{"url": "https://github.com/a/b", "vcs_info": {"vcs": "git"}}', "/venv", ("pip", "")),
    (None, "/venv", ("pip", "")),
])
def test_install_method(monkeypatch, direct, prefix, want):
    dist = type("D", (), {"read_text": lambda self, name: direct})()
    monkeypatch.setattr("claude_artifact_gallery.cli.metadata.distribution", lambda name: dist)
    monkeypatch.setattr("claude_artifact_gallery.cli.sys.prefix", prefix)
    assert install_method() == want


def test_install_method_unknown_when_not_installed(monkeypatch):
    def gone(name):
        raise __import__("importlib.metadata").metadata.PackageNotFoundError(name)
    monkeypatch.setattr("claude_artifact_gallery.cli.metadata.distribution", gone)
    assert install_method() == ("unknown", "")
