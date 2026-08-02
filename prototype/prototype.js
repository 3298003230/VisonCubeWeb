const params = new URLSearchParams(window.location.search)
const isMemberPreview = params.get('state') === 'member'
const requestedPage = params.get('page') || 'home'
let activeReleaseMode = params.get('release')

const products = {
  guanshan: {
    name: '观山',
    software: 'VisonCube-TV',
    description: '把影视内容留在熟悉的屏幕里，专注观看、搜索与播放。',
    tags: ['Android', 'arm64-v8a'],
    sceneCore: '▶',
    releases: [
      {
        clientId: 'tv-android',
        platform: 'Android',
        packageType: 'APK / arm64-v8a',
        displayVersion: '1.0.1',
        publishedAt: '2026.08.01',
        buttonLabel: '下载 Android 版',
        state: 'ready',
      },
    ],
  },
  tingyu: {
    name: '听雨',
    software: 'VisonCube-Music',
    description: '在手机与电脑之间继续聆听，播放历史和收藏跟随同一账户。',
    tags: ['Android', 'Windows x64', '云端同步'],
    sceneCore: 'Ⅱ',
    releases: [
      {
        clientId: 'music-android',
        platform: 'Android',
        packageType: 'APK / 通用版',
        displayVersion: '1.0.1',
        publishedAt: '2026.08.01',
        buttonLabel: '下载 Android 版',
        state: 'ready',
      },
      {
        clientId: 'music-windows',
        platform: 'Windows',
        packageType: '安装程序 / x64',
        displayVersion: '1.0.1',
        publishedAt: '2026.08.01',
        buttonLabel: '下载 Windows 版',
        state: 'ready',
      },
    ],
  },
  zhufeng: {
    name: '逐风',
    software: 'VisonCube-AI',
    description: '让识别、方向与响应聚合在一个轻量的 Windows 工具中。',
    tags: ['Windows x64', 'DirectML'],
    sceneCore: 'AI',
    releases: [
      {
        clientId: 'ai-windows',
        platform: 'Windows',
        packageType: 'Windows x64',
        displayVersion: '',
        publishedAt: '',
        buttonLabel: '暂未提供',
        state: 'unpublished',
      },
    ],
  },
}

const validPage = requestedPage === 'home' || products[requestedPage]
  ? requestedPage
  : 'home'
const activePage = isMemberPreview ? validPage : 'home'

document.body.dataset.auth = isMemberPreview ? 'member' : 'guest'
document.body.dataset.page = activePage

function setDocumentTitle(page) {
  const title = products[page]?.name
  document.title = title ? `${title} | VisonCube` : 'VisonCube'
}

function setActiveNavigation(page) {
  document.querySelectorAll('[data-page-link]').forEach((link) => {
    const isActive = link.dataset.pageLink === page
    link.classList.toggle('active', isActive)
    if (isActive) link.setAttribute('aria-current', 'page')
    else link.removeAttribute('aria-current')
  })
}

function getReleaseState(release) {
  if (release.state === 'unpublished') return 'unpublished'
  if (activeReleaseMode === 'loading') return 'loading'
  if (activeReleaseMode === 'error') return 'error'
  return release.state
}

function configureReleaseAction(row, release, state) {
  const link = row.querySelector('[data-release-link]')
  const button = row.querySelector('[data-release-button]')

  link.hidden = state !== 'ready'
  button.hidden = state === 'ready'

  if (state === 'ready') {
    link.textContent = release.buttonLabel
    link.dataset.demoDownload = release.clientId
    link.setAttribute('aria-label', `${release.buttonLabel}，当前版本 ${release.displayVersion}`)
    return
  }

  button.disabled = state !== 'error'
  button.textContent = state === 'error' ? '重新检查' : state === 'loading' ? '正在获取' : '暂未提供'
  if (state === 'error') button.dataset.releaseRetry = 'true'
}

function configureReleaseContent(row, release, state) {
  row.dataset.state = state
  row.querySelector('[data-release-platform]').textContent = release.platform
  row.querySelector('[data-release-package]').textContent = release.packageType

  const version = row.querySelector('[data-release-version]')
  const date = row.querySelector('[data-release-date]')
  const message = row.querySelector('[data-release-message]')

  version.textContent = state === 'ready' ? `当前版本 ${release.displayVersion}` : ''
  date.textContent = state === 'ready' ? release.publishedAt : ''

  const messages = {
    loading: '正在获取最新版本…',
    error: '更新信息获取失败，请重新检查。',
    unpublished: `${release.platform} 版本暂未提供下载。`,
  }
  message.textContent = messages[state] || ''
  message.hidden = state === 'ready'
}

function createReleaseRow(release) {
  const template = document.querySelector('#release-row-template')
  const row = template.content.firstElementChild.cloneNode(true)
  const state = getReleaseState(release)

  configureReleaseContent(row, release, state)
  configureReleaseAction(row, release, state)
  return row
}

function renderReleases(product) {
  const releaseList = document.querySelector('[data-release-list]')
  releaseList.replaceChildren(...product.releases.map(createReleaseRow))
}

function renderProductPage(page) {
  const product = products[page]
  if (!product) return

  document.body.dataset.product = page
  document.querySelector('[data-product-name]').textContent = product.name
  document.querySelector('[data-product-software]').textContent = product.software
  document.querySelector('[data-product-description]').textContent = product.description
  document.querySelector('[data-scene-name]').textContent = product.name
  document.querySelector('[data-scene-core]').textContent = product.sceneCore

  const tags = product.tags.map((tag) => {
    const item = document.createElement('span')
    item.textContent = tag
    return item
  })
  document.querySelector('[data-product-tags]').replaceChildren(...tags)
  renderReleases(product)
}

function showPage(page) {
  const isProductPage = Boolean(products[page])
  document.querySelector('[data-view="home"]').hidden = isProductPage
  document.querySelector('[data-view="product"]').hidden = !isProductPage

  if (isProductPage) renderProductPage(page)
  else delete document.body.dataset.product

  setActiveNavigation(page)
  setDocumentTitle(page)
}

document.querySelector('.auth-form')?.addEventListener('submit', (event) => {
  event.preventDefault()
})

document.addEventListener('click', (event) => {
  const demoDownload = event.target.closest('[data-demo-download]')
  if (demoDownload) event.preventDefault()

  const retryButton = event.target.closest('[data-release-retry]')
  if (retryButton && products[activePage]) {
    retryButton.blur()
    activeReleaseMode = null
    renderReleases(products[activePage])
  }
})

showPage(activePage)
