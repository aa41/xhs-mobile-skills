#!/usr/bin/env python3
"""OpenAI 兼容出图：POST {base_url}/images/generations。

支持单图 / 批量（prompts-dir 或 batchfile）/ --dry-run。
配置走环境变量（见 references/image-env.md）。
"""

import argparse
import base64
import json
import os
import random
import re
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path


# ---------- env ----------

def load_env_file(path):
    """读取 .env 文件并返回 dict（不直接写入 os.environ）。"""
    p = Path(path).expanduser()
    if not p.exists():
        return {}
    result = {}
    for raw in p.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        result[key.strip()] = value.strip().strip('"').strip("'")
    return result


def load_env():
    # 优先级：process.env > 项目 .xhs-mobile/.env > 用户 ~/.xhs-mobile/.env
    # 先读低优（用户级），再读高优（项目级），setdefault 保证 process.env 始终最高优
    user_vars = load_env_file(Path.home() / ".xhs-mobile" / ".env")
    project_vars = load_env_file(Path.cwd() / ".xhs-mobile" / ".env")
    # 先设用户级（低优先）
    for k, v in user_vars.items():
        os.environ.setdefault(k, v)
    # 再设项目级（高优先，覆盖用户级但不覆盖 process.env）
    for k, v in project_vars.items():
        if k not in os.environ or k in user_vars and os.environ[k] == user_vars[k]:
            os.environ[k] = v


def env(key, default=None):
    return os.environ.get(key, default)


def normalize_base_url(base_url):
    if not base_url:
        return "https://api.openai.com/v1"
    return base_url.rstrip("/")


def validate_size(size):
    if not re.fullmatch(r"\d{2,5}x\d{2,5}", size or ""):
        raise ValueError(f"图片尺寸格式不正确：{size!r}，应类似 1024x1536")
    width, height = (int(part) for part in size.split("x", 1))
    if width < 256 or height < 256 or width > 4096 or height > 4096:
        raise ValueError(f"图片尺寸超出安全范围：{size}（允许 256-4096）")
    return size


def validate_prompt(prompt, source="prompt"):
    prompt = (prompt or "").strip()
    if not prompt:
        raise ValueError(f"{source} 为空")
    if len(prompt) > 12000:
        raise ValueError(f"{source} 过长（{len(prompt)} 字符），请拆成更短的卡片 prompt")
    return prompt


# ---------- settings ----------

class Settings:
    def __init__(self):
        load_env()
        self.base_url = normalize_base_url(env("XHS_IMAGE_BASE_URL") or env("OPENAI_BASE_URL"))
        self.model = env("XHS_IMAGE_MODEL") or env("OPENAI_IMAGE_MODEL") or "gpt-image-1"
        self.api_key = env("XHS_IMAGE_API_KEY") or env("OPENAI_API_KEY") or ""
        self.size = env("XHS_IMAGE_SIZE") or "1024x1536"
        self.quality = env("XHS_IMAGE_QUALITY", "high")
        self.timeout = int(env("XHS_IMAGE_TIMEOUT", "120"))
        self.retries = int(env("XHS_IMAGE_RETRIES", "2"))
        try:
            self.extra_headers = json.loads(env("XHS_IMAGE_EXTRA_HEADERS") or env("OPENAI_EXTRA_HEADERS") or "{}")
            self.extra_payload = json.loads(env("XHS_IMAGE_EXTRA_PAYLOAD") or env("OPENAI_EXTRA_PAYLOAD") or "{}")
        except json.JSONDecodeError:
            raise ValueError("XHS_IMAGE_EXTRA_HEADERS / XHS_IMAGE_EXTRA_PAYLOAD 必须是合法 JSON")
        if not isinstance(self.extra_headers, dict):
            raise ValueError("XHS_IMAGE_EXTRA_HEADERS 必须是 JSON object")
        if not isinstance(self.extra_payload, dict):
            raise ValueError("XHS_IMAGE_EXTRA_PAYLOAD 必须是 JSON object")
        validate_size(self.size)


# ---------- http (stdlib, requests 可选加速) ----------

def _try_import_requests():
    try:
        import requests
        return requests
    except ImportError:
        return None


def post_json(url, headers, payload, timeout):
    requests = _try_import_requests()
    if requests is not None:
        resp = requests.post(url, headers=headers, json=payload, timeout=timeout)
        if resp.status_code >= 400:
            raise RuntimeError(f"{resp.status_code}: {resp.text[:500]}")
        return resp.json()
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            text = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        text = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{exc.code}: {text[:500]}") from exc
    return json.loads(text)


def fetch_url(url, timeout=120):
    requests = _try_import_requests()
    if requests is not None:
        r = requests.get(url, timeout=timeout)
        r.raise_for_status()
        return r.content
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return response.read()


# ---------- core ----------

def build_payload(settings, prompt, size, n=1):
    prompt = validate_prompt(prompt)
    image_size = validate_size(size or settings.size)
    payload = {
        "model": settings.model,
        "prompt": prompt,
        "n": n,
        "size": image_size,
    }
    if settings.quality:
        payload["quality"] = settings.quality
    payload.update(settings.extra_payload)
    return payload


def request_image(settings, prompt, size):
    if not settings.api_key:
        raise RuntimeError("缺少 XHS_IMAGE_API_KEY（或 OPENAI_API_KEY）；用 --dry-run 可免 key 自检")
    headers = {"Authorization": f"Bearer {settings.api_key}", "Content-Type": "application/json"}
    headers.update(settings.extra_headers)
    payload = build_payload(settings, prompt, size)
    endpoint = f"{settings.base_url}/images/generations"

    last_error = None
    for attempt in range(settings.retries + 1):
        try:
            return post_json(endpoint, headers, payload, settings.timeout)
        except Exception as exc:
            last_error = exc
            if attempt < settings.retries:
                time.sleep(1.5 * (attempt + 1) + random.uniform(0, 0.5))
    raise RuntimeError(f"出图请求失败：{last_error}")


def extract_bytes(response_json):
    data = response_json.get("data") or []
    if not data:
        raise RuntimeError("响应没有 data 字段")
    first = data[0]
    if "b64_json" in first:
        return base64.b64decode(first["b64_json"])
    if "url" in first:
        return fetch_url(first["url"])
    raise RuntimeError("响应既无 b64_json 也无 url")


def generate_one(settings, prompt, out_path, size, dry_run):
    out_path = Path(out_path)
    payload = build_payload(settings, prompt, size)
    if dry_run:
        dry = {
            "endpoint": f"{settings.base_url}/images/generations",
            "model": settings.model,
            "size": payload["size"],
            "payload": payload,
        }
        out_path.parent.mkdir(parents=True, exist_ok=True)
        dry_path = out_path.parent / f"{out_path.stem}.request.json"
        dry_path.write_text(json.dumps(dry, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"out": str(out_path), "dry_run": str(dry_path), "status": "dry-run"}

    response_json = request_image(settings, prompt, size)
    image_bytes = extract_bytes(response_json)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(image_bytes)
    return {"out": str(out_path), "status": "ok"}


# ---------- batch sources ----------

def collect_batch(args):
    """返回 [(prompt, out_name, size), ...]。"""
    tasks = []
    if args.batchfile:
        items = json.loads(Path(args.batchfile).read_text(encoding="utf-8"))
        if not isinstance(items, list):
            raise ValueError("batchfile 必须是 JSON array")
        for i, item in enumerate(items, 1):
            if not isinstance(item, dict):
                raise ValueError(f"batchfile 第 {i} 项必须是 object")
            prompt = item.get("prompt") or (Path(item["prompt_file"]).read_text(encoding="utf-8") if item.get("prompt_file") else "")
            prompt = validate_prompt(prompt, f"batchfile 第 {i} 项 prompt")
            out = item.get("out") or f"{i:02d}.png"
            if Path(out).is_absolute() or ".." in Path(out).parts:
                raise ValueError(f"batchfile 第 {i} 项 out 不允许绝对路径或 ..：{out}")
            if item.get("size"):
                validate_size(item["size"])
            tasks.append((prompt.strip(), out, item.get("size")))
    elif args.prompts_dir:
        files = sorted(p for p in Path(args.prompts_dir).glob("*.md"))
        for i, f in enumerate(files, 1):
            prompt = validate_prompt(f.read_text(encoding="utf-8"), str(f))
            tasks.append((prompt, f"{i:02d}-{f.stem}.png", None))
    return tasks


# ---------- cli ----------

def parse_args(argv):
    parser = argparse.ArgumentParser(description="OpenAI 兼容出图（单图 / 批量 / dry-run）")
    parser.add_argument("--prompt")
    parser.add_argument("--prompt-file")
    parser.add_argument("--out", help="单图输出路径")
    parser.add_argument("--prompts-dir", help="批量：读取该目录下所有 .md 作为 prompt")
    parser.add_argument("--batchfile", help="批量：JSON 文件 [{prompt|prompt_file, out, size?}]")
    parser.add_argument("--out-dir", help="批量输出目录")
    parser.add_argument("--size", default=None, help="覆盖尺寸，如 1024x1536 / 1024x1024")
    parser.add_argument("--concurrency", type=int, default=1, help="批量并发数，默认 1；确认网关限流足够后再调高")
    parser.add_argument("--dry-run", action="store_true", help="只写请求 JSON，不真正调用")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv or sys.argv[1:])
    try:
        settings = Settings()
    except ValueError as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False))
        return 1

    # 单图模式
    if not (args.prompts_dir or args.batchfile):
        try:
            if args.prompt_file:
                prompt = validate_prompt(Path(args.prompt_file).read_text(encoding="utf-8"), args.prompt_file)
            elif args.prompt:
                prompt = validate_prompt(args.prompt, "--prompt")
            else:
                print(json.dumps({"error": "需要 --prompt / --prompt-file 或 --prompts-dir / --batchfile"}, ensure_ascii=False))
                return 1
            if not args.out:
                print(json.dumps({"error": "单图模式需要 --out"}, ensure_ascii=False))
                return 1
            result = generate_one(settings, prompt, args.out, args.size, args.dry_run)
        except (OSError, RuntimeError, ValueError) as exc:
            print(json.dumps({"error": str(exc)}, ensure_ascii=False))
            return 1
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    # 批量模式
    if not args.out_dir:
        print(json.dumps({"error": "批量模式需要 --out-dir"}, ensure_ascii=False))
        return 1
    try:
        tasks = collect_batch(args)
    except (OSError, ValueError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False))
        return 1
    if not tasks:
        print(json.dumps({"error": "没有可生成的任务（检查 prompts-dir / batchfile）"}, ensure_ascii=False))
        return 1

    results = []
    with ThreadPoolExecutor(max_workers=max(1, args.concurrency)) as pool:
        future_map = {
            pool.submit(generate_one, settings, prompt, Path(args.out_dir) / out_name, size, args.dry_run): out_name
            for prompt, out_name, size in tasks
        }
        for future in as_completed(future_map):
            out_name = future_map[future]
            try:
                results.append(future.result())
            except Exception as exc:
                results.append({"out": out_name, "status": "error", "error": str(exc)})

    results.sort(key=lambda r: r.get("out", ""))
    summary = {
        "total": len(results),
        "ok": sum(1 for r in results if r.get("status") == "ok"),
        "dry_run": sum(1 for r in results if r.get("status") == "dry-run"),
        "error": sum(1 for r in results if r.get("status") == "error"),
        "results": results,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary["error"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
