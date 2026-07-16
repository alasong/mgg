"""Tests for skill routing (_infer_skill)."""

from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from mgg import _infer_skill


def test_route_review():
    """'审查' keyword routes to paa."""
    assert _infer_skill("审查一下这段代码") == "paa"
    assert _infer_skill("review the PR") == "paa"


def test_route_parallel():
    """'并行' keyword routes to pdu."""
    assert _infer_skill("并行处理多个模块") == "pdu"
    assert _infer_skill("跑多个任务") == "pdu"


def test_route_tdd():
    """'tdd' or '测试驱动' routes to ulw."""
    assert _infer_skill("用tdd实现这个功能") == "ulw"
    assert _infer_skill("测试驱动开发") == "ulw"


def test_route_pipeline():
    """'流程' or 'pipeline' routes to pfs."""
    assert _infer_skill("定义一个部署流程") == "pfs"
    assert _infer_skill("multi-step pipeline") == "pfs"


def test_route_research():
    """'分析' or 'research' routes to pff."""
    assert _infer_skill("分析系统性能") == "pff"
    assert _infer_skill("research the api options") == "pff"


def test_route_default():
    """Unmatched prompt defaults to pdu."""
    assert _infer_skill("写一个函数") == "pdu"
    assert _infer_skill("hello world") == "pdu"


def test_route_case_insensitive():
    """Keyword matching is case-insensitive."""
    assert _infer_skill("REVIEW the design") == "paa"
    assert _infer_skill("TDD") == "ulw"


def test_route_mixed_keywords():
    """When multiple keywords match, first registered keyword wins."""
    result = _infer_skill("分析并审查代码")
    # 'review'/'审查' is checked before '分析'/'research' in source
    assert result == "paa"
