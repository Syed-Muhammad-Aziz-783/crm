<template>
  <FormControl
    v-if="filter.fieldtype == 'Check'"
    v-model="filter.value"
    :label="filter.label"
    type="checkbox"
    @change.stop="updateFilter(filter, $event.target.checked)"
  />
  <!-- Royal: on phones use the phone's own picker. The custom dropdown did not
       refresh the list on iPhone until the page was reloaded. -->
  <select
    v-else-if="filter.fieldtype === 'Select' && isMobileView"
    :value="filter.value || ''"
    class="h-7 w-full rounded border-none bg-surface-gray-2 px-2 text-base text-ink-gray-8 focus:outline-none"
    @change="updateFilter(filter, $event.target.value)"
  >
    <option value="">{{ filter.label }}</option>
    <option
      v-for="opt in nativeOptions"
      :key="opt.value"
      :value="opt.value"
    >
      {{ opt.label }}
    </option>
  </select>
  <FormControl
    v-else-if="filter.fieldtype === 'Select'"
    v-model="filter.value"
    class="form-control cursor-pointer [&_select]:cursor-pointer"
    type="select"
    :options="filter.options"
    :placeholder="filter.label"
    side="bottom"
    @update:modelValue="updateFilter(filter, $event)"
  />
  <Link
    v-else-if="filter.fieldtype === 'Link'"
    :value="filter.value"
    :doctype="filter.options"
    :placeholder="filter.label"
    @change="(data) => updateFilter(filter, data)"
  />
  <component
    :is="filter.fieldtype === 'Date' ? DatePicker : DateTimePicker"
    v-else-if="['Date', 'Datetime'].includes(filter.fieldtype)"
    class="border-none"
    :model-value="filter.value"
    :placeholder="filter.label"
    :format="
      filter.fieldtype === 'Date'
        ? getFormat('', '', true, false, false)
        : getFormat('', '', true, true, false)
    "
    @change="(v) => updateFilter(filter, v)"
  />
  <FormControl
    v-else
    v-model="filter.value"
    type="text"
    :placeholder="filter.label"
    @input.stop="debouncedFn(filter, $event.target.value)"
  />
</template>
<script setup>
import Link from '@/components/Controls/Link.vue'
import { FormControl, DatePicker, DateTimePicker } from 'frappe-ui'
import { getFormat } from '@/utils'
import { useDebounceFn } from '@vueuse/core'
import { computed, reactive, watch } from 'vue'
import { isMobileView } from '@/composables/settings'

const props = defineProps({
  filter: { type: Object, required: true },
})

const filter = reactive(props.filter)

const nativeOptions = computed(() =>
  (props.filter.options || [])
    .map((o) => (typeof o === 'string' ? { label: o, value: o } : o))
    .filter((o) => o.value),
)

const emit = defineEmits(['applyQuickFilter'])

watch(
  () => props.filter,
  (newFilter) => Object.assign(filter, newFilter),
  { deep: true },
)

const debouncedFn = useDebounceFn((f, value) => {
  emit('applyQuickFilter', f, value)
}, 500)

function updateFilter(f, value) {
  emit('applyQuickFilter', f, value)
}
</script>
