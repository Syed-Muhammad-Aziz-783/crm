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
          class="h-8 w-full min-w-0 rounded-md sm:w-auto sm:flex-1 bg-surface-gray-2 px-2.5 text-base text-ink-gray-9 placeholder:text-ink-gray-4 focus:bg-surface-gray-3 focus:outline-none"
          @keydown.enter.prevent="createTag"
        />
        <div class="flex flex-wrap gap-2">
          <button
            v-for="c in TAG_COLORS"
            :key="c.name"
            type="button"
            class="h-6 w-6 rounded-full"
            :style="swatchStyle(c, newColor === c.name)"
            :aria-label="c.name"
            @click="newColor = c.name"
          />
        </div>
        <Button
          variant="solid"
          :label="__('Create')"
          :loading="saving"
          @click="createTag"
        />
      </div>
    </div>

    <div
      v-if="!allTags.length"
      class="py-10 text-center text-base text-ink-gray-5"
    >
      {{ __('No tags yet. Create your first tag above.') }}
    </div>
    <div v-for="tag in allTags" :key="tag" class="border-b py-3">
      <div class="flex items-center gap-3">
        <template v-if="editing === tag">
          <input
            v-model="editName"
            type="text"
            maxlength="60"
            class="h-8 min-w-0 flex-1 rounded-md bg-surface-gray-2 px-2.5 text-base text-ink-gray-9 focus:bg-surface-gray-3 focus:outline-none"
            @keydown.enter.prevent="saveRename(tag)"
            @keydown.esc.prevent="editing = null"
          />
          <Button
            variant="solid"
            :label="__('Save')"
            :loading="renaming"
            @click="saveRename(tag)"
          />
          <Button
            variant="subtle"
            :label="__('Cancel')"
            @click="editing = null"
          />
        </template>
        <template v-else>
          <span
            class="min-w-0 truncate rounded-full px-2.5 py-1 text-sm"
            :style="chipStyle(tag)"
            >{{ tag }}</span
          >
          <span class="shrink-0 text-sm text-ink-gray-5">
            {{ counts[tag] || 0 }} {{ __('records') }}
          </span>
          <Button
            class="ml-auto shrink-0"
            variant="ghost"
            icon="lucide-pencil"
            :aria-label="__('Edit tag')"
            @click="startRename(tag)"
          />
        </template>
        <Button
          class="shrink-0"
          variant="ghost"
          theme="red"
          icon="lucide-trash-2"
          :aria-label="__('Delete tag')"
          @click="removeTag(tag)"
        />
      </div>
      <div class="mt-2.5 flex flex-wrap gap-2">
        <button
          v-for="c in TAG_COLORS"
          :key="c.name"
          type="button"
          class="h-6 w-6 rounded-full"
          :style="swatchStyle(c, colorOf(tag).name === c.name)"
          :aria-label="c.name"
          @click="changeColor(tag, c.name)"
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
  chipStyle,
  colorOf,
  loadTags,
  setTagColor,
  swatchStyle,
} from '@/utils/tagColors'

const newName = ref('')
const newColor = ref('blue')
const saving = ref(false)
const counts = ref({})
const editing = ref(null)
const editName = ref('')
const renaming = ref(false)

function startRename(tag) {
  editing.value = tag
  editName.value = tag
}

async function saveRename(tag) {
  const name = editName.value.replace(/[,#]/g, ' ').replace(/\s+/g, ' ').trim()
  if (!name) return
  if (name === tag) {
    editing.value = null
    return
  }
  if (
    allTags.value.some(
      (t) => t !== tag && t.toLowerCase() === name.toLowerCase(),
    )
  ) {
    toast.error(__('This tag already exists'))
    return
  }
  renaming.value = true
  try {
    await call('crm.api.tags.rename_tag', { old: tag, new: name })
    editing.value = null
    await loadTags(true)
    loadCounts()
    toast.success(__('Tag renamed'))
  } catch (e) {
    toast.error(e?.messages?.[0] || __('Only a manager can rename tags'))
    loadTags(true)
  }
  renaming.value = false
}

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
  if (
    !window.confirm(
      __('Delete the tag "{0}" and remove it from all records?', [tag]),
    )
  )
    return
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

useLiveSync(
  [],
  () => {
    loadTags(true)
    loadCounts()
  },
  { pollSeconds: 60, skipWhenTyping: true },
)
</script>
