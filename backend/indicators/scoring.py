"""综合打分、信号分级、候选股榜单构建。

整合题材(40) + 资金(40) + 技术(20) 三维度，输出 S/A/B/C 信号。
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from backend import config
from backend.fetcher import eastmoney as em
from backend.indicators import capital, sentiment, technical, theme


# ---------------------------------------------------------------------------
# 基础硬过滤
# ---------------------------------------------------------------------------

def passes_filter(stock: dict[str, Any]) -> bool:
    """排除 ST、次新（N/C 前缀）、一字板、市值异常。"""
    name = stock.get("name") or ""
    if config.FILTER["exclude_st"] and ("ST" in name.upper() or "*" in name):
        return False
    # 次新：东财新股命名 N=首日、C=上市次日至第5日
    if name.startswith(("N", "C")):
        return False
    mv = float(stock.get("float_mv") or 0)
    if not (config.FILTER["float_mv_min"] <= mv <= config.FILTER["float_mv_max"]):
        return False
    # 一字板：9:25 即封死（买不进）
    if (stock.get("first_seal_time") or 0) == 92500:
        return False
    return True


def _fit_score(stock: dict[str, Any]) -> float:
    """市值/换手率合适度（0-10）。"""
    mv = float(stock.get("float_mv") or 0)
    turnover = float(stock.get("turnover") or 0)
    score = 0.0
    # 理想流通市值 30-150 亿
    if 30e8 <= mv <= 150e8:
        score += 6.0
    elif config.FILTER["float_mv_min"] <= mv <= config.FILTER["float_mv_max"]:
        score += 4.0
    # 换手率 5-20% 活跃区间
    if config.FILTER["turnover_min"] <= turnover <= config.FILTER["turnover_max"]:
        score += 4.0
    elif turnover > 1:
        score += 2.0
    return score


# ---------------------------------------------------------------------------
# 信号分级
# ---------------------------------------------------------------------------

def classify_signal(
    total_score: float,
    stock: dict[str, Any],
    senti: dict[str, Any],
    board_max_lb: int,
) -> str:
    """S/A/B/C 分级。S 需：高分 + 涨停/接近涨停 + 主升氛围。"""
    if total_score < config.SIGNAL["B"]:
        return "C"
    if total_score < config.SIGNAL["A"]:
        return "B"
    if total_score < config.SIGNAL["S"]:
        return "A"
    pct = float(stock.get("pct_chg") or 0)
    main_rise = senti["stage"] == sentiment.MAIN_RISE or board_max_lb >= 3
    if pct >= 9.0 and main_rise:
        return "S"
    return "A"


# ---------------------------------------------------------------------------
# 候选池构建
# ---------------------------------------------------------------------------

def _build_pool(limit_up_pool: list[dict], stock_flow: list[dict]) -> list[dict]:
    """候选池 = 涨停池(封板) + 资金流前列中涨幅>5%的强势股。"""
    pool: dict[str, dict] = {}
    for p in limit_up_pool:
        if (p.get("break_count") or 0) == 0:
            pool[p["code"]] = {**p, "source": "limit_up"}
    for s in stock_flow[:80]:
        if s["code"] not in pool and float(s.get("pct_chg") or 0) >= 5:
            pool[s["code"]] = {**s, "source": "capital_flow"}
    return list(pool.values())[:30]


def _lhb_index(lhb_list: list[dict]) -> dict[str, dict]:
    """龙虎榜 list → {code: 净买入额最大的记录}，处理同股多原因去重。"""
    idx: dict[str, dict] = {}
    for r in lhb_list:
        code = r.get("code")
        if code not in idx or abs(float(r.get("net_amt") or 0)) > abs(float(idx[code].get("net_amt") or 0)):
            idx[code] = r
    return idx


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

def _score_one(
    stock: dict[str, Any],
    board_heat: list[dict],
    board_by_name: dict[str, dict],
    concept_board_names: set[str],
    lhb_map: dict[str, dict],
    senti: dict[str, Any],
) -> dict[str, Any] | None:
    """计算单只候选股打分（供并行抓取调用）。过滤不通过返回 None。"""
    if not passes_filter(stock):
        return None
    code = stock["code"]
    limit_up_info = stock if stock.get("source") == "limit_up" else None

    # 题材维度
    try:
        concepts = em.get_stock_concepts(code)
    except Exception:
        concepts = None
    theme_res = theme.compute_stock_theme_score(
        stock, board_heat, limit_up_info, concepts, concept_board_names,
    )
    board_names_all = {b.get("board_name") for b in (concepts or {}).get("boards", [])}
    board_names = board_names_all & concept_board_names   # 只保留概念板块
    board_max_lb = max(
        (board_by_name[n].get("max_lb", 0) for n in board_names if n in board_by_name),
        default=0,
    )

    # 资金维度
    try:
        history = em.get_capital_flow_history(code)
    except Exception:
        history = None
    capital_res = capital.compute_capital_score(stock, history, lhb_map, limit_up_info)

    # 技术维度
    try:
        klines = em.get_kline(code)
    except Exception:
        klines = []
    tech = technical.compute_technical(klines)

    total = theme_res["score"] + capital_res["score"] + tech["score"]
    signal = classify_signal(total, stock, senti, board_max_lb)

    return {
        "code": code,
        "name": stock.get("name"),
        "price": stock.get("price"),
        "pct_chg": stock.get("pct_chg"),
        "turnover": stock.get("turnover"),
        "float_mv": stock.get("float_mv"),
        "limit_up_count": (limit_up_info or {}).get("limit_up_count", 0),
        "industry": (limit_up_info or {}).get("industry", ""),
        "total_score": round(total, 1),
        "theme_score": theme_res["score"],
        "capital_score": capital_res["score"],
        "technical_score": tech["score"],
        "signal": signal,
        "reason": _reason_text(signal, theme_res, capital_res, tech, board_names),
    }


def build_candidates() -> dict[str, Any]:
    """构建完整候选股榜单（情绪 + 题材热度 + 候选股）。"""
    boards = em.get_concept_boards()
    limit_up_pool = em.get_limit_up_pool()
    stock_flow = em.get_stock_capital_flow()
    lhb_list = em.get_dragon_tiger()

    senti = sentiment.compute_sentiment(limit_up_pool)
    board_heat = theme.compute_board_heat(boards, limit_up_pool)
    lhb_map = _lhb_index(lhb_list)

    concept_board_names = {b["name"] for b in theme.filter_theme_boards(boards)}
    board_by_name = {b["name"]: b for b in board_heat}
    candidates = _build_pool(limit_up_pool, stock_flow)

    # 并行细算候选股：个股维度接口（题材/资金/技术）占构建耗时的绝大部分
    scored: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=config.PARALLEL_WORKERS) as ex:
        futures = [
            ex.submit(
                _score_one, stock, board_heat, board_by_name,
                concept_board_names, lhb_map, senti,
            )
            for stock in candidates
        ]
        for f in as_completed(futures):
            entry = f.result()
            if entry:
                scored.append(entry)

    scored.sort(key=lambda x: (-x["total_score"], -float(x.get("pct_chg") or 0)))
    return {
        "sentiment": senti,
        "board_heat": board_heat,
        "candidates": scored,
    }


def _reason_text(
    signal: str,
    theme_res: dict,
    capital_res: dict,
    tech: dict,
    board_names: set[str],
) -> str:
    """生成候选股推荐理由文本。"""
    parts = [f"信号{signal}"]
    parts.append(f"题材{theme_res['score']}/资金{capital_res['score']}/技术{tech['score']}")
    if board_names:
        parts.append("题材:" + "/".join(sorted(board_names)[:3]))
    if capital_res["details"].get("lhb", 0) > 0:
        parts.append("上龙虎榜")
    if tech.get("ma_bull"):
        parts.append("均线多头")
    return "；".join(parts)
