"""策略层：买入/卖出/风控规则引擎。

对外主入口 generate_advice：把指标层的候选榜单转化为可执行操作建议。
"""

from __future__ import annotations

from typing import Any

from backend.strategy import entry, exit, risk

__all__ = ["generate_advice", "entry", "exit", "risk"]


def generate_advice(scoring_result: dict[str, Any]) -> dict[str, Any]:
    """根据指标层结果生成完整操作建议。

    scoring_result: indicators.scoring.build_candidates() 的返回
    """
    sentiment = scoring_result["sentiment"]
    candidates = scoring_result["candidates"]

    entries = [entry.entry_advice(c, sentiment) for c in candidates]
    # 可买入清单（S/A 级，且非空仓）
    buyable = [e for e in entries if e["action"] in ("盘中追入", "尾盘买入")]

    return {
        "sentiment": sentiment,
        "risk": risk.risk_summary(sentiment),
        "board_heat": scoring_result["board_heat"],
        "entries": entries,                 # 全部候选 + 建议
        "buyable": buyable,                 # 可买入清单
        "max_holdings": 5,                  # 均衡型最大持仓
    }
