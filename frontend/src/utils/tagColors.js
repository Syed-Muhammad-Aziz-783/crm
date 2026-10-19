import { ref } from 'vue'
import { call } from 'frappe-ui'

// Royal: tag colors (like Odoo). Full class strings so Tailwind keeps them.
export const TAG_COLORS = [
  { name: 'gray', chip: 'bg-gray-200 text-gray-800', dot: 'bg-gray-500' },
  { name: 'red', chip: 'bg-red-100 text-red-800', dot: 'bg-red-500' },
  { name: 'orange', chip: 'bg-orange-100 text-orange-800', dot: 'bg-orange-500' },
  { name: 'amber', chip: 'bg-amber-100 text-amber-800', dot: 'bg-amber-500' },
  { name: 'green', chip: 'bg-green-100 text-green-800', dot: 'bg-green-500' },
  { name: 'teal', chip: 'bg-teal-100 text-teal-800', dot: 'bg-teal-500' },
  { name: 'blue', chip: 'bg-blue-100 text-blue-800', dot: 'bg-blue-500' },
  { name: 'purple', chip: 'bg-purple-100 text-purple-800', dot: 'bg-purple-500' },
  { name: 'pink', chip: 'bg-pink-100 text-pink-800', dot: 'bg-pink-500' },
  { name: 'brown', chip: 'bg-stone-200 text-stone-800', dot: 'bg-stone-500' },
]

// all known tags -> color name ('' = not chosen yet)
export const tagColorMap = ref({})
export const allTags = ref([])
let loading = null

export function loadTags(force = false) {
  if (loading && !force) return loading
  loading = call('crm.api.tags.get_all_tags')
    .then((rows) => {
      const map = {}
      for (const r of rows || []) map[r.name] = r.color || ''
      tagColorMap.value = map
      allTags.value = (rows || []).map((r) => r.name)
    })
    .catch(() => {})
  return loading
}

function hash(str) {
  let h = 0
  for (let i = 0; i < str.length; i++) h = (h * 31 + str.charCodeAt(i)) >>> 0
  return h
}

// chosen color, else a steady color picked from the name (never gray, so tags stand out)
export function colorOf(tag) {
  const chosen = tagColorMap.value[tag]
  if (chosen) return TAG_COLORS.find((c) => c.name === chosen) || TAG_COLORS[1]
  return TAG_COLORS[1 + (hash(tag || '') % (TAG_COLORS.length - 1))]
}

export async function setTagColor(tag, color) {
  tagColorMap.value = { ...tagColorMap.value, [tag]: color }
  if (!allTags.value.includes(tag)) allTags.value = [...allTags.value, tag]
  await call('crm.api.tags.set_tag_color', { tag, color })
}

export function parseTags(value) {
  return String(value?.label ?? value ?? '')
    .split(',')
    .map((t) => t.trim())
    .filter(Boolean)
}

// used right after a record is created
export async function saveTagsToDoc(doctype, name, tags) {
  if (!tags?.length) return
  try {
    const colors = {}
    for (const t of tags) colors[t] = colorOf(t).name
    await call('crm.api.tags.add_tags_to_doc', { doctype, name, tags, colors })
  } catch (e) {
    // the record is already saved; the tags can be added on its page
  }
}
