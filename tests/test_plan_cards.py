import json

import plan_cards


def test_default_count_is_three():
    text = "今天把分享卡顿修了。截图反馈说点分享会卡 2 秒，定位到主线程读图。改成异步后顺了。"
    plan = plan_cards.plan_assets(text, "daily-dev-log")
    assert plan["card_count"] == 3
    assert len(plan["cards"]) == 3


def test_count_override_and_range():
    text = "新增分享功能。修复闪退。调整加载顺序。"
    for n in (1, 9):
        plan = plan_cards.plan_assets(text, "release-note", count=n)
        assert plan["card_count"] == n
    # 超出范围会被 clamp
    plan = plan_cards.plan_assets(text, "release-note", count=20)
    assert plan["card_count"] == plan_cards.MAX_CARDS


def test_each_card_has_render_prompt_and_size():
    plan = plan_cards.plan_assets("新增了小红书分享入口，点击就能把内容发出去。", "release-note", count=3)
    for card in plan["cards"]:
        assert card["api_size"] == "1024x1536"
        assert card["aspect"] == "portrait"
        assert "render_prompt" in card and "1024x1536" in card["render_prompt"]
        assert card["style"] and card["layout"] and card["palette"]


def test_render_prompt_has_text_and_composition_guards():
    plan = plan_cards.plan_assets("新增了小红书分享入口，点击就能把内容发出去。", "release-note", count=1)
    prompt = plan["cards"][0]["render_prompt"]
    assert "文字规则" in prompt
    assert "构图规则" in prompt
    assert "二维码" in prompt
    assert "水印" in prompt


def test_split_points_keeps_feature_name_together():
    plan = plan_cards.plan_assets(
        "新增了小红书分享入口，点击后能把卡片和文案交给手机 App 手动确认发布。",
        "release-note",
        count=1,
    )
    assert plan["cards"][0]["title"] == "新增了小红书分享入口"


def test_cover_and_summary_types():
    plan = plan_cards.plan_assets("内容一。内容二。内容三。", "weekly-dev-log", count=3)
    types = [c["type"] for c in plan["cards"]]
    assert types[0] == "cover"
    assert types[-1] == "summary"


def test_json_serializable():
    plan = plan_cards.plan_assets("一段内容用于序列化测试。", "product-diary", count=2)
    json.dumps(plan, ensure_ascii=False)
