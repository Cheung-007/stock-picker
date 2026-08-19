// 可排序表头：点击切换升/降序，激活列显示方向箭头
export default function SortableTh({ field, label, sort, onToggle, className = '' }) {
  const active = sort.field === field
  return (
    <th
      className={`${className} sortable${active ? ' active' : ''}`}
      onClick={() => onToggle(field)}
      title="点击排序"
    >
      {label}
      {active && <span className="sort-arrow">{sort.dir === 'desc' ? '▼' : '▲'}</span>}
    </th>
  )
}
