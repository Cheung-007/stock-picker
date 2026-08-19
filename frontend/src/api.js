// API 调用封装
const BASE = ''

async function request(path) {
  const resp = await fetch(`${BASE}${path}`)
  if (!resp.ok) {
    throw new Error(`请求失败 ${path}: ${resp.status}`)
  }
  return resp.json()
}

export const getAdvice = () => request('/api/advice')
export const getSentiment = () => request('/api/sentiment')
export const getBoardHeat = () => request('/api/board_heat')
export const getCandidates = () => request('/api/candidates')
export const getStock = (code) => request(`/api/stock/${code}`)
export const refresh = () =>
  fetch(`${BASE}/api/refresh`, { method: 'POST' }).then((r) => r.json())
