#!/usr/bin/env python3
"""把 APK 装到真机/模拟器：检测 adb 设备 → adb install -r → 可选拉起。

无设备时打印明确提示并退出非零（不静默失败）。
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


PACKAGE = "com.xhs.mobile.app"
ACTIVITY = f"{PACKAGE}/.MainActivity"


def resolve_adb():
    for key in ("ANDROID_HOME", "ANDROID_SDK_ROOT"):
        val = os.environ.get(key)
        if val and (Path(val) / "platform-tools" / "adb").exists():
            return str(Path(val) / "platform-tools" / "adb")
    found = shutil.which("adb")
    if found:
        return found
    default = Path.home() / "Library" / "Android" / "sdk" / "platform-tools" / "adb"
    if default.exists():
        return str(default)
    return None


def list_devices(adb):
    result = subprocess.run([adb, "devices"], capture_output=True, text=True)
    devices = []
    for line in result.stdout.splitlines()[1:]:
        line = line.strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) >= 2 and parts[1] == "device":
            devices.append(parts[0])
    return devices


def install(adb, apk, device):
    cmd = [adb]
    if device:
        cmd += ["-s", device]
    cmd += ["install", "-r", str(apk)]
    print(f"$ {' '.join(cmd)}", file=sys.stderr)
    result = subprocess.run(cmd)
    return result.returncode == 0


def launch(adb, device):
    cmd = [adb]
    if device:
        cmd += ["-s", device]
    cmd += ["shell", "am", "start", "-n", ACTIVITY]
    subprocess.run(cmd)


def parse_args(argv):
    parser = argparse.ArgumentParser(description="adb 安装 APK 到真机/模拟器")
    parser.add_argument("--apk", required=True)
    parser.add_argument("--launch", action="store_true", help="安装后拉起 App")
    parser.add_argument("--device", default=None, help="指定设备 serial（多设备时）")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv or sys.argv[1:])
    apk = Path(args.apk).expanduser().resolve()
    if not apk.exists():
        print(json.dumps({"error": f"APK 不存在：{apk}"}, ensure_ascii=False))
        return 1

    adb = resolve_adb()
    if not adb:
        print(json.dumps({
            "error": "未找到 adb。请安装 platform-tools 或设置 ANDROID_HOME。",
            "hint": "export ANDROID_HOME=\"$HOME/Library/Android/sdk\""
        }, ensure_ascii=False))
        return 1

    devices = list_devices(adb)
    if not devices:
        print(json.dumps({
            "error": "未检测到设备。",
            "hint": "用 USB 连接手机并开启「USB 调试」；或在同一局域网用 `adb connect <手机IP>:5555` 后重试。",
            "adb": adb,
        }, ensure_ascii=False))
        return 2

    device = args.device or devices[0]
    if len(devices) > 1 and not args.device:
        print(json.dumps({"warn": "检测到多个设备，默认用第一个；用 --device 指定", "devices": devices},
                         ensure_ascii=False), file=sys.stderr)

    ok = install(adb, apk, device)
    if not ok:
        print(json.dumps({"error": "adb install 失败", "device": device, "apk": str(apk)}, ensure_ascii=False))
        return 1

    if args.launch:
        launch(adb, device)

    print(json.dumps({"status": "installed", "device": device, "apk": str(apk),
                      "launched": args.launch, "package": PACKAGE}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
