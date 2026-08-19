"""FastAPI 路由。"""

from __future__ import annotations

import threading

from fastapi import APIRouter, HTTPException

from backend.api import service

router = APIRouter(prefix="/api")


@router.get("/advice")
def get_advice():
    """完整操作建议（情绪 + 风控 + 题材热度 + 候选股）。"""
    data = service.get_advice()
    if data is None:
        raise HTTPException(status_code=503, detail="数据尚未就绪")
    return data


@router.get("/sentiment")
def get_sentiment():
    """市场情绪仪表盘。"""
    data = service.get_advice()
    if data is None:
        raise HTTPException(status_code=503, detail="数据尚未就绪")
    return {"sentiment": data["sentiment"], "risk": data["risk"]}


@router.get("/board_heat")
def get_board_heat():
    """题材热度榜。"""
    data = service.get_advice()
    if data is None:
        raise HTTPException(status_code=503, detail="数据尚未就绪")
    return {"board_heat": data["board_heat"]}


@router.get("/candidates")
def get_candidates():
    """候选股榜单（含买入建议）。"""
    data = service.get_advice()
    if data is None:
        raise HTTPException(status_code=503, detail="数据尚未就绪")
    return {"entries": data["entries"], "buyable": data["buyable"]}


@router.get("/stock/{code}")
def get_stock(code: str):
    """个股详情。"""
    try:
        return service.get_stock_detail(code)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"个股详情获取失败: {exc}")


@router.post("/refresh")
def refresh():
    """强制刷新（后台线程，立即返回）。"""
    threading.Thread(target=service.get_advice, kwargs={"force": True}, daemon=True).start()
    return {"status": "refreshing"}
