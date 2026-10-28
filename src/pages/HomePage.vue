<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ApiError } from '../api/client'
import { getClientRelease } from '../api/releases'
import type { ClientReleaseInfo } from '../api/types'
import { products, type ProductId, type ProductReleaseDefinition } from '../data/products'

type DownloadState = 'loading' | 'ready' | 'error' | 'unpublished'
type DownloadFilter = 'all' | ProductId

interface ReleaseView {
  state: DownloadState
  release: ClientReleaseInfo | null
}

const activeExperience = ref<ProductId>('guanshan')
const downloadFilter = ref<DownloadFilter>('all')
const releaseViews = ref<Record<string, ReleaseView>>({})

const productList = [products.guanshan, products.zhufeng, products.tingyu]
const productPath: Record<ProductId, string> = {
  guanshan: '/tv',
  zhufeng: '/ai',
  tingyu: '/music',
}

const experienceCopy: Record<ProductId, {
  kicker: string
  title: string
  description: string
  action: string
}> = {
  guanshan: {
    kicker: '01 / ENTERTAINMENT',
    title: '把注意力，\n交还给内容。',
    description: '一个安静的观看入口，让内容先于界面被看见。',
    action: '进入 TV',
  },
  zhufeng: {
    kicker: '02 / INTELLIGENCE',
    title: '让信息，\n更快成形。',
    description: '从识别到响应，保持清晰、直接而有序。',
    action: '进入 AI',
  },
  tingyu: {
    kicker: '03 / SOUND',
    title: '为聆听，\n保留空间。',
    description: '没有多余打扰，只有连续而准确的播放体验。',
    action: '进入 Music',
  },
}

const activeExperienceCopy = computed(() => experienceCopy[activeExperience.value])

const downloadItems = computed(() => productList.flatMap((product) =>
  product.releases.map((definition) => ({ product, definition }))))

const filteredDownloads = computed(() => downloadItems.value.filter(({ product }) =>
  downloadFilter.value === 'all' || downloadFilter.value === product.id))

const downloadFilters = computed<Array<{ value: DownloadFilter; label: string }>>(() => [
  { value: 'all', label: '全部' },
  ...productList.map((product) => ({ value: product.id, label: product.name })),
])

const releaseFor = (definition: ProductReleaseDefinition): ReleaseView =>
  releaseViews.value[definition.clientId] ?? { state: 'loading', release: null }

const displayVersion = (view: ReleaseView) => {
  const version = view.release?.display_version?.trim()
  return version ? `版本 ${version}` : '版本待确认'
}

const formatDate = (value?: string) => {
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric', month: '2-digit', day: '2-digit',
  }).format(date)
}

const safeDownloadUrl = (release: ClientReleaseInfo | null) => {
  if (!release?.download_url) return ''
  try {
    const url = new URL(release.download_url, window.location.origin)
    return url.protocol === 'https:' || (url.protocol === 'http:' && ['localhost', '127.0.0.1'].includes(url.hostname))
      ? url.href
      : ''
  } catch {
    return ''
  }
}

const loadRelease = async (definition: ProductReleaseDefinition) => {
  releaseViews.value[definition.clientId] = { state: 'loading', release: null }
  try {
    const release = await getClientRelease(definition.clientId)
    releaseViews.value[definition.clientId] = {
      state: release.download_url ? 'ready' : 'unpublished',
      release,
    }
  } catch (error) {
    releaseViews.value[definition.clientId] = {
      state: error instanceof ApiError && error.status === 404 ? 'unpublished' : 'error',
      release: null,
    }
  }
}

const loadAllReleases = async () => {
  await Promise.all(downloadItems.value.map(({ definition }) => loadRelease(definition)))
}

onMounted(() => void loadAllReleases())
</script>

<template>
  <div class="marketing-page page-enter">
    <section class="marketing-hero" aria-labelledby="hero-title">
      <div class="marketing-container hero-grid">
        <div class="hero-copy-block">
          <p class="eyebrow"><span></span> A CONSIDERED DIGITAL SYSTEM</p>
          <h1 id="hero-title">让产品，<br><em>回到它该有的秩序。</em></h1>
          <p class="hero-description">VisonCube 将影像、智能与音乐，<br>收束在清晰而克制的体验里。</p>
          <div class="hero-actions">
            <a class="marketing-button marketing-button-primary" href="#products">探索产品 <span aria-hidden="true">↗</span></a>
            <a class="marketing-button marketing-button-quiet" href="#downloads">下载应用 <span aria-hidden="true">↗</span></a>
          </div>
          <div class="hero-proof"><span class="proof-dots" aria-hidden="true"><i></i><i></i><i></i></span><span>THREE PRODUCTS · ONE SYSTEM</span><b></b><span>BUILT WITH INTENT</span></div>
        </div>

        <div class="hero-product-stage" aria-label="三个产品的视觉预览">
          <div class="stage-topline"><span><b>V</b> VisonCube <i>/</i> PRODUCT SYSTEM</span><small>CURATED EXPERIENCE <i></i></small></div>
          <div class="stage-main-art">
            <div class="stage-sun"></div>
            <div class="stage-mountain stage-mountain-far"></div>
            <div class="stage-mountain stage-mountain-near"></div>
            <div class="stage-copy"><small>VISUAL SYSTEM</small><strong>让内容，<br>先于界面被看见。</strong></div>
            <span class="stage-play" aria-hidden="true">▶</span>
          </div>
          <div class="stage-bottomline"><span class="stage-pips"><i class="active"></i><i></i><i></i></span><span>01 <i>/</i> 03</span></div>
          <div class="stage-float stage-float-ai"><b>✳</b><span><strong>AI</strong><small>从识别，到响应</small></span><em>↗</em></div>
          <div class="stage-float stage-float-music"><b>♫</b><span><strong>Music</strong><small>为聆听保留空间</small></span><em>•••</em></div>
          <small class="stage-index">VC / 2026</small>
        </div>
      </div>
    </section>

    <div class="marketing-container section-rail"><span>DESIGNED TO FEEL EFFORTLESS</span><a href="#products">↓ &nbsp; 向下探索</a></div>

    <section id="products" class="marketing-container marketing-section" aria-labelledby="products-title">
      <div class="section-heading-modern"><div><p class="section-kicker">01 <i></i> PRODUCTS</p><h2 id="products-title">三种产品，<br>一套清晰的系统。</h2></div><p>从观看、理解到聆听，功能服从体验。<br>每个细节，都有自己的分寸。</p></div>
      <div class="product-card-grid">
        <RouterLink v-for="product in productList" :key="product.id" class="marketing-product-card" :class="`product-card-${product.id}`" :to="productPath[product.id]">
          <div class="marketing-product-visual">
            <span class="art-caption">VISONCUBE / {{ product.software.replace('VisonCube-', '') }}</span>
            <div v-if="product.id === 'guanshan'" class="card-landscape"><i></i><b></b><span>▶</span></div>
            <div v-else-if="product.id === 'zhufeng'" class="card-orbit"><i>✳</i><b></b><b></b><b></b></div>
            <div v-else class="card-record"><i>V</i><b></b></div>
            <small>{{ product.id === 'guanshan' ? '01' : product.id === 'zhufeng' ? '02' : '03' }}</small>
          </div>
          <div class="marketing-product-body"><span class="product-symbol" aria-hidden="true">{{ product.id === 'guanshan' ? '▶' : product.id === 'zhufeng' ? '✳' : '♫' }}</span><div><p>{{ product.id === 'guanshan' ? 'TV · ENTERTAINMENT' : product.id === 'zhufeng' ? 'AI · INTELLIGENCE' : 'MUSIC · SOUND' }}</p><h3>{{ product.name }}</h3><span>{{ product.description }}</span></div><b class="card-arrow" aria-hidden="true">↗</b></div>
        </RouterLink>
      </div>
    </section>

    <section id="experience" class="experience-band" aria-labelledby="experience-title">
      <div class="marketing-container marketing-section">
        <div class="section-heading-modern"><div><p class="section-kicker">02 <i></i> EXPERIENCE</p><h2 id="experience-title">设计，<br>应该在使用中成立。</h2></div><p>从观看到聆听，每个界面都保持清晰。<br>切换查看三个产品的设计概念。</p></div>
        <div class="experience-shell">
          <div class="experience-tabs" role="tablist" aria-label="产品概念预览">
            <button v-for="product in productList" :key="product.id" type="button" role="tab" :aria-selected="activeExperience === product.id" :class="{ selected: activeExperience === product.id }" @click="activeExperience = product.id"><span class="product-symbol" aria-hidden="true">{{ product.id === 'guanshan' ? '▶' : product.id === 'zhufeng' ? '✳' : '♫' }}</span><span><strong>{{ product.name }}</strong><small>{{ product.id === 'guanshan' ? '沉浸式影视体验' : product.id === 'zhufeng' ? '视觉理解与探索' : '连续聆听体验' }}</small></span><em>↗</em></button>
            <p>THREE PRODUCTS<br>ONE CLEAR SYSTEM</p>
          </div>
          <div class="experience-panel">
            <div class="experience-copy"><span class="mini-tag">{{ activeExperienceCopy.kicker }}</span><h3>{{ activeExperienceCopy.title }}</h3><p>{{ activeExperienceCopy.description }}</p><RouterLink class="text-cta" :to="productPath[activeExperience]">{{ activeExperienceCopy.action }} <span>↗</span></RouterLink></div>
            <div class="experience-preview" :class="`preview-${activeExperience}`" aria-hidden="true">
              <div v-if="activeExperience === 'guanshan'" class="preview-cinema"><small>FEATURED · CINEMA</small><strong>把注意力，<br>交给光影。</strong><span>▶ &nbsp; 进入 TV</span><i></i><i></i><i></i></div>
              <div v-else-if="activeExperience === 'zhufeng'" class="preview-ai"><small>WORKSPACE / READY</small><b>✳</b><strong>识别之后，保持清晰。</strong><span>视觉 · 理解 · 响应</span><em>开始探索 <b>↗</b></em></div>
              <div v-else class="preview-music"><small>NOW PLAYING</small><div><b>V</b></div><strong>Somewhere, Here</strong><span>VisonCube · Design concept</span><i></i><em>◀　<span>▶</span>　▶</em></div>
            </div>
          </div>
        </div>
        <p class="prototype-note">品牌视觉概念预览，功能以对应产品与账户服务为准。</p>
      </div>
    </section>

    <section id="downloads" class="marketing-container marketing-section" aria-labelledby="downloads-title">
      <div class="section-heading-modern"><div><p class="section-kicker">03 <i></i> DOWNLOADS</p><h2 id="downloads-title">从这里，<br>开始使用。</h2></div><p>选择产品与平台，直接开始。<br>版本信息由发布服务实时提供。</p></div>
      <div class="download-shell-modern">
        <div class="download-toolbar"><strong>应用下载 <small>{{ downloadItems.length }} 个版本入口</small></strong><div class="download-filters" role="group" aria-label="按产品筛选"><button v-for="filter in downloadFilters" :key="filter.value" type="button" :class="{ selected: downloadFilter === filter.value }" @click="downloadFilter = filter.value">{{ filter.label }}</button></div></div>
        <div class="download-list-modern">
          <article v-for="item in filteredDownloads" :key="item.definition.clientId" class="download-row-modern" :data-state="releaseFor(item.definition).state">
            <span class="download-dot" :class="`dot-${item.product.id}`" aria-hidden="true"></span><div class="download-name"><strong>{{ item.product.name }}</strong><small>{{ item.definition.platform }} · {{ item.definition.packageType }}</small></div><div class="download-version"><strong v-if="releaseFor(item.definition).state === 'ready'">{{ displayVersion(releaseFor(item.definition)) }}</strong><span v-if="releaseFor(item.definition).state === 'ready'">{{ formatDate(releaseFor(item.definition).release?.published_at) }}</span><span v-else-if="releaseFor(item.definition).state === 'loading'">正在获取最新版本…</span><span v-else-if="releaseFor(item.definition).state === 'error'">更新信息获取失败，请重新检查。</span><span v-else>当前平台暂未提供下载</span></div><a v-if="releaseFor(item.definition).state === 'ready' && safeDownloadUrl(releaseFor(item.definition).release)" class="download-action" :href="safeDownloadUrl(releaseFor(item.definition).release)" :aria-label="`${item.definition.actionLabel}，${displayVersion(releaseFor(item.definition))}`">{{ item.definition.actionLabel }} <span>↗</span></a><button v-else class="download-action" type="button" :disabled="releaseFor(item.definition).state !== 'error'" @click="loadRelease(item.definition)">{{ releaseFor(item.definition).state === 'error' ? '重新检查' : releaseFor(item.definition).state === 'loading' ? '读取中' : '暂未提供' }}</button>
          </article>
        </div>
        <p class="download-footnote">安装包地址来自 VisonCube 发布服务；请根据设备平台选择对应版本。</p>
      </div>
    </section>

    <section class="marketing-container philosophy-band" aria-label="VisonCube 的产品理念"><div><p>OUR APPROACH</p><h2>让复杂退场，<br>让体验留下。</h2></div><div><p>好的产品不需要反复解释。它应该保持克制，让每一次打开都清楚、迅速，并且值得信任。</p><div class="principle-list"><span><b>01</b> 清晰</span><span><b>02</b> 可靠</span><span><b>03</b> 有分寸</span></div></div><div class="philosophy-mark" aria-hidden="true">V</div></section>

    <section id="support" class="marketing-container marketing-section support-section-modern" aria-labelledby="support-title">
      <div class="section-heading-modern"><div><p class="section-kicker">04 <i></i> SUPPORT</p><h2 id="support-title">需要帮助时，<br>答案应该清晰。</h2></div><p>常见问题先在这里找到答案。<br>账户与产品服务保持同一条路径。</p></div>
      <div class="support-grid-modern"><div class="faq-list-modern"><details><summary>如何获取 VisonCube 的应用？<span>＋</span></summary><p>在下载中心选择产品和设备平台，页面会显示发布服务提供的当前版本与安装地址。</p></details><details><summary>注册后为什么需要验证邮箱？<span>＋</span></summary><p>邮箱验证用于确认账户归属，也用于登录验证码和找回密码。完成验证后即可进入账户空间。</p></details><details><summary>下载信息加载失败怎么办？<span>＋</span></summary><p>点击“重新检查”再次请求发布服务；如果仍然失败，请稍后重试或联系支持。</p></details><details><summary>如何兑换授权？<span>＋</span></summary><p>登录后进入账户中心，在“兑换卡密”中输入代码。授权状态由服务端确认并按服务端时间计算。</p></details></div><div class="support-aside-modern"><span>↗</span><p>ACCOUNT & SUPPORT</p><h3>账户与服务，<br>保持在同一条路径上。</h3><p>从账户、下载到授权，每个入口都在合适的位置。</p><RouterLink class="marketing-button marketing-button-quiet" to="/login">进入账户空间 ↗</RouterLink></div></div>
    </section>
  </div>
</template>
