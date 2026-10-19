<template>
  <!-- Royal: tags with colors. Saved records use crm.api.tags (same tags as the ERPNext desk);
       on a create form (no docname) it only collects tags and the form saves them after the record is created. -->
  <div
    ref="root"
    class="flex flex-wrap items-center gap-1.5"
    :class="bare ? 'py-1' : 'border-b px-3 py-2.5 sm:px-5'"
  >
    <LucideTag class="h-3.5 w-3.5 shrink-0 text-ink-gray-5" />
    <span
      v-if="!tags.length && !adding"
      class="text-sm text-ink-gray-5"
    >
      {{ __('No tags') }}
    </span>

    <span
      v-for="tag in tags"
      :key="tag"
      data-tag-chip
      class="relative inline-flex max-w-full items-center rounded-full text-sm"
      :style="chipStyle(tag)"
    >
      <button
        type="button"
        class="max-w-[12rem] truncate py-1 pl-2.5 pr-1"
        :title="__('Change color')"
        @click="togglePicker(tag, $event)"
      >
        {{ tag }}
      </button>
      <button
        type="button"
        class="rounded-full py-1 pl-0.5 pr-2 text-base leading-none opacity-60 hover:opacity-100"
        :aria-label="__('Remove tag')"
        @click="removeTag(tag)"
      >
        &times;
      </button>
      <div
        v-if="pickerFor === tag"
        data-tag-chip
        class="absolute top-full z-30 mt-1 grid w-44 grid-cols-5 gap-2 rounded-6 bg-surface-elevation-2 p-2.5 shadow-2xl ring-1 ring-black ring-opacity-5"
        :class="pickerAlign === 'right' ? 'right-0' : 'left-0'"
      >
        <button
          v-for="c in TAG_COLORS"
          :key="c.name"
          type="button"
          class="h-6 w-6 rounded-full"
          :style="swatchStyle(c, colorOf(tag).name === c.name)"
          :aria-label="c.name"
          @click="chooseColor(tag, c.name)"
        />
      </div>
    </span>

    <form
      v-if="adding"
      ref="formRef"
      class="relative flex items-center gap-1"
      @submit.prevent="addTag(text)"
    >
      <input
        ref="inputRef"
        v-model="text"
        type="text"
        maxlength="60"
        autocomplete="off"
        autocapitalize="words"
        enterkeyhint="done"
        :placeholder="__('Type a tag name')"
        class="h-7 w-40 rounded-md bg-surface-gray-2 px-2.5 text-base text-ink-gray-9 placeholder:text-ink-gray-4 focus:bg-surface-gray-3 focus:outline-none"
        @input="onInput"
        @keydown.esc.prevent="closeInput"
        @blur="onBlur"
      />
      <button
        type="submit"
        class="flex h-7 w-7 items-center justify-center rounded-md bg-surface-gray-9 text-white"
        :aria-label="__('Add tag')"
        @mousedown.prevent
      >
        <LucideCheck class="h-4 w-4" />
      </button>
      <div
        v-if="canCreate || suggestions.length"
        class="absolute left-0 z-30 max-h-56 w-60 overflow-auto rounded-6 bg-surface-elevation-2 p-1 shadow-2xl ring-1 ring-black ring-opacity-5"
        :class="openUp ? 'bottom-full mb-1' : 'top-full mt-1'"
      >
        <button
          v-if="canCreate"
          type="button"
          class="flex w-full items-center gap-2 rounded px-2 py-2 text-left text-base text-ink-gray-8 hover:bg-surface-gray-2"
          @mousedown.prevent="addTag(text)"
        >
          <span class="h-2.5 w-2.5 shrink-0 rounded-full" :style="{ background: colorOf(clean(text)).dot }" />
          <span class="truncate">{{ __('Create') }} "{{ clean(text) }}"</span>
        </button>
        <button
          v-for="s in suggestions"
          :key="s"
          type="button"
          class="flex w-full items-center gap-2 rounded px-2 py-2 text-left text-base text-ink-gray-8 hover:bg-surface-gray-2"
          @mousedown.prevent="addTag(s)"
        >
          <span class="h-2.5 w-2.5 shrink-0 rounded-full" :style="{ background: colorOf(s).dot }" />
          <span class="truncate">{{ s }}</span>
        </button>
      </div>
    </form>
    <button
      v-else
      type="button"
      class="inline-flex items-center gap-1 rounded-full bg-surface-gray-2 px-2.5 py-1 text-sm text-ink-gray-7 hover:bg-surface-gray-3"
      @click="openInput"
    >
      + {{ __('Add tag') }}
    </button>
  </div>
</template>

<script setup>
import { ref, computed, nextTick, watch, onMounted, onBeforeUnmount } from 'vue'
import { call, toast } from 'frappe-ui'
import LucideTag from '~icons/lucide/tag'
import LucideCheck from '~icons/lucide/check'
import { useLiveSync } from '@/composables/useLiveSync'
import {
  TAG_COLORS,
  allTags,
  chipStyle,
  colorOf,
  loadTags,
  swatchStyle,
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
const root = ref(null)
const formRef = ref(null)
const inputRef = ref(null)
const pickerFor = ref(null)
const pickerAlign = ref('left')
const openUp = ref(false)

function clean(raw) {
  return (raw || '').replace(/[,#]/g, ' ').replace(/\s+/g, ' ').trim()
}

const has = (list, tag) => list.some((t) => t.toLowerCase() === tag.toLowerCase())

const suggestions = computed(() => {
  const q = clean(text.value).toLowerCase()
  return allTags.value
    .filter((s) => !has(tags.value, s))
    .filter((s) => !q || s.toLowerCase().includes(q))
})

// offer "Create xyz" only when that exact tag does not exist yet
const canCreate = computed(() => {
  const q = clean(text.value)
  return !!q && !has(allTags.value, q) && !has(tags.value, q)
})

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
  text.value = ''
  if (!tag) return
  // reuse the existing spelling if the tag already exists in another case
  const known = allTags.value.find((s) => s.toLowerCase() === tag.toLowerCase())
  const name = known || tag
  if (has(tags.value, name)) return
  const before = [...tags.value]
  tags.value = [...tags.value, name]
  if (local.value) {
    emit('update:modelValue', tags.value)
  } else {
    try {
      await call('crm.api.tags.add_tag', {
        doctype: props.doctype,
        name: String(props.docname),
        tag: name,
        color: colorOf(name).name,
      })
      loadTags(true)
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
    await call('crm.api.tags.remove_tag', {
      doctype: props.doctype,
      name: String(props.docname),
      tag,
    })
  } catch (e) {
    tags.value = before
    toast.error(e?.messages?.[0] || __('Could not remove the tag'))
  }
}

function togglePicker(tag, event) {
  if (pickerFor.value === tag) {
    pickerFor.value = null
    return
  }
  const r = event.currentTarget.getBoundingClientRect()
  pickerAlign.value = r.left + 176 > window.innerWidth - 8 ? 'right' : 'left'
  pickerFor.value = tag
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
  pickerFor.value = null
  adding.value = true
  loadTags()
  nextTick(() => {
    inputRef.value?.focus()
    const r = formRef.value?.getBoundingClientRect()
    // open the list upward when there is little room below (end of a form, phone keyboard)
    openUp.value = !!r && window.innerHeight - r.bottom < 260 && r.top > 260
  })
}

// a comma ends the tag (works on phone keyboards too)
function onInput() {
  if (text.value.includes(',')) {
    const [first, ...rest] = text.value.split(',')
    addTag(first)
    text.value = rest.join(' ')
  }
}

function closeInput() {
  adding.value = false
  text.value = ''
}

function onBlur() {
  // short delay so a tap on a suggestion is not lost; typed text is kept as a tag, not thrown away
  setTimeout(() => {
    if (document.activeElement === inputRef.value) return
    if (clean(text.value)) addTag(text.value)
    closeInput()
  }, 150)
}

function onOutside(e) {
  if (pickerFor.value && !e.target.closest?.('[data-tag-chip]')) pickerFor.value = null
}

onMounted(() => document.addEventListener('pointerdown', onOutside))
onBeforeUnmount(() => document.removeEventListener('pointerdown', onOutside))

watch(() => props.docname, load, { immediate: true })
loadTags()

// Another device changed this record's tags (or the user came back to the tab): re-read quietly.
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
