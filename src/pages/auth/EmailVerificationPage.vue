<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ApiError } from '../../api/client'
import { useAuth } from '../../auth/useAuth'
import { useCodeCooldown } from '../../auth/useCodeCooldown'

const router = useRouter()
const auth = useAuth()
const cooldown = useCodeCooldown()

const email = ref(auth.user.value?.email ?? '')
const code = ref('')
const sendingCode = ref(false)
const submitting = ref(false)
const signingOut = ref(false)
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
    const result = await auth.requestEmailBindingCode(email.value.trim())
    noticeMessage.value = result.message
    cooldown.start()
  } catch (error) {
    errorMessage.value = error instanceof ApiError ? error.message : '验证码发送失败，请稍后重试'
  } finally {
    sendingCode.value = false
  }
}

const submit = async () => {
  errorMessage.value = ''
  if (!/^\d{6}$/.test(code.value.trim())) {
    errorMessage.value = '请输入 6 位验证码'
    return
  }

  submitting.value = true
  try {
    await auth.confirmEmailBinding(email.value.trim(), code.value.trim())
    await router.replace('/')
  } catch (error) {
    errorMessage.value = error instanceof ApiError ? error.message : '邮箱验证失败，请稍后重试'
  } finally {
    submitting.value = false
  }
}

const exitAccount = async () => {
  signingOut.value = true
  await auth.signOut()
  await router.replace('/login')
}
</script>

<template>
  <div class="auth-heading">
    <p>账户验证</p>
    <h1>验证邮箱</h1>
  </div>

  <form class="auth-form" @submit.prevent="submit">
    <label class="form-field">
      <span>邮箱</span>
      <input v-model="email" type="email" autocomplete="email" placeholder="请输入邮箱" required>
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
    <p v-if="noticeMessage" class="form-message success-message" role="status">{{ noticeMessage }}</p>
    <p v-if="errorMessage" class="form-message error-message" role="alert">{{ errorMessage }}</p>
    <button class="primary-button" type="submit" :disabled="submitting">
      {{ submitting ? '正在验证…' : '完成验证' }}
    </button>
  </form>

  <button class="text-button auth-exit" type="button" :disabled="signingOut" @click="exitAccount">
    使用其他账户
  </button>
</template>
