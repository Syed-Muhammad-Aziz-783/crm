<template>
  <!-- Royal: on a task, show the lead's / deal's status and attachments. Changing the status is
       saved to the lead when the task is saved. Adding / removing a file works on the lead at once. -->
  <div class="mt-4 flex flex-col gap-3 border-t pt-4">
    <div class="flex items-center gap-3">
      <span class="w-28 shrink-0 text-sm text-ink-gray-5">
        {{ refDoctype === 'CRM Deal' ? __('Deal Status') : __('Lead Status') }}
      </span>
      <Dropdown :options="options">
        <Button :label="status || __('Select status')">
          <template v-if="current" #prefix>
            <IndicatorIcon :class="current.color" />
          </template>
          <template #suffix>
            <span class="lucide-chevron-down size-4" aria-hidden="true" />
          </template>
        </Button>
      </Dropdown>
    </div>

    <div class="flex items-start gap-3">
      <span class="w-28 shrink-0 pt-1 text-sm text-ink-gray-5">
        {{ __('Attachments') }}
      </span>
      <div class="flex min-w-0 flex-1 flex-col gap-1.5">
        <div
          v-for="f in files"
          :key="f.name"
          class="flex items-center justify-between gap-2 rounded-md bg-surface-gray-2 px-2.5 py-1.5 text-sm"
        >
          <a
            :href="f.file_url"
            target="_blank"
            class="truncate text-ink-gray-8 hover:underline"
          >
            {{ f.file_name }}
          </a>
          <div class="flex shrink-0 items-center gap-2">
            <span class="text-ink-gray-5">{{ convertSize(f.file_size) }}</span>
            <button
              type="button"
              class="text-base leading-none text-ink-gray-5 hover:text-ink-red-4"
              :aria-label="__('Delete Attachment')"
              @click="removeFile(f)"
            >
              &times;
            </button>
          </div>
        </div>
        <span
          v-if="loaded && !files.length"
          class="pt-1 text-sm text-ink-gray-5"
        >
          {{ __('No attachments') }}
        </span>
        <div>
          <Button
            variant="subtle"
            size="sm"
            :label="__('Add attachment')"
            iconLeft="lucide-paperclip"
            @click="showUploader = true"
          />
        </div>
      </div>
    </div>
  </div>
  <FilesUploader
    v-model="showUploader"
    :doctype="refDoctype"
    :docname="refName"
    @after="loadFiles"
  />
</template>

<script setup>
import IndicatorIcon from '@/components/Icons/IndicatorIcon.vue'
import FilesUploader from '@/components/FilesUploader/FilesUploader.vue'
import { statusesStore } from '@/stores/statuses'
import { globalStore } from '@/stores/global'
import { convertSize } from '@/utils'
import { Button, Dropdown, call, toast } from 'frappe-ui'
import { ref, computed, watch } from 'vue'

const props = defineProps({
  refDoctype: { type: String, default: 'CRM Lead' },
  refName: { type: String, required: true },
})
const status = defineModel('status', { type: String, default: '' })
const emit = defineEmits(['loaded'])

const { $dialog } = globalStore()
const { leadStatuses, dealStatuses, statusOptions } = statusesStore()

const files = ref([])
const loaded = ref(false)
const showUploader = ref(false)

const isDeal = computed(() => props.refDoctype === 'CRM Deal')
const all = computed(() =>
  isDeal.value ? dealStatuses.data : leadStatuses.data,
)
const current = computed(() => all.value.find((s) => s.name === status.value))

// "Lost" needs a lost reason, so it is not offered here: set it on the lead itself
const options = computed(() =>
  statusOptions(
    isDeal.value ? 'deal' : 'lead',
    all.value
      .filter((s) => s.type !== 'Lost' || s.name === status.value)
      .map((s) => s.name),
    (value) => (status.value = value),
  ),
)

async function loadFiles() {
  try {
    files.value = await call('frappe.client.get_list', {
      doctype: 'File',
      fields: ['name', 'file_name', 'file_url', 'file_size'],
      filters: {
        attached_to_doctype: props.refDoctype,
        attached_to_name: props.refName,
      },
      order_by: 'creation asc',
      limit_page_length: 100,
    })
  } catch (e) {
    files.value = []
  }
  loaded.value = true
}

async function loadStatus() {
  try {
    const row = await call('frappe.client.get_value', {
      doctype: props.refDoctype,
      filters: { name: props.refName },
      fieldname: 'status',
    })
    status.value = row?.status || ''
  } catch (e) {
    status.value = ''
  }
  emit('loaded', status.value)
}

function removeFile(f) {
  $dialog({
    title: __('Delete Attachment'),
    message: __('This also removes it from the {0}. Delete {1}?', [
      isDeal.value ? __('deal') : __('lead'),
      f.file_name,
    ]),
    actions: [
      {
        label: __('Delete'),
        variant: 'solid',
        theme: 'red',
        onClick: async ({ close }) => {
          try {
            await call('frappe.client.delete', {
              doctype: 'File',
              name: f.name,
            })
            files.value = files.value.filter((x) => x.name !== f.name)
          } catch (e) {
            toast.error(e?.messages?.[0] || __('Could not delete the file'))
          }
          close()
        },
      },
    ],
  })
}

watch(
  () => [props.refDoctype, props.refName],
  () => {
    loaded.value = false
    files.value = []
    loadFiles()
    loadStatus()
  },
  { immediate: true },
)
</script>
