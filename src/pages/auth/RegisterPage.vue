<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ApiError } from '../../api/client'
import { useAuth } from '../../auth/useAuth'

const router = useRouter()
const auth = useAuth()

const username = ref('')
const email = ref('')
const password = ref('')
const confirmPassword = ref('')
const submitting = ref(false)
const errorMessage = ref('')

const submit = async () => {
  errorMessage.value = ''
  if (username.value.trim().length < 3) {
    errorMessage.value = '用户名至少需要 3 个字符'
    return
  }
  if (password.value.length < 6) {
    errorMessage.value = '密码至少需要 6 个字符'
    return
  }
  if (password.value !== confirmPassword.value) {
    errorMessage.value = '两次输入的密码不一致'
    return
  }

  submitting.value = true
  try {
    await auth.registerAccount({
      username: username.value.trim(),
      email: email.value.trim(),
      password: password.value,
    })
    await router.replace('/verify-email')
  } catch (error) {
    errorMessage.value = error instanceof ApiError ? error.message : '注册失败，请稍后重试'
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="auth-heading">
    <p>创建账户</p>
    <h1>注册 VisonCube</h1>
  </div>

  <form class="auth-form auth-form-compact" @submit.prevent="submit">
    <label class="form-field">
      <span>用户名</span>
      <input v-model="username" type="text" autocomplete="username" minlength="3" placeholder="请输入用户名" required>
    </label>
    <label class="form-field">
      <span>邮箱</span>
      <input v-model="email" type="email" autocomplete="email" placeholder="请输入邮箱" required>
    </label>
    <label class="form-field">
      <span>密码</span>
      <input v-model="password" type="password" autocomplete="new-password" minlength="6" placeholder="请输入密码" required>
    </label>
    <label class="form-field">
      <span>确认密码</span>
      <input v-model="confirmPassword" type="password" autocomplete="new-password" minlength="6" placeholder="再次输入密码" required>
    </label>
    <p v-if="errorMessage" class="form-message error-message" role="alert">{{ errorMessage }}</p>
    <button class="primary-button" type="submit" :disabled="submitting">
      {{ submitting ? '正在注册…' : '注册' }}
    </button>
  </form>

  <p class="auth-switch">已有账户？<RouterLink to="/login">返回登录</RouterLink></p>
</template>
