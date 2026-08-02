<script setup lang="ts">
import SiteHeader from '../components/SiteHeader.vue'
</script>

<template>
  <SiteHeader />
  <main id="main-content" class="member-main">
    <slot />
  </main>
</template>
