"""风控规则（均衡型）。

单股仓位、总仓位、止损、空仓条件，参数集中自 config.RISK。
"""

from __future__ import annotations

from typing import Any

from backend import config
from backend.indicators import sentiment as senti_mod


def suggest_position(signal: str, sentiment_stage: str) -> float:
    """单股建议仓位比例（0-1）。

    均衡型：单股上限 25%，信号越强、情绪越热仓位越高。
    """
    cap = config.RISK["single_position"]
    if signal == "S":
        return cap                              # 25%
    if signal == "A":
        return round(cap * 0.8, 2)              # 20%
    if signal == "B":
        return round(cap * 0.4, 2)              # 10%
    return 0.0                                  # C 放弃


def total_position_cap(sentiment_stage: str) -> float:
    """总仓位上限（0-1），由情绪阶段决定。"""
    _, cap = senti_mod.position_suggestion(sentiment_stage)
    return cap


def is_empty_position(sentiment: dict[str, Any]) -> bool:
    """是否空仓：仅冰点/退潮期。分歧预警只作谨慎提示，不直接空仓。"""
    return sentiment["stage"] in (senti_mod.ICE_FROZEN, senti_mod.RECESSION)


def stop_loss_pct() -> float:
    """个股止损线（-6%）。"""
    return config.RISK["stop_loss"]


def risk_summary(sentiment: dict[str, Any]) -> dict[str, Any]:
    """风控摘要，供看板展示。"""
    return {
        "empty_position": is_empty_position(sentiment),
        "single_position_cap": config.RISK["single_position"],
        "total_position_cap": total_position_cap(sentiment["stage"]),
        "stop_loss": config.RISK["stop_loss"],
        "daily_drawdown": config.RISK["daily_drawdown"],
        "take_profit_gap": config.RISK["take_profit_gap"],
        "take_profit_surge": config.RISK["take_profit_surge"],
    }
