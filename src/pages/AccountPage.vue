<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ApiError } from '../api/client'
import { getLicenseStatus, redeemLicense } from '../api/licenses'
import type { LicenseStatus } from '../api/types'
import { useAuth } from '../auth/useAuth'

const route = useRoute()
const router = useRouter()
const auth = useAuth()
const signingOut = ref(false)
const loadingLicense = ref(true)
const redeeming = ref(false)
const licenseError = ref('')
const redeemMessage = ref('')
const license = ref<LicenseStatus | null>(null)
const cardCode = ref('')
const remainingAtLoad = ref(0)
const loadedAt = ref(0)
const clock = ref(0)
let clockTimer = 0

const user = computed(() => auth.user.value)
const passwordChanged = computed(() => route.query.changed === '1')
const isLicenseAdmin = computed(() => user.value?.username === '3298003230')
const token = computed(() => auth.state.session?.token ?? '')

const remainingSeconds = computed(() => {
  if (!license.value || license.value.is_unlimited || license.value.remaining_seconds === null) return null
  const elapsed = loadedAt.value > 0 ? Math.floor((clock.value - loadedAt.value) / 1000) : 0
  return Math.max(0, remainingAtLoad.value - elapsed)
})

const licenseState = computed(() => {
  if (!license.value) return 'unknown'
  if (license.value.is_unlimited) return 'unlimited'
  if (license.value.state === 'active' && (remainingSeconds.value ?? 0) > 0) return 'active'
  return license.value.state
})

const licenseTitle = computed(() => {
  if (loadingLicense.value) return '正在读取授权'
  if (licenseState.value === 'unlimited') return '无限制'
  if (licenseState.value === 'active') return formatDuration(remainingSeconds.value ?? 0)
  if (licenseState.value === 'expired') return '授权已到期'
  if (licenseState.value === 'none') return '尚未激活'
  return '暂时无法读取'
})

const licenseDescription = computed(() => {
  if (licenseState.value === 'unlimited') return '当前账户不受授权时长限制。'
  if (licenseState.value === 'active') return '授权按服务器时间持续计时，软件未运行时也会正常消耗。'
  if (licenseState.value === 'expired') return '兑换新的卡密后即可恢复软件推理权限。'
  if (licenseState.value === 'none') return '兑换天卡、周卡或月卡后启用软件推理。'
  return '授权状态由服务器确认，本地时间不会改变剩余时长。'
})

const formatDuration = (totalSeconds: number) => {
  const totalMinutes = Math.max(0, Math.floor(totalSeconds / 60))
  const days = Math.floor(totalMinutes / 1440)
  const hours = Math.floor((totalMinutes % 1440) / 60)
  const minutes = totalMinutes % 60
  if (days > 0) return `${days} 天 ${hours} 小时`
  if (hours > 0) return `${hours} 小时 ${minutes} 分钟`
  return `${minutes} 分钟`
}

const formatDate = (value: string | null) => {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '—'
  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  }).format(date)
}

const setLicense = (value: LicenseStatus) => {
  license.value = value
  remainingAtLoad.value = Math.max(0, value.remaining_seconds ?? 0)
  loadedAt.value = performance.now()
  clock.value = loadedAt.value
}

const readableError = (error: unknown) => {
  if (error instanceof ApiError && error.status === 404) {
    return '授权服务尚未完成部署，请稍后再试。'
  }
  return error instanceof Error ? error.message : '授权服务暂时不可用，请稍后重试。'
}

const loadLicense = async () => {
  if (!token.value) return
  loadingLicense.value = true
  licenseError.value = ''
  try {
    setLicense(await getLicenseStatus(token.value))
  } catch (error) {
    license.value = null
    licenseError.value = readableError(error)
  } finally {
    loadingLicense.value = false
  }
}

const submitCode = async () => {
  const code = cardCode.value.trim().toUpperCase()
  if (!code || !token.value) return

  redeeming.value = true
  licenseError.value = ''
  redeemMessage.value = ''
  try {
    const response = await redeemLicense(token.value, code)
    setLicense(response.license)
    redeemMessage.value = response.message || '卡密已兑换，授权时长已更新。'
    cardCode.value = ''
  } catch (error) {
    licenseError.value = readableError(error)
  } finally {
    redeeming.value = false
  }
}

const logout = async () => {
  signingOut.value = true
  await auth.signOut()
  await router.replace('/login')
}

onMounted(() => {
  void loadLicense()
  clock.value = performance.now()
  clockTimer = window.setInterval(() => {
    clock.value = performance.now()
  }, 1000)
})

onBeforeUnmount(() => window.clearInterval(clockTimer))
</script>

<template>
  <section class="account-page page-enter" aria-labelledby="account-title">
    <div class="section-heading account-heading">
      <div>
        <p>VisonCube 账户</p>
        <h1 id="account-title">授权中心</h1>
      </div>
      <button class="quiet-button" type="button" :disabled="loadingLicense" @click="loadLicense">
        {{ loadingLicense ? '正在刷新…' : '刷新授权' }}
      </button>
    </div>

    <p v-if="passwordChanged" class="account-notice" role="status">密码已修改，当前设备已更新登录状态。</p>

    <div class="license-layout">
      <article class="license-overview" :data-state="licenseState">
        <header class="license-overview-head">
          <div>
            <p>当前授权</p>
            <h2>{{ licenseTitle }}</h2>
          </div>
          <span class="license-state-dot" aria-hidden="true"></span>
        </header>
        <p class="license-description">{{ licenseDescription }}</p>

        <ol class="license-timeline" aria-label="授权进度">
          <li class="complete">
            <span aria-hidden="true"></span>
            <div><strong>账户已验证</strong><small>{{ user?.username }}</small></div>
          </li>
          <li :class="{ complete: licenseState === 'active' || licenseState === 'unlimited' }">
            <span aria-hidden="true"></span>
            <div><strong>授权已激活</strong><small>{{ formatDate(license?.activated_at ?? null) }}</small></div>
          </li>
          <li :class="{ complete: licenseState === 'unlimited' }">
            <span aria-hidden="true"></span>
            <div>
              <strong>{{ licenseState === 'unlimited' ? '无限期使用' : '授权到期' }}</strong>
              <small>{{ licenseState === 'unlimited' ? '不受时长限制' : formatDate(license?.expires_at ?? null) }}</small>
            </div>
          </li>
        </ol>
      </article>

      <article class="redeem-panel">
        <div class="panel-kicker">兑换卡密</div>
        <h2>增加使用时长</h2>
        <p>卡密兑换成功后立即开始计时；已有有效时长会顺延。</p>

        <form class="redeem-form" @submit.prevent="submitCode">
          <label for="license-code">卡密代码</label>
          <input
            id="license-code"
            v-model="cardCode"
            autocomplete="off"
            autocapitalize="characters"
            maxlength="64"
            placeholder="输入卡密代码"
            spellcheck="false"
          />
          <button class="primary-button" type="submit" :disabled="redeeming || !cardCode.trim()">
            {{ redeeming ? '正在兑换…' : '立即兑换' }}
          </button>
        </form>

        <p v-if="redeemMessage" class="license-feedback success-message" role="status">{{ redeemMessage }}</p>
        <p v-if="licenseError" class="license-feedback error-message" role="alert">{{ licenseError }}</p>

        <RouterLink v-if="isLicenseAdmin" class="admin-entry" to="/account/licenses">
          <span>卡密管理</span>
          <small>生成与查看卡密批次</small>
        </RouterLink>
      </article>
    </div>

    <div class="account-panel account-profile-panel">
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
