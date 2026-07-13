#!/usr/bin/env python3
"""全局安装 / 更新 / 卸载 xhs-mobile skill 与 Android Runtime。

target: claude / codex / opencode / all
scope : global（用户级，唯一正式支持的安装模式）
command: install（默认） / uninstall   ;  更新 = install --force

Android 工程安装到 ~/.xhs-mobile/runtime/android，不依赖仓库原始路径。
"""

import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path

from runtime_paths import GLOBAL_ANDROID_DIR, GLOBAL_ROOT, bundled_android_dir


SKILL_NAME = "xhs-mobile"
SOURCE_DIR = Path(__file__).resolve().parents[1]          # skills/xhs-mobile
SOURCE_ANDROID_DIR = bundled_android_dir(__file__)

IGNORE = shutil.ignore_patterns(
    ".git", "__pycache__", ".pytest_cache", "tests", "node_modules",
    "build", ".env", "*.request.json",
)

ANDROID_IGNORE = shutil.ignore_patterns(
    ".gradle", ".kotlin", "build", "local.properties", "*.iml", ".DS_Store"
)

def target_dirs(target, scope):
    """返回 {target_name: dest_path}。"""
    if scope != "global":
        raise ValueError("xhs-mobile 仅支持 global scope；项目级差异请写入 <project>/.xhs-mobile/")
    home = Path.home()
    dirs = {}

    if target in ("claude", "all"):
        base = home / ".claude" / "skills"
        dirs["claude"] = base / SKILL_NAME
    if target in ("codex", "all"):
        base = home / ".agents" / "skills"
        dirs["codex"] = base / SKILL_NAME
    if target in ("opencode", "all"):
        base = home / ".config" / "opencode" / "skill"
        dirs["opencode"] = base / SKILL_NAME
    return dirs


def write_config(scope, dry_run):
    config_dir = GLOBAL_ROOT
    config_path = config_dir / "config.json"
    payload = {
        "android_dir": str(GLOBAL_ANDROID_DIR),
        "runtime_dir": str(GLOBAL_ANDROID_DIR.parent),
        "skill_name": SKILL_NAME,
        "scope": scope,
        "schema_version": 2,
    }
    if dry_run:
        return config_path
    config_dir.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return config_path


def install_android_runtime(force, dry_run, source_android_dir=None):
    """Install a self-contained runtime and preserve generated posts on updates."""
    source_android_dir = source_android_dir or SOURCE_ANDROID_DIR
    runtime_existed = GLOBAL_ANDROID_DIR.exists()
    if dry_run:
        return {"status": "dry-run", "dest": str(GLOBAL_ANDROID_DIR)}
    if runtime_existed and not force:
        return {"status": "exists", "dest": str(GLOBAL_ANDROID_DIR)}
    if source_android_dir is None:
        raise RuntimeError("安装包中找不到 Android 工程（缺 gradlew）")

    posts_rel = Path("app/src/main/assets/posts")
    with tempfile.TemporaryDirectory(prefix="xhs-mobile-") as tmp:
        saved_posts = Path(tmp) / "posts"
        current_posts = GLOBAL_ANDROID_DIR / posts_rel
        if current_posts.exists():
            shutil.copytree(current_posts, saved_posts)
        if GLOBAL_ANDROID_DIR.exists():
            shutil.rmtree(GLOBAL_ANDROID_DIR)
        GLOBAL_ANDROID_DIR.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source_android_dir, GLOBAL_ANDROID_DIR, ignore=ANDROID_IGNORE)
        if saved_posts.exists():
            shutil.copytree(saved_posts, GLOBAL_ANDROID_DIR / posts_rel, dirs_exist_ok=True)
    return {"status": "updated" if runtime_existed else "installed", "dest": str(GLOBAL_ANDROID_DIR)}


def do_install(target, scope, force, dry_run):
    dirs = target_dirs(target, scope)
    source_dir = SOURCE_DIR
    source_android_dir = SOURCE_ANDROID_DIR
    staging = None
    resolved_dests = [dest.expanduser().resolve() for dest in dirs.values()]
    if force and any(source_dir == dest or dest in source_dir.parents for dest in resolved_dests):
        staging = tempfile.TemporaryDirectory(prefix="xhs-mobile-skill-")
        staged_skill = Path(staging.name) / SKILL_NAME
        shutil.copytree(source_dir, staged_skill, ignore=IGNORE)
        source_dir = staged_skill
        staged_android = staged_skill / "android-template"
        if staged_android.exists():
            source_android_dir = staged_android

    results = []
    try:
        for name, dest in dirs.items():
            dest = dest.expanduser().resolve()
            if dest.exists():
                if not force:
                    results.append({"target": name, "status": "exists", "dest": str(dest),
                                    "hint": "已存在；加 --force 覆盖（=更新）"})
                    continue
                if not dry_run:
                    shutil.rmtree(dest)
            if not dry_run:
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copytree(source_dir, dest, ignore=IGNORE)
                if source_android_dir and not (dest / "android-template").exists():
                    shutil.copytree(source_android_dir, dest / "android-template", ignore=ANDROID_IGNORE)
            results.append({"target": name, "status": "installed" if not dry_run else "dry-run", "dest": str(dest)})
        runtime = install_android_runtime(force, dry_run, source_android_dir)
        config_path = write_config(scope, dry_run)
        return {"results": results, "runtime": runtime, "config": str(config_path)}
    finally:
        if staging:
            staging.cleanup()


def do_uninstall(target, scope):
    dirs = target_dirs(target, scope)
    results = []
    for name, dest in dirs.items():
        dest = dest.expanduser().resolve()
        if dest.exists():
            shutil.rmtree(dest)
            results.append({"target": name, "status": "removed", "dest": str(dest)})
        else:
            results.append({"target": name, "status": "absent", "dest": str(dest)})
    return {"results": results}


def parse_args(argv):
    parser = argparse.ArgumentParser(description="安装 / 更新 / 卸载 xhs-mobile skill")
    parser.add_argument("command", nargs="?", default="install", choices=["install", "uninstall"])
    parser.add_argument("--target", choices=["claude", "codex", "opencode", "all"], default="all")
    parser.add_argument("--scope", choices=["global"], default="global")
    parser.add_argument("--force", action="store_true", help="覆盖已存在目录（=更新）")
    parser.add_argument("--dry-run", action="store_true", help="只打印目标路径，不写盘")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv or sys.argv[1:])
    if args.command == "uninstall":
        result = do_uninstall(args.target, args.scope)
    else:
        result = do_install(args.target, args.scope, args.force, args.dry_run)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
