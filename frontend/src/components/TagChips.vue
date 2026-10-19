<template>
  <!-- Royal: tags in a list cell. One line only: first tags + "+N", full list on hover. -->
  <div
    class="flex flex-nowrap items-center justify-center gap-1 overflow-hidden"
    :title="list.join(', ')"
  >
    <span
      v-for="t in shown"
      :key="t"
      class="max-w-[7rem] shrink-0 truncate whitespace-nowrap rounded-full px-2 py-0.5 text-sm"
      :style="chipStyle(t)"
      >{{ t }}</span
    >
    <span
      v-if="extra > 0"
      class="shrink-0 whitespace-nowrap rounded-full px-2 py-0.5 text-sm"
      style="background: #e5e7eb; color: #374151"
      >+{{ extra }}</span
    >
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { chipStyle, loadTags, parseTags } from '@/utils/tagColors'

const props = defineProps({
  value: { type: [String, Object], default: '' },
  max: { type: Number, default: 2 },
})
const list = computed(() => parseTags(props.value))
const shown = computed(() => list.value.slice(0, props.max))
const extra = computed(() => list.value.length - shown.value.length)
onMounted(() => loadTags())
</script>
