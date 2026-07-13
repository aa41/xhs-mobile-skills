from pathlib import Path

import install_skill
import pytest


def test_target_dirs_global():
    dirs = install_skill.target_dirs("all", "global")
    assert dirs["claude"] == Path.home() / ".claude" / "skills" / "xhs-mobile"
    assert dirs["codex"] == Path.home() / ".agents" / "skills" / "xhs-mobile"
    assert dirs["opencode"] == Path.home() / ".config" / "opencode" / "skill" / "xhs-mobile"


def test_project_scope_is_rejected():
    with pytest.raises(ValueError, match="仅支持 global scope"):
        install_skill.target_dirs("all", "project")


def test_dry_run_install_does_not_write(tmp_path, monkeypatch):
    target = tmp_path / ".claude/skills/xhs-mobile"
    monkeypatch.setattr(install_skill, "target_dirs", lambda target_name, scope: {"claude": target})
    result = install_skill.do_install("claude", "global", force=False, dry_run=True)
    assert result["results"][0]["status"] == "dry-run"
    # dry-run 不应真正拷贝
    assert not target.exists()
    assert result["runtime"]["status"] == "dry-run"


def test_source_dir_resolves():
    assert install_skill.SOURCE_DIR.name == "xhs-mobile"
    assert (install_skill.SOURCE_DIR / "SKILL.md").exists()


def test_install_runtime_preserves_posts(tmp_path, monkeypatch):
    source = tmp_path / "source-android"
    (source / "app/src/main/assets/posts/sample").mkdir(parents=True)
    (source / "gradlew").write_text("#!/bin/sh\n", encoding="utf-8")
    (source / "app/src/main/assets/posts/sample/source.txt").write_text("source", encoding="utf-8")

    runtime = tmp_path / "runtime/android"
    (runtime / "app/src/main/assets/posts/user-post").mkdir(parents=True)
    (runtime / "app/src/main/assets/posts/user-post/content.txt").write_text("keep", encoding="utf-8")

    monkeypatch.setattr(install_skill, "SOURCE_ANDROID_DIR", source)
    monkeypatch.setattr(install_skill, "GLOBAL_ANDROID_DIR", runtime)
    result = install_skill.install_android_runtime(force=True, dry_run=False)

    assert result["status"] == "updated"
    assert (runtime / "gradlew").exists()
    assert (runtime / "app/src/main/assets/posts/user-post/content.txt").read_text() == "keep"


def test_force_update_can_run_from_installed_skill(tmp_path, monkeypatch):
    installed = tmp_path / ".agents/skills/xhs-mobile"
    (installed / "scripts").mkdir(parents=True)
    (installed / "SKILL.md").write_text("skill", encoding="utf-8")
    template = installed / "android-template"
    template.mkdir()
    (template / "gradlew").write_text("#!/bin/sh\n", encoding="utf-8")

    runtime = tmp_path / ".xhs-mobile/runtime/android"
    monkeypatch.setattr(install_skill, "SOURCE_DIR", installed)
    monkeypatch.setattr(install_skill, "SOURCE_ANDROID_DIR", template)
    monkeypatch.setattr(install_skill, "GLOBAL_ANDROID_DIR", runtime)
    monkeypatch.setattr(install_skill, "target_dirs", lambda target, scope: {"codex": installed})
    monkeypatch.setattr(install_skill, "write_config", lambda scope, dry_run: tmp_path / "config.json")

    result = install_skill.do_install("codex", "global", force=True, dry_run=False)

    assert result["results"][0]["status"] == "installed"
    assert (installed / "SKILL.md").read_text(encoding="utf-8") == "skill"
    assert (installed / "android-template/gradlew").exists()
    assert (runtime / "gradlew").exists()
