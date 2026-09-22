<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute } from 'vue-router'
import { authState } from '../auth/session'

const route = useRoute()
const menu = ref<HTMLDetailsElement | null>(null)

const currentPageName = computed(() => {
  if (route.name === 'change-password') return '账户'
  return typeof route.meta.title === 'string' ? route.meta.title : '首页'
})

const isLicenseAdmin = computed(() => authState.session?.user.username === '3298003230')

const closeMenu = () => {
  if (menu.value) menu.value.open = false
}

const navItems = [
  { name: 'home', label: '首页' },
  { name: 'guanshan', label: '观山' },
  { name: 'tingyu', label: '听雨' },
  { name: 'zhufeng', label: '逐风' },
] as const
</script>

<template>
  <header class="site-header">
    <RouterLink class="brand" to="/" aria-label="VisonCube 首页">VisonCube</RouterLink>

    <nav class="main-nav" aria-label="主导航">
      <RouterLink v-for="item in navItems" :key="item.name" :to="{ name: item.name }">
        {{ item.label }}
      </RouterLink>
      <RouterLink v-if="isLicenseAdmin" :to="{ name: 'license-admin' }">卡密</RouterLink>
    </nav>

    <RouterLink class="account-link" :class="{ active: route.name === 'change-password' }" to="/account">
      账户
    </RouterLink>

    <span class="mobile-page-name">{{ currentPageName }}</span>
    <details ref="menu" class="mobile-menu">
      <summary>目录</summary>
      <nav aria-label="移动端主导航">
        <RouterLink v-for="item in navItems" :key="item.name" :to="{ name: item.name }" @click="closeMenu">
          {{ item.label }}
        </RouterLink>
        <RouterLink to="/account" @click="closeMenu">账户</RouterLink>
        <RouterLink v-if="isLicenseAdmin" to="/account/licenses" @click="closeMenu">卡密管理</RouterLink>
      </nav>
    </details>
  </header>
</template>
