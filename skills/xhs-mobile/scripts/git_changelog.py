#!/usr/bin/env python3
"""把 git 提交历史转成结构化 JSON，供 agent 改写成面向用户的文案。

只做「结构化 + 轻量分类」；反技术叙事的判断由 agent 按 references/style-guide.md 执行。
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path


REC_SEP = "\x1e<<<REC>>>\x1e"
FIELD_SEP = "\x1f"

# 这些 type 通常是用户不可感知的内部改动；标记给 agent 参考（不删除）
INTERNAL_TYPES = {"chore", "ci", "test", "build", "style", "docs", "refactor", "perf", "revert"}

# 文件名里出现这些路径，多半是内部工程文件
INTERNAL_PATH_HINTS = (
    ".github/", "package-lock", "yarn.lock", "Pipfile", "requirements",
    "tsconfig", ".eslintrc", ".prettierrc", "Dockerfile", "Makefile",
)


def run_git(repo, args):
    cmd = ["git", "-C", str(repo)] + args
    try:
        result = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True,
            errors="replace",
        )
    except FileNotFoundError as exc:
        raise RuntimeError("git 未安装或不在 PATH") from exc
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(f"git 命令失败：{' '.join(cmd)}\n{exc.stderr.strip()}") from exc
    return result.stdout


def is_git_repo(repo):
    if (repo / ".git").exists():
        return True
    try:
        return run_git(repo, ["rev-parse", "--is-inside-work-tree"]).strip() == "true"
    except RuntimeError:
        return False


def parse_subject(subject):
    """解析 conventional commit: type(scope)[!]: desc。返回 (type, scope, clean)。"""
    match = re.match(r"^\s*([a-zA-Z]+)(?:\(([^)]+)\))?\s*!?:?\s*(.*)$", subject)
    if not match:
        return "", "", subject.strip()
    ctype, scope, desc = match.group(1).lower(), (match.group(2) or "").strip(), match.group(3).strip()
    return ctype, scope, desc


# \b 对中文无效，中文词单独用裸匹配
INTERNAL_SUBJECT_RE = re.compile(r"\b(bump|upgrade|update dep)\b|依赖升级|依赖更新|版本升级|升级依赖")


def is_likely_internal(ctype, subject):
    if ctype in INTERNAL_TYPES:
        return True
    return bool(INTERNAL_SUBJECT_RE.search(subject.lower()))


def collect_commits(repo, since, until, author, limit):
    fmt = FIELD_SEP.join(["%H", "%ad", "%an", "%s", "%b"]) + REC_SEP
    args = ["log", f"--pretty=format:{fmt}", "--date=short"]
    if since:
        args.append(f"--since={since}")
    if until:
        args.append(f"--until={until}")
    if author:
        args.append(f"--author={author}")
    if limit:
        args.append(f"-n{limit}")

    raw = run_git(repo, args)
    records = [r for r in raw.split(REC_SEP) if r.strip()]
    commits = []
    for record in records:
        parts = record.split(FIELD_SEP)
        if len(parts) < 4:
            continue
        sha, date, who, subject = parts[0], parts[1], parts[2], parts[3]
        body = parts[4] if len(parts) > 4 else ""
        body = body.strip()
        ctype, scope, clean = parse_subject(subject)
        commits.append({
            "sha": sha,
            "date": date,
            "author": who,
            "subject": subject.strip(),
            "clean_subject": clean,
            "type": ctype,
            "scope": scope,
            "body": body,
            "likely_internal": is_likely_internal(ctype, subject),
        })
    return commits


def summarize(commits):
    types = {}
    internal = 0
    for commit in commits:
        types[commit["type"] or "other"] = types.get(commit["type"] or "other", 0) + 1
        if commit["likely_internal"]:
            internal += 1
    dates = [c["date"] for c in commits if c["date"]]
    return {
        "count": len(commits),
        "internal_count": internal,
        "user_facing_count": len(commits) - internal,
        "date_range": [min(dates), max(dates)] if dates else [],
        "types": types,
        "authors": sorted({c["author"] for c in commits}),
    }


def parse_args(argv):
    parser = argparse.ArgumentParser(description="git log → 结构化 JSON")
    parser.add_argument("--repo", default=".", help="git 仓库路径（默认当前目录）")
    parser.add_argument("--since", default=None, help="起始时间，如 '7 days ago' 或 '2026-06-01'")
    parser.add_argument("--until", default=None, help="结束时间")
    parser.add_argument("--author", default=None, help="按作者过滤")
    parser.add_argument("--limit", type=int, default=None, help="最多取多少条")
    parser.add_argument("--out", default=None, help="输出文件路径；不指定则打印到 stdout")
    parser.add_argument("--user-facing-only", action="store_true", help="只输出非内部提交")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv or sys.argv[1:])
    repo = Path(args.repo).expanduser().resolve()
    if not is_git_repo(repo):
        print(json.dumps({"error": f"不是 git 仓库：{repo}"}, ensure_ascii=False))
        return 1
    try:
        commits = collect_commits(repo, args.since, args.until, args.author, args.limit)
    except RuntimeError as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False))
        return 1

    if args.user_facing_only:
        commits = [c for c in commits if not c["likely_internal"]]

    result = {"repo": str(repo), "summary": summarize(commits), "commits": commits}
    output = json.dumps(result, ensure_ascii=False, indent=2)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(output, encoding="utf-8")
    else:
        print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
