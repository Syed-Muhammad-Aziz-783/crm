import { isMobileView } from '@/composables/settings'

// Royal: on phones a list with many columns forces sideways scrolling.
// Show only a few columns and size them to the screen width instead.
// Desktop is untouched (columns come back unchanged).
export function fitColumnsForMobile(columns, preferredKeys = [], count = 3) {
  if (!isMobileView.value || !columns?.length) return columns

  let picked = []
  for (const key of preferredKeys) {
    const col = columns.find((c) => c.key === key)
    if (col) picked.push(col)
  }
  for (const col of columns) {
    if (picked.length >= count) break
    if (!picked.includes(col)) picked.push(col)
  }
  picked = picked.slice(0, count)

  // screen width minus page margin, checkbox column and column gaps (about 120px)
  const usable = Math.max(window.innerWidth - 120, 200)
  const weights = [0.4, 0.3, 0.3]
  return picked.map((col, i) => ({
    ...col,
    width: `${Math.floor(((usable * (weights[i] ?? 0.3)) / 16) * 10) / 10}rem`,
    align: i === picked.length - 1 ? 'right' : col.align,
  }))
}
