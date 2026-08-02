<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ApiError } from '../api/client'
import { useAuth } from '../auth/useAuth'

const router = useRouter()
const auth = useAuth()

const oldPassword = ref('')
const newPassword = ref('')
const confirmPassword = ref('')
const submitting = ref(false)
const errorMessage = ref('')

const submit = async () => {
  errorMessage.value = ''
  if (newPassword.value.length < 6) {
    errorMessage.value = '新密码至少需要 6 个字符'
    return
  }
  if (newPassword.value !== confirmPassword.value) {
    errorMessage.value = '两次输入的新密码不一致'
    return
  }

  submitting.value = true
  try {
    await auth.changePassword(oldPassword.value, newPassword.value)
    await router.replace({ name: 'account', query: { changed: '1' } })
  } catch (error) {
    errorMessage.value = error instanceof ApiError ? error.message : '密码修改失败，请稍后重试'
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <section class="account-page page-enter" aria-labelledby="password-title">
    <RouterLink class="back-link" to="/account"><span aria-hidden="true">←</span> 返回账户</RouterLink>
    <div class="section-heading compact-heading">
      <p>账户安全</p>
      <h1 id="password-title">修改密码</h1>
    </div>

    <form class="settings-form" @submit.prevent="submit">
      <label class="form-field">
        <span>当前密码</span>
        <input v-model="oldPassword" type="password" autocomplete="current-password" placeholder="请输入当前密码" required>
      </label>
      <label class="form-field">
        <span>新密码</span>
        <input v-model="newPassword" type="password" autocomplete="new-password" minlength="6" placeholder="请输入新密码" required>
      </label>
      <label class="form-field">
        <span>确认新密码</span>
        <input v-model="confirmPassword" type="password" autocomplete="new-password" minlength="6" placeholder="再次输入新密码" required>
      </label>
      <p v-if="errorMessage" class="form-message error-message" role="alert">{{ errorMessage }}</p>
      <div class="form-actions">
        <RouterLink class="secondary-button" to="/account">取消</RouterLink>
        <button class="primary-button compact-button" type="submit" :disabled="submitting">
          {{ submitting ? '正在保存…' : '保存新密码' }}
        </button>
      </div>
    </form>
  </section>
</template>
