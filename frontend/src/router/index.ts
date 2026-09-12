import { createRouter, createWebHistory } from 'vue-router'

import { useAuthStore } from '../stores/auth'
import DashboardView from '../views/DashboardView.vue'
import AdminView from '../views/AdminView.vue'
import LoginView from '../views/LoginView.vue'
import RegisterView from '../views/RegisterView.vue'
import ForgotPasswordView from '../views/ForgotPasswordView.vue'
import ResetPasswordView from '../views/ResetPasswordView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/dashboard' },
    { path: '/login', component: LoginView, meta: { guestOnly: true } },
    { path: '/cadastro', component: RegisterView, meta: { guestOnly: true } },
    { path: '/recuperar-senha', component: ForgotPasswordView, meta: { guestOnly: true } },
    { path: '/reset-password', component: ResetPasswordView, meta: { guestOnly: true } },
    { path: '/dashboard', component: DashboardView, meta: { requiresAuth: true } },
    { path: '/admin', component: AdminView, meta: { requiresAuth: true, adminOnly: true } },
  ],
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  if (!auth.user && to.meta.requiresAuth) await auth.restoreSession()
  if (to.meta.requiresAuth && !auth.isAuthenticated) return '/login'
  if (to.meta.adminOnly && auth.user?.role !== 'ADMIN') return '/dashboard'
  if (to.meta.guestOnly && auth.isAuthenticated) return '/dashboard'
})

export default router
