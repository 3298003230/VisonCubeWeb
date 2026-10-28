export type ProductId = 'guanshan' | 'tingyu' | 'zhufeng'

export interface ProductReleaseDefinition {
  clientId:
    | 'tv-android'
    | 'tv-android-leanback'
    | 'tv-android-leanback-v7a'
    | 'music-android'
    | 'music-windows'
    | 'ai-windows'
  platform: string
  packageType: string
  actionLabel: string
}

export interface ProductDefinition {
  id: ProductId
  name: string
  software: string
  description: string
  tags: string[]
  sceneCore: string
  releases: ProductReleaseDefinition[]
}

export const products: Record<ProductId, ProductDefinition> = {
  guanshan: {
    id: 'guanshan',
    name: 'TV',
    software: 'VisonCube-TV',
    description: '沉浸式影视体验，专注内容、搜索与播放。',
    tags: ['Android', 'Android TV', '双架构'],
    sceneCore: '▶',
    releases: [
      {
        clientId: 'tv-android',
        platform: 'Android 手机',
        packageType: 'APK / arm64-v8a',
        actionLabel: '下载手机版',
      },
      {
        clientId: 'tv-android-leanback',
        platform: 'Android TV',
        packageType: 'APK / 64 位 arm64-v8a',
        actionLabel: '下载电视 64 位版',
      },
      {
        clientId: 'tv-android-leanback-v7a',
        platform: 'Android TV',
        packageType: 'APK / 32 位 armeabi-v7a',
        actionLabel: '下载电视 32 位版',
      },
    ],
  },
  tingyu: {
    id: 'tingyu',
    name: 'Music',
    software: 'VisonCube-Music',
    description: '跨设备保持连续聆听，播放历史和收藏跟随账户。',
    tags: ['Android', 'Windows x64', '云端同步'],
    sceneCore: 'Ⅱ',
    releases: [
      {
        clientId: 'music-android',
        platform: 'Android',
        packageType: 'APK / 通用版',
        actionLabel: '下载 Android 版',
      },
      {
        clientId: 'music-windows',
        platform: 'Windows',
        packageType: '安装程序 / x64',
        actionLabel: '下载 Windows 版',
      },
    ],
  },
  zhufeng: {
    id: 'zhufeng',
    name: 'AI',
    software: 'VisonCube-AI',
    description: '让识别、方向与响应汇聚在一个轻量工具中。',
    tags: ['Windows x64', 'DirectML'],
    sceneCore: 'AI',
    releases: [
      {
        clientId: 'ai-windows',
        platform: 'Windows',
        packageType: '安装程序 / x64',
        actionLabel: '下载 Windows 版',
      },
    ],
  },
}
