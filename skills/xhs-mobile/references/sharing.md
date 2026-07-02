# 分享路径与边界

本 skill 用 **Android 原生分享 Intent** 把内容交给手机上真实的小红书 / 微信 App，**由用户手动确认发布**。这是为了规避网页端自动化（Playwright/CDP）被风控的问题——分享动作由真实 App、真实用户发起，不触发风控。

## 小红书（主路径：原生 Intent）

`ACTION_SEND_MULTIPLE` + `FileProvider` 提供 content URI（图片）+ `EXTRA_TEXT`（正文 + 标签）→ 弹出系统分享面板 → 用户选「小红书」→ 在小红书 App 里确认发布。

- 图片必须经 `FileProvider` 转成 `content://` URI，不能直接发 `file://`（Android 7+ 限制）。
- 全程用户手动确认，**不自动点发布**。

## 小红书 scheme（可选，best-effort）

尝试 `xhsdiscover://` 深链直达发布页；`try/catch`，失败或未安装则**回退到原生 Intent**。scheme 跨版本可能失效，原生 Intent 是保底。

## 微信（原生 Intent）

`ACTION_SEND` 图文 → 微信（发到聊天 / 收藏 / 朋友圈）。

## 微信公众号（诚实边界）

第三方 App **没有可靠 scheme 直达公众号草稿编辑器**。本 skill 的兜底策略：

1. 把公众号正文 HTML **复制到剪贴板**。
2. 打开微信 / 「公众号助手」App / 浏览器 `mp.weixin.qq.com`。
3. 用户手动粘贴、配图、发布。

UI 与文档**明示**「需手动粘贴」，**不承诺**一键发布到公众号。

> 真正的公众号无人值守发布需要官方 API（`access_token` + 草稿 + freepublish）且账号有发布权限，2025 年后部分个人/未认证账号已无发布 API 权限。该路径超出本 skill（移动端分享）范围；如需，用 baoyu-post-to-wechat 或专门工具。

## 不要做的事

- ❌ 不承诺「小红书普通账号稳定一键发布」。
- ❌ 不承诺「公众号无人值守发布」。
- ❌ 不在文案里写「绕过审核 / 风控 / 验证码」「Cookie 永久稳定」等表述（`review_content.py` 会拦）。
