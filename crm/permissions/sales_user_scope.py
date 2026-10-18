# Royal Aluminium Rwanda Ltd custom rule.
# For Sales Users (not Sales Manager / System Manager) limit CRM Task, FCRM Note,
# Contact and CRM Organization to: records they created, OR records that belong to
# a Lead / Deal that is owned by them or assigned to them.

import frappe

_FULL_ACCESS_ROLES = {"System Manager", "Sales Manager"}


def _full_access(user: str) -> bool:
	return user == "Administrator" or bool(_FULL_ACCESS_ROLES & set(frappe.get_roles(user)))


def _assigned_names(doctype: str, u: str) -> str:
	# names of records of `doctype` assigned to the user through ToDo
	return (
		"SELECT `reference_name` FROM `tabToDo` "
		f"WHERE `reference_type` = '{doctype}' AND `allocated_to` = {u} AND `status` != 'Cancelled'"
	)


def _visible(doctype: str, owner_field: str, u: str) -> str:
	# names of Leads / Deals the user owns or is assigned to
	return (
		f"SELECT `name` FROM `tab{doctype}` "
		f"WHERE `{owner_field}` = {u} OR `name` IN ({_assigned_names(doctype, u)})"
	)


def _reference_clause(table: str, u: str) -> str:
	lead = _visible("CRM Lead", "lead_owner", u)
	deal = _visible("CRM Deal", "deal_owner", u)
	return (
		f"(`{table}`.`reference_doctype` = 'CRM Lead' AND `{table}`.`reference_docname` IN ({lead})) "
		f"OR (`{table}`.`reference_doctype` = 'CRM Deal' AND `{table}`.`reference_docname` IN ({deal}))"
	)


def _condition(doctype: str, user: str | None) -> str:
	user = user or frappe.session.user
	if _full_access(user):
		return ""

	u = frappe.db.escape(user)
	table = f"tab{doctype}"
	own = f"`{table}`.`owner` = {u}"

	if doctype == "CRM Task":
		assigned = (
			f"`{table}`.`assigned_to` = {u} OR `{table}`.`name` IN ({_assigned_names('CRM Task', u)})"
		)
		return f"({own} OR {assigned} OR {_reference_clause(table, u)})"

	if doctype == "FCRM Note":
		return f"({own} OR {_reference_clause(table, u)})"

	deal = _visible("CRM Deal", "deal_owner", u)

	if doctype == "Contact":
		via_deal = (
			f"`{table}`.`name` IN (SELECT `contact` FROM `tabCRM Deal` "
			f"WHERE `contact` IS NOT NULL AND `name` IN ({deal})) "
			f"OR `{table}`.`name` IN (SELECT `contact` FROM `tabCRM Contacts` "
			f"WHERE `parenttype` = 'CRM Deal' AND `parent` IN ({deal}))"
		)
		return f"({own} OR {via_deal})"

	if doctype == "CRM Organization":
		via_deal = (
			f"`{table}`.`name` IN (SELECT `organization` FROM `tabCRM Deal` "
			f"WHERE `organization` IS NOT NULL AND `name` IN ({deal}))"
		)
		return f"({own} OR {via_deal})"

	return ""


def _has_permission(doc, ptype, user, doctype: str):
	user = user or frappe.session.user
	if ptype == "create" or not doc.name or _full_access(user):
		return True

	cond = _condition(doctype, user)
	if not cond:
		return True

	return bool(
		frappe.db.sql(
			f"SELECT `name` FROM `tab{doctype}` WHERE `name` = %s AND {cond} LIMIT 1",
			(doc.name,),
		)
	)


def task_query(user=None):
	return _condition("CRM Task", user)


def note_query(user=None):
	return _condition("FCRM Note", user)


def contact_query(user=None):
	return _condition("Contact", user)


def organization_query(user=None):
	return _condition("CRM Organization", user)


def task_has_permission(doc, ptype=None, user=None):
	return _has_permission(doc, ptype, user, "CRM Task")


def note_has_permission(doc, ptype=None, user=None):
	return _has_permission(doc, ptype, user, "FCRM Note")


def contact_has_permission(doc, ptype=None, user=None):
	return _has_permission(doc, ptype, user, "Contact")


def organization_has_permission(doc, ptype=None, user=None):
	return _has_permission(doc, ptype, user, "CRM Organization")
