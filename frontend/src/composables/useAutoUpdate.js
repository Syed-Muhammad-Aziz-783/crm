import { onMounted, onBeforeUnmount } from 'vue'

/**
 * Royal: when a new version of the CRM screen is deployed, every open copy
 * picks it up by itself (quietly, when the user is not typing), so nobody
 * has to refresh after we change something.
 */
const MAIN_JS = /src="([^"]*\/index-[^"]+\.js)"/

export function useAutoUpdate(checkEverySeconds = 90) {
  let timer = null
  let busy = false

  const current = () =>
    document
      .querySelector('script[type="module"][src*="/index-"]')
      ?.getAttribute('src')

  const typing = () => {
    const a = document.activeElement
    return (
      !!a &&
      (['INPUT', 'TEXTAREA', 'SELECT'].includes(a.tagName) ||
        a.isContentEditable)
    )
  }

  async function check() {
    if (busy || document.visibilityState !== 'visible') return
    const mine = current()
    if (!mine) return
    busy = true
    try {
      const res = await fetch('/crm', {
        cache: 'no-store',
        credentials: 'same-origin',
      })
      if (!res.ok) return
      const latest = (await res.text()).match(MAIN_JS)?.[1]
      let tried = null
      try {
        tried = sessionStorage.getItem('royal_update_target')
      } catch (e) {}
      // reload at most once per new version (no endless reload if a cache holds the old one)
      if (latest && latest !== mine && latest !== tried && !typing()) {
        try {
          sessionStorage.setItem('royal_update_target', latest)
        } catch (e) {}
        try {
          const regs = (await navigator.serviceWorker?.getRegistrations?.()) || []
          await Promise.all(regs.map((r) => r.update()))
        } catch (e) {}
        window.location.reload()
      }
    } catch (e) {
      // server restarting during an update: try again next time
    } finally {
      busy = false
    }
  }

  const onVisible = () => {
    if (document.visibilityState === 'visible') check()
  }

  onMounted(() => {
    timer = setInterval(check, checkEverySeconds * 1000)
    document.addEventListener('visibilitychange', onVisible)
  })
  onBeforeUnmount(() => {
    clearInterval(timer)
    document.removeEventListener('visibilitychange', onVisible)
  })
}
