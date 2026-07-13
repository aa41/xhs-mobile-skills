#!/usr/bin/env python3
"""把文案 + 卡片图 + plan.json 打包进 Android App 的 assets/posts/<date>-<slug>/。

产物（App 扫描该目录读取 manifest.json）：
  assets/posts/<YYYY-MM-DD>-<slug>/
    manifest.json   列表/预览用的元数据
    images/01.png .. NN.png
    caption.md      小红书正文
    title.txt       小红书标题
    tags.txt        标签（每行一个）
    wechat.html     公众号正文 HTML
"""

import argparse
import datetime
import json
import re
import shutil
import sys
from pathlib import Path

from runtime_paths import resolve_android_dir

ASSETS_POSTS_REL = "app/src/main/assets/posts"


def slugify(text):
    text = re.sub(r"[^\w一-龥 -]", "", text or "").strip()
    text = re.sub(r"[\s_-]+", "-", text)
    return text[:40].strip("-").lower() or "post"


def today():
    return datetime.date.today().isoformat()


def copy_images(images_dir, dest_images_dir):
    dest_images_dir.mkdir(parents=True, exist_ok=True)
    sources = sorted(
        p for p in Path(images_dir).iterdir()
        if p.is_file() and p.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}
    )
    copied = []
    for index, src in enumerate(sources, 1):
        target = dest_images_dir / f"{index:02d}{src.suffix.lower()}"
        shutil.copy2(src, target)
        copied.append({"file": f"images/{target.name}", "index": index})
    return copied


def build_manifest(*, post_id, date, slug, title, role, caption, tags, cards, wechat, plan_meta):
    return {
        "id": post_id,
        "date": date,
        "slug": slug,
        "title": title,
        "role": role,
        "platforms": ["xhs", "wechat"],
        "caption": caption,
        "tags": tags,
        "cards": cards,
        "wechat": wechat,
        "style": plan_meta.get("style"),
        "palette": plan_meta.get("palette"),
        "layout": plan_meta.get("layout"),
        "cardCount": len(cards),
    }


def package(*, plan_path, images_dir, caption_file, title, tags, wechat_html, wechat_title,
            wechat_digest, android_dir, slug, date, role):
    plan = json.loads(Path(plan_path).read_text(encoding="utf-8")) if plan_path else {}
    cards_meta = plan.get("cards", [])
    plan_style = cards_meta[0].get("style") if cards_meta else None
    plan_palette = cards_meta[0].get("palette") if cards_meta else None
    plan_layout = cards_meta[0].get("layout") if cards_meta else None

    date = date or today()
    slug = slugify(slug or title or "post")
    post_id = f"{date}-{slug}"

    post_dir = Path(android_dir) / ASSETS_POSTS_REL / post_id
    if post_dir.exists():
        shutil.rmtree(post_dir)
    (post_dir / "images").mkdir(parents=True, exist_ok=True)

    # 图片
    copied = copy_images(images_dir, post_dir / "images")
    # 若有 plan 卡片标题，合并到 copied
    if cards_meta and len(cards_meta) == len(copied):
        for card, meta in zip(copied, cards_meta):
            card["title"] = meta.get("title", "")

    # 文案
    caption = Path(caption_file).read_text(encoding="utf-8").strip() if caption_file else ""
    (post_dir / "caption.md").write_text(caption + "\n", encoding="utf-8")
    (post_dir / "title.txt").write_text(title.strip() + "\n", encoding="utf-8")
    (post_dir / "tags.txt").write_text("\n".join(f"#{t}" for t in tags) + "\n", encoding="utf-8")

    # 公众号
    wechat = {
        "title": wechat_title or title,
        "digest": wechat_digest or "",
        "html_file": "wechat.html" if wechat_html else None,
    }
    if wechat_html:
        html = Path(wechat_html).read_text(encoding="utf-8")
        (post_dir / "wechat.html").write_text(html, encoding="utf-8")

    manifest = build_manifest(
        post_id=post_id, date=date, slug=slug, title=title, role=role,
        caption=caption, tags=tags, cards=copied, wechat=wechat,
        plan_meta={"style": plan_style, "palette": plan_palette, "layout": plan_layout},
    )
    (post_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return manifest, post_dir


def parse_tags(raw):
    tags = []
    for item in raw:
        for tag in item.replace(",", " ").split():
            cleaned = tag.strip().lstrip("#")
            if cleaned:
                tags.append(cleaned)
    return tags


def parse_args(argv):
    parser = argparse.ArgumentParser(description="打包到 Android assets/posts/")
    parser.add_argument("--plan", default=None, help="plan_cards.py 产出的 plan.json")
    parser.add_argument("--images-dir", required=True)
    parser.add_argument("--caption-file", default=None)
    parser.add_argument("--title", required=True)
    parser.add_argument("--tag", action="append", default=[])
    parser.add_argument("--wechat-html", default=None)
    parser.add_argument("--wechat-title", default=None)
    parser.add_argument("--wechat-digest", default=None)
    parser.add_argument("--android-dir", default=None,
                        help="默认使用 ~/.xhs-mobile/runtime/android")
    parser.add_argument("--slug", default=None)
    parser.add_argument("--date", default=None, help="YYYY-MM-DD，默认今天")
    parser.add_argument("--role", default="daily-dev-log")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv or sys.argv[1:])
    android_dir = resolve_android_dir(args.android_dir, __file__)
    if not (android_dir / "gradlew").exists():
        print(json.dumps({
            "error": f"未安装全局 Android Runtime：{android_dir}",
            "hint": "请重新运行 install_skill.py --target all --scope global"
        }, ensure_ascii=False))
        return 1
    manifest, post_dir = package(
        plan_path=args.plan,
        images_dir=args.images_dir,
        caption_file=args.caption_file,
        title=args.title,
        tags=parse_tags(args.tag),
        wechat_html=args.wechat_html,
        wechat_title=args.wechat_title,
        wechat_digest=args.wechat_digest,
        android_dir=android_dir,
        slug=args.slug,
        date=args.date,
        role=args.role,
    )
    print(json.dumps({"post_dir": str(post_dir), "manifest": manifest}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
