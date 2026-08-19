"""数据服务层：候选榜单缓存 + 个股详情。

build_candidates 需数十秒（大量接口调用），此处做内存缓存，
避免每个 API 请求都重跑全量计算。
"""

from __future__ import annotations

import threading
import time
from typing import Any

from backend.fetcher import eastmoney as em
from backend.indicators import scoring, technical
from backend.strategy import generate_advice

# 主数据缓存（5 分钟 TTL，盘中刷新由 scheduler 主动 force 更新）
_TTL = 300
_cache: dict[str, Any] = {"data": None, "ts": 0.0}
_lock = threading.Lock()
_build_lock = threading.Lock()  # 构建串行化：避免并发抓取触发东财限流


def _refresh() -> dict[str, Any]:
    # 串行化构建：首次打开时前端请求与调度器预加载会并发抓取，加剧东财限流
    with _build_lock:
        # double-check：等待期间可能已有其他线程完成构建，直接复用避免重复抓取
        with _lock:
            data, ts = _cache["data"], _cache["ts"]
        if data is not None and time.monotonic() - ts < _TTL:
            return data
        result = scoring.build_candidates()
        advice = generate_advice(result)
        with _lock:
            _cache["data"] = advice
            _cache["ts"] = time.monotonic()
    return advice


def get_advice(force: bool = False) -> dict[str, Any] | None:
    """获取完整操作建议。force=True 强制重新计算。"""
    with _lock:
        data, ts = _cache["data"], _cache["ts"]
    if not force and data is not None and time.monotonic() - ts < _TTL:
        return data
    if force:
        return _refresh()
    # 首次且无缓存：同步刷新
    return _refresh()


def get_stock_detail(code: str) -> dict[str, Any]:
    """个股详情：基础 + 资金流历史 + 技术指标 + 题材归属。

    各数据源独立容错：历史 K 线/资金流（push2his）在网络受限下可能不可达，
    失败时降级为空，不影响概念板块等可用数据的返回。
    """
    try:
        concepts = em.get_stock_concepts(code)
    except Exception:
        concepts = None
    try:
        history = em.get_capital_flow_history(code)
    except Exception:
        history = []
    try:
        klines = em.get_kline(code)
    except Exception:
        klines = []

    tech = technical.compute_technical(klines)
    boards = [b["board_name"] for b in (concepts or {}).get("boards", [])]
    themes = [t["keyword"] for t in (concepts or {}).get("themes", [])]

    return {
        "code": code,
        "concepts": boards,
        "themes": themes,
        "capital_history": history,
        "kline": klines,
        "technical": tech,
    }
