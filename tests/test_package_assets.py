import json
from pathlib import Path

import package_assets


def _make_images(tmp_path):
    images_dir = tmp_path / "src_images"
    images_dir.mkdir()
    for i in range(1, 4):
        (images_dir / f"{i:02d}-cover.png").write_bytes(b"\x89PNG fake")
    return images_dir


def _make_plan(tmp_path):
    plan = {
        "role": {"label": "版本更新"},
        "card_count": 3,
        "cards": [
            {"index": 1, "title": "封面", "style": "notion-lab", "palette": "macaron-tech", "layout": "hero-dashboard"},
            {"index": 2, "title": "细节", "style": "study-notes", "palette": "macaron-tech", "layout": "checklist-debug"},
            {"index": 3, "title": "总结", "style": "sketch-notes", "palette": "warm-paper", "layout": "checklist-debug"},
        ],
    }
    plan_path = tmp_path / "plan.json"
    plan_path.write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")
    return plan_path


def test_package_writes_manifest_and_images(tmp_path):
    images_dir = _make_images(tmp_path)
    plan_path = _make_plan(tmp_path)
    caption = tmp_path / "caption.md"
    caption.write_text("新增了分享功能，点击就能发到小红书。\n", encoding="utf-8")
    android_dir = tmp_path / "android"

    manifest, post_dir = package_assets.package(
        plan_path=plan_path, images_dir=images_dir, caption_file=caption,
        title="新增分享到小红书", tags=["小红书", "版本更新"],
        wechat_html=None, wechat_title=None, wechat_digest=None,
        android_dir=android_dir, slug="share-xhs", date="2026-07-02", role="release-note",
    )

    assert manifest["id"] == "2026-07-02-share-xhs"
    assert manifest["date"] == "2026-07-02"
    assert manifest["title"] == "新增分享到小红书"
    assert manifest["cardCount"] == 3
    assert len(manifest["cards"]) == 3
    assert manifest["cards"][0]["file"] == "images/01.png"
    assert manifest["cards"][0]["title"] == "封面"
    assert manifest["platforms"] == ["xhs", "wechat"]

    # 文件落盘
    assert (post_dir / "manifest.json").exists()
    assert (post_dir / "images" / "01.png").exists()
    assert (post_dir / "images" / "03.png").exists()
    assert (post_dir / "title.txt").exists()
    assert (post_dir / "caption.md").exists()
    assert (post_dir / "tags.txt").read_text(encoding="utf-8").strip().splitlines() == ["#小红书", "#版本更新"]


def test_slugify():
    assert package_assets.slugify("新增 分享 功能！") == "新增-分享-功能"
    assert package_assets.slugify("") == "post"
