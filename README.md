# xhs-mobile-skills · 小红书 & 微信公众号移动端分享

把开发/产品/运营进展，变成**反 AI 口吻的小红书文案 + 卡片图**，打包进一个自带的 Android App，用手机原生分享 Intent 发给小红书 / 微信 / 公众号——**不触发网页端风控**，因为分享动作由真实 App、真实用户发起，最后一确由你手动点发布。

```
git 提交 → 文案(反 AI) → 出图(OpenAI) → 打包进 APK → 装到手机 → 点一下分享
```

## 适用场景

- 开发日志 / 周报 → 小红书发一条，用户能看懂
- 版本更新 → 图文卡片告诉用户有什么变化
- 日常运营 → 复盘动作和反馈
- 产品日记 → 记录取舍和场景

## 项目结构

```
xhs-mobile-skills/
├── skills/xhs-mobile/           ← 核心 skill 定义
│   ├── SKILL.md                 ← 10 步工作流（agent 入口）
│   ├── .env.example             ← 出图 API 模板
│   ├── requirements.txt          ← Python 依赖
│   ├── references/               ← 设计参考文档
│   │   ├── roles.md              ← 5 种内容角色 + 口吻
│   │   ├── style-guide.md        ← 反 AI 味写作指南
│   │   ├── card-design.md        ← 12 Style × 8 Layout × 3 Palette
│   │   ├── sharing.md            ← 分享路径与边界
│   │   ├── image-env.md          ← 出图环境配置
│   │   └── android-build.md      ← Android 构建文档
│   ├── scripts/                  ← 7 个独立脚本（stdlib-based）
│   │   ├── git_changelog.py      ← git log → 结构化 JSON
│   │   ├── review_content.py     ← 反 AI 门禁审稿
│   │   ├── plan_cards.py         ← 文案 → N 张卡片规划
│   │   ├── generate_images.py    ← OpenAI 兼容出图
│   │   ├── package_assets.py     ← 打包到 Android assets
│   │   ├── build_apk.py          ← 构建 debug APK
│   │   ├── install_apk.py        ← adb 安装到手机
│   │   └── install_skill.py     ← 安装本 skill 到各 agent
│   └── agents/openai.yaml       ← Codex agent 描述
├── android/                      ← Android 分享助手 App
│   ├── app/src/main/
│   │   ├── java/.../share/ShareHelper.kt   ← 分享核心: XHS / 微信 / 公众号
│   │   ├── java/.../data/Models.kt         ← PostManifest 数据模型
│   │   ├── java/.../data/PostRepository.kt ← 扫描 assets 加载内容
│   │   └── res/layout/                     ← 5 个 XML 布局
│   └── build.gradle.kts          ← AGP 8.7 + Kotlin, SDK 35
└── tests/                        ← pytest 测试
```

---

## 快速开始（一句自然语言安装）

**以下提示词复制到 Claude Code / Codex / OpenCode 即可自动安装：**

> 请帮我安装 xhs-mobile-skills。从 github.com 把仓库 clone 下来（如果已 clone 就跳过），进入仓库目录，跑 `python3 skills/xhs-mobile/scripts/install_skill.py --target all --scope global` 安装 skill，然后帮我创建 `~/.xhs-mobile/.env` 出图配置文件（API key 我会之后填），最后装 Python 依赖 `pip3 install -r skills/xhs-mobile/requirements.txt`。

安装完成后，以后只需说：

> 把最近 git 提交整理成小红书和公众号发布稿

就可以自动走完：采集 → 审稿 → 规划卡片 → 出图 → 打包 → 构建 → 安装到手机 的全流程。

---

## 环境要求

### 本机

| 工具 | 版本 | 用途 |
|------|------|------|
| Python | 3.10+ | 7 个纯脚本运行 |
| Git | 2.x | 采集提交历史 |
| JDK | 17+ | 编译 Android APK |
| Android SDK | platform-tools + platforms;android-34 + build-tools | 构建 & adb 连接 |

### Python 依赖

```bash
pip3 install -r skills/xhs-mobile/requirements.txt
# 只依赖：pytest、requests(可选)、Pillow(可选)
# review_content / plan_cards / package_assets / build_apk / install_apk / install_skill 只用标准库
```

### Android SDK 快速安装

macOS 已安装 Android Studio 时，SDK 路径通常为 `~/Library/Android/sdk`。脚本会自动检测 `ANDROID_HOME` → 默认路径。也可以手动设置：

```bash
# 写入 shell 环境（推荐，一次配置永久生效）
export ANDROID_HOME="$HOME/Library/Android/sdk"
export PATH="$ANDROID_HOME/platform-tools:$PATH"
```

### 手机

- Android 手机一台，开启「开发者选项」→「USB 调试」
- 或同一局域网无线调试：`adb connect <手机IP>:5555`

---

## 出图配置

出图调用 **OpenAI 兼容** 的 `/images/generations` 接口。支持官方 OpenAI、中转/代理、阿里通义万相兼容模式等。

### 创建配置文件

```bash
mkdir -p ~/.xhs-mobile
cp skills/xhs-mobile/.env.example ~/.xhs-mobile/.env
# 编辑 ~/.xhs-mobile/.env，填入真实 key 和地址
```

### 配置项

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `XHS_IMAGE_API_KEY` | **必填**。API key | — |
| `XHS_IMAGE_BASE_URL` | 接口地址（也读 `OPENAI_BASE_URL`） | `https://api.openai.com/v1` |
| `XHS_IMAGE_MODEL` | 模型名（也读 `OPENAI_IMAGE_MODEL`） | `gpt-image-1` |
| `XHS_IMAGE_SIZE` | 图片尺寸 | `1024x1536` |
| `XHS_IMAGE_QUALITY` | 质量等级 | `high` |
| `XHS_IMAGE_TIMEOUT` | 请求超时秒数 | `120` |
| `XHS_IMAGE_RETRIES` | 失败重试次数 | `2` |
| `XHS_IMAGE_EXTRA_HEADERS` | 额外 HTTP 头（JSON 格式） | `{}` |

### 配置优先级

```
命令行 export 的变量  >  项目级 .xhs-mobile/.env  >  用户级 ~/.xhs-mobile/.env
```

团队共享项目时，把公共配置（baseurl/model/size）放在项目 `.xhs-mobile/.env` 并提交；个人 key 放 `~/.xhs-mobile/.env`（已在 `.gitignore` 中）。

### 无 key 验证

如果你还没 key，可以用 `--dry-run` 验证整个链路是否通畅：

```bash
python3 skills/xhs-mobile/scripts/generate_images.py \
  --prompt "test" --out /tmp/test.png --dry-run
# 会写出请求 JSON 到 /tmp/test.request.json，不真正调用 API
```

---

## 完整工作流（10 步）

### 方式一：让大模型自动执行（推荐）

安装 skill 后直接说：

> 把最近 git 提交整理成小红书和公众号发布稿

Agent 会按 SKILL.md 的 10 步顺序自动推进，每步自检通过后才进入下一步。

### 方式二：手动逐步执行

```bash
BASE=skills/xhs-mobile/scripts
ROLE=daily-dev-log          # daily-dev-log | weekly-dev-log | release-note | daily-ops | product-diary
COUNT=3                      # 卡片张数 1-9

# Step 1 · 识别角色 → 选 ROLE

# Step 2 · 采集素材
python3 $BASE/git_changelog.py --repo /path/to/your-project --since "7 days ago" --out changelog.json

# Step 3 · 写文案（大模型完成，存为 caption.md）

# Step 4 · 反 AI 门禁（必须 passed 才能继续）
python3 $BASE/review_content.py --file caption.md --role $ROLE --platform xhs --multi-agent --out review.json
python3 $BASE/review_content.py --file wechat.md  --role $ROLE --platform wechat --multi-agent --out review_wechat.json

# Step 5 · 规划卡片
python3 $BASE/plan_cards.py --file caption.md --role $ROLE --count $COUNT --out plan.json

# Step 6 · 出图（先 dry-run 验证）
python3 $BASE/generate_images.py --prompts-dir prompts --out-dir post/images --size 1024x1536 --dry-run
python3 $BASE/generate_images.py --prompts-dir prompts --out-dir post/images --size 1024x1536

# Step 7 · 打包到 App assets
python3 $BASE/package_assets.py \
  --plan plan.json --images-dir post/images \
  --caption-file caption.md --title "你的标题" \
  --tag 小红书 --tag 版本更新 \
  --wechat-html wechat.html --wechat-title "公众号标题" --wechat-digest "摘要" \
  --android-dir android --slug feature-slug --date $(date +%Y-%m-%d)

# Step 8 · 构建 APK
python3 $BASE/build_apk.py --android-dir android

# Step 9 · 安装到手机
python3 $BASE/install_apk.py --apk android/app/build/outputs/apk/debug/app-debug.apk --launch

# Step 10 · 在手机上打开 App → 点卡片 → 点分享按钮 → 选小红书/微信 → 确认发布
```

---

## 迁移指南

### 迁移到另一台电脑

```bash
# 1. Clone 仓库到新电脑
git clone <repo-url> xhs-mobile-skills && cd xhs-mobile-skills

# 2. 安装 skill
python3 skills/xhs-mobile/scripts/install_skill.py --target all --scope global

# 3. 配置出图环境
mkdir -p ~/.xhs-mobile
cp skills/xhs-mobile/.env.example ~/.xhs-mobile/.env
# 编辑 ~/.xhs-mobile/.env，填入 API key

# 4. 安装依赖
pip3 install -r skills/xhs-mobile/requirements.txt

# 5. 配置 Android SDK（如果有 Android Studio 则自动检测）
export ANDROID_HOME="$HOME/Library/Android/sdk"   # macOS
# export ANDROID_HOME="$HOME/Android/Sdk"          # Linux

# 6. 验证
python3 skills/xhs-mobile/scripts/review_content.py --text "测试" --role daily-dev-log --platform xhs
```

### 迁移到另一个项目（复用 skill 和 App）

`xhs-mobile-skills` 本身已经是一个独立仓库，git clone 到任意目录即可。关键点：

- **Skill 安装是全局的**（`--scope global`），装一次可以给多个项目用
- `XHS_ANDROID_DIR` 环境变量可以覆盖 Android 工程路径
- 每个项目可以有独立的 `.xhs-mobile/.env`（项目级配置覆盖用户级）

```bash
# 在另一个项目中指向本 skill 的 Android 工程
export XHS_ANDROID_DIR=/path/to/xhs-mobile-skills/android
python3 /path/to/xhs-mobile-skills/skills/xhs-mobile/scripts/package_assets.py ...
```

### 只迁移 Android App（给非技术用户用）

把 APK 直接发给用户手机即可，无需仓库、无需 Python：

```bash
# 构建后发 APK
adb pull /path/to/app-debug.apk
# 或直接
python3 skills/xhs-mobile/scripts/install_apk.py --apk <apk> --launch
```

App 内置的 sample 内容会展示完整功能。后续更新内容只需重新安装新 APK。

---

## Android App 说明

### 功能
- **内容列表**：按日期倒序显示所有 generated posts
- **小红书预览**：ViewPager2 翻页查看卡片图 + 标题/正文/标签
- **公众号预览**：WebView 加载 HTML + 标题/摘要
- **三个分享按钮**：分享到小红书 / 发到微信 / 发送到公众号

### 分享原理
- 小红书：`ACTION_SEND_MULTIPLE` + `FileProvider` content URI + `*/*` MIME 类型（确保图文都被接收）
- 微信：多图用 `SEND_MULTIPLE`，单图用 `SEND`，图片 + 文字一起发
- 公众号：正文 → 剪贴板 + 图片 → 相册 → 打开微信「订阅号」手动粘贴（暂无可直达草稿的可靠 scheme）
- 全程由用户手动确认发布，不自动化——这是**规避风控的核心设计**

### 内容目录格式

```
android/app/src/main/assets/posts/
└── 2026-07-02-feature-slug/
    ├── manifest.json     ← 列表 & 预览用的元数据
    ├── caption.md         ← 小红书正文
    ├── title.txt          ← 小红书标题
    ├── tags.txt           ← 标签（每行一个 #tag）
    ├── wechat.html        ← 公众号 HTML 正文
    └── images/
        ├── 01.png          ← 封面卡
        ├── 02.png          ← 细节卡
        └── 03.png          ← 总结卡
```

`manifest.json` 结构见 `Models.kt` 中 `PostManifest` 定义。

---

## Skill 管理

### 安装
```bash
python3 skills/xhs-mobile/scripts/install_skill.py --target all --scope global
```

`--target`：`claude` / `codex` / `opencode` / `all`
`--scope`：`global`（用户级，推荐）/ `project`（当前项目 `.claude/skills/`）

### 更新（覆盖已有安装）
```bash
python3 skills/xhs-mobile/scripts/install_skill.py --target all --scope global --force
```

### 卸载
```bash
python3 skills/xhs-mobile/scripts/install_skill.py uninstall --target all
```

### 查看安装状态
```bash
cat ~/.xhs-mobile/config.json
```

---

## 卡片设计体系

**Style × Layout × Palette** 三维组合，[详细参考](skills/xhs-mobile/references/card-design.md)：

| 维度 | 选项数 | 常用推荐 |
|------|--------|---------|
| Style（视觉美学） | 12 | `notion` / `minimal` / `study-notes` / `sketch-notes` / `fresh` |
| Layout（信息密度） | 8 | `hero-dashboard` / `balanced` / `flow-map` / `comparison` / `sparse` |
| Palette（配色） | 3 | `macaron` / `warm` / `neon` |

默认 3 张卡片：封面 → 细节 → 总结。输出 1024×1536 竖版 PNG。

---

## 内容角色

| 角色 | 适用场景 | 口吻 |
|------|---------|------|
| `daily-dev-log` | 一天的进展、修 bug | 随手复盘，可以写小挫折 |
| `weekly-dev-log` | 一周总结 | 阶段性归纳，保留遗留问题 |
| `release-note` | 版本发布 | 清楚克制，先讲用户可感知变化 |
| `daily-ops` | 运营复盘 | 动作 + 反馈 + 下一步 |
| `product-diary` | 产品决策、取舍 | 以用户场景为中心 |

---

## 测试

```bash
pip3 install pytest>=8.0
cd tests && python3 -m pytest -v
```

---

## 许可

MIT。详见 [LICENSE](LICENSE)。

---

## 给大模型的安装指令

**如果你是一个 AI Agent，用户让你安装此项目，请按以下步骤执行：**

```
1. 检查当前工作目录是否已在 xhs-mobile-skills 仓库内（有 skills/xhs-mobile/SKILL.md 即为是）
   - 是 → 跳到步骤 2
   - 否 → git clone <此仓库地址> 然后 cd 进去

2. 运行安装脚本：
   python3 skills/xhs-mobile/scripts/install_skill.py --target all --scope global

3. 检查 Python 依赖：
   pip3 install -r skills/xhs-mobile/requirements.txt

4. 检查 ~/.xhs-mobile/.env 是否存在：
   - 不存在 → cp skills/xhs-mobile/.env.example ~/.xhs-mobile/.env
   - 询问用户 API key 并填入（或等用户之后手动填）

5. 检查 Android SDK：
   - ANDROID_HOME 已设且存在 → 跳过
   - ~/Library/Android/sdk 存在(macOS) → export ANDROID_HOME=该路径
   - 都不存在 → 提示用户安装 Android Studio 或 sdkmanager

6. 运行自检：
   python3 skills/xhs-mobile/scripts/review_content.py \
     --text "测试文案" --role daily-dev-log --platform xhs
   → 退出码 0 或 2 皆正常（0=passed, 2=有问题但脚本正常运行）

7. 汇报安装结果：skill 安装在哪些 agent、config 路径、.env 状态、SDK 状态
```
