// Royal: a column with a bad width (for example "20" typed in the Columns
// popover, or "undefined") makes the whole list grid invalid, and every cell
// stacks into one column. Fix such widths before the list is drawn.
//
// Royal: the Tags column is also made wide enough for the row with the most tags
// (pass the raw list rows as 2nd argument), so every tag stays on one line and the
// heading stays centered over them. A wider width saved by the user is kept.
import { tagsColumnWidth } from '@/utils/tagColors'

const VALID = /^\d+(\.\d+)?(px|rem|em|%|fr|vw)$/

function fixWidth(col) {
  const w = col?.width
  if (w === undefined || w === null || w === '') return col
  if (typeof w === 'number' && Number.isFinite(w) && w > 0) return col
  const s = String(w).trim()
  if (VALID.test(s)) return col
  if (/^\d+(\.\d+)?$/.test(s) && Number(s) > 0) {
    return { ...col, width: Number(s) }
  }
  return { ...col, width: '10rem' }
}

function widthInPx(w) {
  if (typeof w !== 'string') return 0
  const n = parseFloat(w)
  if (!Number.isFinite(n)) return 0
  if (w.endsWith('rem')) return n * 16
  if (w.endsWith('px')) return n
  return 0
}

export function sanitizeColumnWidths(columns, rows) {
  if (!Array.isArray(columns)) return columns
  return columns.map((col) => {
    const fixed = fixWidth(col)
    if (fixed?.key !== '_user_tags') return fixed
    const need = tagsColumnWidth(rows)
    const have = widthInPx(fixed.width)
    return { ...fixed, width: `${Math.max(need, have, 112)}px` }
  })
}
