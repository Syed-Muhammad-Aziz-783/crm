# Royal build

Branch `royal` of this fork is Royal Aluminium Rwanda Ltd's CRM. It is built by GitHub Actions into `ghcr.io/syed-muhammad-aziz-783/royal-erpnext` (full image) and `hotpatch-crm` (fast lane). See `ROYAL_BUILD_NOTES.md` for the frozen frappe / erpnext / hrms forks and the build guard.

Last updated: 2026-10-19.

## How a change goes live
1. Push to `royal`. Two workflows start: the fast lane (`hotpatch.yml`, about 1-2 minutes, builds only this app) and the full image (`build-image.yml`, about 10 minutes).
2. The server picks the fast lane up by itself within about 3 minutes. Users refresh once.
3. Schema or doctype changes also need a migrate on the server (never automatic).
4. Every push to `royal`, even a notes-only one, starts both workflows. Batch doc edits into one push.
5. Green means compiled, not tested. Test on desktop AND phone, and as a Sales User for permission changes.

## What Royal changed (summary)
- Tasks: title optional, Due Date and Assigned To required, status only Todo or Done, colored due date (red passed, yellow today, green future), Done / Done and Schedule Next buttons, "Show Done" switch.
- Leads: Lead Owner required, "Show Won / Lost" switch, Convert to Deal hidden, one Phone field (Mobile No hidden and kept in sync), copy button on phone numbers.
- Lists: Kanban removed everywhere, headings and data centered, invalid column widths repaired, mobile keeps all columns with sideways scroll, selected-rows bar fits the phone.
- Open Tasks and Notes columns for Leads and Deals. The Open Tasks number is colored by the LAST CREATED open task (`_task_due`, `components/OpenTasksCell.vue`, `utils/dueColor.js`, shared with the Tasks list).
- Tags (Odoo style, colored) on Leads, Deals, Contacts, Organizations, Tasks: `crm/api/tags.py`, `components/TagsBox.vue`, `components/TagChips.vue`, `utils/tagColors.js`, `pages/Tags.vue`. Built on Frappe's `_user_tags`, Tag and Tag Link; the color is stored in `Tag.description` as `color:<name>`.
  - Lists show every tag on one line; the Tags column is widened to the widest row by `sanitizeColumnWidths(columns, rows)`.
  - Tags filter: Has tag / Doesn't have tag / Is set, with a dropdown of saved tags (`Filter.vue`); exact match on the server in `royal_tag_filters` (`crm/api/doc.py`).
- Live sync: lists, Lead and Deal pages and tags refresh by themselves (`composables/useLiveSync.js`, Frappe realtime `list_update`, focus, 60 s fallback); open apps pick up a new build by themselves (`composables/useAutoUpdate.js`).
- Self-heal: `frontend/index.html` clears old service workers and caches once and reloads if the app fails to start after an update.
- One-click delete for Lead / Deal / Task (`royal_delete`, `royal_delete_bulk`).
- ERPNext desk: copy button and Phone label, red dot on today's date (`crm/public/js/royal_desk.js`, `crm/public/css/royal_desk.css`).
- iPhone: dialogs scroll (CSS in `frontend/src/index.css`).
- Permissions: Sales User sees own records or those on leads they own or are assigned (`crm/permissions/sales_user_scope.py`).

## Technical notes
- Tailwind here uses the frappe-ui preset: no `stone` palette, no `ring-ink-*` classes. A missing class fails silently, so colors that must be seen are inline hex styles.
- The frappe-ui experimental ListView draws the header and each row as separate grids from `column.width`; a column sized to its content needs a computed px width.
- `get_data` (`crm/api/doc.py`): `default_filters` override user filters; virtual columns (`_task_count`, `_note_count`, `_task_due`) are filled by `royal_add_counts` and never break the list.
- Tag changes do not change `modified`, so the tag API publishes `list_update` itself.
- Local test: `cd frontend && yarn install && npx vite build --base=/assets/crm/frontend/`, then open the built app in Chromium with the API mocked. This checks the look and the layout, never live data.

## Still to confirm on live data
1. Tags filter, one-line tags column, Open Tasks colors (tasks due yesterday, today, tomorrow).
2. Real cause of the white screen (stale service worker is the suspect, unproven).
3. Websocket realtime and `royal_desk.js` being served on the server; iPhone dialog scroll on a real iPhone.
4. Open Tasks color rule: "last created open task" (current) or "nearest due date".
