// 候选股榜单（支持点击表头排序）
import useSort from '../useSort'
import SortableTh from './SortableTh'

const SIGNAL_STYLE = {
  S: 'sig-s',
  A: 'sig-a',
  B: 'sig-b',
  C: 'sig-c',
}

// 信号排序权重：S > A > B > C（字母序不满足，需自定义）
const SIGNAL_ORDER = { S: 4, A: 3, B: 2, C: 1 }
const comparators = {
  signal: (va, vb) => (SIGNAL_ORDER[va] ?? 0) - (SIGNAL_ORDER[vb] ?? 0),
}

// 信号分级说明（阈值见后端 config.SIGNAL）
const SIGNAL_LEGEND = [
  { s: 'S', cls: 'sig-s', label: '强势主升', text: '（≥85 且涨停/近涨停）盘中追入' },
  { s: 'A', cls: 'sig-a', label: '高分', text: '（70-84）尾盘买入' },
  { s: 'B', cls: 'sig-b', label: '观察', text: '（55-69）跟踪确认' },
  { s: 'C', cls: 'sig-c', label: '放弃', text: '（<55）信号不足' },
]

export default function CandidateTable({ entries, onSelect }) {
  const { sorted, sort, toggle } = useSort(entries, {
    defaultField: 'total_score',
    defaultDir: 'desc',
    comparators,
  })

  if (!entries || entries.length === 0) return <div className="empty">加载中…</div>

  return (
    <div className="panel">
      <div className="signal-legend">
        {SIGNAL_LEGEND.map((x) => (
          <span key={x.s} className="item">
            <span className={`sig ${x.cls}`}>{x.s}</span>
            <b>{x.label}</b>
            {x.text}
          </span>
        ))}
      </div>
      <table className="table">
        <thead>
          <tr>
            <SortableTh field="signal" label="信号" sort={sort} onToggle={toggle} />
            <SortableTh field="code" label="代码" sort={sort} onToggle={toggle} />
            <SortableTh field="name" label="名称" sort={sort} onToggle={toggle} />
            <SortableTh field="total_score" label="总分" sort={sort} onToggle={toggle} className="num" />
            <SortableTh field="theme_score" label="题材" sort={sort} onToggle={toggle} className="num" />
            <SortableTh field="capital_score" label="资金" sort={sort} onToggle={toggle} className="num" />
            <SortableTh field="technical_score" label="技术" sort={sort} onToggle={toggle} className="num" />
            <SortableTh field="pct_chg" label="涨幅" sort={sort} onToggle={toggle} className="num" />
            <SortableTh field="limit_up_count" label="连板" sort={sort} onToggle={toggle} className="num" />
            <th>买点</th>
            <SortableTh field="position" label="仓位" sort={sort} onToggle={toggle} className="num" />
            <th>理由</th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((e) => (
            <tr key={e.code} onClick={() => onSelect && onSelect(e.code)} className="clickable">
              <td><span className={`sig ${SIGNAL_STYLE[e.signal] || 'sig-c'}`}>{e.signal}</span></td>
              <td className="mono">{e.code}</td>
              <td className="strong">{e.name}</td>
              <td className="num strong">{e.total_score}</td>
              <td className="num">{e.theme_score}</td>
              <td className="num">{e.capital_score}</td>
              <td className="num">{e.technical_score}</td>
              <td className={`num ${e.pct_chg >= 0 ? 'up' : 'down'}`}>{Number(e.pct_chg || 0).toFixed(2)}%</td>
              <td className="num">{e.limit_up_count}</td>
              <td>{e.action}</td>
              <td className="num">{e.position ? `${(e.position * 100).toFixed(0)}%` : '-'}</td>
              <td className="muted reason">{e.reason}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
