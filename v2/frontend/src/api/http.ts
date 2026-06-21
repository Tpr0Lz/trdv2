import axios from 'axios'

// 中文注释：统一 axios 实例，所有 API 默认携带 HttpOnly cookie。
export const http = axios.create({
  baseURL: '/api',
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json'
  }
})

