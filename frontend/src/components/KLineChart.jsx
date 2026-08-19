// K 线图（蜡烛 + MA 均线 + 成交量），canvas 手绘，无第三方依赖
import { useEffect, useRef } from 'react'

const COLOR = {
  up: '#f85149',   // 红涨
  down: '#3fb950', // 绿跌
  ma5: '#f0b90b',
  ma10: '#58a6ff',
  ma20: '#d29922',
  grid: '#30363d',
  text: '#8b949e',
}

// 简单移动平均序列：不足周期处为 null
function sma(values, period) {
  const out = new Array(values.length).fill(null)
  let sum = 0
  for (let i = 0; i < values.length; i++) {
    sum += values[i]
    if (i >= period) sum -= values[i - period]
    if (i >= period - 1) out[i] = sum / period
  }
  return out
}

function draw(canvas, klines) {
  const dpr = window.devicePixelRatio || 1
  const cssW = canvas.clientWidth || 900
  const cssH = 420
  canvas.width = Math.round(cssW * dpr)
  canvas.height = Math.round(cssH * dpr)
  canvas.style.height = cssH + 'px'
  const ctx = canvas.getContext('2d')
  ctx.scale(dpr, dpr)

  const n = klines.length
  const open = klines.map((k) => +k.open)
  const close = klines.map((k) => +k.close)
  const high = klines.map((k) => +k.high)
  const low = klines.map((k) => +k.low)
  const volume = klines.map((k) => +k.volume)

  const ma5 = sma(close, 5)
  const ma10 = sma(close, 10)
  const ma20 = sma(close, 20)

  const padL = 8
  const padR = 54
  const padT = 10
  const priceBottom = 296
  const volTop = 318
  const volBottom = cssH - 24
  const plotW = cssW - padL - padR
  const step = plotW / n
  const candleW = Math.max(1, step * 0.7)

  const extremes = [
    ...high, ...low,
    ...ma5.filter((v) => v != null),
    ...ma10.filter((v) => v != null),
    ...ma20.filter((v) => v != null),
  ]
  let maxP = Math.max(...extremes)
  let minP = Math.min(...extremes)
  const pad = (maxP - minP) * 0.06 || 1
  maxP += pad
  minP -= pad
  const maxV = Math.max(...volume) || 1

  const px = (i) => padL + step * i + step / 2
  const py = (p) => padT + ((maxP - p) / (maxP - minP)) * (priceBottom - padT)

  ctx.clearRect(0, 0, cssW, cssH)

  // 网格 + 价格刻度（右侧）
  ctx.font = '10px system-ui'
  ctx.strokeStyle = COLOR.grid
  ctx.fillStyle = COLOR.text
  ctx.lineWidth = 1
  for (let i = 0; i <= 4; i++) {
    const p = minP + ((maxP - minP) * i) / 4
    const yy = py(p)
    ctx.beginPath()
    ctx.moveTo(padL, yy)
    ctx.lineTo(cssW - padR, yy)
    ctx.stroke()
    ctx.textAlign = 'left'
    ctx.fillText(p.toFixed(2), cssW - padR + 6, yy + 3)
  }

  // 蜡烛（红涨绿跌，按开收决定阴阳）
  for (let i = 0; i < n; i++) {
    const x = px(i)
    const up = close[i] >= open[i]
    ctx.strokeStyle = up ? COLOR.up : COLOR.down
    ctx.fillStyle = up ? COLOR.up : COLOR.down
    ctx.beginPath()
    ctx.moveTo(x, py(high[i]))
    ctx.lineTo(x, py(low[i]))
    ctx.stroke()
    const y1 = py(open[i])
    const y2 = py(close[i])
    const top = Math.min(y1, y2)
    const height = Math.max(1, Math.abs(y2 - y1))
    ctx.fillRect(x - candleW / 2, top, candleW, height)
  }

  // 均线
  const drawMA = (ma, color) => {
    ctx.strokeStyle = color
    ctx.lineWidth = 1.2
    ctx.beginPath()
    let started = false
    for (let i = 0; i < n; i++) {
      if (ma[i] == null) continue
      const x = px(i)
      const yy = py(ma[i])
      if (!started) {
        ctx.moveTo(x, yy)
        started = true
      } else {
        ctx.lineTo(x, yy)
      }
    }
    ctx.stroke()
  }
  drawMA(ma5, COLOR.ma5)
  drawMA(ma10, COLOR.ma10)
  drawMA(ma20, COLOR.ma20)

  // 成交量
  const volH = volBottom - volTop
  for (let i = 0; i < n; i++) {
    const x = px(i)
    const up = close[i] >= open[i]
    ctx.fillStyle = up ? 'rgba(248,81,73,0.55)' : 'rgba(63,185,80,0.55)'
    const hh = (volume[i] / maxV) * volH
    ctx.fillRect(x - candleW / 2, volBottom - hh, candleW, hh)
  }

  // 日期刻度（MM-DD）
  ctx.fillStyle = COLOR.text
  ctx.textAlign = 'center'
  const labelEvery = Math.ceil(n / 6)
  for (let i = 0; i < n; i += labelEvery) {
    ctx.fillText(String(klines[i].date || '').slice(5), px(i), cssH - 8)
  }
}

export default function KLineChart({ klines }) {
  const ref = useRef(null)

  useEffect(() => {
    if (!ref.current || !klines || klines.length === 0) return
    const drawNow = () => draw(ref.current, klines)
    drawNow()
    window.addEventListener('resize', drawNow)
    return () => window.removeEventListener('resize', drawNow)
  }, [klines])

  if (!klines || klines.length === 0) return <div className="empty">暂无 K 线数据</div>

  return (
    <div className="kline-wrap">
      <div className="kline-legend">
        <span className="ma5">MA5</span>
        <span className="ma10">MA10</span>
        <span className="ma20">MA20</span>
      </div>
      <canvas ref={ref} className="kline-canvas" />
    </div>
  )
}
