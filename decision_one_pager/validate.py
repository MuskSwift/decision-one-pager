"""Exact H2 heading validation for the decision one-pager."""

from __future__ import annotations

REQUIRED_HEADINGS: tuple[str, ...] = (
    "## 问题陈述",
    "## 选项对比",
    "## 推荐",
    "## 否决或缓做",
    "## 待核实事实",
    "## 明确不做",
)


def missing_headings(markdown: str) -> list[str]:
    """Return required H2 strings that are absent (exact substring match)."""
    return [heading for heading in REQUIRED_HEADINGS if heading not in markdown]
