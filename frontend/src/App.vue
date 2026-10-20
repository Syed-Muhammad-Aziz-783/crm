<template>
  <FrappeUIProvider>
    <NotPermitted v-if="$route.name === 'Not Permitted'" />
    <router-view v-else-if="$route.name === 'Onboarding'" />
    <Layout v-else-if="session.isLoggedIn" class="isolate">
      <router-view :key="$route.fullPath" />
    </Layout>
    <Dialogs />
    <DoctypeModals />
  </FrappeUIProvider>
</template>

<script setup>
import NotPermitted from '@/pages/NotPermitted.vue'
import DoctypeModals from '@/components/Modals/DoctypeModals.vue'
import { Dialogs } from '@/utils/dialogs'
import { sessionStore } from '@/stores/session'
import { useAutoUpdate } from '@/composables/useAutoUpdate'
import { FrappeUIProvider, setConfig, useColorScheme } from 'frappe-ui'
import { computed, defineAsyncComponent, provide } from 'vue'

useAutoUpdate()

const session = sessionStore()
provide('session', session)

// Royal: the app shows what the user chose (light or dark) and never follows the
// phone / computer setting. frappe-ui starts in "system" when nothing is saved, which
// turned the app dark on iPhones at night, so "system" is changed to light here.
const { colorScheme, setColorScheme } = useColorScheme()
if (colorScheme.value === 'system') {
  setColorScheme('light')
}

const MobileLayout = defineAsyncComponent(
  () => import('./components/Layouts/MobileLayout.vue'),
)
const DesktopLayout = defineAsyncComponent(
  () => import('./components/Layouts/DesktopLayout.vue'),
)
const Layout = computed(() => {
  if (window.innerWidth < 640) {
    return MobileLayout
  } else {
    return DesktopLayout
  }
})

setConfig('systemTimezone', window.timezone?.system || null)
setConfig('localTimezone', window.timezone?.user || null)
setConfig('translatedMessages', window.translated_messages || {})
</script>
