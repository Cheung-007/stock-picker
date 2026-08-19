"""技术形态指标（均线、突破、MACD）。

输入 fetcher.get_kline 的返回（字段为字符串，此处转数值后用 pandas 计算）。
"""

from __future__ import annotations

from typing import Any

import pandas as pd


def _to_df(klines: list[dict[str, Any]]) -> pd.DataFrame:
    df = pd.DataFrame(klines)
    for col in ("open", "close", "high", "low", "volume", "pct_chg", "turnover"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def compute_technical(klines: list[dict[str, Any]]) -> dict[str, Any]:
    """计算均线多头、突破新高、MACD 等形态指标。"""
    if not klines or len(klines) < 2:
        return {"ma_bull": False, "breakout": False, "macd_golden": False,
                "macd_red_amp": False, "score": 0.0}

    df = _to_df(klines)
    close = df["close"]
    n = len(df)

    ma5 = close.rolling(5).mean()
    ma10 = close.rolling(10).mean()
    ma20 = close.rolling(20).mean()

    # 均线多头：MA5 > MA10 > MA20（不足 20 日则无法判定）
    ma_bull = bool(ma5.iloc[-1] > ma10.iloc[-1] > ma20.iloc[-1]) if n >= 20 else False

    # 突破 20 日新高：今日收盘 > 前 20 日（不含今日）最高价
    prev_high = df["high"].iloc[-21:-1].max() if n > 20 else df["high"].iloc[:-1].max()
    breakout = bool(df["close"].iloc[-1] > prev_high)

    # MACD（12/26/9）
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    dif = ema12 - ema26
    dea = dif.ewm(span=9, adjust=False).mean()
    macd_hist = 2 * (dif - dea)

    macd_golden = bool(dif.iloc[-1] > dea.iloc[-1] and dif.iloc[-2] <= dea.iloc[-2])
    macd_red_amp = bool(macd_hist.iloc[-1] > macd_hist.iloc[-2] > 0)

    # 形态得分（0-10，供打分模型使用）
    score = 0.0
    score += 4.0 if ma_bull else 0.0
    score += 3.0 if breakout else 0.0
    score += 3.0 if (macd_golden or macd_red_amp) else 0.0

    return {
        "ma_bull": ma_bull,
        "breakout": breakout,
        "macd_golden": macd_golden,
        "macd_red_amp": macd_red_amp,
        "ma5": round(float(ma5.iloc[-1]), 2),
        "ma10": round(float(ma10.iloc[-1]), 2),
        "ma20": round(float(ma20.iloc[-1]), 2),
        "score": round(score, 1),
    }
