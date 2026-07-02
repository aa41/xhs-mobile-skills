# 出图环境配置

`scripts/generate_images.py` 调用一个 **OpenAI 兼容**的图像端点：`POST {base_url}/images/generations`，body `{model, prompt, n, size}`，解析 `data[].b64_json` 或 `data[].url`。

## 环境变量

优先级（高覆盖低）：命令行环境变量 > `process.env` > `<cwd>/.xhs-mobile/.env`（项目级）> `~/.xhs-mobile/.env`（用户级）。

| 变量 | 说明 | 默认 |
|------|------|------|
| `XHS_IMAGE_BASE_URL` | OpenAI 兼容端点（亦认 `OPENAI_BASE_URL`） | `https://api.openai.com/v1` |
| `XHS_IMAGE_MODEL` | 模型 ID（亦认 `OPENAI_IMAGE_MODEL`） | `gpt-image-1` |
| `XHS_IMAGE_API_KEY` | API key，必填（亦认 `OPENAI_API_KEY`） | — |
| `XHS_IMAGE_SIZE` | 尺寸，如 `1024x1536`（竖版卡片）/ `1024x1024` | `1024x1536` |
| `XHS_IMAGE_QUALITY` | 质量（部分模型支持） | `high` |
| `XHS_IMAGE_TIMEOUT` | 请求超时（秒） | `120` |
| `XHS_IMAGE_RETRIES` | 失败重试次数 | `2` |
| `XHS_IMAGE_EXTRA_HEADERS` | 网关额外 header（JSON 字符串） | `{}` |

## 配置方法

```bash
# 用户级
mkdir -p ~/.xhs-mobile
cat > ~/.xhs-mobile/.env << 'EOF'
XHS_IMAGE_API_KEY=sk-xxx
XHS_IMAGE_BASE_URL=https://api.openai.com/v1
XHS_IMAGE_MODEL=gpt-image-1
XHS_IMAGE_SIZE=1024x1536
EOF

# 项目级（团队共享，记得 .gitignore）
mkdir -p .xhs-mobile
# 写 .xhs-mobile/.env，内容同上；勿提交真实 key
```

## 常见中转/代理

官方 OpenAI：`XHS_IMAGE_BASE_URL=https://api.openai.com/v1`，model `gpt-image-1`。
第三方中转：把 `XHS_IMAGE_BASE_URL` 指向中转地址，`XHS_IMAGE_MODEL` 用中转支持的图像模型名。
兼容 `/images/generations` 的任意端点均可（阿里通义万相 OpenAI 兼容模式、自建网关等）。

## 无 key 自检

```bash
python3 scripts/generate_images.py --prompt-file prompts/01-cover-demo.md --out /tmp/x.png --dry-run
```

`--dry-run` 只把将要发送的请求（endpoint / payload / size）写到 `<out>.request.json`，不真正调用、不需要 key。用于验证 baseurl/model/size 是否正确。
