<template>
  <!-- Royal: tags with colors. Saved records use Frappe's own tag API (same data as the desk "Tags");
       on a create form (no docname) it only collects tags and the form saves them after the record is created. -->
  <div
    class="flex flex-wrap items-center gap-1.5"
    :class="bare ? 'py-1' : 'border-b px-3 py-2.5 sm:px-5'"
  >
    <span v-if="bare" class="mr-1 text-sm text-ink-gray-5">{{ __('Tags') }}</span>
    <span
      v-for="tag in tags"
      :key="tag"
      class="relative inline-flex max-w-full items-center gap-1 rounded-full px-2.5 py-1 text-sm"
      :class="colorOf(tag).chip"
    >
      <button
        type="button"
        class="truncate"
        :title="__('Change color')"
        @click="pickerFor = pickerFor === tag ? null : tag"
      >
        {{ tag }}
      </button>
      <button
        type="button"
        class="rounded-full px-0.5 opacity-60 hover:opacity-100"
        :aria-label="__('Remove tag')"
        @click="removeTag(tag)"
      >
        &times;
      </button>
      <div
        v-if="pickerFor === tag"
        class="absolute left-0 top-8 z-30 flex w-max gap-1.5 rounded border bg-surface-white p-2 shadow-lg"
      >
        <button
          v-for="c in TAG_COLORS"
          :key="c.name"
          type="button"
          class="h-6 w-6 rounded-full border-2"
          :class="[c.dot, colorOf(tag).name === c.name ? 'border-ink-gray-9' : 'border-transparent']"
          :aria-label="c.name"
          @click="chooseColor(tag, c.name)"
        />
      </div>
    </span>
    <div v-if="adding" class="relative">
      <input
        ref="inputRef"
        v-model="text"
        type="text"
        maxlength="60"
        :placeholder="__('Type a tag, press Enter')"
        class="h-7 w-44 rounded border border-outline-gray-2 bg-surface-white px-2 text-base text-ink-gray-9 focus:outline-none focus:ring-1 focus:ring-outline-gray-4"
        @keydown.enter.prevent="addTag(text)"
        @keydown.esc.prevent="closeInput"
        @blur="onBlur"
      />
      <div
        v-if="suggestions.length"
        class="absolute left-0 top-8 z-30 max-h-48 w-44 overflow-auto rounded border bg-surface-white p-1 shadow-lg"
      >
        <button
          v-for="s in suggestions"
          :key="s"
          type="button"
          class="flex w-full items-center gap-2 truncate rounded px-2 py-1.5 text-left text-base text-ink-gray-8 hover:bg-surface-gray-2"
          @mousedown.prevent="addTag(s)"
        >
          <span class="h-2.5 w-2.5 shrink-0 rounded-full" :class="colorOf(s).dot" />
          <span class="truncate">{{ s }}</span>
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
import { ref, computed, nextTick, watch } from 'vue'
import { call, toast } from 'frappe-ui'
import { useLiveSync } from '@/composables/useLiveSync'
import {
  TAG_COLORS,
  allTags,
  colorOf,
  loadTags,
  parseTags,
  setTagColor,
} from '@/utils/tagColors'

const props = defineProps({
  doctype: { type: String, required: true },
  docname: { type: [String, Number], default: '' },
  modelValue: { type: Array, default: () => [] }, // create form only
  bare: { type: Boolean, default: false },
})
const emit = defineEmits(['update:modelValue'])

const local = computed(() => !props.docname)
const tags = ref(local.value ? [...props.modelValue] : [])
const adding = ref(false)
const text = ref('')
const inputRef = ref(null)
const pickerFor = ref(null)

const suggestions = computed(() => {
  const q = clean(text.value).toLowerCase()
  return allTags.value
    .filter((s) => !tags.value.some((t) => t.toLowerCase() === s.toLowerCase()))
    .filter((s) => !q || s.toLowerCase().includes(q))
    .slice(0, 8)
})

function clean(raw) {
  return (raw || '').replace(/[,#]/g, ' ').replace(/\s+/g, ' ').trim()
}

async function load() {
  if (local.value) return
  try {
    const rows = await call('frappe.client.get_list', {
      doctype: props.doctype,
      fields: ['name', '_user_tags'],
      filters: { name: props.docname },
      limit_page_length: 1,
    })
    tags.value = parseTags(rows?.[0]?._user_tags)
  } catch (e) {
    // the tag column is created on the first tag, so a miss just means "no tags"
    tags.value = []
  }
}

async function addTag(raw) {
  const tag = clean(raw)
  if (!tag) return
  // reuse the existing spelling if the tag already exists in another case
  const known = allTags.value.find((s) => s.toLowerCase() === tag.toLowerCase())
  const name = known || tag
  text.value = ''
  if (tags.value.some((t) => t.toLowerCase() === name.toLowerCase())) return
  const before = [...tags.value]
  tags.value = [...tags.value, name]
  if (local.value) {
    emit('update:modelValue', tags.value)
    if (!known) setTagColor(name, colorOf(name).name).catch(() => {})
  } else {
    try {
      await call('frappe.desk.doctype.tag.tag.add_tag', {
        tag: name,
        dt: props.doctype,
        dn: String(props.docname),
      })
      if (!known) {
        await setTagColor(name, colorOf(name).name).catch(() => {})
      }
    } catch (e) {
      tags.value = before
      toast.error(e?.messages?.[0] || __('Could not add the tag'))
    }
  }
  nextTick(() => inputRef.value?.focus())
}

async function removeTag(tag) {
  const before = [...tags.value]
  tags.value = tags.value.filter((t) => t !== tag)
  pickerFor.value = null
  if (local.value) {
    emit('update:modelValue', tags.value)
    return
  }
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

async function chooseColor(tag, color) {
  pickerFor.value = null
  try {
    await setTagColor(tag, color)
  } catch (e) {
    toast.error(e?.messages?.[0] || __('Could not change the color'))
    loadTags(true)
  }
}

function openInput() {
  adding.value = true
  nextTick(() => inputRef.value?.focus())
}

function closeInput() {
  adding.value = false
  text.value = ''
}

function onBlur() {
  // short delay so a tap on a suggestion is not lost
  setTimeout(() => {
    if (document.activeElement !== inputRef.value) closeInput()
  }, 150)
}

watch(() => props.docname, load, { immediate: true })
loadTags()

// Tag changes do not bump "modified", so re-read when the user comes back and every 60 s.
if (!local.value) {
  useLiveSync(
    [props.doctype],
    () => {
      load()
      loadTags(true)
    },
    { pollSeconds: 60, skipWhenTyping: true },
  )
}
</script>
