<template>
  <!-- Royal: tags in a list cell. Every tag, one line, centered. The column is made
       wide enough for the widest row by sanitizeColumnWidths (see tagsColumnWidth). -->
  <div
    class="flex flex-nowrap items-center justify-center gap-1"
    :title="list.join(', ')"
  >
    <span
      v-for="t in list"
      :key="t"
      class="shrink-0 whitespace-nowrap rounded-full px-2 py-0.5 text-sm"
      :style="chipStyle(t)"
      >{{ t }}</span
    >
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { chipStyle, loadTags, parseTags } from '@/utils/tagColors'

const props = defineProps({
  value: { type: [String, Object], default: '' },
})
const list = computed(() => parseTags(props.value))
onMounted(() => loadTags())
</script>
