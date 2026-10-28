<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ensureLicenseCapabilities, licenseCapabilities } from '../auth/capabilities'
import { authState } from '../auth/session'

const route = useRoute()
const menu = ref<HTMLDetailsElement | null>(null)

const currentPageName = computed(() => {
  if (route.name === 'change-password') return '账户中心'
  return typeof route.meta.title === 'string' ? route.meta.title : 'VisonCube'
})

const isSignedIn = computed(() => Boolean(authState.session))
const canManageLicenses = computed(() => licenseCapabilities.canManageLicenses)

const navItems = [
  { label: '产品', href: '/#products' },
  { label: '体验', href: '/#experience' },
  { label: '下载', href: '/#downloads' },
  { label: '帮助', href: '/#support' },
] as const

const closeMenu = () => {
  if (menu.value) menu.value.open = false
}

onMounted(() => void ensureLicenseCapabilities())
watch(() => authState.session?.token, () => void ensureLicenseCapabilities(true))
</script>

<template>
  <header class="site-header">
    <div class="site-header-inner">
      <RouterLink class="brand" to="/" aria-label="VisonCube 首页">
        <span class="brand-mark" aria-hidden="true">V</span>
        <span class="brand-word">Vison<span>Cube</span></span>
      </RouterLink>

      <nav class="main-nav" aria-label="主导航">
        <a v-for="item in navItems" :key="item.href" :href="item.href">{{ item.label }}</a>
        <RouterLink v-if="canManageLicenses" :to="{ name: 'license-admin' }">授权管理</RouterLink>
      </nav>

      <RouterLink v-if="isSignedIn" class="account-link" :class="{ active: route.name === 'account' || route.name === 'change-password' }" to="/account">
        账户中心
      </RouterLink>
      <RouterLink v-else class="account-link account-link-primary" to="/login">登录 / 注册 <span aria-hidden="true">↗</span></RouterLink>

      <span class="mobile-page-name">{{ currentPageName }}</span>
      <details ref="menu" class="mobile-menu">
        <summary>目录</summary>
        <nav aria-label="移动端主导航">
          <a v-for="item in navItems" :key="item.href" :href="item.href" @click="closeMenu">{{ item.label }}</a>
          <RouterLink v-if="isSignedIn" to="/account" @click="closeMenu">账户中心</RouterLink>
          <RouterLink v-else to="/login" @click="closeMenu">登录 / 注册</RouterLink>
          <RouterLink v-if="canManageLicenses" to="/account/licenses" @click="closeMenu">授权管理</RouterLink>
        </nav>
      </details>
    </div>
  </header>
</template>
