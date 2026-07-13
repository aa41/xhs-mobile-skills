import json
from pathlib import Path

import runtime_paths


def test_resolve_android_dir_prefers_cli(tmp_path):
    target = tmp_path / "custom-android"
    assert runtime_paths.resolve_android_dir(str(target)) == target.resolve()


def test_resolve_android_dir_uses_env(tmp_path, monkeypatch):
    target = tmp_path / "env-android"
    monkeypatch.setenv("XHS_ANDROID_DIR", str(target))
    assert runtime_paths.resolve_android_dir() == target.resolve()


def test_config_survives_repository_move(tmp_path, monkeypatch):
    home = tmp_path / "home"
    runtime = home / ".xhs-mobile/runtime/android"
    runtime.mkdir(parents=True)
    config_dir = home / ".xhs-mobile"
    config_dir.mkdir(exist_ok=True)
    (config_dir / "config.json").write_text(json.dumps({"android_dir": str(runtime)}))

    monkeypatch.setattr(runtime_paths.Path, "home", classmethod(lambda cls: home))
    monkeypatch.chdir(tmp_path)
    assert runtime_paths.load_config_android_dir() == runtime.resolve()
