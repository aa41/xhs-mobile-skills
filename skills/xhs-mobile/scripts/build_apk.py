#!/usr/bin/env python3
"""构建 Android debug APK：解析 SDK → gradlew assembleDebug → 定位 APK。"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

from runtime_paths import resolve_android_dir


APK_REL = "app/build/outputs/apk/debug/app-debug.apk"


def resolve_sdk():
    for key in ("ANDROID_HOME", "ANDROID_SDK_ROOT"):
        val = os.environ.get(key)
        if val and Path(val).exists():
            return Path(val)
    default = Path.home() / "Library" / "Android" / "sdk"
    if default.exists():
        return default
    return None


def run_gradle(android_dir, sdk):
    gradlew = android_dir / "gradlew"
    if not gradlew.exists():
        raise RuntimeError(f"找不到 gradlew：{gradlew}（确认 android 工程完整）")
    gradlew.chmod(0o755)
    env = dict(os.environ)
    env["ANDROID_HOME"] = str(sdk)
    env["ANDROID_SDK_ROOT"] = str(sdk)
    cmd = [str(gradlew), ":app:assembleDebug", "--console=plain"]
    print(f"$ cd {android_dir} && ANDROID_HOME={sdk} {' '.join(cmd)}", file=sys.stderr)
    result = subprocess.run(cmd, cwd=str(android_dir), env=env)
    if result.returncode != 0:
        raise RuntimeError(f"gradle 构建失败，退出码 {result.returncode}")


def parse_args(argv):
    parser = argparse.ArgumentParser(description="构建 Android debug APK")
    parser.add_argument("--android-dir", default=None)
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv or sys.argv[1:])
    android_dir = resolve_android_dir(args.android_dir, __file__)
    if not (android_dir / "gradlew").exists():
        print(json.dumps({"error": f"不是有效的 Android 工程（缺 gradlew）：{android_dir}"}, ensure_ascii=False))
        return 1

    sdk = resolve_sdk()
    if not sdk:
        print(json.dumps({
            "error": "未找到 Android SDK。请设置 ANDROID_HOME，或安装 Android Studio / sdkmanager。",
            "hint": "export ANDROID_HOME=\"$HOME/Library/Android/sdk\""
        }, ensure_ascii=False))
        return 1

    try:
        run_gradle(android_dir, sdk)
    except RuntimeError as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False))
        return 1

    apk = android_dir / APK_REL
    if not apk.exists():
        print(json.dumps({"error": f"构建结束但未找到 APK：{apk}"}, ensure_ascii=False))
        return 1
    print(json.dumps({"apk": str(apk), "android_dir": str(android_dir), "sdk": str(sdk)},
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
