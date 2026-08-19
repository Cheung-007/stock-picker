"""HTTP 客户端封装：随机 UA + 请求间隔 + 重试 + TTL 缓存。

东方财富公开接口对请求频率敏感，本模块统一处理反爬与降频，
避免盘中高频刷新触发封禁。
"""

from __future__ import annotations

import random
import threading
import time
from typing import Any

import httpx

from backend import config


class EastmoneyClient:
    """带反爬策略的同步 HTTP 客户端。"""

    def __init__(self) -> None:
        self._client = httpx.Client(
            headers={"Accept": "application/json, text/plain, */*"},
            timeout=config.TIMEOUT,
            follow_redirects=True,
        )
        self._cache: dict[str, tuple[float, Any]] = {}
        self._last_request_ts = 0.0
        self._lock = threading.Lock()  # 保护节流与缓存，支持多线程抓取

    def _headers(self) -> dict[str, str]:
        return {"User-Agent": random.choice(config.USER_AGENTS)}

    def get_json(self, url: str, *, cache_ttl: int | None = None) -> Any:
        """GET 并解析 JSON，带缓存与重试。

        cache_ttl 为 None 时使用全局 CACHE_TTL。
        """
        ttl = config.CACHE_TTL if cache_ttl is None else cache_ttl
        with self._lock:
            now = time.monotonic()
            if url in self._cache:
                ts, data = self._cache[url]
                if now - ts < ttl:
                    return data
            # 全局节流：相邻请求至少间隔 REQUEST_INTERVAL 秒
            wait = config.REQUEST_INTERVAL - (now - self._last_request_ts)
            if wait > 0:
                time.sleep(wait)
            self._last_request_ts = time.monotonic()

        last_exc: Exception | None = None
        for attempt in range(config.MAX_RETRIES):
            try:
                resp = self._client.get(url, headers=self._headers())
                resp.raise_for_status()
                data = resp.json()
                with self._lock:
                    self._cache[url] = (time.monotonic(), data)
                return data
            except Exception as exc:  # noqa: BLE001 - 网络异常统一重试
                last_exc = exc
                # 指数退避，东财对频繁请求会断连，退避可缓解
                time.sleep(1.0 * (2 ** attempt))
        raise RuntimeError(f"请求失败 {url}: {last_exc}")

    def close(self) -> None:
        self._client.close()


# 模块级单例，避免重复创建连接池
_client: EastmoneyClient | None = None


def get_client() -> EastmoneyClient:
    global _client
    if _client is None:
        _client = EastmoneyClient()
    return _client
