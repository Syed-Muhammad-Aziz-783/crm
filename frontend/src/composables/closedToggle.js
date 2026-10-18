import { useStorage } from '@vueuse/core'

// Royal: hide finished records by default, with a switch to show them.
// The switch state is kept per browser and shared by list + kanban.
const states = {}

export function useShowClosed(key) {
  if (!states[key]) states[key] = useStorage('royal_show_closed_' + key, false)
  return states[key]
}

export const closedConfig = {
  'CRM Lead': {
    key: 'leads',
    label: 'Show Won / Lost',
    field: 'status',
    values: ['Won', 'Lost'],
  },
  'CRM Task': {
    key: 'tasks',
    label: 'Show Done',
    field: 'status',
    values: ['Done'],
  },
}
