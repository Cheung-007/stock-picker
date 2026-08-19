#!/usr/bin/env python3
"""生成桌面应用图标：深色底 + 上升 K 线蜡烛图（红涨绿跌）。

产出 iconset -> AppIcon.icns（供 macOS .app 使用）。
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw

OUT_ICNS = Path(__file__).resolve().parent.parent / "scripts" / "AppIcon.icns"

# 主题色（与前端 index.css 一致）
BG = (15, 20, 28, 255)          # 深色背景
UP = (248, 81, 73, 255)         # 红涨 #f85149
DOWN = (63, 185, 80, 255)       # 绿跌 #3fb950
LINE = (255, 200, 87, 255)      # 金色均线
WICK = (180, 190, 205, 255)     # 影线


def _candle(draw, x, top, bottom, body_w, up: bool, wick_top, wick_bottom):
    """画一根蜡烛。body 用涨跌色，影线用浅灰。"""
    color = UP if up else DOWN
    # 影线
    draw.line([(x, wick_top), (x, wick_bottom)], fill=WICK, width=14)
    # 实体
    draw.rounded_rectangle(
        [x - body_w / 2, top, x + body_w / 2, bottom], radius=14, fill=color
    )


def build(size: int = 1024) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    radius = int(size * 0.22)
    d.rounded_rectangle([0, 0, size, size], radius=radius, fill=BG)

    # 五根蜡烛，整体呈上升趋势
    candles = [
        # (x, body_top, body_bottom, up, wick_top, wick_bottom)
        (0.22, 0.66, 0.74, False, 0.60, 0.78),
        (0.38, 0.58, 0.67, False, 0.52, 0.71),
        (0.54, 0.48, 0.58, True, 0.42, 0.64),
        (0.70, 0.36, 0.47, True, 0.30, 0.53),
        (0.86, 0.22, 0.34, True, 0.16, 0.40),
    ]
    body_w = size * 0.11
    for cx, t, b, up, wt, wb in candles:
        _candle(d, cx * size, t * size, b * size, body_w, up, wt * size, wb * size)

    # 金色上升均线（穿过实体中间）
    pts = [
        (0.22 * size, 0.78 * size),
        (0.38 * size, 0.71 * size),
        (0.54 * size, 0.64 * size),
        (0.70 * size, 0.53 * size),
        (0.86 * size, 0.40 * size),
    ]
    d.line(pts, fill=LINE, width=int(size * 0.035), joint="curve")

    # 右上角红色向上箭头（寓意次日高开/冲高）
    ax0, ay0 = 0.74 * size, 0.16 * size
    ax1, ay1 = 0.92 * size, 0.34 * size
    d.polygon(
        [(ax0, ay1), ((ax0 + ax1) / 2, ay0), (ax1, ay1)],
        fill=UP,
    )
    d.rounded_rectangle(
        [ax0 + (ax1 - ax0) * 0.28, ay1 + (ax1 - ax0) * 0.35, ax1 - (ax1 - ax0) * 0.28, ay1 + (ax1 - ax0) * 0.52],
        radius=8, fill=UP,
    )

    return img


def main() -> None:
    iconset = Path("/tmp/superselect.iconset")
    iconset.mkdir(parents=True, exist_ok=True)

    sizes = {
        "16": 16, "32": 32, "128": 128, "256": 256, "512": 512,
    }
    master = build(1024)
    for name, px in sizes.items():
        master.resize((px, px), Image.LANCZOS).save(iconset / f"icon_{px}x{px}.png")
        master.resize((px * 2, px * 2), Image.LANCZOS).save(iconset / f"icon_{px}x{px}@2x.png")

    subprocess.run(
        ["iconutil", "-c", "icns", str(iconset), "-o", str(OUT_ICNS)],
        check=True,
    )
    print(f"已生成: {OUT_ICNS}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001
        print(f"生成图标失败: {exc}", file=sys.stderr)
        sys.exit(1)
