// Royal: Odoo-style due colors, one place for Tasks and for the Open Tasks column
// in Leads / Deals.  Red = passed, yellow = today, green = future.
// Done / cancelled tasks get no color.
const pad = (n) => String(n).padStart(2, '0')

export function dueKind(due, status) {
  if (!due || status === 'Done' || status === 'Canceled') return ''
  const t = new Date()
  const today = `${t.getFullYear()}-${pad(t.getMonth() + 1)}-${pad(t.getDate())}`
  const day = String(due).slice(0, 10)
  if (day < today) return 'overdue'
  if (day === today) return 'today'
  return 'future'
}

const STYLES = {
  overdue: { backgroundColor: '#dc2626', color: '#ffffff' },
  today: { backgroundColor: '#facc15', color: '#1f2937' },
  future: { backgroundColor: '#16a34a', color: '#ffffff' },
}

export function dueStyle(due, status) {
  return STYLES[dueKind(due, status)] || {}
}
