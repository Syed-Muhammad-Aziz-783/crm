// Royal: a column with a bad width (for example "20" typed in the Columns
// popover, or "undefined") makes the whole list grid invalid, and every cell
// stacks into one column. Fix such widths before the list is drawn.
const VALID = /^\d+(\.\d+)?(px|rem|em|%|fr|vw)$/

export function sanitizeColumnWidths(columns) {
  if (!Array.isArray(columns)) return columns
  return columns.map((col) => {
    const w = col?.width
    if (w === undefined || w === null || w === '') return col
    if (typeof w === 'number' && Number.isFinite(w) && w > 0) return col
    const s = String(w).trim()
    if (VALID.test(s)) return col
    if (/^\d+(\.\d+)?$/.test(s) && Number(s) > 0) {
      return { ...col, width: Number(s) }
    }
    return { ...col, width: '10rem' }
  })
}
