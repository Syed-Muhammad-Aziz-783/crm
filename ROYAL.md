# Royal build

Branch `royal` of this fork is Royal Aluminium Rwanda Ltd's CRM. It is built by GitHub Actions into `ghcr.io/syed-muhammad-aziz-783/royal-erpnext` (full image) and `hotpatch-crm` (fast lane). See `ROYAL_BUILD_NOTES.md` for the frozen frappe / erpnext / hrms forks and the build guard.

Last updated: 2026-10-20.

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
- Color filter (2026-10-20) on Tasks, Leads, Deals: field `_due_color`, operators Is / Is not, four values: "Yellow, Red, Green" (all colors, sorted in that order), Yellow, Red, Green. Several Color filters are joined with OR. Tasks use their own due date (open only); Leads and Deals use the last created open task; no open task means no color. Server: `royal_color_kinds`, `royal_color_picked`, `royal_color_filter` in `crm/api/doc.py` (rank sort in `get_data`). Export uses `royal_resolve_filters`.
- Repeated filters: the same filter can be added many times (`field__2` keys; `royal_split_filters`, `royal_list_filters`; `Filter.vue` remounts the Add Filter combobox with a key).
- Tags on tasks: a task starts with its lead's tags; existing tasks were filled once.
- Location: custom doctype `Rwanda Location` (Kigali plus 416 sectors, named `Sector (District)`), required Link field `CRM Lead.location`, copied to `CRM Task.lead_location` (`fill_from_lead`, lead `on_update`). Web forms or automations that create leads must now send a Location.
- Task form (`components/LeadLinkBox.vue`, `Modals/DoctypeModal.vue`): shows and changes the lead's status and attachments. Add and remove act on the lead at once. Lost is not offered (needs a lost reason).
- Team standard screens: `default_list_data` in `crm_lead.py` and `crm_task.py` hold the owner's column layout; a user's own saved view wins; new users get the standard.
- Role Profiles (set in Frappe, no code): "Royal CRM - Own Records" and "Royal CRM - All Records".
- Theme: Light or Dark by the user's choice, never follows the phone (`App.vue`, `ThemeSwitcher.vue`).

## Technical notes
- Tailwind here uses the frappe-ui preset: no `stone` palette, no `ring-ink-*` classes. A missing class fails silently, so colors that must be seen are inline hex styles.
- The frappe-ui experimental ListView draws the header and each row as separate grids from `column.width`; a column sized to its content needs a computed px width.
- `get_data` (`crm/api/doc.py`): `default_filters` override user filters; virtual columns (`_task_count`, `_note_count`, `_task_due`) are filled by `royal_add_counts` and never break the list.
- Tag changes do not change `modified`, so the tag API publishes `list_update` itself.
- Local test: `cd frontend && yarn install && npx vite build --base=/assets/crm/frontend/`, then open the built app in Chromium with the API mocked. This checks the look and the layout, never live data.
- frappe-ui `useColorScheme()` initialises on first call and stores `system`; set defaults after reading `colorScheme.value`, not by testing localStorage.
- frappe-ui `Combobox` keeps its last pick; remount with a changing `:key` to allow picking the same option twice.
- CRM View Settings are per user; quick filters are global. With no saved view, `default_list_data()` in code is used.
- A vite build passing does not catch a missing Vue import; always open the screen.
- Process records oldest-modified first when bulk updating over REST, so list order stays.

## Still to confirm on live data
1. Tags filter, one-line tags column, Open Tasks colors (tasks due yesterday, today, tomorrow).
2. Real cause of the white screen (stale service worker is the suspect, unproven).
3. Websocket realtime and `royal_desk.js` being served on the server; iPhone dialog scroll on a real iPhone.
4. Open Tasks color rule: "last created open task" (current) or "nearest due date".
5. Color filter (all four options, adding it twice), Location (create a lead, search a sector, task copy), task form status and attachments, Role Profiles on a test user, theme on a real iPhone, new-user standard columns.
6. Web forms or automations creating leads now need a Location.
