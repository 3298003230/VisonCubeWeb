<script setup lang="ts">
import { computed } from 'vue'
import { RouterView, useRoute } from 'vue-router'
import { authState, ensureSessionRestored } from './auth/session'
import AppLayout from './layouts/AppLayout.vue'
import AuthLayout from './layouts/AuthLayout.vue'
import { router } from './router'

const route = useRoute()
const activeLayout = computed(() => route.meta.layout === 'app' ? AppLayout : AuthLayout)

const retryRestore = async () => {
  await ensureSessionRestored(true)
  if (authState.status !== 'restore_error') {
    await router.replace(route.fullPath || '/')
  }
}
</script>

<template>
  <a class="skip-link" href="#main-content">跳到主要内容</a>
  <div class="ambient ambient-left" aria-hidden="true"></div>
  <div class="ambient ambient-right" aria-hidden="true"></div>

  <main v-if="authState.status === 'restoring'" class="session-screen" aria-live="polite">
    <p class="brand brand-large">VisonCube</p>
    <div class="session-loader" aria-hidden="true"><i></i><i></i><i></i></div>
    <p>正在确认登录状态</p>
  </main>

  <main v-else-if="authState.status === 'restore_error'" class="session-screen">
    <p class="brand brand-large">VisonCube</p>
    <h1>暂时无法连接账户服务</h1>
    <p>{{ authState.restoreError }}</p>
    <button class="primary-button compact-button" type="button" @click="retryRestore">重新连接</button>
  </main>

  <component :is="activeLayout" v-else>
    <RouterView />
  </component>
</template>
