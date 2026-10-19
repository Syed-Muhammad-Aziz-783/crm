import { toast } from 'frappe-ui'

// Royal: copy text to the clipboard, with a fallback for browsers that block it
export async function copyText(text) {
  const value = String(text ?? '').trim()
  if (!value) return
  try {
    await navigator.clipboard.writeText(value)
  } catch {
    const el = window.document.createElement('textarea')
    el.value = value
    el.style.position = 'fixed'
    el.style.opacity = '0'
    window.document.body.appendChild(el)
    el.select()
    window.document.execCommand('copy')
    window.document.body.removeChild(el)
  }
  toast.success(__('Copied'))
}
