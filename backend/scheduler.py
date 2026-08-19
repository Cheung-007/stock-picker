"""盘中定时刷新调度器。

交易日内盘中每 5 分钟强制刷新一次候选榜单；
调度任务在线程池执行，不阻塞 API。
"""

from __future__ import annotations

import datetime as dt

from apscheduler.schedulers.background import BackgroundScheduler

from backend.api import service

# 盘中交易时段（含尾盘选股窗口）
TRADE_SESSIONS = [
    (dt.time(9, 30), dt.time(11, 30)),
    (dt.time(13, 0), dt.time(15, 0)),
]

REFRESH_MINUTES = 5


def is_trading_day(now: dt.datetime) -> bool:
    """是否交易日（周末休市；节假日暂不精确处理，可后续接入交易日历）。"""
    return now.weekday() < 5


def in_trading_session(now: dt.datetime) -> bool:
    """是否在盘中交易时段。"""
    t = now.time()
    return any(start <= t <= end for start, end in TRADE_SESSIONS)


def refresh_if_trading() -> None:
    """仅在交易日盘中执行刷新。"""
    now = dt.datetime.now()
    if is_trading_day(now) and in_trading_session(now):
        service.get_advice(force=True)


def start() -> BackgroundScheduler:
    """启动调度器，并预加载一次数据。"""
    scheduler = BackgroundScheduler(timezone="Asia/Shanghai")
    scheduler.add_job(
        refresh_if_trading,
        trigger="interval",
        minutes=REFRESH_MINUTES,
        id="intraday_refresh",
        max_instances=1,          # 防止上一次未完成时堆积
        coalesce=True,
    )
    scheduler.start()

    # 首次预加载（后台线程）
    import threading
    threading.Thread(target=service.get_advice, kwargs={"force": True}, daemon=True).start()
    return scheduler


if __name__ == "__main__":
    start()
    try:
        while True:
            import time
            time.sleep(3600)
    except KeyboardInterrupt:
        pass
