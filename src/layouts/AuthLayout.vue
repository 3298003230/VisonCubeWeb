<script setup lang="ts">
import SiteFooter from '../components/SiteFooter.vue'
</script>

<template>
  <header class="guest-header">
    <RouterLink class="brand" to="/" aria-label="VisonCube 首页">
      <span class="brand-mark" aria-hidden="true">V</span>
      <span class="brand-word">Vison<span>Cube</span></span>
    </RouterLink>
    <RouterLink class="guest-back-link" to="/">返回官网 <span aria-hidden="true">↗</span></RouterLink>
  </header>

  <main id="main-content" class="guest-main">
    <section class="auth-shell">
      <div class="auth-visual">
        <div class="brand-field" aria-hidden="true">
          <div class="field-header"><span>VISONCUBE</span><span>ONE ACCOUNT</span></div>
          <div class="field-wordmark">VisonCube</div>
          <div class="field-track"><i></i><i></i><i></i><i></i></div>
        </div>
        <div class="visual-summary">
          <p class="auth-visual-kicker">A QUIET PLACE FOR GOOD THINGS</p>
          <h1>一套账户，连接每一种体验。</h1>
          <p>TV、AI、Music，从这里继续。</p>
          <div class="signal-status"><span></span>服务在线</div>
        </div>
      </div>

      <div class="auth-panel">
        <slot />
      </div>
    </section>
    <SiteFooter />
  </main>
</template>
