import axios from 'axios'
import type { Batch } from '../types'

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
    const resp = e.response
    if (typeof resp === 'object' && resp !== null && 'data' in resp) {
      const data = resp.data
      if (typeof data === 'object' && data !== null && 'detail' in data) {
        const detail = data.detail
        if (typeof detail === 'string') return detail
        if (typeof detail === 'object' && detail !== null && 'message' in detail) {
          const msg = detail.message
          if (typeof msg === 'string') return msg
        }
      }
    }
  }
  return fallback
}

/** 考生自查有效批次 */
export async function activeBatch(): Promise<Batch | null> {
  const { data } = await api.get<Batch[]>('/batches')
  return data.find((b) => b.is_active) ?? data[0] ?? null
}
