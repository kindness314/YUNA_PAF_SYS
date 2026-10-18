import axios from 'axios'

export const api = axios.create({ baseURL: '/api' })

api.interceptors.request.use((cfg) => {
  const token = localStorage.getItem('token')
  if (token) cfg.headers.Authorization = `Bearer ${token}`
  return cfg
})

api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (axios.isAxiosError(err) && err.response?.status === 401) {
      if (!location.pathname.startsWith('/login')) {
        localStorage.removeItem('token')
        location.href = '/login'
      }
    }
    return Promise.reject(err)
  },
)

/** 从 axios 错误中提取后端 detail 文案（兼容 string 与 {message,...} 两种形态） */
export function errText(e: unknown, fallback = '操作失败'): string {
  if (typeof e === 'object' && e !== null && 'response' in e) {
    const resp = (e as { response?: { data?: { detail?: unknown } } }).response
    const detail = resp?.data?.detail
    if (typeof detail === 'string') return detail
    if (typeof detail === 'object' && detail !== null && 'message' in detail) {
      const msg = (detail as { message?: unknown }).message
      if (typeof msg === 'string') return msg
    }
  }
  return fallback
}
