"""卖出策略（次日，严格隔日 T+1）。

规则优先级：止损 > 止盈 > 时间止损 > 题材退潮离场。
"""

from __future__ import annotations

from typing import Any

from backend import config


def exit_advice(
    holding: dict[str, Any],
    quote: dict[str, Any],
    sentiment: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """持仓股次日卖出建议。

    holding: {code, name, buy_price}
    quote: 当日行情 {price 现价, prev_close 昨收, open 今开, pct_chg 当日涨幅}
    sentiment: 市场情绪（用于题材退潮/龙头断板判断）
    """
    buy_price = float(holding.get("buy_price") or 0)
    price = float(quote.get("price") or 0)
    prev_close = float(quote.get("prev_close") or 0)
    open_price = float(quote.get("open") or 0)
    pct_chg = float(quote.get("pct_chg") or 0)

    if buy_price <= 0 or price <= 0:
        return {"code": holding.get("code"), "action": "持有", "reason": "行情缺失"}

    pnl = (price - buy_price) / buy_price
    gap = (open_price - prev_close) / prev_close if prev_close else 0.0

    # 1. 止损（最高优先级）
    if pnl <= config.RISK["stop_loss"]:
        return {"code": holding.get("code"), "action": "无条件止损", "reason": f"跌破止损线 {pnl:.1%}"}

    # 2. 高开止盈
    if gap > config.RISK["take_profit_gap"]:
        return {"code": holding.get("code"), "action": "竞价/开盘止盈", "reason": f"高开 {gap:.1%}"}

    # 3. 冲高分批止盈
    if pnl > config.RISK["take_profit_surge"]:
        return {"code": holding.get("code"), "action": "分批止盈", "reason": f"冲高 {pnl:.1%}，先落袋一半"}

    # 4. 题材退潮 / 龙头断板 → 早盘离场
    if sentiment and sentiment.get("divergence_warning"):
        return {"code": holding.get("code"), "action": "早盘离场", "reason": "市场分歧加大，题材退潮"}

    # 5. 时间止损（14:30 前不涨不跌 → 尾盘离场）
    if pct_chg <= 0:
        return {"code": holding.get("code"), "action": "尾盘离场", "reason": "当日未走强，严守隔日纪律"}

    return {"code": holding.get("code"), "action": "持有观察", "reason": f"当前浮盈 {pnl:.1%}"}
