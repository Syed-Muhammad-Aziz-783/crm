import frappe
from frappe.desk.doctype.tag.tag import DocTags

# Royal: tags for CRM records, with colors (like Odoo).
# Frappe's Tag doctype has no color field and only System Manager can read it,
# so the color is kept in Tag.description as "color:<name>" and these helpers
# read/write it for every CRM user. No migrate needed.

TAG_DOCTYPES = {
	"CRM Lead",
	"CRM Deal",
	"CRM Task",
	"CRM Organization",
	"Contact",
	"FCRM Note",
}
COLORS = {"gray", "red", "orange", "amber", "green", "teal", "blue", "purple", "pink", "brown"}
PREFIX = "color:"


def _check_user():
	if frappe.session.user == "Guest":
		frappe.throw(frappe._("Not permitted"), frappe.PermissionError)


def _color_of(description):
	d = (description or "").strip()
	if d.startswith(PREFIX):
		c = d[len(PREFIX) :].strip()
		return c if c in COLORS else None
	return None


def _clean(tag):
	return " ".join((tag or "").replace(",", " ").replace("#", " ").split())[:60]


@frappe.whitelist()
def get_all_tags():
	"""Every tag with its color (color may be empty = the app picks one from the name)."""
	_check_user()
	rows = frappe.get_all("Tag", fields=["name", "description"], limit_page_length=1000, order_by="name asc")
	return [{"name": r.name, "color": _color_of(r.description)} for r in rows]


@frappe.whitelist()
def set_tag_color(tag: str, color: str):
	"""Create the tag if needed and store its color."""
	_check_user()
	tag = _clean(tag)
	if not tag or color not in COLORS:
		frappe.throw(frappe._("Invalid tag or color"))
	if frappe.db.exists("Tag", tag):
		current = frappe.db.get_value("Tag", tag, "description")
		# never overwrite a real description someone typed in the desk
		if current and not current.strip().startswith(PREFIX):
			return {"name": tag, "color": color, "stored": False}
		frappe.db.set_value("Tag", tag, "description", PREFIX + color, update_modified=False)
	else:
		frappe.get_doc({"doctype": "Tag", "name": tag, "description": PREFIX + color}).insert(
			ignore_permissions=True
		)
	return {"name": tag, "color": color, "stored": True}


@frappe.whitelist()
def add_tags_to_doc(doctype: str, name: str | int, tags: str | list, colors: str | dict | None = None):
	"""Add several tags to one record (used right after a record is created)."""
	_check_user()
	if doctype not in TAG_DOCTYPES:
		frappe.throw(frappe._("Tags are not enabled for {0}").format(doctype))
	name = str(name)
	frappe.has_permission(doctype, "write", name, throw=True)
	tags = frappe.parse_json(tags) or []
	colors = frappe.parse_json(colors) or {}
	dt = DocTags(doctype)
	for tag in tags:
		tag = _clean(tag)
		if not tag:
			continue
		dt.add(name, tag)
		if colors.get(tag) in COLORS:
			set_tag_color(tag, colors[tag])
	return dt.get_tags(name)


@frappe.whitelist()
def get_tag_counts():
	"""How many records use each tag (Tag Link rows)."""
	_check_user()
	rows = frappe.db.sql("select tag, count(*) from `tabTag Link` group by tag")
	return {r[0]: r[1] for r in rows}


@frappe.whitelist()
def delete_tag(tag: str):
	"""Remove a tag from every record, then delete it. Managers only."""
	frappe.only_for(("System Manager", "Sales Manager"))
	tag = _clean(tag)
	if not frappe.db.exists("Tag", tag):
		return
	links = frappe.get_all(
		"Tag Link",
		filters={"tag": tag},
		fields=["document_type", "document_name"],
		limit_page_length=0,
	)
	for link in links:
		try:
			DocTags(link.document_type).remove(link.document_name, tag)
		except Exception:
			frappe.log_error(title="Royal tag delete: could not strip tag from a record")
	frappe.delete_doc("Tag", tag, ignore_permissions=True, force=True)
