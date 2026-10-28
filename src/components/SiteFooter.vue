<template>
  <footer class="site-footer">
    <div class="site-footer-inner">
      <div class="site-footer-brand">
        <RouterLink class="footer-brand" to="/" aria-label="VisonCube 首页">
          <span class="brand-mark" aria-hidden="true">V</span>
          <span class="brand-word">Vison<span>Cube</span></span>
        </RouterLink>
        <p>影像、智能、音乐。为每一种体验保留清晰的秩序。</p>
      </div>

      <nav class="site-footer-links" aria-label="页脚导航">
        <div>
          <strong>探索</strong>
          <a href="/#products">产品</a>
          <a href="/#experience">产品体验</a>
          <a href="/#downloads">下载中心</a>
        </div>
        <div>
          <strong>服务</strong>
          <a href="/#support">帮助中心</a>
          <RouterLink to="/account">账户中心</RouterLink>
          <RouterLink to="/login">登录 / 注册</RouterLink>
        </div>
      </nav>
    </div>

    <div class="site-footer-bottom">
      <span>© {{ new Date().getFullYear() }} VisonCube. All rights reserved.</span>
      <a href="https://beian.miit.gov.cn/" target="_blank" rel="noopener noreferrer">
        鄂ICP备2026021693号-2
      </a>
    </div>
  </footer>
</template>
