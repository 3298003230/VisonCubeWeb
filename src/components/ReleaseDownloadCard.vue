<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ApiError } from '../api/client'
import { getClientRelease } from '../api/releases'
import type { ClientReleaseInfo } from '../api/types'
import type { ProductReleaseDefinition } from '../data/products'

const props = defineProps<{
  definition: ProductReleaseDefinition
}>()

type ReleaseState = 'loading' | 'ready' | 'error' | 'unpublished'

const state = ref<ReleaseState>('loading')
const release = ref<ClientReleaseInfo | null>(null)

const publicVersion = computed(() => release.value?.display_version?.trim() ?? '')

const publishedDate = computed(() => {
  if (!release.value?.published_at) return ''
  const date = new Date(release.value.published_at)
  if (Number.isNaN(date.getTime())) return ''
  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).format(date)
})

const safeDownloadUrl = computed(() => {
  if (!release.value?.download_url) return ''
  try {
    const url = new URL(release.value.download_url, window.location.origin)
    return url.protocol === 'https:' || url.protocol === 'http:' ? url.href : ''
  } catch {
    return ''
  }
})

const load = async () => {
  state.value = 'loading'
  release.value = null
  try {
    const result = await getClientRelease(props.definition.clientId)
    release.value = result
    state.value = result.download_url ? 'ready' : 'unpublished'
  } catch (error) {
    state.value = error instanceof ApiError && error.status === 404 ? 'unpublished' : 'error'
  }
}

onMounted(load)
</script>

<template>
  <article class="release-row" :data-state="state">
    <div class="release-platform">
      <span class="platform-mark" aria-hidden="true"></span>
      <div>
        <h3>{{ definition.platform }}</h3>
        <p>{{ definition.packageType }}</p>
      </div>
    </div>

    <div v-if="state === 'ready' && release" class="release-meta">
      <strong>{{ publicVersion ? `当前版本 ${publicVersion}` : '当前版本待确认' }}</strong>
      <span>{{ publishedDate }}</span>
    </div>
    <div v-else class="release-message" aria-live="polite">
      <template v-if="state === 'loading'">正在获取最新版本…</template>
      <template v-else-if="state === 'error'">更新信息获取失败，请重新检查。</template>
      <template v-else>{{ definition.platform }} 版本暂未提供下载。</template>
    </div>

    <a
      v-if="state === 'ready' && safeDownloadUrl"
      class="release-action"
      :href="safeDownloadUrl"
      :aria-label="publicVersion ? `${definition.actionLabel}，当前版本 ${publicVersion}` : definition.actionLabel"
    >
      {{ definition.actionLabel }}
    </a>
    <button
      v-else
      class="release-action release-button"
      type="button"
      :disabled="state !== 'error'"
      @click="load"
    >
      {{ state === 'error' ? '重新检查' : state === 'loading' ? '正在获取' : '暂未提供' }}
    </button>
  </article>
</template>
