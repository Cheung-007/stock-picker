// 题材热度榜（支持点击表头排序）
import useSort from '../useSort'
import SortableTh from './SortableTh'

export default function BoardHeatTable({ boards }) {
  const { sorted, sort, toggle } = useSort(boards, { defaultField: 'heat_score', defaultDir: 'desc' })

  if (!boards || boards.length === 0) return <div className="empty">加载中…</div>

  return (
    <div className="panel">
      <table className="table">
        <thead>
          <tr>
            <th>#</th>
            <SortableTh field="name" label="题材" sort={sort} onToggle={toggle} />
            <SortableTh field="heat_score" label="热度" sort={sort} onToggle={toggle} className="num" />
            <SortableTh field="pct_chg" label="涨幅" sort={sort} onToggle={toggle} className="num" />
            <SortableTh field="limit_up_count" label="涨停" sort={sort} onToggle={toggle} className="num" />
            <SortableTh field="max_lb" label="最高板" sort={sort} onToggle={toggle} className="num" />
            <SortableTh field="lead_stock" label="领涨股" sort={sort} onToggle={toggle} />
          </tr>
        </thead>
        <tbody>
          {sorted.map((b, i) => (
            <tr key={b.code}>
              <td className="rank">{i + 1}</td>
              <td className="strong">{b.name}</td>
              <td className="num heat">{b.heat_score}</td>
              <td className={`num ${b.pct_chg >= 0 ? 'up' : 'down'}`}>{Number(b.pct_chg || 0).toFixed(2)}%</td>
              <td className="num">{b.limit_up_count}</td>
              <td className="num">{b.max_lb}板</td>
              <td className="muted">{b.lead_stock}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
