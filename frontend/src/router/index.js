import { createRouter, createWebHistory } from 'vue-router'
import AppLayout from '@/layouts/AppLayout.vue'
import EmailDashboard from '@/views/EmailDashboard.vue'

const routes = [
  {
    path: '/',
    component: AppLayout,
    children: [
      {
        path: '',          // 空路径表示 / 下直接渲染 EmailDashboard
        name: 'Dashboard',
        component: EmailDashboard
      }
      // 未来增加其他子路由，如：
      // { path: 'settings', component: Settings }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router