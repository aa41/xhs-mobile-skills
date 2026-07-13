#!/usr/bin/env python3
"""Resolve the shared xhs-mobile Android runtime consistently."""

import json
import os
from pathlib import Path


GLOBAL_ROOT = Path.home() / ".xhs-mobile"
GLOBAL_RUNTIME_DIR = GLOBAL_ROOT / "runtime"
GLOBAL_ANDROID_DIR = GLOBAL_RUNTIME_DIR / "android"


def load_config_android_dir():
    """Read project override first, then the user-level runtime config."""
    for base in (Path.cwd(), Path.home()):
        config_path = base / ".xhs-mobile" / "config.json"
        if not config_path.exists():
            continue
        try:
            data = json.loads(config_path.read_text(encoding="utf-8"))
            value = data.get("android_dir")
            if value:
                candidate = Path(value).expanduser()
                if candidate.exists():
                    return candidate.resolve()
        except (OSError, ValueError, TypeError):
            continue
    return None


def bundled_android_dir(script_file):
    """Find an Android source bundled beside an installed skill or its repo."""
    skill_dir = Path(script_file).resolve().parents[1]
    candidates = (
        skill_dir / "android-template",
        skill_dir.parents[1] / "android",
    )
    for candidate in candidates:
        if (candidate / "gradlew").exists():
            return candidate.resolve()
    return None


def resolve_android_dir(arg=None, script_file=__file__):
    """Resolve CLI override -> env -> config -> global runtime -> bundled source."""
    if arg:
        return Path(arg).expanduser().resolve()

    env_dir = os.environ.get("XHS_ANDROID_DIR")
    if env_dir:
        return Path(env_dir).expanduser().resolve()

    config_dir = load_config_android_dir()
    if config_dir:
        return config_dir

    if GLOBAL_ANDROID_DIR.exists():
        return GLOBAL_ANDROID_DIR.resolve()

    bundled = bundled_android_dir(script_file)
    if bundled:
        return bundled

    return GLOBAL_ANDROID_DIR.resolve()
