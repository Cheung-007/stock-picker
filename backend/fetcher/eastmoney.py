"""东方财富公开接口封装。

每个函数返回语义化字段的 list[dict]，字段重命名集中于此，
上层（指标计算）无需关心东财原始字段名。
"""

from __future__ import annotations

import datetime as dt
from typing import Any

from backend import config
from backend.fetcher import alt
from backend.fetcher.http_client import get_client


# ---------------------------------------------------------------------------
# 工具
# ---------------------------------------------------------------------------

def _to_secid(code: str) -> str:
    """股票代码 → 东财 secid（沪市 1.，深市/北交 0.）。"""
    if code.startswith(("60", "68")):
        return f"1.{code}"
    return f"0.{code}"


def _market_prefix(code: str) -> str:
    """股票代码 → F10 接口的 SH/SZ 前缀。"""
    return "SH" if code.startswith(("60", "68")) else "SZ"


# ---------------------------------------------------------------------------
# 板块
# ---------------------------------------------------------------------------

_BOARD_MAP = {
    "f12": "code", "f14": "name", "f3": "pct_chg", "f62": "main_net_inflow",
    "f104": "up_count", "f105": "down_count",
    "f128": "lead_stock", "f136": "lead_stock_pct", "f140": "lead_stock_code",
}


def _rename(rows: list[dict], mapping: dict[str, str]) -> list[dict]:
    return [{mapping.get(k, k): v for k, v in row.items()} for row in rows]


def _clist_get(params: str) -> Any:
    """clist 行情请求，带多主机 fallback（主站不可达时自动切换备用主机）。"""
    client = get_client()
    last_exc: Exception | None = None
    for host in config.PUSH2_HOSTS:
        try:
            return client.get_json(f"{host}/api/qt/clist/get?{params}")
        except Exception as exc:  # noqa: BLE001 - 单主机失败尝试下一个
            last_exc = exc
    raise RuntimeError(f"所有行情主机均请求失败: {last_exc}")


def get_concept_boards() -> list[dict]:
    """概念板块列表，按涨幅降序。"""
    params = (
        f"pn=1&pz=500&po=1&np=1&fltt=2&invt=2&fid=f3&fs=m:90+t:3"
        f"&fields={config.BOARD_FIELDS}"
    )
    data = _clist_get(params)
    diff = (data.get("data") or {}).get("diff") or []
    return _rename(diff, _BOARD_MAP)


def get_industry_boards() -> list[dict]:
    """行业板块列表，按涨幅降序（涨停池的 hybk 为行业名，用于映射）。"""
    params = (
        f"pn=1&pz=200&po=1&np=1&fltt=2&invt=2&fid=f3&fs=m:90+t:2"
        f"&fields={config.BOARD_FIELDS}"
    )
    data = _clist_get(params)
    diff = (data.get("data") or {}).get("diff") or []
    return _rename(diff, _BOARD_MAP)


def get_board_constituents(board_code: str) -> list[dict]:
    """指定板块成分股（board_code 如 BK0816）。"""
    params = (
        f"pn=1&pz=500&po=1&np=1&fltt=2&invt=2&fid=f3&fs=b:{board_code}"
        f"&fields={config.CONSTITUENT_FIELDS}"
    )
    data = _clist_get(params)
    diff = (data.get("data") or {}).get("diff") or []
    mapping = {"f12": "code", "f14": "name", "f3": "pct_chg", "f62": "main_net_inflow", "f2": "price", "f8": "turnover"}
    return _rename(diff, mapping)


# ---------------------------------------------------------------------------
# 个股资金流
# ---------------------------------------------------------------------------

_STOCK_CAPITAL_MAP = {
    "f12": "code", "f14": "name", "f2": "price", "f3": "pct_chg", "f8": "turnover",
    "f20": "total_mv", "f21": "float_mv", "f62": "main_net_inflow",
    "f66": "super_large_inflow", "f72": "large_inflow",
    "f78": "medium_inflow", "f84": "small_inflow", "f184": "main_inflow_ratio",
}


def get_stock_capital_flow(sort_by: str = "main_net_inflow", page_size: int = 500) -> list[dict]:
    """全市场个股资金流，按主力净流入降序。

    sort_by 对应东财 fid：main_net_inflow→f62 / pct_chg→f3。
    """
    fid = "f62" if sort_by == "main_net_inflow" else "f3"
    params = (
        f"pn=1&pz={page_size}&po=1&np=1&fltt=2&invt=2&fid={fid}"
        f"&fs=m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23"
        f"&fields={config.STOCK_CAPITAL_FIELDS}"
    )
    data = _clist_get(params)
    diff = (data.get("data") or {}).get("diff") or []
    return _rename(diff, _STOCK_CAPITAL_MAP)


# ---------------------------------------------------------------------------
# 涨停池 / 龙虎榜
# ---------------------------------------------------------------------------

def get_limit_up_pool(date: str | None = None) -> list[dict]:
    """涨停池（含炸板，zbc>0 表示曾炸板）。date 格式 YYYYMMDD，默认当日。"""
    date = date or dt.date.today().strftime("%Y%m%d")
    results: list[dict] = []
    page = 0
    while True:
        url = (
            f"{config.PUSH2EX_HOST}/getTopicZTPool"
            f"?ut={config.EASTMONEY_UT}&dpt=wz.ztzt&Pageindex={page}&pagesize=500"
            f"&sort=fbt:asc&date={date}"
        )
        data = get_client().get_json(url)
        pool = (data.get("data") or {}).get("pool") or []
        if not pool:
            break
        results.extend(pool)
        if len(pool) < 500:
            break
        page += 1
    return [
        {
            "code": r.get("c"), "name": r.get("n"),
            "price": round((r.get("p") or 0) / 1000, 2),
            "pct_chg": round(r.get("zdp") or 0, 2), "amount": r.get("amount"),
            "float_mv": r.get("ltsz"), "turnover": r.get("hs"),
            "limit_up_count": r.get("lbc"),   # 连板数
            "first_seal_time": r.get("fbt"),  # 首次封板时间（HHMMSS）
            "last_seal_time": r.get("lbt"),
            "seal_fund": r.get("fund"),       # 封单资金
            "break_count": r.get("zbc"),      # 炸板次数
            "industry": r.get("hybk"),
            "stat": r.get("zttj"),            # 涨停统计 {days, ct}
        }
        for r in results
    ]


def get_dragon_tiger(date: str | None = None) -> list[dict]:
    """龙虎榜个股汇总。date 格式 YYYY-MM-DD，默认上一交易日。"""
    date = date or (dt.date.today() - dt.timedelta(days=1)).strftime("%Y-%m-%d")
    url = (
        f"{config.DATACENTER_HOST}/api/data/v1/get"
        f"?sortColumns=SECURITY_CODE&sortTypes=1&pageSize=500&pageNumber=1"
        f"&reportName={config.DETAILS_REPORT}&columns=ALL"
        f"&filter=(TRADE_DATE%3D%27{date}%27)"
    )
    data = get_client().get_json(url)
    rows = (data.get("result") or {}).get("data") or []
    return [
        {
            "code": r.get("SECURITY_CODE"), "name": r.get("SECURITY_NAME_ABBR"),
            "close": r.get("CLOSE_PRICE"), "pct_chg": r.get("CHANGE_RATE"),
            "turnover": r.get("TURNOVERRATE"),
            "net_amt": r.get("BILLBOARD_NET_AMT"),      # 净买入额
            "buy_amt": r.get("BILLBOARD_BUY_AMT"),
            "sell_amt": r.get("BILLBOARD_SELL_AMT"),
            "reason": r.get("EXPLANATION"),             # 上榜原因
            "explain": r.get("EXPLAIN"),                # 席位说明（机构/游资）
        }
        for r in rows
    ]


# ---------------------------------------------------------------------------
# K 线 / 个股题材
# ---------------------------------------------------------------------------

def get_capital_flow_history(code: str, days: int = 30) -> list[dict]:
    """个股历史资金流（日线）。

    字段：主力净流入 / 小单 / 中单 / 大单 / 超大单 / 主力净占比 / 收盘价 / 涨跌幅。
    push2his 不可达（反爬/断连）时回退新浪资金流。
    """
    try:
        secid = _to_secid(code)
        url = (
            f"{config.PUSH2HIS_HOST}/api/qt/stock/fflow/daykline/get"
            f"?secid={secid}&fields1=f1,f2,f3,f7"
            f"&fields2=f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f62,f63"
            f"&klt=101"
        )
        data = get_client().get_json(url)
        klines = (data.get("data") or {}).get("klines") or []
        if not klines:
            raise RuntimeError("push2his 资金流为空")
        keys = ["date", "main_net_inflow", "small_inflow", "medium_inflow",
                "large_inflow", "super_large_inflow", "main_ratio", "small_ratio",
                "medium_ratio", "large_ratio", "super_large_ratio", "close", "pct_chg"]
        result = []
        for line in klines:
            parts = line.split(",")
            row = {k: parts[i] for i, k in enumerate(keys) if i < len(parts)}
            result.append(row)
        return result[-days:]
    except Exception:  # noqa: BLE001 - 主源失败回退新浪
        return alt.get_capital_flow_history(code, days)


def get_kline(code: str, days: int = 30, fqt: int = 1) -> list[dict]:
    """日 K 线（前复权）。返回 日期/开/收/高/低/量/额/振幅/涨幅/涨跌额/换手。

    push2his 不可达（反爬/断连）时回退腾讯 K 线。
    """
    try:
        end = dt.date.today().strftime("%Y%m%d")
        beg = (dt.date.today() - dt.timedelta(days=days * 2)).strftime("%Y%m%d")
        secid = _to_secid(code)
        url = (
            f"{config.PUSH2HIS_HOST}/api/qt/stock/kline/get"
            f"?secid={secid}&fields1=f1,f2,f3,f4,f5,f6&fields2={config.KLINE_FIELDS2}"
            f"&klt=101&fqt={fqt}&beg={beg}&end={end}"
        )
        data = get_client().get_json(url)
        klines = (data.get("data") or {}).get("klines") or []
        if not klines:
            raise RuntimeError("push2his K 线为空")
        keys = ["date", "open", "close", "high", "low", "volume", "amount",
                "amplitude", "pct_chg", "change", "turnover"]
        result = []
        for line in klines:
            parts = line.split(",")
            result.append({k: parts[i] for i, k in enumerate(keys) if i < len(parts)})
        return result
    except Exception:  # noqa: BLE001 - 主源失败回退腾讯
        return alt.get_kline(code, days)


def get_stock_concepts(code: str) -> dict[str, list[dict]]:
    """个股所属板块与核心题材（F10）。

    返回 {"boards": [...], "themes": [...]}。
    boards 含 BOARD_NAME（行业/概念/地域/风格板块）。
    """
    prefix = _market_prefix(code)
    url = f"{config.EMWEB_HOST}/PC_HSF10/CoreConception/PageAjax?code={prefix}{code}"
    data = get_client().get_json(url)
    boards = data.get("ssbk") or []
    themes = data.get("hxtc") or []
    return {
        "boards": [
            {"board_name": b.get("BOARD_NAME"), "board_code": b.get("BOARD_CODE"),
             "board_rank": b.get("BOARD_RANK")}
            for b in boards
        ],
        "themes": [
            {"keyword": t.get("KEYWORD"), "mainpoint": t.get("MAINPOINT")}
            for t in themes
        ],
    }
