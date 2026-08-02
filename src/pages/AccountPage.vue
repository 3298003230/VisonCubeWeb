<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuth } from '../auth/useAuth'

const route = useRoute()
const router = useRouter()
const auth = useAuth()
const signingOut = ref(false)

const user = computed(() => auth.user.value)
const passwordChanged = computed(() => route.query.changed === '1')

const logout = async () => {
  signingOut.value = true
  await auth.signOut()
  await router.replace('/login')
}
</script>

<template>
  <section class="account-page page-enter" aria-labelledby="account-title">
    <div class="section-heading">
      <p>VisonCube 账户</p>
      <h1 id="account-title">账户</h1>
    </div>

    <p v-if="passwordChanged" class="account-notice" role="status">密码已修改，当前设备已更新登录状态。</p>

    <div class="account-panel">
      <div class="account-identity">
        <div class="account-monogram" aria-hidden="true">{{ user?.username.slice(0, 1).toUpperCase() }}</div>
        <div>
          <strong>{{ user?.username }}</strong>
          <span>{{ user?.email }}</span>
        </div>
      </div>

      <dl class="account-details">
        <div>
          <dt>用户名</dt>
          <dd>{{ user?.username }}</dd>
        </div>
        <div>
          <dt>邮箱</dt>
          <dd>{{ user?.email }}</dd>
        </div>
      </dl>

      <div class="account-actions">
        <RouterLink class="secondary-button" to="/account/password">修改密码</RouterLink>
        <button class="danger-button" type="button" :disabled="signingOut" @click="logout">
          {{ signingOut ? '正在退出…' : '退出登录' }}
        </button>
      </div>
    </div>
  </section>
</template>
