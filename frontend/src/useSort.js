import { useMemo, useState } from 'react'

// 通用字段比较：数值按大小、其余按字符串（中文 locale），空值排最后
function compareValues(va, vb) {
  if (va == null && vb == null) return 0
  if (va == null) return 1
  if (vb == null) return -1
  const na = Number(va)
  const nb = Number(vb)
  const vaNum = va !== '' && !Number.isNaN(na)
  const vbNum = vb !== '' && !Number.isNaN(nb)
  if (vaNum && vbNum) return na - nb
  return String(va).localeCompare(String(vb), 'zh')
}

/**
 * 表格排序 hook。
 * @param items 原始数组
 * @param {object} [opts]
 * @param {string} [opts.defaultField]  默认排序字段
 * @param {string} [opts.defaultDir]    默认方向 'desc' | 'asc'
 * @param {object} [opts.comparators]   字段级自定义比较函数 { field: (va, vb) => number }
 *                                      （需传模块级常量，保证引用稳定）
 */
export default function useSort(items, { defaultField, defaultDir = 'desc', comparators = {} } = {}) {
  const [sort, setSort] = useState({ field: defaultField, dir: defaultDir })

  const toggle = (field) => {
    setSort((prev) =>
      prev.field === field
        ? { field, dir: prev.dir === 'desc' ? 'asc' : 'desc' }
        : { field, dir: 'desc' }
    )
  }

  const sorted = useMemo(() => {
    if (!items || items.length === 0) return items || []
    const { field, dir } = sort
    const cmp = comparators[field] || compareValues
    const arr = [...items].sort((a, b) => {
      const r = cmp(a[field], b[field], a, b)
      return dir === 'desc' ? -r : r
    })
    return arr
  }, [items, sort, comparators])

  return { sorted, sort, toggle }
}
