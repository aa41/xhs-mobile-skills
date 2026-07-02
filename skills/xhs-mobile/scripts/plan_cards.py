#!/usr/bin/env python3
"""把文案规划成 N 张小红书卡片（默认 3，1-9），含 style×layout×palette 与 render_prompt。

复刻 baoyu-xhs-images 的三维体系；详细的 12 style / 8 layout / 3 palette 见
references/card-design.md。本脚本做确定性规划，agent 可在 plan.json 基础上微调 prompt。
"""

import argparse
import json
import re
import sys
from pathlib import Path


ROLES = {
    "daily-dev-log": {"label": "每日开发日志", "tone": "真实开发记录，具体到功能、错误码、截图或决策。"},
    "weekly-dev-log": {"label": "每周开发日志", "tone": "阶段性复盘，有进展、有取舍、有遗留问题。"},
    "release-note": {"label": "版本更新", "tone": "清楚克制，先讲用户能感知到的变化。"},
    "daily-ops": {"label": "日常运营", "tone": "运营复盘，讲动作、反馈和下一步。"},
    "product-diary": {"label": "产品日记", "tone": "围绕用户场景和产品取舍。"},
}

STYLE_PRESETS = {
    "cute": {
        "name": "cute",
        "description": "甜美可爱，圆润元素、柔和配色、手绘感图标",
        "material": "圆角卡片、柔和渐变、小贴纸、暖色高光",
    },
    "fresh": {
        "name": "fresh",
        "description": "清爽自然，白底为主、绿色点缀、呼吸感留白",
        "material": "轻阴影、细线图标、植物元素、纸张肌理",
    },
    "warm": {
        "name": "warm",
        "description": "温暖亲切，暖色调、毛玻璃质感、生活化元素",
        "material": "磨砂玻璃、暖色渐变、柔和阴影、布纹肌理",
    },
    "bold": {
        "name": "bold",
        "description": "高对比强冲击，大色块、粗标题、视觉张力",
        "material": "强对比色、几何图形、粗边框、投影层次",
    },
    "minimal": {
        "name": "minimal",
        "description": "极简精致，大量留白、克制配色、精准排版",
        "material": "细线分隔、微阴影、单色系渐变、网格对齐",
    },
    "retro": {
        "name": "retro",
        "description": "复古怀旧，暖黄纸底、打字机字体、旧印刷质感",
        "material": "纸张做旧、网点纹理、褪色彩印、胶卷颗粒感",
    },
    "pop": {
        "name": "pop",
        "description": "鲜艳活力，高饱和配色、波普艺术、大胆图案",
        "material": "荧光色、粗边框、波点纹理、漫画网点",
    },
    "notion": {
        "name": "notion",
        "description": "极简手绘线稿知性风格，白底、淡灰网格、模块化信息块",
        "material": "虚线边框、淡灰网格底纹、手绘感图标、轻阴影卡片",
    },
    "chalkboard": {
        "name": "chalkboard",
        "description": "黑板粉笔风格，深色底、粉笔手写、公式草图感",
        "material": "黑板纹理、粉笔笔触、彩色粉笔标注、粉尘颗粒",
    },
    "study-notes": {
        "name": "study-notes",
        "description": "真实手写笔记风格，蓝笔主写、红笔批注、黄荧光笔高亮",
        "material": "横线纸底纹、手写字体、荧光笔痕迹、红笔圈注、胶带贴纸",
    },
    "screen-print": {
        "name": "screen-print",
        "description": "海报丝网印刷风格，叠色效果、油墨质感、手工感",
        "material": "油墨叠印、纸张粗纹理、套色偏移、丝网网点",
    },
    "sketch-notes": {
        "name": "sketch-notes",
        "description": "手绘信息图风格，马卡龙暖奶油底、流程图、涂鸦元素",
        "material": "马克笔色块、手绘箭头、便签、涂鸦边框、暖奶油纸底",
    },
}

LAYOUT_PRESETS = {
    "hero-dashboard": {
        "name": "hero-dashboard",
        "description": "上方大标题，中部真实界面/设备渲染，下方三枚状态指标",
        "density": "中高信息密度，首屏 3 秒内能读懂主题",
    },
    "flow-map": {
        "name": "flow-map",
        "description": "流程地图，节点有小状态灯，突出路径和动作",
        "density": "中等信息密度，重点突出路径和动作",
    },
    "checklist-debug": {
        "name": "checklist-debug",
        "description": "检查清单 + 要点 + 局部标注，适合功能说明与排查",
        "density": "高信息密度，但分区清晰，不要挤满",
    },
    "sparse": {
        "name": "sparse",
        "description": "极简布局，1-2 个核心信息点，大留白",
        "density": "低信息密度，适合封面或金句",
    },
    "balanced": {
        "name": "balanced",
        "description": "均衡布局，3-4 个信息点，图文比例协调",
        "density": "中等信息密度，适合常规内容",
    },
    "dense": {
        "name": "dense",
        "description": "密集布局，5-8 个信息点，知识卡片式编排",
        "density": "高信息密度，适合干货总结",
    },
    "comparison": {
        "name": "comparison",
        "description": "双栏对比布局，Before/After 或优劣对比",
        "density": "中高信息密度，左右对比清晰",
    },
    "list": {
        "name": "list",
        "description": "清单排行布局，4-7 项条目，序号清晰",
        "density": "中高信息密度，条目分明",
    },
}

PALETTES = {
    "macaron": {"name": "macaron", "description": "马卡龙柔和色块（浅蓝/浅绿/浅紫/浅橙），暖白底，柔和干净"},
    "warm": {"name": "warm", "description": "暖色系（橙、赭石、金），暖白纸张、浅杏、墨黑、荧光黄标注"},
    "neon": {"name": "neon", "description": "霓虹色（粉、青、黄），深色底，白底深墨蓝亮蓝荧光绿状态点"},
    # 保留旧名称作为别名
    "macaron-tech": {"name": "macaron-tech", "description": "奶油白、雾蓝、薄荷绿、少量珊瑚橙，科技但不冷"},
    "warm-paper": {"name": "warm-paper", "description": "暖白纸张、浅杏、墨黑、荧光黄标注，笔记感更强"},
    "clean-neon": {"name": "clean-neon", "description": "白底、深墨蓝、亮蓝、荧光绿状态点，适合日志和链路检查"},
}

MIN_CARDS, MAX_CARDS, DEFAULT_CARDS = 1, 9, 3


def split_points(text):
    points = []
    for line in text.splitlines():
        cleaned = line.strip(" -•\t")
        if not cleaned:
            continue
        parts = re.split(
            r"(?<=[。！？!?；;：:])|(?=新增|修复|注意|幕后|结果|问题|调整|数据|下一步|功能|页面|分享)",
            cleaned,
        )
        for part in parts:
            point = part.strip(" -•\t；;。 ")
            if point:
                points.append(point)
    if not points:
        points = [text.strip()]
    return merge_heading_points(points)


def merge_heading_points(points):
    merged, pending = [], ""
    for point in points:
        if re.fullmatch(r"[一-龥A-Za-z0-9 ._-]{2,12}[：:]", point):
            pending = f"{pending}{point}"
            continue
        if pending:
            merged.append(f"{pending}{point}")
            pending = ""
        else:
            merged.append(point)
    if pending:
        merged.append(pending)
    return merged


def strip_sentence_end(text):
    return text.rstrip("。！？!?；;，,、 ")


def estimate_count(text, role):
    points = split_points(text)
    punctuation_parts = len(re.findall(r"[。！？!?；;：:]", text))
    length_score = len(text) // 90
    signal_words = len(re.findall(r"新增|修复|调整|注意|数据|复盘|步骤|问题|结果|迁移|上线|功能|页面|分享", text))
    score = max(len(points), punctuation_parts, length_score + signal_words)
    if role in {"release-note", "weekly-dev-log"}:
        score += 1
    score = max(MIN_CARDS, min(MAX_CARDS, score))
    if score <= 2:
        return 1
    if score <= 3:
        return 2
    if score <= 5:
        return 3
    if score <= 8:
        return 4
    return 5


def select_style(role, card_type, point, override=None):
    if override:
        # 允许引用 preset 里的 name 或完全自定义
        if override in STYLE_PRESETS:
            return STYLE_PRESETS[override]
        return {"name": override, "description": f"自定义风格 {override}", "material": "按 references/card-design.md 指定"}
    if card_type == "cover":
        return STYLE_PRESETS["notion"]
    if re.search(r"日志|请求|端口|HTTP|连接|失败|状态|链路", point, re.IGNORECASE):
        return STYLE_PRESETS["sketch-notes"]
    if role in {"daily-dev-log", "weekly-dev-log"}:
        return STYLE_PRESETS["study-notes"]
    if role in {"release-note"}:
        return STYLE_PRESETS["minimal"]
    if role in {"daily-ops"}:
        return STYLE_PRESETS["fresh"]
    return STYLE_PRESETS["notion"]


def select_layout(card_type, point, override=None):
    if override:
        if override in LAYOUT_PRESETS:
            return LAYOUT_PRESETS[override]
        return {"name": override, "description": f"自定义版式 {override}", "density": "按 references/card-design.md 指定"}
    if card_type == "cover":
        return LAYOUT_PRESETS["sparse"]
    if re.search(r"连接|链路|HTTP|流程|步骤|地址|路径", point, re.IGNORECASE):
        return LAYOUT_PRESETS["flow-map"]
    if re.search(r"对比|before|after|优劣|差异|前后", point, re.IGNORECASE):
        return LAYOUT_PRESETS["comparison"]
    return LAYOUT_PRESETS["balanced"]


def select_palette(card_type, point, override=None):
    if override:
        if override in PALETTES:
            return PALETTES[override]
        return {"name": override, "description": f"自定义配色 {override}"}
    if re.search(r"日志|HTTP|请求|连接|状态|链路", point, re.IGNORECASE):
        return PALETTES["neon"]
    if card_type == "summary":
        return PALETTES["warm"]
    return PALETTES["macaron"]


def render_brief(style_preset, layout_preset, palette):
    return (
        f"{style_preset['description']}；{layout_preset['description']}；"
        f"调色={palette['description']}；材质={style_preset['material']}；"
        "层次清楚，微阴影，局部标注，真实界面与日志细节。"
    )


def trim_title(point, limit):
    return strip_sentence_end(point[:limit])


def make_card(index, count, role, point, style_override=None, layout_override=None, palette_override=None):
    clean_point = strip_sentence_end(point)
    if index == 0:
        card_type, title = "cover", trim_title(clean_point, 32)
    elif index == count - 1 and count > 2:
        card_type, title = "summary", "这次留下的判断"
    else:
        card_type, title = "detail", trim_title(clean_point, 28)

    style_preset = select_style(role, card_type, clean_point, style_override)
    layout_preset = select_layout(card_type, clean_point, layout_override)
    palette = select_palette(card_type, clean_point, palette_override)
    render_effect = render_brief(style_preset, layout_preset, palette)

    prompt = "\n".join([
        "小红书竖版图文卡片，1024x1536，高完成度商业插画 + 真实产品界面混合风格。",
        f"角色：{ROLES[role]['label']}；卡片：{index + 1}/{count}；类型：{card_type}。",
        f"主标题：{title}",
        f"内容线索：{clean_point}",
        f"风格预设：{style_preset['name']} - {style_preset['description']}",
        f"版式预设：{layout_preset['name']} - {layout_preset['description']}",
        f"信息密度：{layout_preset['density']}。",
        f"调色板：{palette['name']} - {palette['description']}。",
        f"材质与质感：{style_preset['material']}；真实界面截图感、细腻微阴影、轻颗粒、边缘高光。",
        "画面层次：标题层 / 主视觉层 / 数据或日志层 / 局部标注层 / 留白呼吸区。",
        "必须包含：局部标注、状态点、真实界面或日志块、至少一个和内容相关的小细节。",
        f"渲染重点：{render_effect}",
        "禁止：官方logo，伪造小红书品牌标识，空泛渐变背景，企业PPT感，大段乱码文字，过度简单图标堆砌。",
        "中文排版要稳，主标题清晰可读，细节文字少量但要像真实产品记录。",
    ])

    return {
        "index": index + 1,
        "type": card_type,
        "title": title,
        "source_point": clean_point,
        "aspect": "portrait",
        "api_size": "1024x1536",
        "style": style_preset["name"],
        "layout": layout_preset["name"],
        "palette": palette["name"],
        "render_effect": render_effect,
        "render_prompt": prompt,
    }


def plan_assets(text, role="daily-dev-log", count=None, style=None, layout=None, palette=None):
    if role not in ROLES:
        raise ValueError(f"unknown role: {role}")
    if count is None:
        count = DEFAULT_CARDS
    count = max(MIN_CARDS, min(MAX_CARDS, int(count)))

    points = split_points(text)
    while len(points) < count:
        points.append(points[-1])

    cards = [
        make_card(i, count, role, points[i], style, layout, palette)
        for i in range(count)
    ]
    return {"role": ROLES[role], "card_count": count, "cards": cards}


def parse_args(argv):
    parser = argparse.ArgumentParser(description="规划 N 张小红书卡片（默认 3）")
    parser.add_argument("--text")
    parser.add_argument("--file")
    parser.add_argument("--role", default="daily-dev-log", choices=sorted(ROLES))
    parser.add_argument("--count", type=int, default=DEFAULT_CARDS, help=f"卡片张数 {MIN_CARDS}-{MAX_CARDS}，默认 {DEFAULT_CARDS}")
    parser.add_argument("--style", default=None, help="覆盖风格名（见 references/card-design.md）")
    parser.add_argument("--layout", default=None, help="覆盖版式名")
    parser.add_argument("--palette", default=None, help="覆盖配色名")
    parser.add_argument("--out", default=None)
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv or sys.argv[1:])
    if args.file:
        text = Path(args.file).read_text(encoding="utf-8")
    elif args.text:
        text = args.text
    else:
        text = sys.stdin.read()

    if not (MIN_CARDS <= args.count <= MAX_CARDS):
        print(json.dumps({"error": f"count 必须在 {MIN_CARDS}-{MAX_CARDS}"}, ensure_ascii=False))
        return 1

    result = plan_assets(text, args.role, args.count, args.style, args.layout, args.palette)
    output = json.dumps(result, ensure_ascii=False, indent=2)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(output, encoding="utf-8")
    else:
        print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
