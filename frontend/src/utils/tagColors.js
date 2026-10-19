import { ref } from 'vue'
import { call } from 'frappe-ui'

// Royal: tag colors (like Odoo). Plain hex values (not Tailwind classes) so they always show,
// whatever the Tailwind palette of the app contains.
export const TAG_COLORS = [
  { name: 'gray', bg: '#e5e7eb', fg: '#374151', dot: '#6b7280' },
  { name: 'red', bg: '#fee2e2', fg: '#991b1b', dot: '#ef4444' },
  { name: 'orange', bg: '#ffedd5', fg: '#9a3412', dot: '#f97316' },
  { name: 'amber', bg: '#fef3c7', fg: '#92400e', dot: '#f59e0b' },
  { name: 'green', bg: '#dcfce7', fg: '#166534', dot: '#22c55e' },
  { name: 'teal', bg: '#ccfbf1', fg: '#115e59', dot: '#14b8a6' },
  { name: 'blue', bg: '#dbeafe', fg: '#1e40af', dot: '#3b82f6' },
  { name: 'purple', bg: '#f3e8ff', fg: '#6b21a8', dot: '#a855f7' },
  { name: 'pink', bg: '#fce7f3', fg: '#9d174d', dot: '#ec4899' },
  { name: 'brown', bg: '#e7e5e4', fg: '#44403c', dot: '#78716c' },
]

export const chipStyle = (tag) => {
  const c = colorOf(tag)
  return { background: c.bg, color: c.fg }
}

export const swatchStyle = (c, selected) => ({
  background: c.dot,
  boxShadow: selected ? '0 0 0 2px #fff, 0 0 0 4px #1f2937' : 'none',
})

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
