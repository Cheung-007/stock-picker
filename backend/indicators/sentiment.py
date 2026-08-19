"""市场情绪周期判定。

输入涨停池（fetcher.get_limit_up_pool 的返回），输出全局情绪指标与阶段。
阶段决定操作仓位：冰点/退潮 → 空仓，发酵 → 轻仓，主升 → 重仓，高潮 → 谨慎。
"""

from __future__ import annotations

from typing import Any

from backend import config

# 阶段枚举（顺序即强弱）
ICE_FROZEN = "冰点期"
FERMENT = "发酵期"
MAIN_RISE = "主升期"
CLIMAX = "高潮期"
RECESSION = "退潮期"


def compute_sentiment(limit_up_pool: list[dict[str, Any]]) -> dict[str, Any]:
    """根据涨停池计算市场情绪。

    涨停池均为当前封板个股（zbc>0 表示盘中炸板后回封），
    故涨停家数取 len(pool)，炸板回封率反映封板质量（分歧度）。
    """
    if not limit_up_pool:
        return {"stage": ICE_FROZEN, "limit_up_count": 0, "max_lb": 0,
                "broke_rate": 0.0, "divergence_warning": False}

    total_count = len(limit_up_pool)                       # 涨停家数
    max_lb = max((p.get("limit_up_count") or 1 for p in limit_up_pool), default=1)
    broke_count = sum(1 for p in limit_up_pool if (p.get("break_count") or 0) > 0)
    broke_rate = broke_count / total_count if total_count else 0.0   # 炸板回封率

    stage = _classify(total_count, max_lb, broke_rate)
    return {
        "stage": stage,
        "limit_up_count": total_count,               # 涨停家数
        "max_lb": max_lb,                            # 最高连板
        "broke_rate": round(broke_rate, 3),          # 炸板回封率（分歧度）
        "divergence_warning": broke_rate >= 0.4,     # 分歧预警
    }


def _classify(limit_up_count: int, max_lb: int, broke_rate: float) -> str:
    s = config.SENTIMENT
    # 高潮：涨停爆量
    if limit_up_count > s["climax"]["limit_up_gt"]:
        return CLIMAX
    # 主升：涨停数进入区间且连板高度足够
    lo, hi = s["main_rise"]["limit_up_range"]
    if lo <= limit_up_count <= hi and max_lb >= s["main_rise"]["max_lb_ge"]:
        return MAIN_RISE
    # 冰点：涨停稀少且无高标
    if limit_up_count < s["ice_frozen"]["limit_up_lt"] and max_lb <= s["ice_frozen"]["max_lb_le"]:
        return ICE_FROZEN
    # 发酵：其余（含涨停 <20 但连板 ≥3 的局部热点）
    return FERMENT


def position_suggestion(stage: str) -> tuple[str, float]:
    """阶段 → (仓位建议文本, 建议仓位比例)。"""
    table = {
        ICE_FROZEN: ("空仓观望", 0.0),
        RECESSION: ("空仓/轻仓", 0.0),
        FERMENT: ("轻仓试错", 0.3),
        MAIN_RISE: ("重仓进攻", 0.8),
        CLIMAX: ("谨慎防分歧", 0.4),
    }
    return table.get(stage, ("观望", 0.0))
