<script setup lang="ts">
import { computed } from 'vue'
import ReleaseDownloadCard from '../components/ReleaseDownloadCard.vue'
import { products, type ProductId } from '../data/products'

const props = defineProps<{
  productId: ProductId
}>()

const product = computed(() => products[props.productId])
</script>

<template>
  <section class="product-page page-enter" :data-product="product.id" :aria-labelledby="`${product.id}-title`">
    <RouterLink class="back-link" to="/"><span aria-hidden="true">←</span> 返回首页</RouterLink>

    <div class="product-hero">
      <div class="product-copy">
        <p class="product-eyebrow">{{ product.software }}</p>
        <h1 :id="`${product.id}-title`">{{ product.name }}</h1>
        <p class="product-description">{{ product.description }}</p>
        <div class="product-tags" aria-label="支持平台">
          <span v-for="tag in product.tags" :key="tag">{{ tag }}</span>
        </div>
      </div>

      <div class="product-showcase" aria-hidden="true">
        <div class="scene-grid"></div>
        <div class="scene-mountain scene-mountain-back"></div>
        <div class="scene-mountain scene-mountain-front"></div>
        <div class="scene-screen"><span>16:9</span></div>
        <div class="scene-rain scene-rain-one"></div>
        <div class="scene-rain scene-rain-two"></div>
        <div class="scene-rain scene-rain-three"></div>
        <div class="scene-wave"><i></i><i></i><i></i><i></i><i></i><i></i><i></i></div>
        <div class="scene-wind scene-wind-one"></div>
        <div class="scene-wind scene-wind-two"></div>
        <div class="scene-wind scene-wind-three"></div>
        <div class="scene-core">{{ product.sceneCore }}</div>
        <p class="scene-name">{{ product.name }}</p>
      </div>
    </div>

    <section class="release-section" aria-labelledby="download-title">
      <div class="release-heading">
        <div>
          <h2 id="download-title">版本与下载</h2>
          <p>下载信息由 VisonCube 发布服务统一提供。</p>
        </div>
        <span class="release-source">linux.sjmf.xyz</span>
      </div>
      <div class="release-list">
        <ReleaseDownloadCard
          v-for="definition in product.releases"
          :key="definition.clientId"
          :definition="definition"
        />
      </div>
    </section>
  </section>
</template>
