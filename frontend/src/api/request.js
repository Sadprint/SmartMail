// request.js
import axios from 'axios'

const request = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '',
  timeout: 100000
})

// 响应拦截器：如果后端直接返回 { message, results }，就不需要额外处理
request.interceptors.response.use(
  response => response.data,   // 这里直接返回 response.data，所以调用方拿到的是 { message, results }
  error => Promise.reject(error)
)

export default request