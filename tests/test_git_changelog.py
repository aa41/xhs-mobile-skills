import git_changelog


def test_parse_subject_conventional():
    assert git_changelog.parse_subject("feat(share): add xhs intent") == ("feat", "share", "add xhs intent")
    assert git_changelog.parse_subject("fix: crash on null") == ("fix", "", "crash on null")
    assert git_changelog.parse_subject("随便一句中文") == ("", "", "随便一句中文")


def test_likely_internal_detection():
    assert git_changelog.is_likely_internal("chore", "chore: bump deps")
    assert git_changelog.is_likely_internal("ci", "ci: tweak workflow")
    assert git_changelog.is_likely_internal("build", "build: gradle 8.7")
    assert git_changelog.is_likely_internal("feat", "feat: 依赖升级到 5.x")
    assert not git_changelog.is_likely_internal("feat", "feat: 新增分享功能")


def test_summarize_counts():
    commits = [
        {"date": "2026-07-01", "author": "a", "subject": "feat: x", "type": "feat", "likely_internal": False},
        {"date": "2026-07-02", "author": "b", "subject": "chore: bump", "type": "chore", "likely_internal": True},
    ]
    summary = git_changelog.summarize(commits)
    assert summary["count"] == 2
    assert summary["internal_count"] == 1
    assert summary["user_facing_count"] == 1
    assert summary["date_range"] == ["2026-07-01", "2026-07-02"]
    assert summary["types"]["feat"] == 1
