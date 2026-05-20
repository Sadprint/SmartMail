import { createRouter, createWebHistory } from 'vue-router'
import AppLayout from '@/layouts/AppLayout.vue'
import EmailDashboard from '@/views/EmailDashboard.vue'
import ChatAssistant from '@/views/ChatAssistant.vue'

const routes = [
  {
    path: '/',
    component: AppLayout,
    children: [
      {
        path: '',
        name: 'Dashboard',
        component: EmailDashboard
      },
      {
        path: 'chat',
        name: 'Chat',
        component: ChatAssistant
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router