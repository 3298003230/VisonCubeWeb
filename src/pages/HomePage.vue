<template>
  <section class="hero page-enter" aria-labelledby="hero-title">
    <div class="hero-intro">
      <h1 id="hero-title">选择一个产品。</h1>
      <p class="hero-copy">观山、听雨、逐风，共用当前 VisonCube 账户。</p>
    </div>

    <div class="product-stage">
      <div class="stage-toolbar">
        <h2>产品</h2>
        <p>观山 / 听雨 / 逐风</p>
      </div>

      <div class="stage-content">
        <RouterLink class="product product-tv" to="/guanshan">
          <div class="product-art tv-art" aria-hidden="true">
            <div class="mountain mountain-back"></div>
            <div class="mountain mountain-front"></div>
            <div class="play-orbit"><span>▶</span></div>
          </div>
          <div class="product-meta">
            <div><p class="product-name">观山</p><p>VisonCube-TV</p></div>
            <span>Android</span>
          </div>
        </RouterLink>

        <RouterLink class="product product-music" to="/tingyu">
          <div class="music-head">
            <div class="music-identity"><span>正在聆听</span><strong>音乐播放与云端同步</strong></div>
            <span class="music-control" aria-hidden="true">Ⅱ</span>
          </div>
          <div class="waveform" aria-hidden="true">
            <i></i><i></i><i></i><i></i><i></i><i></i><i></i><i></i><i></i><i></i><i></i><i></i>
          </div>
          <div class="progress" aria-hidden="true"><span></span></div>
          <div class="product-meta">
            <div><p class="product-name">听雨</p><p>VisonCube-Music</p></div>
            <span>Android、Windows</span>
          </div>
        </RouterLink>

        <RouterLink class="product product-ai" to="/zhufeng">
          <div class="product-art ai-art" aria-hidden="true">
            <div class="wind-line wind-one"></div>
            <div class="wind-line wind-two"></div>
            <div class="wind-line wind-three"></div>
            <div class="ai-core">AI</div>
          </div>
          <div class="product-meta">
            <div><p class="product-name">逐风</p><p>VisonCube-AI</p></div>
            <span>Windows</span>
          </div>
        </RouterLink>
      </div>
    </div>
  </section>
</template>
