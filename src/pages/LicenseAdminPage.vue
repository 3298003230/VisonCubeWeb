<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import {
  createLicenseBatch,
  getLicenseAdminOverview,
  listLicenseAudit,
  listLicenseBatchCodes,
  listLicenseBatches,
  listLicenseEntitlements,
  revokeLicenseBatch,
  revokeLicenseCode,
} from '../api/licenses'
import type {
  LicenseAdminOverview,
  LicenseAuditEntry,
  LicenseBatchSummary,
  LicenseCodeStatus,
  LicenseCodeSummary,
  LicenseEntitlementSummary,
  LicensePlan,
  PagedResponse,
} from '../api/types'
import { useAuth } from '../auth/useAuth'

type RecordView = 'entitlements' | 'audit'

const PAGE_SIZE = 100
const emptyPage = <T>(): PagedResponse<T> => ({ items: [], total: 0, limit: PAGE_SIZE, offset: 0 })

const auth = useAuth()
const token = computed(() => auth.state.session?.token ?? '')
const plan = ref<LicensePlan>('day')
const quantity = ref(1)
const note = ref('')
const loading = ref(true)
const generating = ref(false)
const errorMessage = ref('')
const actionMessage = ref('')
const overview = ref<LicenseAdminOverview | null>(null)
const batches = ref<LicenseBatchSummary[]>([])
const generatedCodes = ref<string[]>([])
const selectedBatchId = ref('')
const codeFilter = ref<LicenseCodeStatus | null>(null)
const codePage = ref<PagedResponse<LicenseCodeSummary>>(emptyPage())
const loadingCodes = ref(false)
const pendingCodeRevoke = ref<number | null>(null)
const pendingBatchRevoke = ref('')
const revokingCode = ref<number | null>(null)
const revokingBatch = ref('')
const recordView = ref<RecordView>('entitlements')
const entitlementPage = ref<PagedResponse<LicenseEntitlementSummary>>(emptyPage())
const auditPage = ref<PagedResponse<LicenseAuditEntry>>(emptyPage())
const loadingRecords = ref(false)
let codeRequestVersion = 0

const planOptions: Array<{ value: LicensePlan; title: string; duration: string }> = [
  { value: 'day', title: '天卡', duration: '24 小时' },
  { value: 'week', title: '周卡', duration: '7 天' },
  { value: 'month', title: '月卡', duration: '30 天' },
]

const codeFilters: Array<{ value: LicenseCodeStatus | null; label: string }> = [
  { value: null, label: '全部' },
  { value: 'unused', label: '未使用' },
  { value: 'redeemed', label: '已兑换' },
  { value: 'revoked', label: '已停用' },
]

const selectedBatch = computed(() =>
  batches.value.find((batch) => batch.id === selectedBatchId.value) ?? null,
)

const planLabel = (value: LicensePlan) =>
  planOptions.find((option) => option.value === value)?.title ?? value

const statusLabel = (value: LicenseCodeStatus) => ({
  unused: '未使用',
  redeemed: '已兑换',
  revoked: '已停用',
})[value]

const auditLabel = (event: string) => ({
  batch_created: '生成批次',
  code_redeemed: '兑换卡密',
  code_revoked: '停用卡密',
  batch_revoked: '停用批次',
})[event] ?? event

const formatDate = (value: string | null) => {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '—'
  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', hour12: false,
  }).format(date)
}

const formatDuration = (totalSeconds: number) => {
  const minutes = Math.max(0, Math.floor(totalSeconds / 60))
  const days = Math.floor(minutes / 1440)
  const hours = Math.floor((minutes % 1440) / 60)
  const remainingMinutes = minutes % 60
  if (days > 0) return `${days} 天 ${hours} 小时`
  if (hours > 0) return `${hours} 小时 ${remainingMinutes} 分钟`
  return `${remainingMinutes} 分钟`
}

const readableError = (error: unknown, fallback: string) =>
  error instanceof Error ? error.message : fallback

const auditDetails = (entry: LicenseAuditEntry) => {
  const labels: Record<string, string> = {
    plan: '类型', quantity: '数量', reason: '原因', revoked_count: '停用数量',
  }
  const values = Object.entries(entry.details)
    .filter(([, value]) => ['string', 'number', 'boolean'].includes(typeof value))
    .map(([key, value]) => `${labels[key] ?? key}：${String(value)}`)
  return values.length ? values.join(' · ') : '无附加信息'
}

const loadDashboard = async () => {
  if (!token.value) return
  loading.value = true
  loadingRecords.value = true
  errorMessage.value = ''
  const [overviewResult, batchesResult, entitlementsResult, auditResult] = await Promise.allSettled([
    getLicenseAdminOverview(token.value),
    listLicenseBatches(token.value),
    listLicenseEntitlements(token.value, PAGE_SIZE, 0),
    listLicenseAudit(token.value, PAGE_SIZE, 0),
  ])

  if (overviewResult.status === 'fulfilled') overview.value = overviewResult.value
  if (batchesResult.status === 'fulfilled') batches.value = batchesResult.value
  if (entitlementsResult.status === 'fulfilled') entitlementPage.value = entitlementsResult.value
  if (auditResult.status === 'fulfilled') auditPage.value = auditResult.value

  const failure = [overviewResult, batchesResult, entitlementsResult, auditResult]
    .find((result) => result.status === 'rejected')
  if (failure?.status === 'rejected') {
    errorMessage.value = readableError(failure.reason, '管理数据未能完整加载，请重新刷新。')
  }
  loading.value = false
  loadingRecords.value = false
}

const refreshAfterMutation = async () => {
  if (!token.value) return
  const [overviewResult, batchesResult, auditResult] = await Promise.allSettled([
    getLicenseAdminOverview(token.value),
    listLicenseBatches(token.value),
    listLicenseAudit(token.value, PAGE_SIZE, auditPage.value.offset),
  ])
  if (overviewResult.status === 'fulfilled') overview.value = overviewResult.value
  if (batchesResult.status === 'fulfilled') batches.value = batchesResult.value
  if (auditResult.status === 'fulfilled') auditPage.value = auditResult.value
  const failure = [overviewResult, batchesResult, auditResult]
    .find((result) => result.status === 'rejected')
  if (failure?.status === 'rejected') {
    errorMessage.value = '操作已经完成，但部分统计刷新失败，请点击“刷新数据”重新同步。'
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
    await refreshAfterMutation()
  } catch (error) {
    errorMessage.value = readableError(error, '生成卡密失败，请稍后重试。')
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

const loadBatchCodes = async (offset = codePage.value.offset) => {
  if (!token.value || !selectedBatchId.value) return
  const requestVersion = ++codeRequestVersion
  loadingCodes.value = true
  errorMessage.value = ''
  try {
    const response = await listLicenseBatchCodes(
      token.value, selectedBatchId.value, codeFilter.value, PAGE_SIZE, offset,
    )
    if (requestVersion === codeRequestVersion) codePage.value = response
  } catch (error) {
    if (requestVersion === codeRequestVersion) {
      errorMessage.value = readableError(error, '无法读取批次内的卡密。')
    }
  } finally {
    if (requestVersion === codeRequestVersion) loadingCodes.value = false
  }
}

const openBatch = (batchId: string) => {
  selectedBatchId.value = batchId
  codeFilter.value = null
  codePage.value = emptyPage()
  pendingCodeRevoke.value = null
  pendingBatchRevoke.value = ''
  void loadBatchCodes(0)
}

const closeBatch = () => {
  codeRequestVersion += 1
  selectedBatchId.value = ''
  codePage.value = emptyPage()
  loadingCodes.value = false
  pendingCodeRevoke.value = null
  pendingBatchRevoke.value = ''
}

const changeCodeFilter = (value: LicenseCodeStatus | null) => {
  codeFilter.value = value
  pendingCodeRevoke.value = null
  void loadBatchCodes(0)
}

const revokeCode = async (code: LicenseCodeSummary) => {
  if (!token.value || code.status !== 'unused') return
  if (pendingCodeRevoke.value !== code.id) {
    pendingCodeRevoke.value = code.id
    return
  }
  revokingCode.value = code.id
  errorMessage.value = ''
  actionMessage.value = ''
  try {
    const response = await revokeLicenseCode(token.value, code.id, '管理员从网站停用')
    actionMessage.value = response.message
    pendingCodeRevoke.value = null
    await Promise.all([loadBatchCodes(codePage.value.offset), refreshAfterMutation()])
  } catch (error) {
    errorMessage.value = readableError(error, '停用卡密失败，请稍后重试。')
  } finally {
    revokingCode.value = null
  }
}

const revokeBatch = async (batch: LicenseBatchSummary) => {
  if (!token.value || batch.unused_count <= 0) return
  if (pendingBatchRevoke.value !== batch.id) {
    pendingBatchRevoke.value = batch.id
    return
  }
  revokingBatch.value = batch.id
  errorMessage.value = ''
  actionMessage.value = ''
  try {
    const response = await revokeLicenseBatch(token.value, batch.id, '管理员从网站停用批次')
    actionMessage.value = response.message
    pendingBatchRevoke.value = ''
    await refreshAfterMutation()
    if (selectedBatchId.value === batch.id) await loadBatchCodes(0)
  } catch (error) {
    errorMessage.value = readableError(error, '停用批次失败，请稍后重试。')
  } finally {
    revokingBatch.value = ''
  }
}

const loadEntitlements = async (offset = entitlementPage.value.offset) => {
  if (!token.value) return
  loadingRecords.value = true
  errorMessage.value = ''
  try {
    entitlementPage.value = await listLicenseEntitlements(token.value, PAGE_SIZE, offset)
  } catch (error) {
    errorMessage.value = readableError(error, '无法读取授权账户。')
  } finally {
    loadingRecords.value = false
  }
}

const loadAudit = async (offset = auditPage.value.offset) => {
  if (!token.value) return
  loadingRecords.value = true
  errorMessage.value = ''
  try {
    auditPage.value = await listLicenseAudit(token.value, PAGE_SIZE, offset)
  } catch (error) {
    errorMessage.value = readableError(error, '无法读取审计记录。')
  } finally {
    loadingRecords.value = false
  }
}

const selectRecordView = (view: RecordView) => {
  recordView.value = view
  if (view === 'entitlements' && !entitlementPage.value.items.length) void loadEntitlements(0)
  if (view === 'audit' && !auditPage.value.items.length) void loadAudit(0)
}

onMounted(() => void loadDashboard())
</script>

<template>
  <section class="account-page license-admin-page page-enter" aria-labelledby="license-admin-title">
    <RouterLink class="back-link" to="/account">← 返回授权中心</RouterLink>

    <div class="section-heading admin-heading">
      <div><p>仅限授权管理员</p><h1 id="license-admin-title">卡密管理</h1></div>
      <div class="admin-heading-actions">
        <span class="admin-identity">3298003230 · 无限制</span>
        <button class="quiet-button" type="button" :disabled="loading" @click="loadDashboard">
          {{ loading ? '正在刷新…' : '刷新数据' }}
        </button>
      </div>
    </div>

    <section class="license-command-strip" aria-label="卡密库存概况">
      <div class="command-primary"><span>可用卡密</span><strong>{{ overview?.codes.unused ?? '—' }}</strong><small>尚未兑换，可随时停用</small></div>
      <dl class="command-metrics">
        <div><dt>批次数</dt><dd>{{ overview?.batch_count ?? '—' }}</dd></div>
        <div><dt>已兑换</dt><dd>{{ overview?.codes.redeemed ?? '—' }}</dd></div>
        <div><dt>有效账户</dt><dd>{{ overview?.entitlements.active ?? '—' }}</dd></div>
        <div><dt>已停用</dt><dd>{{ overview?.codes.revoked ?? '—' }}</dd></div>
      </dl>
      <span class="command-sync">服务器时间 {{ formatDate(overview?.server_time ?? null) }}</span>
    </section>

    <div class="license-admin-grid">
      <form class="license-generator" @submit.prevent="generateBatch">
        <div class="panel-kicker">新建批次</div><h2>生成卡密</h2>
        <p class="generator-help">代码由服务器安全随机生成。明文只返回一次，请生成后立即保存。</p>
        <fieldset class="plan-selector">
          <legend>选择时长</legend>
          <label v-for="option in planOptions" :key="option.value" :class="{ selected: plan === option.value }">
            <input v-model="plan" type="radio" name="license-plan" :value="option.value" />
            <strong>{{ option.title }}</strong><small>{{ option.duration }}</small>
          </label>
        </fieldset>
        <div class="generator-fields">
          <label><span>生成数量</span><input v-model.number="quantity" type="number" min="1" max="100" inputmode="numeric" /></label>
          <label><span>批次备注（可选）</span><input v-model="note" type="text" maxlength="80" placeholder="例如：9 月测试用户" /></label>
        </div>
        <button class="primary-button generator-submit" type="submit" :disabled="generating">
          {{ generating ? '正在安全生成…' : `生成 ${quantity || 1} 个${planLabel(plan)}` }}
        </button>
      </form>

      <aside class="generated-vault" :class="{ populated: generatedCodes.length }" aria-live="polite">
        <div class="vault-head"><div><p>本次生成</p><h2>{{ generatedCodes.length ? `${generatedCodes.length} 个卡密` : '等待生成' }}</h2></div><span aria-hidden="true">一次显示</span></div>
        <div v-if="generatedCodes.length" class="code-vault-list"><code v-for="code in generatedCodes" :key="code">{{ code }}</code></div>
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
      <header><div><div class="panel-kicker">卡密生命周期</div><h2 id="batch-ledger-title">批次台账</h2></div><span class="ledger-total">共 {{ batches.length }} 个最近批次</span></header>
      <div v-if="batches.length" class="batch-table-wrap">
        <table class="batch-table batch-management-table">
          <thead><tr><th>批次</th><th>类型</th><th>数量</th><th>未使用</th><th>已兑换</th><th>已停用</th><th>创建时间</th><th>操作</th></tr></thead>
          <tbody>
            <tr v-for="batch in batches" :key="batch.id" :class="{ selected: selectedBatchId === batch.id }">
              <td><strong>{{ batch.note || batch.id }}</strong><small>{{ batch.id }}</small></td>
              <td><span class="plan-badge">{{ planLabel(batch.plan) }}</span></td><td>{{ batch.quantity }}</td><td>{{ batch.unused_count }}</td><td>{{ batch.redeemed_count }}</td><td>{{ batch.revoked_count }}</td><td>{{ formatDate(batch.created_at) }}</td>
              <td><div class="ledger-actions">
                <button class="table-action" type="button" @click="openBatch(batch.id)">查看卡密</button>
                <template v-if="batch.unused_count > 0">
                  <button v-if="pendingBatchRevoke !== batch.id" class="table-action danger" type="button" @click="pendingBatchRevoke = batch.id">停用剩余</button>
                  <template v-else>
                    <button class="table-action danger confirm" type="button" :disabled="revokingBatch === batch.id" @click="revokeBatch(batch)">{{ revokingBatch === batch.id ? '正在停用…' : `确认停用 ${batch.unused_count} 个` }}</button>
                    <button class="table-action" type="button" @click="pendingBatchRevoke = ''">取消</button>
                  </template>
                </template>
              </div></td>
            </tr>
          </tbody>
        </table>
      </div>
      <p v-else-if="!loading" class="ledger-empty">还没有卡密批次。创建第一批后，这里会显示使用情况。</p>
      <p v-else class="ledger-empty">正在读取卡密批次…</p>
    </section>

    <section v-if="selectedBatch" class="batch-detail" aria-labelledby="batch-detail-title">
      <header class="batch-detail-head"><div><div class="panel-kicker">批次明细</div><h2 id="batch-detail-title">{{ selectedBatch.note || planLabel(selectedBatch.plan) }}</h2><code>{{ selectedBatch.id }}</code></div><button class="quiet-button" type="button" @click="closeBatch">关闭明细</button></header>
      <div class="status-filter" aria-label="筛选卡密状态">
        <button v-for="filter in codeFilters" :key="filter.label" type="button" :class="{ active: codeFilter === filter.value }" :aria-pressed="codeFilter === filter.value" @click="changeCodeFilter(filter.value)">{{ filter.label }}</button>
      </div>
      <div v-if="codePage.items.length" class="batch-table-wrap">
        <table class="batch-table code-detail-table">
          <thead><tr><th>卡密提示</th><th>状态</th><th>关联账户</th><th>状态时间</th><th>操作</th></tr></thead>
          <tbody>
            <tr v-for="code in codePage.items" :key="code.id">
              <td><code>{{ code.code_hint }}</code></td><td><span class="code-status" :data-status="code.status">{{ statusLabel(code.status) }}</span></td><td>{{ code.redeemed_by_id ?? '—' }}</td><td>{{ formatDate(code.redeemed_at ?? code.revoked_at) }}</td>
              <td>
                <div v-if="code.status === 'unused'" class="ledger-actions">
                  <button v-if="pendingCodeRevoke !== code.id" class="table-action danger" type="button" @click="pendingCodeRevoke = code.id">停用</button>
                  <template v-else>
                    <button class="table-action danger confirm" type="button" :disabled="revokingCode === code.id" @click="revokeCode(code)">{{ revokingCode === code.id ? '处理中…' : '确认停用' }}</button>
                    <button class="table-action" type="button" @click="pendingCodeRevoke = null">取消</button>
                  </template>
                </div>
                <span v-else class="table-muted">无需操作</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <p v-else class="ledger-empty">{{ loadingCodes ? '正在读取批次明细…' : '当前筛选下没有卡密。' }}</p>
      <footer class="ledger-pagination"><span>共 {{ codePage.total }} 条</span><div>
        <button class="table-action" type="button" :disabled="loadingCodes || codePage.offset <= 0" @click="loadBatchCodes(Math.max(0, codePage.offset - PAGE_SIZE))">上一页</button>
        <button class="table-action" type="button" :disabled="loadingCodes || codePage.offset + codePage.limit >= codePage.total" @click="loadBatchCodes(codePage.offset + PAGE_SIZE)">下一页</button>
      </div></footer>
    </section>

    <section class="admin-records" aria-labelledby="admin-records-title">
      <header><div><div class="panel-kicker">授权追踪</div><h2 id="admin-records-title">账户与审计</h2></div><div class="record-tabs" role="tablist" aria-label="账户与审计视图">
        <button type="button" :class="{ active: recordView === 'entitlements' }" role="tab" :aria-selected="recordView === 'entitlements'" @click="selectRecordView('entitlements')">授权账户</button>
        <button type="button" :class="{ active: recordView === 'audit' }" role="tab" :aria-selected="recordView === 'audit'" @click="selectRecordView('audit')">操作记录</button>
      </div></header>
      <template v-if="recordView === 'entitlements'">
        <div v-if="entitlementPage.items.length" class="batch-table-wrap"><table class="batch-table">
          <thead><tr><th>账户</th><th>状态</th><th>剩余时长</th><th>激活时间</th><th>到期时间</th></tr></thead>
          <tbody><tr v-for="item in entitlementPage.items" :key="item.user_id">
            <td><strong>{{ item.username }}</strong><small>用户 ID {{ item.user_id }}</small></td><td><span class="code-status" :data-status="item.state">{{ item.state === 'active' ? '有效' : '已到期' }}</span></td><td>{{ formatDuration(item.remaining_seconds) }}</td><td>{{ formatDate(item.activated_at) }}</td><td>{{ formatDate(item.expires_at) }}</td>
          </tr></tbody>
        </table></div>
        <p v-else class="ledger-empty">{{ loadingRecords ? '正在读取授权账户…' : '还没有账户兑换过卡密。' }}</p>
        <footer class="ledger-pagination"><span>共 {{ entitlementPage.total }} 个账户</span><div>
          <button class="table-action" type="button" :disabled="loadingRecords || entitlementPage.offset <= 0" @click="loadEntitlements(Math.max(0, entitlementPage.offset - PAGE_SIZE))">上一页</button>
          <button class="table-action" type="button" :disabled="loadingRecords || entitlementPage.offset + entitlementPage.limit >= entitlementPage.total" @click="loadEntitlements(entitlementPage.offset + PAGE_SIZE)">下一页</button>
        </div></footer>
      </template>
      <template v-else>
        <div v-if="auditPage.items.length" class="audit-list">
          <article v-for="entry in auditPage.items" :key="entry.id"><span class="audit-mark" aria-hidden="true"></span><div>
            <header><strong>{{ auditLabel(entry.event) }}</strong><time>{{ formatDate(entry.created_at) }}</time></header><p>{{ auditDetails(entry) }}</p>
            <small>操作人 {{ entry.actor_username }}<template v-if="entry.batch_id"> · 批次 {{ entry.batch_id }}</template><template v-if="entry.code_hint"> · 卡密 {{ entry.code_hint }}</template><template v-if="entry.target_user_id"> · 用户 ID {{ entry.target_user_id }}</template></small>
          </div></article>
        </div>
        <p v-else class="ledger-empty">{{ loadingRecords ? '正在读取操作记录…' : '还没有卡密操作记录。' }}</p>
        <footer class="ledger-pagination"><span>共 {{ auditPage.total }} 条记录</span><div>
          <button class="table-action" type="button" :disabled="loadingRecords || auditPage.offset <= 0" @click="loadAudit(Math.max(0, auditPage.offset - PAGE_SIZE))">上一页</button>
          <button class="table-action" type="button" :disabled="loadingRecords || auditPage.offset + auditPage.limit >= auditPage.total" @click="loadAudit(auditPage.offset + PAGE_SIZE)">下一页</button>
        </div></footer>
      </template>
    </section>
  </section>
</template>
