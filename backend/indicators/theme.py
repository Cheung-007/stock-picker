"""题材热度与个股题材地位打分（0-40）。

题材维度 = 是否热门板块(15) + 题材阶段(10) + 是否龙头(15)。
依赖 fetcher 获取板块成分与个股所属板块。
"""

from __future__ import annotations

from typing import Any

from backend import config
from backend.fetcher import eastmoney as em


def filter_theme_boards(boards: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """过滤风格/衍生板块（昨日连板、破净股、AB股等），只保留真正概念题材。"""
    def _is_theme(b: dict[str, Any]) -> bool:
        name = b.get("name") or ""
        return not any(kw in name for kw in config.BOARD_BLACKLIST_KEYWORDS)
    return [b for b in boards if _is_theme(b)]


def compute_board_heat(
    boards: list[dict[str, Any]],
    limit_up_pool: list[dict[str, Any]],
    top_n: int = 30,
) -> list[dict[str, Any]]:
    """计算题材热度榜（按热度分降序）。

    基础热度来自板块自身（涨幅+资金流），涨停家数/连板高度通过板块成分计算。
    """
    sealed_codes = {p["code"] for p in limit_up_pool if (p.get("break_count") or 0) == 0}
    lb_map = {p["code"]: p for p in limit_up_pool}

    boards = filter_theme_boards(boards)

    # 先按涨幅降序取 top_n 热门板块，减少成分接口调用
    sorted_boards = sorted(boards, key=lambda b: -float(b.get("pct_chg") or 0))
    hot = sorted_boards[:top_n]

    for b in hot:
        try:
            cons = em.get_board_constituents(b["code"])
        except Exception:
            cons = []
        lb_in_board = [lb_map[c["code"]] for c in cons if c["code"] in sealed_codes]
        b["limit_up_count"] = len(lb_in_board)
        b["max_lb"] = max((lb.get("limit_up_count") or 1 for lb in lb_in_board), default=0)

    # 归一化热度分：涨幅排名 + 涨停家数 + 连板高度 + 资金流
    hot_sorted = sorted(hot, key=lambda b: -float(b.get("pct_chg") or 0))
    for rank, b in enumerate(hot_sorted, start=1):
        pct = float(b.get("pct_chg") or 0)
        inflow = float(b.get("main_net_inflow") or 0)
        heat = 0.0
        heat += max(0, 30 - rank * 2)                 # 涨幅排名 0-30
        heat += min(b.get("limit_up_count", 0) * 3, 15)   # 涨停家数 0-15
        heat += min(b.get("max_lb", 0) * 4, 16)           # 连板高度 0-16
        heat += 8 if inflow > 0 else 0                    # 资金流 0-8
        heat += pct * 2                                   # 涨幅加成
        b["heat_score"] = round(heat, 1)

    hot_sorted.sort(key=lambda b: -b["heat_score"])
    return hot_sorted


def compute_stock_theme_score(
    stock: dict[str, Any],
    board_heat: list[dict[str, Any]],
    limit_up_info: dict[str, Any] | None,
    concepts: dict[str, Any] | None,
    concept_board_names: set[str] | None = None,
) -> dict[str, Any]:
    """个股题材维度得分（0-40）。"""
    w = config.SCORING["theme"]
    details: dict[str, Any] = {}

    all_boards = {b.get("board_name") for b in (concepts or {}).get("boards", [])}
    # 只保留真正的概念板块（排除行业/地域/风格/指数板块）
    if concept_board_names is not None:
        board_names = all_boards & concept_board_names
    else:
        board_names = all_boards

    # 1. 是否 top5 热门板块（15 分）
    top5_names = {b["name"] for b in board_heat[:5]}
    in_top5 = bool(board_names & top5_names)
    top_board_score = w["top_board"] if in_top5 else 0.0
    details["top_board"] = top_board_score

    # 2. 题材阶段（10 分）：所属板块中连板最高者近似题材强度
    matched = [b for b in board_heat if b["name"] in board_names]
    max_lb = max((b.get("max_lb", 0) for b in matched), default=0)
    stage_score = _stage_tier(max_lb)
    details["stage"] = stage_score

    # 3. 是否龙头（15 分）：领涨股 或 板块内最高连板
    leader_score = 0.0
    if limit_up_info:
        code = stock.get("code")
        is_lead = any(b.get("lead_stock_code") == code for b in matched)
        lb = limit_up_info.get("limit_up_count") or 1
        is_top_lb = lb >= 2 and any(b.get("max_lb", 0) == lb for b in matched)
        if is_lead or is_top_lb:
            leader_score = w["leader"]
        elif lb >= 2:
            leader_score = w["leader"] * 0.6
    details["leader"] = round(leader_score, 1)

    total = top_board_score + stage_score + leader_score
    return {"score": round(total, 1), "details": details}


def _stage_tier(max_lb: int) -> float:
    """题材阶段分档（0-10），以板块最高连板近似。"""
    w = config.SCORING["theme"]["stage"]
    if max_lb >= 3:
        return w          # 主升
    if max_lb == 2:
        return w * 0.8    # 发酵偏强
    if max_lb == 1:
        return w * 0.6    # 启动
    return w * 0.3        # 无涨停，弱势
