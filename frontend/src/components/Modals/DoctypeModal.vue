<template>
  <Dialog
    v-model:open="show"
    :size="doctype === 'FCRM Note' ? '2xl' : 'xl'"
    :dismissible="doctype !== 'FCRM Note'"
    bare
  >
    <template #default>
      <div
        class="bg-surface-elevation-2 px-4 pb-6 pt-5 sm:px-6"
        @keydown.meta.enter.capture.prevent.stop="submit"
        @keydown.ctrl.enter.capture.prevent.stop="submit"
      >
        <div class="mb-5 flex items-center justify-between">
          <div class="flex gap-2 items-center">
            <Dialog.Title as-child>
              <h3 class="text-3xl-semibold leading-6 text-ink-gray-9">
                {{
                  editMode
                    ? __('Edit {0}', [__(doctypeTitle || doctype)])
                    : __('Create {0}', [__(doctypeTitle || doctype)])
                }}
              </h3>
            </Dialog.Title>
          </div>
          <div class="flex items-center gap-1">
            <CustomActions
              v-if="document.actions?.length"
              :actions="document.actions"
              :close="() => (show = false)"
            />
            <Button
              v-if="isManager() && !isMobileView"
              variant="ghost"
              class="w-7"
              :tooltip="__('Edit Fields Layout')"
              :icon="EditIcon"
              @click="openQuickEntryModal"
            />
            <Dialog.Close as-child>
              <Button
                :aria-label="__('Close')"
                variant="ghost"
                class="w-7"
                icon="lucide-x"
              />
            </Dialog.Close>
          </div>
        </div>
        <div>
          <FieldLayout
            v-if="layout.data"
            :tabs="layout.data"
            :data="doc"
            :doctype="doctype"
            :docname="docname"
          />
          <TagsBox
            v-if="doctype === 'CRM Task'"
            doctype="CRM Task"
            :docname="editMode ? docname : ''"
            v-model="newTags"
            bare
            class="mt-3"
          />
          <LeadLinkBox
            v-if="showLeadBox"
            :ref-doctype="doc.reference_doctype"
            :ref-name="String(doc.reference_docname)"
            v-model:status="leadStatus"
            @loaded="(s) => (leadStatusOriginal = s)"
          />
          <ErrorMessage v-if="error" class="mt-4" :message="__(error)" />
        </div>
      </div>
      <div class="px-4 pb-7 pt-4 sm:px-6">
        <div class="flex flex-row-reverse flex-wrap gap-2">
          <Button
            variant="solid"
            :label="editMode ? __('Update') : __('Create')"
            :loading="editMode ? document.save.loading : create.loading"
            @click="submit"
          />
          <template v-if="doctype === 'CRM Task' && editMode">
            <Button
              variant="solid"
              :label="__('Done and Schedule Next')"
              :loading="document.save.loading"
              @click="markDone(true)"
            />
            <Button
              variant="solid"
              :label="__('Done')"
              :loading="document.save.loading"
              @click="markDone(false)"
            />
          </template>
        </div>
      </div>
    </template>
  </Dialog>
</template>

<script setup>
import EditIcon from '@/components/Icons/EditIcon.vue'
import FieldLayout from '@/components/FieldLayout/FieldLayout.vue'
import CustomActions from '@/components/CustomActions.vue'
import { useDocument } from '@/data/document'
import { globalStore } from '@/stores/global'
import { usersStore } from '@/stores/users'
import { showQuickEntryModal, quickEntryProps } from '@/composables/modals'
import { isMobileView } from '@/composables/settings'
import { setupCustomizations } from '@/utils'
import { useDoctypeModal } from '@/composables/doctypeModal'

import TagsBox from '@/components/TagsBox.vue'
import LeadLinkBox from '@/components/LeadLinkBox.vue'
import { saveTagsToDoc, parseTags } from '@/utils/tagColors'
import { Dialog, call, createResource, toast } from 'frappe-ui'
import { ref, computed, watch, nextTick, onMounted } from 'vue'
import { useRouter } from 'vue-router'

const props = defineProps({
  doctypeTitle: { type: String, default: '' },
  doctype: { type: String, default: '' },
  docname: { type: String, default: '' },
  defaults: { type: Object, default: () => ({}) },
})

const show = defineModel({ type: Boolean })

const emit = defineEmits(['afterInsert', 'afterUpdate'])

const router = useRouter()

const { isManager } = usersStore()
const doctypeModalState = useDoctypeModal()
const { $dialog, $socket } = globalStore()

const { document, scripts, triggerOnRender, triggerOnBeforeCreate } =
  useDocument(props.doctype, props.docname || null)

const doc = computed(() => document.doc || {})

const layout = createResource({
  url: 'crm.fcrm.doctype.crm_fields_layout.crm_fields_layout.get_fields_layout',
  cache: ['Quick Entry', props.doctype],
  params: { doctype: props.doctype, type: 'Quick Entry' },
  auto: true,
})

const error = ref(null)
const editMode = computed(() => Boolean(document.doc?.name))

const newTags = ref([])

// Royal: the lead's / deal's status shown on the task. A change is saved to the lead
// together with the task (a Lost status needs a reason, so it is set on the lead itself).
const leadStatus = ref('')
const leadStatusOriginal = ref(undefined)
const showLeadBox = computed(
  () =>
    props.doctype === 'CRM Task' &&
    document.doc?.reference_docname &&
    ['CRM Lead', 'CRM Deal'].includes(document.doc?.reference_doctype),
)

async function syncLeadStatus() {
  if (!showLeadBox.value) return true
  if (leadStatusOriginal.value === undefined) return true
  if (!leadStatus.value || leadStatus.value === leadStatusOriginal.value)
    return true
  try {
    await call('frappe.client.set_value', {
      doctype: document.doc.reference_doctype,
      name: document.doc.reference_docname,
      fieldname: 'status',
      value: leadStatus.value,
    })
    leadStatusOriginal.value = leadStatus.value
    return true
  } catch (e) {
    error.value =
      e?.messages?.[0] || __('Could not change the status of the lead')
    return false
  }
}

// Royal: a new task starts with the tags of its lead / deal. They can be removed
// before saving. Picking another lead loads that lead's tags instead.
watch(
  () => [document.doc?.reference_doctype, document.doc?.reference_docname],
  async ([refDoctype, refName]) => {
    if (props.doctype !== 'CRM Task' || editMode.value) return
    if (!refName) return
    try {
      const rows = await call('frappe.client.get_list', {
        doctype: refDoctype || 'CRM Lead',
        fields: ['name', '_user_tags'],
        filters: { name: refName },
        limit_page_length: 1,
      })
      newTags.value = parseTags(rows?.[0]?._user_tags)
    } catch (e) {
      // no tags column yet or no access: the task simply starts without tags
    }
  },
  { immediate: true },
)

const _create = createResource({
  url: 'frappe.client.insert',
  onSuccess: async (d) => {
    if (props.doctype === 'CRM Task') await saveTagsToDoc('CRM Task', d.name, newTags.value)
    document.doc = {}
    emit('afterInsert', d)
    show.value = false
  },
  onError: (err) => {
    if (err.exc_type == 'MandatoryError') {
      const fieldName = err.messages
        .map((msg) => {
          let arr = msg.split(': ')
          return arr[arr.length - 1].trim()
        })
        .join(', ')
      error.value = __('Mandatory field error: {0}', [fieldName])
      return
    }
    error.value = err.messages?.[0] || __('Could not create document')
  },
})

async function create() {
  await triggerOnBeforeCreate?.()
  if (!(await syncLeadStatus())) return

  _create.submit({
    doc: {
      doctype: props.doctype,
      ...document.doc,
    },
  })
}

async function update() {
  error.value = null
  const statusChanged =
    showLeadBox.value &&
    leadStatus.value &&
    leadStatusOriginal.value !== undefined &&
    leadStatus.value !== leadStatusOriginal.value
  if (!(await syncLeadStatus())) return
  // frappe-ui skips saving an unchanged doc without calling back, so handle it here
  if (!document.isDirty) {
    if (!statusChanged) toast.info(__('Nothing to update'))
    show.value = false
    return
  }
  document.save.submit(null, {
    onSuccess: (d) => {
      emit('afterUpdate', d)
      show.value = false
    },
    onError: (err) => {
      error.value = err.messages?.[0] || __('Could not update document')
    },
  })
}

// Royal: mark the task Done. With scheduleNext, open a new task for the same
// lead (same name, phone and assignee) so the next follow-up can be set.
async function markDone(scheduleNext) {
  window.document.activeElement?.blur()
  if (!(await syncLeadStatus())) return
  const d = document.doc
  const next = {
    reference_doctype: d.reference_doctype,
    reference_docname: d.reference_docname,
    lead_name: d.lead_name,
    lead_phone: d.lead_phone,
    lead_location: d.lead_location,
    assigned_to: d.assigned_to,
  }
  const callbacks = { ...doctypeModalState.callbacks.value }
  document.doc.status = 'Done'

  const finish = (saved) => {
    emit('afterUpdate', saved)
    show.value = false
    if (scheduleNext) {
      setTimeout(() => {
        doctypeModalState.showModal({
          doctype: 'CRM Task',
          title: 'Task',
          defaults: next,
          callbacks,
        })
      }, 300)
    }
  }

  // isDirty is updated by a watcher after the next tick, so compare directly.
  // Already Done and nothing edited: nothing to save.
  const changed =
    JSON.stringify(document.doc) !== JSON.stringify(document.originalDoc)
  if (!changed) return finish({ ...document.doc })

  document.save.submit(null, {
    onSuccess: finish,
    onError: (err) => {
      error.value = err.messages?.[0] || __('Could not update document')
    },
  })
}

async function submit() {
  // editors save their text on blur, so blur first when saving from the keyboard
  window.document.activeElement?.blur()
  await nextTick()
  if (editMode.value) update()
  else create()
}

function openQuickEntryModal() {
  showQuickEntryModal.value = true
  quickEntryProps.value = { doctype: props.doctype }
  nextTick(() => (show.value = false))
}

watch(
  () => document.doc,
  async (_doc) => {
    if (scripts.data?.length) {
      setupCustomizations(scripts.data, {
        doc: _doc,
        $dialog,
        $socket,
        router,
        call,
      })
    }
  },
  { once: true },
)

onMounted(async () => {
  document.doc = {
    ...document.doc,
    ...props.defaults,
  }
  await triggerOnRender()
})
</script>
