from pathlib import Path

import install_skill


def test_target_dirs_global():
    dirs = install_skill.target_dirs("all", "global")
    assert dirs["claude"] == Path.home() / ".claude" / "skills" / "xhs-mobile"
    assert dirs["codex"] == Path.home() / ".agents" / "skills" / "xhs-mobile"
    assert dirs["opencode"] == Path.home() / ".config" / "opencode" / "skill" / "xhs-mobile"


def test_target_dirs_project(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    dirs = install_skill.target_dirs("all", "project")
    assert dirs["claude"] == tmp_path / ".claude" / "skills" / "xhs-mobile"
    assert dirs["opencode"] == tmp_path / ".opencode" / "skill" / "xhs-mobile"


def test_dry_run_install_does_not_write(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = install_skill.do_install("claude", "project", force=False, dry_run=True)
    assert result["results"][0]["status"] == "dry-run"
    # dry-run 不应真正拷贝
    assert not (tmp_path / ".claude" / "skills" / "xhs-mobile").exists()


def test_source_dir_resolves():
    assert install_skill.SOURCE_DIR.name == "xhs-mobile"
    assert (install_skill.SOURCE_DIR / "SKILL.md").exists()
