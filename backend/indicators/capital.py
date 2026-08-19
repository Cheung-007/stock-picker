"""资金流指标与资金维度打分（0-40）。

权重与分档阈值为初版默认值，可校准（见 plan「待校准项」）。
"""

from __future__ import annotations

from typing import Any

from backend import config


def compute_capital_score(
    stock: dict[str, Any],
    history: list[dict[str, Any]] | None,
    lhb: dict[str, Any] | None,
    limit_up_info: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """计算单只股票的资金维度得分（0-40）。

    stock: 当日资金流（get_stock_capital_flow 的一条）
    history: 历史资金流（get_capital_flow_history 返回，用于持续性）
    lhb: 龙虎榜汇总（按 code 索引，用于游资/机构）
    limit_up_info: 涨停池信息；涨停股的主力净流入失真（封单排不进），改用封板强度
    """
    details: dict[str, Any] = {}

    # 1. 涨停股用封板强度，非涨停股用主力净流入额+占比（15 分）
    if limit_up_info:
        details["seal_strength"] = _seal_strength_score(limit_up_info)
        details["net_inflow"] = 0.0
    else:
        inflow = float(stock.get("main_net_inflow") or 0)
        ratio = float(stock.get("main_inflow_ratio") or 0)
        details["net_inflow"] = round(_amount_tier(inflow) + _ratio_tier(ratio), 1)
        details["seal_strength"] = 0.0

    # 2. 资金持续性 3/5 日（10 分）
    details["continuity"] = _continuity_score(history)

    # 3. 龙虎榜 / 游资机构（10 分）
    details["lhb"] = _lhb_score(stock.get("code"), lhb)

    # 4. 量价配合（5 分）
    details["volume_price"] = _volume_price_score(stock)

    total = (details["net_inflow"] + details["seal_strength"]
             + details["continuity"] + details["lhb"] + details["volume_price"])
    return {"score": round(total, 1), "details": details}


def _seal_strength_score(info: dict[str, Any]) -> float:
    """封板强度（0-15）：封单资金 + 封板时间 + 炸板次数。"""
    score = 0.0
    # 封单资金（5 分）
    seal = float(info.get("seal_fund") or 0)
    if seal > 3e8:
        score += 5.0
    elif seal > 1e8:
        score += 4.0
    elif seal > 5e7:
        score += 3.0
    else:
        score += 2.0
    # 封板时间（5 分，越早越强）
    ft = info.get("first_seal_time") or 0
    if ft <= 93000:
        score += 5.0
    elif ft <= 100000:
        score += 4.0
    elif ft <= 113000:
        score += 3.0
    else:
        score += 2.0
    # 炸板次数（5 分，越少越强）
    bc = info.get("break_count") or 0
    if bc == 0:
        score += 5.0
    elif bc == 1:
        score += 3.0
    else:
        score += 1.0
    return score


def _amount_tier(inflow: float) -> float:
    """主力净流入额分档（0-7）。"""
    if inflow > 1e8:
        return 7.0
    if inflow > 5e7:
        return 5.0
    if inflow > 1e7:
        return 3.0
    if inflow > 0:
        return 1.0
    return 0.0


def _ratio_tier(ratio: float) -> float:
    """主力净流入占比分档（0-8）。"""
    if ratio > 20:
        return 8.0
    if ratio > 10:
        return 6.0
    if ratio > 5:
        return 4.0
    if ratio > 0:
        return 2.0
    return 0.0


def _continuity_score(history: list[dict[str, Any]] | None) -> float:
    """资金持续性（0-10）：3/5 日累计主力净流入为正且逐日放大得分更高。"""
    if not history:
        return 0.0
    inflows = [float(h.get("main_net_inflow") or 0) for h in history]

    sum3 = sum(inflows[-3:]) if len(inflows) >= 3 else sum(inflows)
    sum5 = sum(inflows[-5:]) if len(inflows) >= 5 else sum(inflows)
    increasing = len(inflows) >= 3 and all(
        inflows[i] > 0 and inflows[i] >= inflows[i - 1] for i in range(-3, 0)
    )

    if increasing and sum3 > 0:
        return 10.0
    if sum3 > 0:
        return 7.0
    if sum5 > 0:
        return 5.0
    if sum5 > -1e7:
        return 2.0
    return 0.0


def _lhb_score(code: str | None, lhb: dict[str, Any] | None) -> float:
    """龙虎榜得分（0-10）。"""
    if not lhb or not code or code not in lhb:
        return 0.0
    info = lhb[code]
    net = float(info.get("net_amt") or 0)
    if net > 0:
        return 10.0
    return 4.0


def _volume_price_score(stock: dict[str, Any]) -> float:
    """量价配合（0-5）：换手率处于活跃区间且收涨。"""
    turnover = float(stock.get("turnover") or 0)
    pct_chg = float(stock.get("pct_chg") or 0)
    lo, hi = config.FILTER["turnover_min"], config.FILTER["turnover_max"]
    if lo <= turnover <= hi and pct_chg > 0:
        return 5.0
    if lo <= turnover <= hi:
        return 3.0
    return 1.0
