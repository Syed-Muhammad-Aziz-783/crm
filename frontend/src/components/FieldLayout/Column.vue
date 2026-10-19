<template>
  <div class="column flex flex-col gap-4 min-w-0 flex-1">
    <div
      v-if="column.label && !column.hideLabel"
      class="text-ink-gray-9 max-w-fit text-base"
    >
      {{ column.label }}
    </div>
    <template v-for="field in visibleFields" :key="field.fieldname">
      <Field :field="field" :data-name="field.fieldname" />
    </template>
  </div>
</template>
<script setup>
import Field from '@/components/FieldLayout/Field.vue'
import { computed } from 'vue'
import { royalPhoneFields } from '@/utils/royalPhone'

const props = defineProps({
  column: { type: Object, required: true },
})

// Royal: one phone field only. Mobile No is hidden everywhere, the server keeps it equal to Phone.
const visibleFields = computed(() => royalPhoneFields(props.column.fields))
</script>
