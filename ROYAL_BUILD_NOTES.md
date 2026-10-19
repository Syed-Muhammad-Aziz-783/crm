# Royal build notes

The full image (`.github/workflows/build-image.yml`) is built ONLY from our own forks:

| App | Our fork | Branch | Frozen at (2026-10-19) |
| --- | --- | --- | --- |
| frappe | Syed-Muhammad-Aziz-783/frappe | version-16 | 4515014c87ece6cb20ee91d2cfb121c5cbd1ff4a (2026-10-14) |
| erpnext | Syed-Muhammad-Aziz-783/erpnext | version-16 | 5af6561f5aa48104559692fb4fd82f2580e8d338 (2026-10-15) |
| hrms | Syed-Muhammad-Aziz-783/hrms | version-16 | 2478afc7a8f4959d500f6d17522853f0d244e38f (2026-10-15) |
| crm | Syed-Muhammad-Aziz-783/crm | royal | (our work) |

These commits are exactly what the server image contained at the last full build before the switch.

Rules:
1. Never press "Sync fork" on frappe, erpnext or hrms. That pulls frappe.io code in unreviewed.
2. To take a frappe.io update on purpose: merge it into the fork's version-16 branch on a test branch, review, build, back up, then merge and run migrate.
3. Frappe, ERPNext and HRMS fixes of our own go into the forks too.
4. GUARD: the build workflow checks that the three forks are still on the frozen commits above. If one moved (mistaken Sync fork), the build STOPS before building and the server keeps its old image. To take new code on purpose, change the SHAs in the guard step in the same change.
5. If Sync fork was pressed by mistake: do not push anything, tell Claude. Claude resets the fork's version-16 to the frozen commit.
6. This notes file also lives on branch `royal-notes` in the frappe, erpnext and hrms forks (a separate branch, so version-16 stays untouched and frozen).

Status check 2026-10-19: the three forks were not changed today. The frozen commits in the table above are still the ones the guard checks. All CRM changes are listed in `ROYAL.md` (branch `royal` of the crm fork).
