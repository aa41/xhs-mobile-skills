---
name: xhs-mobile
description: >-
  把 git 提交历史或用户需求变成面向用户的小红书 / 微信公众号分享内容（反 AI 口吻文案 +
  复刻 baoyu-xhs-images 的卡片图），打包进自带 Android App 的 assets，构建 APK 并用
  adb 装到真机；App 内按日期+功能列出，点击查看小红书/公众号模拟预览，再用原生分享
  Intent（规避风控）或 scheme 跳转到真实 App 完成。涉及"小红书分享""公众号""版本更新"
  "开发日报/周报""出图""打包安装到手机"时使用。支持 Claude Code / Codex / OpenCode。
version: 1.0.0
metadata:
  openclaw:
    homepage: https://github.com/your-org/xhs-mobile-skills#xhs-mobile
    requires:
      bins:
        - python3
---

# 小红书 / 微信公众号 · 移动端分享 skill

把真实的开发 / 产品 / 运营进展，变成可以在手机上分享到小红书和微信公众号的内容。和「浏览器自动登录点发布」的旧方案不同，本 skill **不直接发布**——它产出**文案 + 卡片图**，打包进一个 Android App，App 用**原生系统分享 Intent** 把内容交给手机上真实的小红书 / 微信 App，**由用户手动确认**。这样不触发网页端风控。

## 设计前提（务必遵守）

1. **不承诺无人值守一键发布。** 小红书走原生分享 + 人工确认；微信公众号第三方 App 无可靠 scheme 直达草稿，走「复制正文 + 打开编辑器」兜底。详见 [references/sharing.md](references/sharing.md)。
2. **文案面向用户，不要技术叙事。** 用户看到的是「这次 App/网页有什么新功能」，不是「重构了某模块」「升级了某依赖」。技术升级若与用户可感知功能无关，**不写**。详见 [references/style-guide.md](references/style-guide.md)。
3. **反 AI 口吻是硬门禁。** 起草后必须跑 `scripts/review_content.py`，修掉所有 `ai_tone` / `translation_smell` / `role_fit` 问题才算定稿。

## User Input Tools

当本 skill 需要询问用户时，按此优先级选择工具：

1. **优先用当前 agent 运行时内置的用户输入工具**——例如 `AskUserQuestion`、`request_user_input`、`clarify`、`ask_user` 或任何等价工具。
2. **回退**：若没有这类工具，输出带编号的纯文本消息，请用户逐项回复编号/答案。
3. **批量**：工具支持多问题时合并成一次调用；只支持单问题时按优先级逐个询问。

下文出现的 `AskUserQuestion` 是示例——其他运行时请替换为本地等价工具。

## Language

提问、进度、错误、完成汇报都用用户的语言（默认中文）。技术 token（风格名、文件路径、命令、包名）保留英文。

## Required Flow（BLOCKING 顺序）

每一步完成且自检通过后，才进入下一步。

### Step 1 · 识别角色

从 `references/roles.md` 选一个：

- `daily-dev-log` 每日开发日志
- `weekly-dev-log` 每周开发日志
- `release-note` 版本更新
- `daily-ops` 日常运营
- `product-diary` 产品日记

若用户没明说，按内容推断：有"版本/新增/修复"→ `release-note`；"本周/这周"→ `weekly-dev-log`；单条进展 → `daily-dev-log`；讲取舍/场景 → `product-diary`；讲动作/数据/反馈 → `daily-ops`。

### Step 2 · 采集素材

- 有 git 仓库：跑 `scripts/git_changelog.py` 取结构化提交（`--repo`、`--since`、`--until`、`--author` 可选）。
- 无 git：直接用用户口述的需求。
- **过滤纯技术提交**：依赖升级、内部重构、CI/测试改动、纯文档——只要不影响用户可感知的功能，就**不进**文案。由 agent 按 [references/style-guide.md](references/style-guide.md) 判断。

```
python3 {baseDir}/scripts/git_changelog.py --repo <path> --since "7 days ago" --out changelog.json
```

### Step 3 · 起草文案

按角色口吻写两版：

- **小红书**：标题（16–28 字，含具体对象）+ 正文（短段落，每段一个点）+ 标签（3–8 个）。
- **微信公众号**：标题（耐读，少夸张）+ 摘要（≤120 字）+ 正文（可更完整，段落要短）。

### Step 4 · 反 AI 门禁（必经）

```
python3 {baseDir}/scripts/review_content.py --file caption.md --role <role> --platform xhs --multi-agent --out review.json
```

- 退出码非 0 = 有问题。**逐条修复**后再跑，直到 `passed: true`。
- 微信公众号正文单独跑一遍 `--platform wechat`。

### Step 5 · 卡片规划（默认 3 张）

```
python3 {baseDir}/scripts/plan_cards.py --file caption.md --role <role> --count 3 --out plan.json
```

- `--count` 默认 **3**，用户可选 1–9。先用 `AskUserQuestion` 确认张数与风格偏好（style/layout/palette，见 [references/card-design.md](references/card-design.md)）。
- 据输出的 `cards[].render_prompt`，为每张卡片写独立 prompt 文件（`prompts/NN-<type>-<slug>.md`），作为可复现记录。

### Step 6 · 出图（OpenAI 兼容）

```
python3 {baseDir}/scripts/generate_images.py --prompts-dir prompts --out-dir <post>/images --size 1024x1536
```

- 配置走环境变量（baseurl/model/apikey/size 等），见 [references/image-env.md](references/image-env.md)。
- 无 key 时用 `--dry-run` 自检请求是否正确，不真正出图。
- 卡片为竖版，默认 `1024x1536`。
- 批量出图默认单并发，优先稳定；确认图像网关限流足够后再加 `--concurrency`。
- 若中转端点需要额外 body 字段，用 `XHS_IMAGE_EXTRA_PAYLOAD` 配置，不要直接改脚本。

### Step 7 · 打包到 App assets

```
python3 {baseDir}/scripts/package_assets.py \
  --plan plan.json --images-dir <post>/images \
  --caption-file caption.md --title "标题" \
  --tag 标签1 --tag 标签2 \
  --wechat-html wechat.html --wechat-title "公众号标题" --wechat-digest "摘要" \
  --slug <功能slug> --date <YYYY-MM-DD>
```

产物默认写入全局 Runtime：`~/.xhs-mobile/runtime/android/app/src/main/assets/posts/<YYYY-MM-DD>-<slug>/`。App 扫描该目录。仅调试时才用 `--android-dir` 或 `XHS_ANDROID_DIR` 覆盖。

### Step 8 · 构建 APK

```
python3 {baseDir}/scripts/build_apk.py
```

- 自动解析 `ANDROID_HOME`（env → `~/Library/Android/sdk` → 报错并给指引）。
- 跑 `gradlew assembleDebug`，产出 `app/build/outputs/apk/debug/app-debug.apk`。

### Step 9 · 安装到真机

```
python3 {baseDir}/scripts/install_apk.py --apk <apk> --launch
```

- 先 `adb devices`。**没有设备时**：明确提示用户「请用 USB 连接手机并开启 USB 调试，或 `adb connect <ip>:5555`」，退出非零，不要静默失败。
- 有设备：`adb install -r <apk>`，可选 `am start` 拉起 App。

### Step 10 · 汇报

列出：文案产物路径、卡片图路径、assets 子目录、APK 路径、安装结果、App 内查看位置（列表第几条）。提示用户在手机上打开 App → 点开该条目 → 点「分享到小红书 / 发送到公众号」。

## {baseDir} 解析

`{baseDir}` = 本 `SKILL.md` 所在目录。所有 `scripts/...` 相对该目录。

## 安装 / 更新 / 卸载

见仓库根 `README.md`。一键：

```
# Claude Code / Codex / OpenCode，全局安装（唯一正式支持模式）
python3 {baseDir}/scripts/install_skill.py --target all --scope global      # 安装
python3 {baseDir}/scripts/install_skill.py --target all --scope global --force   # 更新（覆盖）
python3 {baseDir}/scripts/install_skill.py uninstall --target all           # 卸载
```

或 Claude Code 插件市场：`/plugin marketplace add <owner>/<repo>` → `/plugin install xhs-mobile-skills@xhs-mobile`。
或 `npx skills add <owner>/<repo>`。
或直接告诉 agent：「请安装 github.com/.../xhs-mobile-skills」。

安装会同时部署共享 Android Runtime 到 `~/.xhs-mobile/runtime/android`。业务项目中只保存内容素材和可选的 `.xhs-mobile/.env` / `config.json`，不要复制 Android 工程。
