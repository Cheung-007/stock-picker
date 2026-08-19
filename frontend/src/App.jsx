import { useEffect, useState, useCallback } from 'react'
import { getAdvice, refresh } from './api'
import SentimentPanel from './components/SentimentPanel'
import BoardHeatTable from './components/BoardHeatTable'
import CandidateTable from './components/CandidateTable'
import StockDetail from './components/StockDetail'

const TABS = [
  { key: 'sentiment', label: '情绪仪表盘' },
  { key: 'board', label: '题材热度' },
  { key: 'candidates', label: '候选股' },
]

export default function App() {
  const [advice, setAdvice] = useState(null)
  const [tab, setTab] = useState('sentiment')
  const [selectedCode, setSelectedCode] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    try {
      const d = await getAdvice()
      setAdvice(d)
      setError('')
    } catch (e) {
      setError(e.message)
    }
  }, [])

  useEffect(() => {
    load()
    const timer = setInterval(load, 60000) // 每分钟拉取（命中后端缓存）
    return () => clearInterval(timer)
  }, [load])

  const handleRefresh = async () => {
    setLoading(true)
    try {
      await refresh()
      // 等待后端重新计算后拉取
      setTimeout(async () => {
        await load()
        setLoading(false)
      }, 3000)
    } catch (e) {
      setError(e.message)
      setLoading(false)
    }
  }

  if (selectedCode) {
    return <StockDetail code={selectedCode} onClose={() => setSelectedCode(null)} />
  }

  if (!advice && !error) {
    return (
      <div className="app">
        <header className="topbar"><h1>T+1 超短线选股系统</h1></header>
        <div className="loading-full">正在抓取行情数据，首次加载约需 1 分钟…</div>
      </div>
    )
  }

  return (
    <div className="app">
      <header className="topbar">
        <h1>T+1 超短线选股系统</h1>
        <div className="topbar-right">
          {error && <span className="error-text">{error}</span>}
          <button className="btn" onClick={handleRefresh} disabled={loading}>
            {loading ? '刷新中…' : '刷新数据'}
          </button>
        </div>
      </header>

      <nav className="tabs">
        {TABS.map((t) => (
          <button
            key={t.key}
            className={`tab ${tab === t.key ? 'active' : ''}`}
            onClick={() => setTab(t.key)}
          >
            {t.label}
          </button>
        ))}
      </nav>

      <main className="content">
        {tab === 'sentiment' && (
          <SentimentPanel sentiment={advice?.sentiment} risk={advice?.risk} />
        )}
        {tab === 'board' && <BoardHeatTable boards={advice?.board_heat} />}
        {tab === 'candidates' && (
          <CandidateTable entries={advice?.entries} onSelect={setSelectedCode} />
        )}
      </main>
    </div>
  )
}
