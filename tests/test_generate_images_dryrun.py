import json
from pathlib import Path

import generate_images


def test_dry_run_writes_request_without_key(tmp_path, monkeypatch):
    # 确保没有 key 也能 dry-run
    monkeypatch.setenv("XHS_IMAGE_API_KEY", "")
    monkeypatch.setenv("OPENAI_API_KEY", "")
    monkeypatch.setenv("XHS_IMAGE_BASE_URL", "https://api.openai.com/v1")
    monkeypatch.setenv("XHS_IMAGE_MODEL", "gpt-image-1")
    monkeypatch.setenv("XHS_IMAGE_SIZE", "1024x1536")

    settings = generate_images.Settings()
    assert settings.api_key == ""

    out = tmp_path / "01-cover.png"
    result = generate_images.generate_one(settings, "一张封面图", out, "1024x1536", dry_run=True)
    assert result["status"] == "dry-run"

    dry = json.loads(Path(result["dry_run"]).read_text(encoding="utf-8"))
    assert dry["model"] == "gpt-image-1"
    assert dry["size"] == "1024x1536"
    assert dry["payload"]["prompt"] == "一张封面图"
    assert dry["endpoint"].endswith("/images/generations")


def test_build_payload_shape(tmp_path, monkeypatch):
    monkeypatch.setenv("XHS_IMAGE_API_KEY", "")
    settings = generate_images.Settings()
    payload = generate_images.build_payload(settings, "prompt text", "1024x1024")
    assert payload["model"] == settings.model
    assert payload["size"] == "1024x1024"
    assert payload["prompt"] == "prompt text"
    assert payload["n"] == 1


def test_normalize_base_url(monkeypatch):
    assert generate_images.normalize_base_url(None) == "https://api.openai.com/v1"
    assert generate_images.normalize_base_url("https://x.com/v1/") == "https://x.com/v1"
