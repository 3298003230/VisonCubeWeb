import { createRouter, createWebHistory } from 'vue-router'
import { authState, ensureSessionRestored, hasVerifiedEmail } from '../auth/session'
import AccountPage from '../pages/AccountPage.vue'
import ChangePasswordPage from '../pages/ChangePasswordPage.vue'
import HomePage from '../pages/HomePage.vue'
import LicenseAdminPage from '../pages/LicenseAdminPage.vue'
import ProductPage from '../pages/ProductPage.vue'
import EmailVerificationPage from '../pages/auth/EmailVerificationPage.vue'
import LoginPage from '../pages/auth/LoginPage.vue'
import PasswordResetPage from '../pages/auth/PasswordResetPage.vue'
import RegisterPage from '../pages/auth/RegisterPage.vue'

declare module 'vue-router' {
  interface RouteMeta {
    layout: 'auth' | 'app'
    guestOnly?: boolean
    requiresAuth?: boolean
    allowUnverifiedEmail?: boolean
    requiresLicenseAdmin?: boolean
    title?: string
  }
}

export const router = createRouter({
  history: createWebHistory(),
  scrollBehavior: () => ({ top: 0 }),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: LoginPage,
      meta: { layout: 'auth', guestOnly: true, title: '登录' },
    },
    {
      path: '/register',
      name: 'register',
      component: RegisterPage,
      meta: { layout: 'auth', guestOnly: true, title: '注册' },
    },
    {
      path: '/forgot-password',
      name: 'forgot-password',
      component: PasswordResetPage,
      meta: { layout: 'auth', guestOnly: true, title: '找回密码' },
    },
    {
      path: '/verify-email',
      name: 'verify-email',
      component: EmailVerificationPage,
      meta: {
        layout: 'auth',
        requiresAuth: true,
        allowUnverifiedEmail: true,
        title: '验证邮箱',
      },
    },
    {
      path: '/',
      name: 'home',
      component: HomePage,
      meta: { layout: 'app', requiresAuth: true, title: '首页' },
    },
    {
      path: '/guanshan',
      name: 'guanshan',
      component: ProductPage,
      props: { productId: 'guanshan' },
      meta: { layout: 'app', requiresAuth: true, title: '观山' },
    },
    {
      path: '/tingyu',
      name: 'tingyu',
      component: ProductPage,
      props: { productId: 'tingyu' },
      meta: { layout: 'app', requiresAuth: true, title: '听雨' },
    },
    {
      path: '/zhufeng',
      name: 'zhufeng',
      component: ProductPage,
      props: { productId: 'zhufeng' },
      meta: { layout: 'app', requiresAuth: true, title: '逐风' },
    },
    {
      path: '/account',
      name: 'account',
      component: AccountPage,
      meta: { layout: 'app', requiresAuth: true, title: '账户' },
    },
    {
      path: '/account/password',
      name: 'change-password',
      component: ChangePasswordPage,
      meta: { layout: 'app', requiresAuth: true, title: '修改密码' },
    },
    {
      path: '/account/licenses',
      name: 'license-admin',
      component: LicenseAdminPage,
      meta: {
        layout: 'app',
        requiresAuth: true,
        requiresLicenseAdmin: true,
        title: '卡密管理',
      },
    },
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
})

router.beforeEach(async (to) => {
  await ensureSessionRestored()
  if (authState.status === 'restore_error') return false

  const session = authState.session
  const verified = Boolean(session && hasVerifiedEmail(session.user))

  if (to.meta.requiresAuth && !session) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }

  if (to.name === 'verify-email') {
    if (!session) return { name: 'login' }
    if (verified) return { name: 'home' }
    return true
  }

  if (to.meta.requiresAuth && !to.meta.allowUnverifiedEmail && !verified) {
    return { name: 'verify-email' }
  }

  if (to.meta.requiresLicenseAdmin && session?.user.username !== '3298003230') {
    return { name: 'account' }
  }

  if (to.meta.guestOnly && session) {
    return { name: verified ? 'home' : 'verify-email' }
  }

  return true
})

router.afterEach((to) => {
  document.title = to.meta.title ? `${to.meta.title} | VisonCube` : 'VisonCube'
})
