"""买入策略：信号分级 → 买点时点 + 仓位。

S 级盘中追 / A 级尾盘买 / B 级观察 / C 级放弃，情绪冰点/退潮降级为空仓。
"""

from __future__ import annotations

from typing import Any

from backend.strategy import risk

# 信号 → 买点映射
_ACTION = {
    "S": ("盘中追入", "突破/封板确认后追入"),
    "A": ("尾盘买入", "14:30 后确认信号买入"),
    "B": ("观察", "暂不买，跟踪确认"),
    "C": ("放弃", "信号不足"),
}


def entry_advice(candidate: dict[str, Any], sentiment: dict[str, Any]) -> dict[str, Any]:
    """单只候选股的买入建议。"""
    signal = candidate["signal"]
    action, timing = _ACTION.get(signal, ("放弃", ""))

    # 情绪冰点/退潮 → 一律空仓观望
    if risk.is_empty_position(sentiment):
        action, timing = "空仓观望", "市场情绪冰点/退潮，不参与"
        position = 0.0
    else:
        position = risk.suggest_position(signal, sentiment["stage"])

    # 透传 candidate 的全部字段（total_score/pct_chg/limit_up_count 等），
    # 前端候选榜需展示这些打分明细。
    return {
        **candidate,
        "signal": signal,
        "action": action,
        "timing": timing,
        "position": position,
        "reason": candidate.get("reason", ""),
    }
