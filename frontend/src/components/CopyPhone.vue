<template>
  <button
    type="button"
    class="flex items-center rounded p-0.5 text-ink-gray-5 hover:text-ink-gray-8"
    :title="__('Copy number')"
    :aria-label="__('Copy number')"
    @click.stop.prevent="copyText(value)"
  >
    <span class="lucide-copy block size-4" />
  </button>
</template>

<script setup>
import { copyText } from '@/utils/copyText'

defineProps({ value: { type: [String, Number], default: '' } })
</script>
