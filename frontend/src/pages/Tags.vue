<template>
  <LayoutHeader>
    <template #left-header>
      <Breadcrumbs :items="[{ label: __('Tags'), route: { name: 'Tags' } }]" />
    </template>
  </LayoutHeader>
  <div class="mx-auto w-full max-w-3xl overflow-auto px-4 py-5 sm:px-6">
    <div class="mb-5 rounded-lg border p-3">
      <div class="mb-2 text-base font-medium text-ink-gray-9">
        {{ __('New tag') }}
      </div>
      <div class="flex flex-wrap items-center gap-2">
        <input
          v-model="newName"
          type="text"
          maxlength="60"
          :placeholder="__('Tag name')"
          class="h-8 min-w-0 flex-1 rounded border border-outline-gray-2 bg-surface-white px-2 text-base text-ink-gray-9 focus:outline-none focus:ring-1 focus:ring-outline-gray-4"
          @keydown.enter.prevent="createTag"
        />
        <div class="flex gap-1.5">
          <button
            v-for="c in TAG_COLORS"
            :key="c.name"
            type="button"
            class="h-6 w-6 rounded-full border-2"
            :class="[c.dot, newColor === c.name ? 'border-ink-gray-9' : 'border-transparent']"
            :aria-label="c.name"
            @click="newColor = c.name"
          />
        </div>
        <Button variant="solid" :label="__('Create')" :loading="saving" @click="createTag" />
      </div>
    </div>

    <div v-if="!allTags.length" class="py-10 text-center text-base text-ink-gray-5">
      {{ __('No tags yet. Create your first tag above.') }}
    </div>
    <div v-for="tag in allTags" :key="tag" class="flex flex-wrap items-center gap-3 border-b py-3">
      <span class="rounded-full px-2.5 py-1 text-sm" :class="colorOf(tag).chip">{{ tag }}</span>
      <span class="text-sm text-ink-gray-5">
        {{ counts[tag] || 0 }} {{ __('records') }}
      </span>
      <div class="ml-auto flex items-center gap-1.5">
        <button
          v-for="c in TAG_COLORS"
          :key="c.name"
          type="button"
          class="h-5 w-5 rounded-full border-2"
          :class="[c.dot, colorOf(tag).name === c.name ? 'border-ink-gray-9' : 'border-transparent']"
          :aria-label="c.name"
          @click="changeColor(tag, c.name)"
        />
        <Button
          variant="ghost"
          theme="red"
          icon="lucide-trash-2"
          :aria-label="__('Delete tag')"
          @click="removeTag(tag)"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { Breadcrumbs, Button, call, toast } from 'frappe-ui'
import LayoutHeader from '@/components/LayoutHeader.vue'
import { useLiveSync } from '@/composables/useLiveSync'
import {
  TAG_COLORS,
  allTags,
  colorOf,
  loadTags,
  setTagColor,
} from '@/utils/tagColors'

const newName = ref('')
const newColor = ref('blue')
const saving = ref(false)
const counts = ref({})

async function loadCounts() {
  try {
    counts.value = (await call('crm.api.tags.get_tag_counts')) || {}
  } catch (e) {
    counts.value = {}
  }
}

async function createTag() {
  const name = newName.value.replace(/[,#]/g, ' ').replace(/\s+/g, ' ').trim()
  if (!name) return
  if (allTags.value.some((t) => t.toLowerCase() === name.toLowerCase())) {
    toast.error(__('This tag already exists'))
    return
  }
  saving.value = true
  try {
    await setTagColor(name, newColor.value)
    newName.value = ''
    toast.success(__('Tag created'))
  } catch (e) {
    toast.error(e?.messages?.[0] || __('Could not create the tag'))
    loadTags(true)
  }
  saving.value = false
}

async function changeColor(tag, color) {
  try {
    await setTagColor(tag, color)
  } catch (e) {
    toast.error(e?.messages?.[0] || __('Could not change the color'))
    loadTags(true)
  }
}

async function removeTag(tag) {
  if (!window.confirm(__('Delete the tag "{0}" and remove it from all records?', [tag]))) return
  try {
    await call('crm.api.tags.delete_tag', { tag })
    await loadTags(true)
    loadCounts()
    toast.success(__('Tag deleted'))
  } catch (e) {
    toast.error(e?.messages?.[0] || __('Only a manager can delete tags'))
  }
}

onMounted(() => {
  loadTags(true)
  loadCounts()
})

useLiveSync([], () => {
  loadTags(true)
  loadCounts()
}, { pollSeconds: 60, skipWhenTyping: true })
</script>
