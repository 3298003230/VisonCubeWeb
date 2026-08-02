<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ApiError } from '../../api/client'
import type { AuthSession } from '../../api/types'
import { hasVerifiedEmail } from '../../auth/session'
import { useAuth } from '../../auth/useAuth'
import { useCodeCooldown } from '../../auth/useCodeCooldown'

type LoginMode = 'password' | 'email'

const route = useRoute()
const router = useRouter()
const auth = useAuth()
const cooldown = useCodeCooldown()

const mode = ref<LoginMode>('password')
const username = ref('')
const password = ref('')
const email = ref('')
const code = ref('')
const submitting = ref(false)
const sendingCode = ref(false)
const errorMessage = ref('')
const noticeMessage = ref('')

const getErrorMessage = (error: unknown) =>
  error instanceof ApiError ? error.message : '操作失败，请稍后重试'

const postLoginTarget = () => {
  const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : ''
  return redirect.startsWith('/') && !redirect.startsWith('//') ? redirect : '/'
}

const finishLogin = async (session: AuthSession) => {
  await router.replace(hasVerifiedEmail(session.user) ? postLoginTarget() : '/verify-email')
}

const selectMode = (nextMode: LoginMode) => {
  mode.value = nextMode
  errorMessage.value = ''
  noticeMessage.value = ''
}

const submitPassword = async () => {
  errorMessage.value = ''
  submitting.value = true
  try {
    const session = await auth.loginWithPassword({
      username: username.value.trim(),
      password: password.value,
    })
    await finishLogin(session)
  } catch (error) {
    errorMessage.value = getErrorMessage(error)
  } finally {
    submitting.value = false
  }
}

const sendEmailCode = async () => {
  errorMessage.value = ''
  noticeMessage.value = ''
  const normalizedEmail = email.value.trim()
  if (!normalizedEmail) {
    errorMessage.value = '请输入邮箱'
    return
  }

  sendingCode.value = true
  try {
    const result = await auth.requestEmailLoginCode(normalizedEmail)
    noticeMessage.value = result.message
    cooldown.start()
  } catch (error) {
    errorMessage.value = getErrorMessage(error)
  } finally {
    sendingCode.value = false
  }
}

const submitEmailCode = async () => {
  errorMessage.value = ''
  if (!/^\d{6}$/.test(code.value.trim())) {
    errorMessage.value = '请输入 6 位验证码'
    return
  }

  submitting.value = true
  try {
    const session = await auth.loginWithEmailCode(email.value.trim(), code.value.trim())
    await finishLogin(session)
  } catch (error) {
    errorMessage.value = getErrorMessage(error)
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="auth-heading">
    <p>欢迎回来</p>
    <h1 id="auth-title">登录 VisonCube</h1>
  </div>

  <div class="auth-tabs" role="tablist" aria-label="登录方式">
    <button
      :class="{ active: mode === 'password' }"
      type="button"
      role="tab"
      :aria-selected="mode === 'password'"
      @click="selectMode('password')"
    >
      密码登录
    </button>
    <button
      :class="{ active: mode === 'email' }"
      type="button"
      role="tab"
      :aria-selected="mode === 'email'"
      @click="selectMode('email')"
    >
      验证码登录
    </button>
  </div>

  <form v-if="mode === 'password'" class="auth-form" @submit.prevent="submitPassword">
    <label class="form-field">
      <span>用户名或邮箱</span>
      <input v-model="username" type="text" autocomplete="username" placeholder="请输入用户名或邮箱" required>
    </label>
    <label class="form-field">
      <span>密码</span>
      <input v-model="password" type="password" autocomplete="current-password" placeholder="请输入密码" required>
    </label>
    <div class="auth-options auth-options-end">
      <RouterLink to="/forgot-password">找回密码</RouterLink>
    </div>
    <p v-if="errorMessage" class="form-message error-message" role="alert">{{ errorMessage }}</p>
    <button class="primary-button" type="submit" :disabled="submitting">
      {{ submitting ? '正在登录…' : '登录' }}
    </button>
  </form>

  <form v-else class="auth-form" @submit.prevent="submitEmailCode">
    <label class="form-field">
      <span>邮箱</span>
      <input v-model="email" type="email" autocomplete="email" placeholder="请输入邮箱" required>
    </label>
    <label class="form-field">
      <span>验证码</span>
      <span class="code-input">
        <input v-model="code" type="text" inputmode="numeric" autocomplete="one-time-code" maxlength="6" placeholder="6 位验证码" required>
        <button type="button" :disabled="sendingCode || !cooldown.canSend.value" @click="sendEmailCode">
          {{ sendingCode ? '正在发送…' : cooldown.buttonText.value }}
        </button>
      </span>
    </label>
    <p v-if="noticeMessage" class="form-message success-message" role="status">{{ noticeMessage }}</p>
    <p v-if="errorMessage" class="form-message error-message" role="alert">{{ errorMessage }}</p>
    <button class="primary-button" type="submit" :disabled="submitting">
      {{ submitting ? '正在登录…' : '登录' }}
    </button>
  </form>

  <p class="auth-switch">还没有账户？<RouterLink to="/register">注册账户</RouterLink></p>
</template>
