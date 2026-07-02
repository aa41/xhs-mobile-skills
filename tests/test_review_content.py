import review_content


def test_ai_tone_detected():
    text = "在这个快节奏的时代，我们全面升级了体验，赋能用户。希望对你有帮助。今天修了分享接口 401。"
    result = review_content.review_text(text, "daily-dev-log")
    categories = {i["category"] for i in result["issues"]}
    assert "ai_tone" in categories
    assert result["passed"] is False


def test_clean_text_passes():
    text = (
        "今天把分享卡顿收了个尾。用户截图反馈点分享卡 2 秒，定位到主线程读图。"
        "改成异步加载后，耗时从 2100ms 降到 80ms。下一步看安卓 8 以下的表现。"
    )
    result = review_content.review_text(text, "daily-dev-log")
    assert result["passed"], result["issues"]


def test_abstract_claim_without_concrete_flagged():
    text = "我们优化了体验，提升了效率。"
    result = review_content.review_text(text, "release-note")
    assert any(i["category"] == "ai_tone" for i in result["issues"])


def test_publishing_risk_xhs():
    text = "用 access_key 就能稳定一键发布笔记，无需人工。"
    issues = review_content.review_publishing_risk(text, "xhs")
    assert any(i["category"] == "publishing_risk" for i in issues)


def test_platform_fit_wechat_too_short():
    issues = review_content.review_platform_fit("太短了。", "wechat")
    assert any(i["category"] == "platform_fit" for i in issues)
