import { onBeforeUnmount, watch, type Ref } from 'vue'

export function useAutoDismiss(messages: Ref<string>[], delay = 4000) {
  const timers = new Map<Ref<string>, ReturnType<typeof setTimeout>>()

  messages.forEach((message) => {
    watch(message, (value) => {
      const previousTimer = timers.get(message)
      if (previousTimer) clearTimeout(previousTimer)
      if (!value) return

      const timer = setTimeout(() => {
        message.value = ''
        timers.delete(message)
      }, delay)
      timers.set(message, timer)
    })
  })

  onBeforeUnmount(() => {
    timers.forEach((timer) => clearTimeout(timer))
    timers.clear()
  })
}
