<script setup lang="ts">
import SiteHeader from '../components/SiteHeader.vue'
import SiteFooter from '../components/SiteFooter.vue'
</script>

<template>
  <SiteHeader />
  <main id="main-content" class="member-main">
    <slot />
    <SiteFooter />
  </main>
</template>
