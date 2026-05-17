// stores/emailStore.js
import { defineStore } from 'pinia'
import { fetchProcessedEmails } from '@/api/email'

export const useEmailStore = defineStore('email', {
  state: () => ({
    message: '',
    emailList: [],
    loading: false,
    error: null,
    currentIndex: 0,
    debugVisible: []     // 存储每个邮件的折叠状态
  }),
  actions: {
    async fetchEmails() {
  this.loading = true
  this.error = null
  this.message = ''
  try {
    const data = await fetchProcessedEmails()
    console.log('【1】fetchProcessedEmails 返回的 data:', data)
    console.log('【2】data 的类型:', typeof data)
    console.log('【3】data 是否为对象:', data && typeof data === 'object')
    console.log('【4】data.results:', data?.results)
    console.log('【5】data.results 类型:', Array.isArray(data?.results))
    console.log('【6】data.results 长度:', data?.results?.length)

    // 尝试另一种可能：数据被包裹在 data.data 里
    console.log('【7】data.data?.results:', data?.data?.results)

    this.message = data.message || '获取成功'
    // 尝试多种路径
    const results = data.results || data.data?.results || []
    this.emailList = results
    console.log('【8】最终 emailList 长度:', this.emailList.length)

    this.debugVisible = new Array(this.emailList.length).fill(false)
    this.currentIndex = 0
  } catch (err) {
    this.error = err.message || '后端请求失败，请检查服务或 CORS'
    console.error(err)
  } finally {
    this.loading = false
  }
},
    nextEmail() {
      if (this.currentIndex < this.emailList.length - 1) {
        this.currentIndex++
      }
    },
    prevEmail() {
      if (this.currentIndex > 0) {
        this.currentIndex--
      }
    },
    setCurrentIndex(idx) {
      if (idx >= 0 && idx < this.emailList.length) {
        this.currentIndex = idx
      }
    },
    toggleDebug(index) {
      if (this.debugVisible[index] !== undefined) {
        this.debugVisible[index] = !this.debugVisible[index]
      }
    }
  }
})