<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ApiError } from '../../api/client'
import { useAuth } from '../../auth/useAuth'
import { useCodeCooldown } from '../../auth/useCodeCooldown'

const router = useRouter()
const auth = useAuth()
const cooldown = useCodeCooldown()

const step = ref<'email' | 'reset'>('email')
const email = ref('')
const code = ref('')
const newPassword = ref('')
const confirmPassword = ref('')
const sendingCode = ref(false)
const submitting = ref(false)
const errorMessage = ref('')
const noticeMessage = ref('')

const sendCode = async () => {
  errorMessage.value = ''
  noticeMessage.value = ''
  if (!email.value.trim()) {
    errorMessage.value = '请输入邮箱'
    return
  }

  sendingCode.value = true
  try {
    const result = await auth.requestPasswordResetCode(email.value.trim())
    noticeMessage.value = result.message
    step.value = 'reset'
    cooldown.start()
  } catch (error) {
    errorMessage.value = error instanceof ApiError ? error.message : '验证码发送失败，请稍后重试'
  } finally {
    sendingCode.value = false
  }
}

const submitReset = async () => {
  errorMessage.value = ''
  if (!/^\d{6}$/.test(code.value.trim())) {
    errorMessage.value = '请输入 6 位验证码'
    return
  }
  if (newPassword.value.length < 6) {
    errorMessage.value = '新密码至少需要 6 个字符'
    return
  }
  if (newPassword.value !== confirmPassword.value) {
    errorMessage.value = '两次输入的密码不一致'
    return
  }

  submitting.value = true
  try {
    await auth.resetPassword(email.value.trim(), code.value.trim(), newPassword.value)
    await router.replace('/')
  } catch (error) {
    errorMessage.value = error instanceof ApiError ? error.message : '密码重置失败，请稍后重试'
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="auth-heading">
    <p>账户恢复</p>
    <h1>找回密码</h1>
  </div>

  <form v-if="step === 'email'" class="auth-form" @submit.prevent="sendCode">
    <label class="form-field">
      <span>邮箱</span>
      <input v-model="email" type="email" autocomplete="email" placeholder="请输入邮箱" required>
    </label>
    <p v-if="errorMessage" class="form-message error-message" role="alert">{{ errorMessage }}</p>
    <button class="primary-button" type="submit" :disabled="sendingCode">
      {{ sendingCode ? '正在发送…' : '发送验证码' }}
    </button>
  </form>

  <form v-else class="auth-form auth-form-compact" @submit.prevent="submitReset">
    <label class="form-field">
      <span>邮箱</span>
      <input v-model="email" type="email" autocomplete="email" required>
    </label>
    <label class="form-field">
      <span>验证码</span>
      <span class="code-input">
        <input v-model="code" type="text" inputmode="numeric" autocomplete="one-time-code" maxlength="6" placeholder="6 位验证码" required>
        <button type="button" :disabled="sendingCode || !cooldown.canSend.value" @click="sendCode">
          {{ sendingCode ? '正在发送…' : cooldown.buttonText.value }}
        </button>
      </span>
    </label>
    <label class="form-field">
      <span>新密码</span>
      <input v-model="newPassword" type="password" autocomplete="new-password" minlength="6" placeholder="请输入新密码" required>
    </label>
    <label class="form-field">
      <span>确认新密码</span>
      <input v-model="confirmPassword" type="password" autocomplete="new-password" minlength="6" placeholder="再次输入新密码" required>
    </label>
    <p v-if="noticeMessage" class="form-message success-message" role="status">{{ noticeMessage }}</p>
    <p v-if="errorMessage" class="form-message error-message" role="alert">{{ errorMessage }}</p>
    <button class="primary-button" type="submit" :disabled="submitting">
      {{ submitting ? '正在重置…' : '重置密码' }}
    </button>
  </form>

  <p class="auth-switch"><RouterLink to="/login">返回登录</RouterLink></p>
</template>
