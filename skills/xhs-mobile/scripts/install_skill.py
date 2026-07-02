#!/usr/bin/env python3
"""安装 / 更新 / 卸载 xhs-mobile skill。

target: claude / codex / opencode / all
scope : global（用户级）/ project（当前项目）
command: install（默认） / uninstall   ;  更新 = install --force

安装后写一份 config.json（记录 repo_root / android_dir），供全局安装的 skill 定位 Android 工程构建。
"""

import argparse
import json
import shutil
import sys
from pathlib import Path


SKILL_NAME = "xhs-mobile"
SOURCE_DIR = Path(__file__).resolve().parents[1]          # skills/xhs-mobile
REPO_ROOT = SOURCE_DIR.parents[1]                          # 仓库根
ANDROID_DIR = REPO_ROOT / "android"

IGNORE = shutil.ignore_patterns(
    ".git", "__pycache__", ".pytest_cache", "tests", "node_modules",
    "build", ".env", "*.request.json",
)

CONFIG_RELPATH = ".xhs-mobile/config.json"


def target_dirs(target, scope):
    """返回 {target_name: dest_path}。"""
    home = Path.home()
    cwd = Path.cwd()
    dirs = {}

    if target in ("claude", "all"):
        base = home / ".claude" / "skills" if scope == "global" else cwd / ".claude" / "skills"
        dirs["claude"] = base / SKILL_NAME
    if target in ("codex", "all"):
        base = home / ".agents" / "skills" if scope == "global" else cwd / ".agents" / "skills"
        dirs["codex"] = base / SKILL_NAME
    if target in ("opencode", "all"):
        base = home / ".config" / "opencode" / "skill" if scope == "global" else cwd / ".opencode" / "skill"
        dirs["opencode"] = base / SKILL_NAME
    return dirs


def write_config(scope, dry_run):
    config_dir = (Path.home() if scope == "global" else Path.cwd()) / ".xhs-mobile"
    config_path = config_dir / "config.json"
    payload = {
        "repo_root": str(REPO_ROOT),
        "android_dir": str(ANDROID_DIR),
        "skill_name": SKILL_NAME,
        "scope": scope,
    }
    if dry_run:
        return config_path
    config_dir.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return config_path


def do_install(target, scope, force, dry_run):
    dirs = target_dirs(target, scope)
    results = []
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
            shutil.copytree(SOURCE_DIR, dest, ignore=IGNORE)
        results.append({"target": name, "status": "installed" if not dry_run else "dry-run", "dest": str(dest)})
    config_path = write_config(scope, dry_run)
    return {"results": results, "config": str(config_path), "repo_root": str(REPO_ROOT)}


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
    parser.add_argument("--scope", choices=["global", "project"], default="global")
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
