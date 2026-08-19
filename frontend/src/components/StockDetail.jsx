// 个股详情
import { useEffect, useState } from 'react'
import { getStock } from '../api'
import KLineChart from './KLineChart'

export default function StockDetail({ code, onClose }) {
  const [data, setData] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!code) return
    setData(null)
    setError('')
    getStock(code)
      .then(setData)
      .catch((e) => setError(e.message))
  }, [code])

  if (error) return <div className="panel"><div className="empty">{error}</div></div>

  if (!data) return <div className="panel"><div className="empty">加载个股详情…</div></div>

  const t = data.technical
  const hist = (data.capital_history || []).slice(-6)

  return (
    <div className="panel detail">
      <div className="detail-head">
        <h2>{data.code}</h2>
        <button className="btn" onClick={onClose}>返回</button>
      </div>

      <section>
        <h3>K 线（近 30 日）</h3>
        <KLineChart klines={data.kline} />
      </section>

      <section>
        <h3>概念板块</h3>
        <div className="chips">
          {(data.concepts || []).map((c) => <span key={c} className="chip">{c}</span>)}
        </div>
      </section>

      <section>
        <h3>技术形态</h3>
        <div className="tech-grid">
          <span className={t.ma_bull ? 'tag on' : 'tag'}>均线多头</span>
          <span className={t.breakout ? 'tag on' : 'tag'}>突破新高</span>
          <span className={t.macd_golden ? 'tag on' : 'tag'}>MACD金叉</span>
          <span className={t.macd_red_amp ? 'tag on' : 'tag'}>红柱放大</span>
          <span className="tag">形态分 {t.score}/10</span>
        </div>
      </section>

      <section>
        <h3>主力资金流（近 6 日，万元）</h3>
        <table className="table">
          <thead>
            <tr><th>日期</th><th className="num">主力净流入</th><th className="num">涨跌幅</th></tr>
          </thead>
          <tbody>
            {hist.map((h) => (
              <tr key={h.date}>
                <td className="mono">{h.date}</td>
                <td className={`num ${parseFloat(h.main_net_inflow) >= 0 ? 'up' : 'down'}`}>
                  {(parseFloat(h.main_net_inflow) / 1e4).toFixed(0)}
                </td>
                <td className={`num ${parseFloat(h.pct_chg) >= 0 ? 'up' : 'down'}`}>{Number(h.pct_chg || 0).toFixed(2)}%</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  )
}
