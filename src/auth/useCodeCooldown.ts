import { computed, onBeforeUnmount, ref } from 'vue'

export const useCodeCooldown = () => {
  const remainingSeconds = ref(0)
  let timerId: number | null = null

  const stop = () => {
    if (timerId !== null) window.clearInterval(timerId)
    timerId = null
  }

  const start = (seconds = 60) => {
    stop()
    remainingSeconds.value = seconds
    timerId = window.setInterval(() => {
      remainingSeconds.value -= 1
      if (remainingSeconds.value <= 0) stop()
    }, 1_000)
  }

  onBeforeUnmount(stop)

  return {
    remainingSeconds,
    canSend: computed(() => remainingSeconds.value <= 0),
    buttonText: computed(() => remainingSeconds.value > 0 ? `${remainingSeconds.value} 秒后重发` : '发送验证码'),
    start,
  }
}
