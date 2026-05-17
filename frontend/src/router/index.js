import { createRouter, createWebHistory } from 'vue-router'
import EmailDashboard from '../views/EmailDashboard.vue'

const routes = [
  { path: '/', component: EmailDashboard },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router