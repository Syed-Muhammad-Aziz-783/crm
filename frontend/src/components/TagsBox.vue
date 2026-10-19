<template>
  <!-- Royal: tags for a record. Uses Frappe's own tag API, so it is the same data as the desk "Tags". -->
  <div class="flex flex-wrap items-center gap-1.5 border-b px-3 py-2.5 sm:px-5">
    <span
      v-for="tag in tags"
      :key="tag"
      class="inline-flex max-w-full items-center gap-1 rounded-full bg-surface-gray-3 px-2.5 py-1 text-sm text-ink-gray-8"
    >
      <span class="truncate">{{ tag }}</span>
      <button
        type="button"
        class="rounded-full px-0.5 text-ink-gray-5 hover:text-ink-gray-9"
        :aria-label="__('Remove tag')"
        @click="removeTag(tag)"
      >
        &times;
      </button>
    </span>
    <div v-if="adding" class="relative">
      <input
        ref="inputRef"
        v-model="text"
        type="text"
        maxlength="60"
        :placeholder="__('Type a tag, press Enter')"
        class="h-7 w-44 rounded border border-outline-gray-2 bg-surface-white px-2 text-base text-ink-gray-9 focus:outline-none focus:ring-1 focus:ring-outline-gray-4"
        @input="onInput"
        @keydown.enter.prevent="addTag(text)"
        @keydown.esc.prevent="closeInput"
        @blur="onBlur"
      />
      <div
        v-if="suggestions.length"
        class="absolute left-0 top-8 z-20 max-h-48 w-44 overflow-auto rounded border bg-surface-white p-1 shadow-lg"
      >
        <button
          v-for="s in suggestions"
          :key="s"
          type="button"
          class="block w-full truncate rounded px-2 py-1.5 text-left text-base text-ink-gray-8 hover:bg-surface-gray-2"
          @mousedown.prevent="addTag(s)"
        >
          {{ s }}
        </button>
      </div>
    </div>
    <button
      v-else
      type="button"
      class="inline-flex items-center gap-1 rounded-full border border-dashed border-outline-gray-3 px-2.5 py-1 text-sm text-ink-gray-6 hover:bg-surface-gray-2"
      @click="openInput"
    >
      + {{ __('Add tag') }}
    </button>
  </div>
</template>

<script setup>
import { ref, nextTick, watch } from 'vue'
import { call, toast } from 'frappe-ui'
import { useDebounceFn } from '@vueuse/core'
import { useLiveSync } from '@/composables/useLiveSync'

const props = defineProps({
  doctype: { type: String, required: true },
  docname: { type: [String, Number], required: true },
})

const tags = ref([])
const adding = ref(false)
const text = ref('')
const suggestions = ref([])
const inputRef = ref(null)

function parse(value) {
  return (value || '')
    .split(',')
    .map((t) => t.trim())
    .filter(Boolean)
}

async function load() {
  try {
    const rows = await call('frappe.client.get_list', {
      doctype: props.doctype,
      fields: ['name', '_user_tags'],
      filters: { name: props.docname },
      limit_page_length: 1,
    })
    tags.value = parse(rows?.[0]?._user_tags)
  } catch (e) {
    // the tag column is created on the first tag, so a miss just means "no tags"
    tags.value = []
  }
}

function clean(raw) {
  return (raw || '').replace(/[,#]/g, ' ').replace(/\s+/g, ' ').trim()
}

async function addTag(raw) {
  const tag = clean(raw)
  if (!tag) return
  if (tags.value.some((t) => t.toLowerCase() === tag.toLowerCase())) {
    text.value = ''
    suggestions.value = []
    return
  }
  const before = [...tags.value]
  tags.value = [...tags.value, tag]
  text.value = ''
  suggestions.value = []
  try {
    await call('frappe.desk.doctype.tag.tag.add_tag', {
      tag,
      dt: props.doctype,
      dn: String(props.docname),
    })
  } catch (e) {
    tags.value = before
    toast.error(e?.messages?.[0] || __('Could not add the tag'))
  }
  nextTick(() => inputRef.value?.focus())
}

async function removeTag(tag) {
  const before = [...tags.value]
  tags.value = tags.value.filter((t) => t !== tag)
  try {
    await call('frappe.desk.doctype.tag.tag.remove_tag', {
      tag,
      dt: props.doctype,
      dn: String(props.docname),
    })
  } catch (e) {
    tags.value = before
    toast.error(e?.messages?.[0] || __('Could not remove the tag'))
  }
}

const fetchSuggestions = useDebounceFn(async () => {
  try {
    const list = await call('frappe.desk.doctype.tag.tag.get_tags', {
      doctype: props.doctype,
      txt: clean(text.value),
    })
    suggestions.value = (list || [])
      .filter((s) => !tags.value.some((t) => t.toLowerCase() === s.toLowerCase()))
      .slice(0, 8)
  } catch (e) {
    suggestions.value = []
  }
}, 250)

function onInput() {
  fetchSuggestions()
}

function openInput() {
  adding.value = true
  fetchSuggestions()
  nextTick(() => inputRef.value?.focus())
}

function closeInput() {
  adding.value = false
  text.value = ''
  suggestions.value = []
}

function onBlur() {
  // short delay so a tap on a suggestion is not lost
  setTimeout(() => {
    if (document.activeElement !== inputRef.value) closeInput()
  }, 150)
}

watch(() => props.docname, load, { immediate: true })

// Tag changes do not bump "modified", so re-read when the user comes back and every 60 s.
useLiveSync([props.doctype], load, { pollSeconds: 60, skipWhenTyping: true })
</script>
