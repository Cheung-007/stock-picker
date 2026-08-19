"""备用开源数据源（腾讯 K 线 / 新浪资金流）。

东财 push2his（历史 K 线、历史资金流）在网络受限/反爬下可能不可达，
这两个开源公开接口作为兜底，返回字段与 eastmoney.py 对齐，
上层指标计算无需感知数据源差异。

- 腾讯 K 线：https://web.ifzq.gtimg.cn/appstock/app/fqkline/get（前复权，含当日）
- 新浪资金流：https://vip.stock.finance.sina.com.cn/.../MoneyFlow.ssl_qsfx_zjlrqs
"""

from __future__ import annotations

from backend.fetcher.http_client import get_client


def _market_prefix(code: str) -> str:
    """股票代码 → 腾讯/新浪的 sh/sz 前缀。"""
    return "sh" if code.startswith(("60", "68")) else "sz"


def get_kline(code: str, days: int = 30) -> list[dict]:
    """腾讯日 K（前复权），字段对齐 eastmoney.get_kline。"""
    prefix = _market_prefix(code)
    url = (
        f"https://web.ifzq.gtimg.cn/appstock/app/fqkline/get"
        f"?param={prefix}{code},day,,,{days},qfq"
    )
    data = get_client().get_json(url)
    node = (data.get("data") or {}).get(f"{prefix}{code}") or {}
    raw = node.get("qfqday") or node.get("day") or []

    result: list[dict] = []
    prev_close: float | None = None
    for k in raw:
        # 腾讯字段顺序：日期, 开, 收, 高, 低, 成交量(手)
        date, o, c, h, l, v = k[0], float(k[1]), float(k[2]), float(k[3]), float(k[4]), float(k[5])
        pct = round((c - prev_close) / prev_close * 100, 2) if prev_close else 0.0
        result.append({
            "date": date,
            "open": o, "close": c, "high": h, "low": l,
            "volume": v,
            "amount": 0.0,                                            # 腾讯无成交额
            "amplitude": round((h - l) / prev_close * 100, 2) if prev_close else 0.0,
            "pct_chg": pct,
            "change": round(c - prev_close, 2) if prev_close else 0.0,
            "turnover": 0.0,                                          # 腾讯无换手率
        })
        prev_close = c
    return result[-days:]


def get_capital_flow_history(code: str, days: int = 30) -> list[dict]:
    """新浪主力资金流，字段对齐 eastmoney.get_capital_flow_history。"""
    prefix = _market_prefix(code)
    url = (
        f"https://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php"
        f"/MoneyFlow.ssl_qsfx_zjlrqs?page=1&num={days}&sort=opendate&asc=0"
        f"&daima={prefix}{code}"
    )
    data = get_client().get_json(url)
    rows = data if isinstance(data, list) else []

    result: list[dict] = []
    for r in reversed(rows):  # 新浪按日期倒序返回，转为正序（旧→新）
        result.append({
            "date": r.get("opendate"),
            "main_net_inflow": float(r.get("netamount") or 0),
            "super_large_inflow": float(r.get("r0_net") or 0),
            "small_inflow": 0.0,                                      # 新浪无分单明细
            "medium_inflow": 0.0,
            "large_inflow": 0.0,
            "main_ratio": float(r.get("ratioamount") or 0),
            "small_ratio": 0.0,
            "medium_ratio": 0.0,
            "large_ratio": 0.0,
            "super_large_ratio": 0.0,
            "close": float(r.get("trade") or 0),
            "pct_chg": round(float(r.get("changeratio") or 0) * 100, 2),  # 新浪为小数，转百分比
        })
    return result[-days:]
