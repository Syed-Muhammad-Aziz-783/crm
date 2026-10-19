<template>
  <!-- Royal: Open Tasks number in Leads / Deals. The color comes from the due date of
       the last created open task: red = passed, yellow = today, green = future. -->
  <div
    class="flex min-w-[1.75rem] items-center justify-center rounded-full px-2 py-0.5 text-base"
    :class="colored ? 'font-medium' : ''"
    :style="style"
    :title="title"
  >
    {{ count }}
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { dueKind, dueStyle } from '@/utils/dueColor'
import { formatDate } from '@/utils'

const props = defineProps({
  count: { type: [String, Number], default: '' },
  due: { type: String, default: '' },
})

const open = computed(() => Number(props.count) > 0)
const colored = computed(() => open.value && !!dueKind(props.due))
const style = computed(() => (open.value ? dueStyle(props.due) : {}))
const title = computed(() => {
  if (!open.value || !props.due) return ''
  let when = props.due
  try {
    when = formatDate(props.due, 'ddd, D MMM YYYY, hh:mm a')
  } catch (e) {
    // a hover text must never break the list
  }
  return __('Last task due {0}', [when])
})
</script>
