<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { createLicenseBatch, listLicenseBatches } from '../api/licenses'
import type { LicenseBatchSummary, LicensePlan } from '../api/types'
import { useAuth } from '../auth/useAuth'

const auth = useAuth()
const token = computed(() => auth.state.session?.token ?? '')
const plan = ref<LicensePlan>('day')
const quantity = ref(1)
const note = ref('')
const loading = ref(true)
const generating = ref(false)
const errorMessage = ref('')
const actionMessage = ref('')
const batches = ref<LicenseBatchSummary[]>([])
const generatedCodes = ref<string[]>([])

const planOptions: Array<{ value: LicensePlan; title: string; duration: string }> = [
  { value: 'day', title: '天卡', duration: '24 小时' },
  { value: 'week', title: '周卡', duration: '7 天' },
  { value: 'month', title: '月卡', duration: '30 天' },
]

const planLabel = (value: LicensePlan) =>
  planOptions.find((option) => option.value === value)?.title ?? value

const formatDate = (value: string) => {
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

const loadBatches = async () => {
  if (!token.value) return
  loading.value = true
  errorMessage.value = ''
  try {
    batches.value = await listLicenseBatches(token.value)
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '无法读取卡密批次。'
  } finally {
    loading.value = false
  }
}

const generateBatch = async () => {
  if (!token.value) return
  const safeQuantity = Math.max(1, Math.min(100, Math.trunc(quantity.value || 1)))
  quantity.value = safeQuantity
  generating.value = true
  generatedCodes.value = []
  errorMessage.value = ''
  actionMessage.value = ''
  try {
    const response = await createLicenseBatch(token.value, {
      plan: plan.value,
      quantity: safeQuantity,
      note: note.value.trim() || undefined,
    })
    generatedCodes.value = response.codes
    batches.value = [response.batch, ...batches.value.filter((batch) => batch.id !== response.batch.id)]
    note.value = ''
    actionMessage.value = `已生成 ${response.codes.length} 个${planLabel(plan.value)}，代码只在本次显示。`
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '生成卡密失败，请稍后重试。'
  } finally {
    generating.value = false
  }
}

const copyCodes = async () => {
  if (!generatedCodes.value.length) return
  try {
    await navigator.clipboard.writeText(generatedCodes.value.join('\n'))
    actionMessage.value = '卡密已复制到剪贴板。'
  } catch {
    errorMessage.value = '浏览器未允许复制，请手动选择代码。'
  }
}

const downloadCodes = () => {
  if (!generatedCodes.value.length) return
  const blob = new Blob([`${generatedCodes.value.join('\r\n')}\r\n`], { type: 'text/plain;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `VisonCube-${plan.value}-${new Date().toISOString().slice(0, 10)}.txt`
  link.click()
  URL.revokeObjectURL(url)
}

onMounted(() => void loadBatches())
</script>

<template>
  <section class="account-page license-admin-page page-enter" aria-labelledby="license-admin-title">
    <RouterLink class="back-link" to="/account">← 返回授权中心</RouterLink>

    <div class="section-heading admin-heading">
      <div>
        <p>仅限授权管理员</p>
        <h1 id="license-admin-title">卡密管理</h1>
      </div>
      <span class="admin-identity">3298003230 · 无限制</span>
    </div>

    <div class="license-admin-grid">
      <form class="license-generator" @submit.prevent="generateBatch">
        <div class="panel-kicker">新建批次</div>
        <h2>生成卡密</h2>
        <p class="generator-help">代码由服务器安全随机生成。明文只返回一次，请生成后立即保存。</p>

        <fieldset class="plan-selector">
          <legend>选择时长</legend>
          <label v-for="option in planOptions" :key="option.value" :class="{ selected: plan === option.value }">
            <input v-model="plan" type="radio" name="license-plan" :value="option.value" />
            <strong>{{ option.title }}</strong>
            <small>{{ option.duration }}</small>
          </label>
        </fieldset>

        <div class="generator-fields">
          <label>
            <span>生成数量</span>
            <input v-model.number="quantity" type="number" min="1" max="100" inputmode="numeric" />
          </label>
          <label>
            <span>批次备注（可选）</span>
            <input v-model="note" type="text" maxlength="80" placeholder="例如：9 月测试用户" />
          </label>
        </div>

        <button class="primary-button generator-submit" type="submit" :disabled="generating">
          {{ generating ? '正在安全生成…' : `生成 ${quantity || 1} 个${planLabel(plan)}` }}
        </button>
      </form>

      <aside class="generated-vault" :class="{ populated: generatedCodes.length }" aria-live="polite">
        <div class="vault-head">
          <div>
            <p>本次生成</p>
            <h2>{{ generatedCodes.length ? `${generatedCodes.length} 个卡密` : '等待生成' }}</h2>
          </div>
          <span aria-hidden="true">一次显示</span>
        </div>

        <div v-if="generatedCodes.length" class="code-vault-list">
          <code v-for="code in generatedCodes" :key="code">{{ code }}</code>
        </div>
        <p v-else class="vault-empty">生成后的卡密会出现在这里。离开页面后无法再次查看明文。</p>

        <div class="vault-actions">
          <button class="secondary-button" type="button" :disabled="!generatedCodes.length" @click="copyCodes">复制全部</button>
          <button class="secondary-button" type="button" :disabled="!generatedCodes.length" @click="downloadCodes">下载文本</button>
        </div>
      </aside>
    </div>

    <p v-if="actionMessage" class="account-notice admin-message" role="status">{{ actionMessage }}</p>
    <p v-if="errorMessage" class="license-admin-error" role="alert">{{ errorMessage }}</p>

    <section class="batch-ledger" aria-labelledby="batch-ledger-title">
      <header>
        <div>
          <div class="panel-kicker">审计台账</div>
          <h2 id="batch-ledger-title">最近批次</h2>
        </div>
        <button class="quiet-button" type="button" :disabled="loading" @click="loadBatches">
          {{ loading ? '正在读取…' : '刷新台账' }}
        </button>
      </header>

      <div v-if="batches.length" class="batch-table-wrap">
        <table class="batch-table">
          <thead>
            <tr>
              <th>批次</th>
              <th>类型</th>
              <th>数量</th>
              <th>未使用</th>
              <th>已兑换</th>
              <th>已停用</th>
              <th>创建时间</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="batch in batches" :key="batch.id">
              <td><strong>{{ batch.note || batch.id }}</strong><small>{{ batch.id }}</small></td>
              <td><span class="plan-badge">{{ planLabel(batch.plan) }}</span></td>
              <td>{{ batch.quantity }}</td>
              <td>{{ batch.unused_count }}</td>
              <td>{{ batch.redeemed_count }}</td>
              <td>{{ batch.revoked_count }}</td>
              <td>{{ formatDate(batch.created_at) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <p v-else-if="!loading" class="ledger-empty">还没有卡密批次。创建第一批后，这里会显示使用情况。</p>
      <p v-else class="ledger-empty">正在读取卡密批次…</p>
    </section>
  </section>
</template>
