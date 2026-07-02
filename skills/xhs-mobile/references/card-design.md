# 卡片设计体系（复刻 baoyu-xhs-images）

复刻 baoyu-xhs-images 的「**Style × Layout × Palette**」三维体系，把内容拆成 1–9 张竖版卡片（**默认 3 张**）。三个维度独立可组合。

> ⛔ 出图只能用光栅图像后端（`scripts/generate_images.py`），**不要**用 SVG / HTML / canvas 代码渲染冒充。文本不清就改 prompt 重出，不要在生成的位图上用程序涂抹覆盖文字。

## 张数（默认 3）

| 张数 | 适用 |
|------|------|
| 1 | 单条短更新、一个清晰结论 |
| 2–3（默认 3） | 有 before/after、步骤、小故事线 |
| 4–6 | 版本更新、周报、多模块小结 |
| 7–9 | 大版本、季度复盘（慎用，太长读者会划走） |

封面（第 1 张）+ 中间细节卡 + 收尾总结卡（最后一张，张数 > 2 时）。

## Style（12，视觉美学）

`cute`(默认) 甜美可爱 / `fresh` 清爽自然 / `warm` 温暖亲切 / `bold` 高对比强冲击 / `minimal` 极简精致 / `retro` 复古怀旧 / `pop` 鲜艳活力 / `notion` 极简手绘线稿知性 / `chalkboard` 黑板粉笔 / `study-notes` 真实手写笔记（蓝笔红批注黄高亮）/ `screen-print` 海报丝网印刷 / `sketch-notes` 手绘信息图（马卡龙暖奶油底）。

**面向开发者/产品更新推荐**：`notion`、`minimal`、`study-notes`、`sketch-notes`、`fresh`。

## Layout（8，信息密度）

| 布局 | 密度 | 适用 |
|------|------|------|
| `sparse` | 1–2 点 | 封面、金句 |
| `balanced` | 3–4 点 | 常规内容 |
| `dense` | 5–8 点 | 干货总结、知识卡 |
| `list` | 4–7 项 | 清单、排行 |
| `comparison` | 双栏 | 对比、优劣（before/after） |
| `flow` | 3–6 步 | 流程、时间线 |

（baoyu 另有 `hero-dashboard` / `checklist-debug` 等扩展布局，可在 EXTEND 里追加。）

## Palette（3，可选配色覆盖）

| 配色 | 描述 |
|------|------|
| `macaron` | 马卡龙柔和色块（浅蓝/浅绿/浅紫/浅橙）暖白底 |
| `warm` | 暖色系（橙、赭石、金） |
| `neon` | 霓虹色（粉、青、黄）深色底 |

不指定 palette → 用 style 自带配色。

## 每张图必须包含

- 明确信息密度说明（layout 的 density）。
- 材质与微阴影描述。
- 真实界面截图感、日志块或流程节点（与内容相关的小细节）。
- 局部标注、状态点、小贴纸/便签。
- **禁止**：官方 logo、空泛渐变背景、企业 PPT 感、大段乱码文字、过度简单的图标堆砌、伪造小红书品牌标识。

## Prompt 模板

```
小红书竖版图文卡片，1024x1536，高完成度商业插画 + 真实产品界面混合风格。
角色：<role 标签>；卡片：<i>/<count>；类型：<cover|detail|summary>。
主标题：<title>
内容线索：<clean_point>
风格：<style> - <description>
版式：<layout> - <description>；信息密度：<density>。
调色板：<palette> - <description>。
材质与质感：<material>；真实界面截图感、细腻微阴影、轻颗粒、边缘高光。
画面层次：标题层 / 主视觉层 / 数据或日志层 / 局部标注层 / 留白呼吸区。
必须包含：局部标注、状态点、真实界面或日志块、至少一个和内容相关的小细节。
禁止：官方 logo、伪造小红书品牌标识、空泛渐变、企业 PPT、大段乱码、图标堆砌。
中文排版稳，主标题清晰可读，细节文字少量但要像真实产品记录。
```

`scripts/plan_cards.py` 会按角色/卡片类型自动选 style/layout/palette 并填好这份模板，输出到 `plan.json` 的 `cards[].render_prompt`。
