<template>
  <header class="guest-header">
    <RouterLink class="brand" to="/login" aria-label="VisonCube 登录">VisonCube</RouterLink>
  </header>

  <main id="main-content" class="guest-main">
    <section class="auth-shell">
      <div class="auth-visual" aria-hidden="true">
        <div class="brand-field">
          <div class="field-header"><span>VISONCUBE</span><span>统一账户</span></div>
          <div class="field-wordmark">VisonCube</div>
          <div class="field-track"><i></i><i></i><i></i><i></i></div>
        </div>
        <div class="visual-summary">
          <h1>登录后继续访问 VisonCube。</h1>
          <div class="signal-status"><span></span>账户服务</div>
        </div>
      </div>

      <div class="auth-panel">
        <slot />
      </div>
    </section>
  </main>
</template>
