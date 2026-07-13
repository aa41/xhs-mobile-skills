# Android 构建与安装

`scripts/build_apk.py` + `scripts/install_apk.py` 负责「打包好的 assets → 可装到手机的 APK」。

## 工具链要求

- **JDK 17+**（已验证 Java 21 可用）。
- **Android SDK**：含 `platform-tools`（adb）+ 对应 `platforms;android-34` + `build-tools`。
- **Gradle**：用全局 Runtime 自带的 `android/gradlew` wrapper，**不需要**全局 gradle。

## ANDROID_HOME 解析

`build_apk.py` / `install_apk.py` 按以下顺序解析 SDK 根目录：

1. 环境变量 `ANDROID_HOME` 或 `ANDROID_SDK_ROOT`。
2. 默认 `~/Library/Android/sdk`（macOS 标准位置，本机已存在）。
3. 都没有 → 报错并打印安装指引（装 Android Studio 或 `sdkmanager`）。

建议把 SDK 写进 shell 环境，避免每次猜：

```bash
# ~/.zshrc
export ANDROID_HOME="$HOME/Library/Android/sdk"
export PATH="$ANDROID_HOME/platform-tools:$ANDROID_HOME/cmdline-tools/latest/bin:$PATH"
```

## 定位 Android 工程

按以下顺序找 `android/` 目录（含 `gradlew`）：

1. `--android-dir` 参数。
2. `XHS_ANDROID_DIR` 环境变量。
3. 当前项目或用户目录 `.xhs-mobile/config.json` 里的 `android_dir`。
4. 全局 Runtime：`~/.xhs-mobile/runtime/android`。
5. 仅源码开发时，回退到 skill 自带模板或仓库根 `android/`。

## 构建命令

```bash
python3 scripts/build_apk.py
# 等价于：cd ~/.xhs-mobile/runtime/android && ./gradlew :app:assembleDebug
# 产物：~/.xhs-mobile/runtime/android/app/build/outputs/apk/debug/app-debug.apk
```

首次构建会下载 Gradle distribution + 依赖，需联网，耗时几分钟。

## 安装命令

```bash
python3 scripts/install_apk.py --apk <apk> [--launch] [--device <serial>]
```

- 先 `adb devices`。
- **无设备**：打印明确提示并退出非零（不静默失败）：
  > 未检测到设备。请用 USB 连接手机并开启「USB 调试」，或在同一局域网用 `adb connect <手机IP>:5555` 后重试。
- 有设备：`adb install -r <apk>`（`-r` 覆盖安装，保留数据）。
- `--launch`：`adb shell am start -n com.xhs.mobile.app/.MainActivity` 拉起 App。

## 签名

debug APK 用 Android 默认 debug keystore 签名，**仅用于自测安装**。要上架或长期安装到他人设备，需自建 release keystore 并改 `android/app/build.gradle.kts` 的 signingConfig（超出本 skill 范围，文档提示即可）。
