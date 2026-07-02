#!/usr/bin/env python3
"""确定性的反 AI 味 / 角色契合度审稿，用于中文发布文案门禁。"""

import argparse
import json
import re
import sys
from pathlib import Path


AI_TONE_PATTERNS = [
    "在这个快节奏的时代",
    "赋能",
    "全面升级",
    "重磅上线",
    "焕新",
    "希望对你有帮助",
    "让我们一起",
    "不难发现",
    "以下是",
    "我们很兴奋地宣布",
    "我很高兴地宣布",
    "完整的解决方案",
    "值得注意的是",
    "通过这种方式",
]

AI_TONE_REGEXES = [
    r"作为一?个\s*AI",
    r"作为一?名\s*AI",
    r"(很兴奋|很高兴).{0,6}宣布",
    r"(完整|全面).{0,4}(总结|解决方案|指南)",
]

ROLE_SIGNALS = {
    "daily-dev-log": [
        [r"\d+", r"接口|日志|错误码|bug|Bug|修复|超时|重试|上线|配置|白名单|截图|模块|功能|页面|分享"],
    ],
    "weekly-dev-log": [
        [r"本周|这周|周一|周二|周三|周四|周五", r"\d+|上线|遗留|指标|接口|修复|新增|用户|截图|反馈|数据"],
        [r"\d+|接口|错误码|截图|指标|数据|用户反馈|上线|修复|新增|遗留"],
    ],
    "release-note": [
        [r"版本|新增|修复|调整|上线", r"迁移|废弃|注意|影响|用户|配置|字段|功能|页面"],
    ],
    "daily-ops": [
        [r"数据|曝光|转化|评论|私信|活动|投放|选题", r"复盘|反馈|观察|标签|账号|笔记"],
    ],
    "product-diary": [
        [r"用户|场景|反馈|取舍", r"体验|路径|为什么|不做|入口|流程|功能"],
    ],
}


def add_issue(issues, category, message, evidence):
    issues.append({"category": category, "message": message, "evidence": evidence})


def review_text(text, role="daily-dev-log"):
    if role not in ROLE_SIGNALS:
        raise ValueError(f"unknown role: {role}")

    issues = []

    for pattern in AI_TONE_PATTERNS:
        if pattern in text:
            add_issue(issues, "ai_tone", "删除模板化或营销化表达", pattern)

    for pattern in AI_TONE_REGEXES:
        if re.search(pattern, text, re.IGNORECASE):
            add_issue(issues, "ai_tone", "删除 AI 自我指称或英文报告句式", pattern)

    if re.search(r"(优化|提升|改善|升级).{0,8}(体验|效率|能力|质量)", text) and not re.search(
        r"\d|接口|日志|错误码|截图|用户|评论|耗时|配置|模块|功能|页面|分享", text
    ):
        add_issue(
            issues,
            "ai_tone",
            "抽象成效缺少具体对象，给一个实物（功能名/截图/耗时/反馈）",
            "优化/提升/改善/升级 + 体验/效率/能力/质量",
        )

    role_groups = ROLE_SIGNALS[role]
    if not all(any(re.search(pattern, text) for pattern in group) for group in role_groups):
        add_issue(issues, "role_fit", f"内容缺少 {role} 应有的具体证据", role)

    if len(text.strip()) < 20:
        add_issue(issues, "role_fit", "内容太短，无法形成可信笔记", text.strip())

    return {"passed": not issues, "role": role, "issues": issues}


def review_platform_fit(text, platform):
    issues = []
    if platform == "xhs":
        if len(text.strip()) > 1200:
            add_issue(issues, "platform_fit", "小红书正文过长，建议拆卡或压缩", "length>1200")
        if not re.search(r"#|标签|开发|运营|版本|产品|功能|分享|小红书", text):
            add_issue(issues, "platform_fit", "缺少可搜索标签或明确笔记主题", platform)
    elif platform == "wechat":
        if len(text.strip()) < 80:
            add_issue(issues, "platform_fit", "公众号正文过短，难以形成完整文章", "length<80")
    return issues


def review_publishing_risk(text, platform):
    issues = []
    if platform == "xhs":
        risky = [
            r"access_key.{0,12}(发布|一键|自动|稳定)",
            r"(稳定|保证|无需人工).{0,12}(一键发布|自动发布|发笔记)",
            r"绕过.{0,8}(审核|风控|验证码)",
            r"Cookie.{0,12}(稳定|永久|保证)",
        ]
        for pattern in risky:
            if re.search(pattern, text, re.IGNORECASE):
                add_issue(
                    issues,
                    "publishing_risk",
                    "不要承诺小红书普通账号稳定一键发布；改成分享包或人工确认流程",
                    pattern,
                )
    if platform == "wechat" and "草稿" in text and "发布成功" in text:
        add_issue(
            issues,
            "publishing_risk",
            "草稿创建不等于发布成功，公众号需走 freepublish 或人工发布",
            "草稿 + 发布成功",
        )
    return issues


def multi_agent_review(text, role="daily-dev-log", platform="xhs"):
    role_review = review_text(text, role)
    reviews = [
        {"agent": "role_editor", "focus": "人格/角色审稿", "issues": role_review["issues"]},
        {"agent": "platform_editor", "focus": "平台适配审稿", "issues": review_platform_fit(text, platform)},
        {"agent": "publishing_risk_editor", "focus": "发布风险审稿", "issues": review_publishing_risk(text, platform)},
    ]
    return {
        "passed": all(not review["issues"] for review in reviews),
        "role": role,
        "platform": platform,
        "reviews": reviews,
    }


def parse_args(argv):
    parser = argparse.ArgumentParser(description="反 AI 味 / 角色契合度审稿")
    parser.add_argument("--text")
    parser.add_argument("--file")
    parser.add_argument("--role", default="daily-dev-log", choices=sorted(ROLE_SIGNALS))
    parser.add_argument("--platform", choices=["xhs", "wechat"], default="xhs")
    parser.add_argument("--multi-agent", action="store_true")
    parser.add_argument("--out")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv or sys.argv[1:])
    if args.file:
        text = Path(args.file).read_text(encoding="utf-8")
    elif args.text:
        text = args.text
    else:
        text = sys.stdin.read()

    result = (
        multi_agent_review(text, args.role, args.platform)
        if args.multi_agent
        else review_text(text, args.role)
    )

    # 非 multi-agent 模式下也追加平台适配和发布风险检查
    if not args.multi_agent:
        extra_issues = (
            review_platform_fit(text, args.platform) +
            review_publishing_risk(text, args.platform)
        )
        if extra_issues:
            result["issues"].extend(extra_issues)
            result["passed"] = False

    output = json.dumps(result, ensure_ascii=False, indent=2)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(output, encoding="utf-8")
    else:
        print(output)
    return 0 if result["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
