import { onMounted, onBeforeUnmount } from 'vue'
import { useDebounceFn } from '@vueuse/core'
import { globalStore } from '@/stores/global'

/**
 * Royal: live sync. Runs onChange (a quiet re-fetch, never a page refresh) when
 *  1. the server says one of these doctypes changed (Frappe realtime "list_update"),
 *  2. the user comes back to the app / tab (phones), or
 *  3. every pollSeconds as a safety net if the realtime connection is down.
 * It waits while the user is typing so nothing they are writing is overwritten.
 */
export function useLiveSync(
  doctypes,
  onChange,
  { pollSeconds = 0, skipWhenTyping = false } = {},
) {
  const { $socket } = globalStore()
  let pending = false
  let pollTimer = null
  let retryTimer = null

  const typing = () => {
    const a = document.activeElement
    return (
      !!a &&
      (['INPUT', 'TEXTAREA', 'SELECT'].includes(a.tagName) ||
        a.isContentEditable)
    )
  }

  const fire = useDebounceFn(() => {
    if (document.visibilityState === 'hidden') {
      pending = true
      return
    }
    if (skipWhenTyping && typing()) {
      pending = true
      return
    }
    pending = false
    try {
      onChange()
    } catch (e) {
      console.error('live sync', e)
    }
  }, 400)

  function onUpdate(data) {
    if (!data?.doctype || doctypes.includes(data.doctype)) fire()
  }
  function onVisible() {
    if (document.visibilityState === 'visible') fire()
  }

  onMounted(() => {
    doctypes.forEach((dt) => $socket?.emit('doctype_subscribe', dt))
    $socket?.on('list_update', onUpdate)
    document.addEventListener('visibilitychange', onVisible)
    window.addEventListener('focus', onVisible)
    if (pollSeconds) {
      pollTimer = setInterval(() => {
        if (document.visibilityState === 'visible') fire()
      }, pollSeconds * 1000)
    }
    retryTimer = setInterval(() => {
      if (pending) fire()
    }, 2000)
  })

  onBeforeUnmount(() => {
    doctypes.forEach((dt) => $socket?.emit('doctype_unsubscribe', dt))
    $socket?.off('list_update', onUpdate)
    document.removeEventListener('visibilitychange', onVisible)
    window.removeEventListener('focus', onVisible)
    clearInterval(pollTimer)
    clearInterval(retryTimer)
  })
}
