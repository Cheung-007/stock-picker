"""FastAPI 应用入口。"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.api import routes

app = FastAPI(title="T+1 超短线选股系统", version="0.1.0")

# 允许本地前端跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(routes.router)


@app.on_event("startup")
def _startup() -> None:
    """启动盘中调度器（交易日内盘中定时刷新）。"""
    from backend import scheduler
    scheduler.start()


# 托管前端构建产物，单进程即可运行整个看板（双击即用）。
# 顺序关键：/api 路由先注册，故 API 优先匹配；其余路径（含 /）落到静态页面。
_DIST = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if _DIST.exists():
    app.mount("/", StaticFiles(directory=str(_DIST), html=True), name="static")
else:
    @app.get("/")
    def _root():
        return {
            "name": "T+1 超短线选股系统",
            "hint": "请先构建前端：cd frontend && npm run build",
            "docs": "/docs",
        }
