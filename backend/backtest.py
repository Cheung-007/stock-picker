"""隔日超短回测：验证「涨停股次日有溢价」这一核心假设。

回测模型（严格 T+1）：
  T 日涨停价买入 → T+1 日竞价/收盘卖出
收益指标：
  - 次日开盘溢价 = (次日开盘 - 今日收盘) / 今日收盘（竞价卖出）
  - 次日收盘涨幅 = (次日收盘 - 今日收盘) / 今日收盘（持有到尾盘）
按连板数分组统计，用于校准信号分级与仓位。
"""

from __future__ import annotations

import datetime as dt
from collections import defaultdict
from typing import Any

from backend.fetcher import eastmoney as em


def recent_trading_days(n: int) -> list[dt.date]:
    """最近 n 个交易日（跳过周末，节假日暂不精确处理）。"""
    days: list[dt.date] = []
    d = dt.date.today() - dt.timedelta(days=1)
    while len(days) < n:
        if d.weekday() < 5:
            days.append(d)
        d -= dt.timedelta(days=1)
    return list(reversed(days))


def _next_day_pct(code: str, next_day: dt.date) -> tuple[float, float] | None:
    """返回 (次日开盘溢价, 次日收盘涨幅)，找不到或抓取失败返回 None。"""
    try:
        klines = em.get_kline(code, days=30)
    except Exception:
        return None  # 限流/抓取失败，跳过该样本
    target = next_day.strftime("%Y-%m-%d")
    for i, k in enumerate(klines):
        if k["date"] == target and i > 0:
            prev_close = float(klines[i - 1]["close"])
            if prev_close <= 0:
                return None
            open_pct = (float(k["open"]) - prev_close) / prev_close
            close_pct = (float(k["close"]) - prev_close) / prev_close
            return open_pct, close_pct
    return None


def backtest(days: int = 5, verbose: bool = True) -> dict[str, Any]:
    """回测最近 N 个交易日的涨停股次日表现。"""
    trading_days = recent_trading_days(days + 1)  # 多取一天用于次日
    records: list[dict[str, Any]] = []
    skipped = 0

    for i, day in enumerate(trading_days[:-1]):
        date_str = day.strftime("%Y%m%d")
        next_day = trading_days[i + 1]
        try:
            pool = em.get_limit_up_pool(date_str)
        except Exception:
            continue
        sealed = [p for p in pool if (p.get("break_count") or 0) == 0]
        if verbose:
            print(f"  {date_str}: {len(sealed)} 只涨停")
        for p in sealed:
            res = _next_day_pct(p["code"], next_day)
            if res is None:
                skipped += 1
                continue
            open_pct, close_pct = res
            records.append({
                "date": date_str,
                "code": p["code"],
                "name": p["name"],
                "lb": p["limit_up_count"],
                "open_pct": round(open_pct * 100, 2),
                "close_pct": round(close_pct * 100, 2),
            })

    if not records:
        return {"days": days, "samples": 0, "summary": [], "skipped": skipped}

    # 总体统计
    total = len(records)
    avg_open = sum(r["open_pct"] for r in records) / total
    avg_close = sum(r["close_pct"] for r in records) / total
    win_open = sum(1 for r in records if r["open_pct"] > 0) / total
    win_close = sum(1 for r in records if r["close_pct"] > 0) / total

    # 按连板分组
    grouped = defaultdict(list)
    for r in records:
        key = "3板+" if r["lb"] >= 3 else (f"{r['lb']}板" if r["lb"] >= 2 else "首板")
        grouped[key].append(r)

    summary = []
    for key in ["首板", "2板", "3板+"]:
        g = grouped.get(key, [])
        if not g:
            continue
        n = len(g)
        summary.append({
            "group": key,
            "count": n,
            "avg_open_pct": round(sum(r["open_pct"] for r in g) / n, 2),
            "avg_close_pct": round(sum(r["close_pct"] for r in g) / n, 2),
            "win_open": round(sum(1 for r in g if r["open_pct"] > 0) / n, 2),
        })

    return {
        "days": days,
        "samples": total,
        "avg_open_pct": round(avg_open, 2),
        "avg_close_pct": round(avg_close, 2),
        "win_open": round(win_open, 2),
        "win_close": round(win_close, 2),
        "skipped": skipped,
        "summary": summary,
    }


if __name__ == "__main__":
    import json
    print(json.dumps(backtest(), ensure_ascii=False, indent=2))
