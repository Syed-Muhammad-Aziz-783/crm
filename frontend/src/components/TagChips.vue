<template>
  <div class="flex flex-wrap items-center justify-center gap-1">
    <span
      v-for="t in list"
      :key="t"
      class="rounded-full px-2 py-0.5 text-sm"
      :class="colorOf(t).chip"
      >{{ t }}</span
    >
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { colorOf, loadTags, parseTags } from '@/utils/tagColors'

const props = defineProps({ value: { type: [String, Object], default: '' } })
const list = computed(() => parseTags(props.value))
onMounted(() => loadTags())
</script>
