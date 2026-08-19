// 大盘情绪仪表盘
const STAGE_COLOR = {
  冰点期: 'var(--down)',
  发酵期: 'var(--warn)',
  主升期: 'var(--up)',
  高潮期: 'var(--up)',
  退潮期: 'var(--down)',
}

function Stat({ label, value, sub }) {
  return (
    <div className="stat">
      <div className="stat-label">{label}</div>
      <div className="stat-value">{value}</div>
      {sub && <div className="stat-sub">{sub}</div>}
    </div>
  )
}

export default function SentimentPanel({ sentiment, risk }) {
  if (!sentiment) return <div className="empty">加载中…</div>
  const stage = sentiment.stage
  return (
    <div className="panel">
      <div className="stage-banner" style={{ borderColor: STAGE_COLOR[stage] || 'var(--border)' }}>
        <div className="stage-name" style={{ color: STAGE_COLOR[stage] }}>
          {stage}
        </div>
        <div className="stage-tip">
          {sentiment.divergence_warning ? '⚠ 分歧预警：封板质量差，谨慎参与' : '情绪健康'}
        </div>
      </div>

      <div className="stat-grid">
        <Stat label="涨停家数" value={sentiment.limit_up_count} />
        <Stat label="最高连板" value={`${sentiment.max_lb} 板`} />
        <Stat label="炸板回封率" value={`${(sentiment.broke_rate * 100).toFixed(1)}%`} />
        <Stat label="空仓状态" value={risk?.empty_position ? '空仓' : '可操作'} sub={risk?.empty_position ? '冰点/退潮' : '正常'} />
      </div>

      <div className="risk-row">
        <span>单股上限 <b>{risk ? (risk.single_position_cap * 100).toFixed(0) : '-'}%</b></span>
        <span>总仓位上限 <b>{risk ? (risk.total_position_cap * 100).toFixed(0) : '-'}%</b></span>
        <span>止损 <b>{risk ? (risk.stop_loss * 100).toFixed(0) : '-'}%</b></span>
        <span>止盈(高开) <b>{risk ? (risk.take_profit_gap * 100).toFixed(0) : '-'}%</b></span>
      </div>
    </div>
  )
}
