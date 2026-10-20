import json
import re

import frappe
from frappe import _
from frappe.custom.doctype.property_setter.property_setter import make_property_setter
from frappe.desk.form.assign_to import set_status
from frappe.model import no_value_fields
from frappe.model.delete_doc import get_dynamic_linked_docs, get_linked_docs
from frappe.model.document import get_controller
from frappe.utils import make_filter_tuple
from pypika import Criterion

from crm.api.views import get_views
from crm.fcrm.doctype.crm_form_script.crm_form_script import get_form_script
from crm.utils import is_frappe_version

COUNT_NAME = (
	{"COUNT": "name", "as": "total_count"}
	if is_frappe_version("16", above=True)
	else "count(name) as total_count"
)


@frappe.whitelist()
def sort_options(doctype: str):
	fields = frappe.get_meta(doctype).fields
	fields = [field for field in fields if field.fieldtype not in no_value_fields]
	fields = [
		{
			"label": _(field.label),
			"value": field.fieldname,
			"fieldname": field.fieldname,
		}
		for field in fields
		if field.label and field.fieldname
	]

	standard_fields = [
		{"label": "Name", "fieldname": "name"},
		{"label": "Created On", "fieldname": "creation"},
		{"label": "Last Modified", "fieldname": "modified"},
		{"label": "Modified By", "fieldname": "modified_by"},
		{"label": "Owner", "fieldname": "owner"},
	]

	for field in standard_fields:
		field["label"] = _(field["label"])
		field["value"] = field["fieldname"]
		fields.append(field)

	return fields


@frappe.whitelist()
def get_filterable_fields(doctype: str):
	allowed_fieldtypes = [
		"Check",
		"Data",
		"Float",
		"Int",
		"Currency",
		"Dynamic Link",
		"Link",
		"Long Text",
		"Select",
		"Small Text",
		"Text Editor",
		"Text",
		"Duration",
		"Rating",
		"Date",
		"Datetime",
	]

	c = get_controller(doctype)
	restricted_fields = []
	if hasattr(c, "get_non_filterable_fields"):
		restricted_fields = c.get_non_filterable_fields()

	fields = []

	meta = frappe.get_meta(doctype).as_dict()

	# append standard fields (getting error when using frappe.model.std_fields)
	standard_fields = [
		{"fieldname": "name", "fieldtype": "Link", "label": "Name", "options": doctype},
		{"fieldname": "owner", "fieldtype": "Link", "label": "Created By", "options": "User"},
		{
			"fieldname": "modified_by",
			"fieldtype": "Link",
			"label": "Last Updated By",
			"options": "User",
		},
		{"fieldname": "_user_tags", "fieldtype": "Data", "label": "Tags"},
		{"fieldname": "_liked_by", "fieldtype": "Data", "label": "Like"},
		{"fieldname": "_comments", "fieldtype": "Text", "label": "Comments"},
		{"fieldname": "_assign", "fieldtype": "Text", "label": "Assigned To"},
		{"fieldname": "creation", "fieldtype": "Datetime", "label": "Created On"},
		{"fieldname": "modified", "fieldtype": "Datetime", "label": "Last Updated On"},
	]

	# Royal: "Color" = the due-date color (red passed, yellow today, green future).
	# On Tasks it is the task's own due date; on Leads / Deals it is the color of the
	# Open Tasks circle (last created open task). Worked out on the server in royal_color_filter.
	if doctype in ROYAL_COLOR_DOCTYPES:
		standard_fields.append(
			{
				"fieldname": "_due_color",
				"fieldtype": "Select",
				"label": "Color",
				"options": "Yellow, Red, Green\nYellow\nRed\nGreen",
			}
		)

	for field in standard_fields + meta.get("fields", []):
		if field.get("fieldname") not in restricted_fields and field.get("fieldtype") in allowed_fieldtypes:
			field["name"] = field.get("fieldname")
			field["label"] = _(field.get("label"))
			field["value"] = field.get("fieldname")
			fields.append(field)

	return fields


@frappe.whitelist()
def get_group_by_fields(doctype: str):
	allowed_fieldtypes = [
		"Check",
		"Data",
		"Float",
		"Int",
		"Currency",
		"Dynamic Link",
		"Link",
		"Select",
		"Duration",
		"Date",
		"Datetime",
	]

	fields = frappe.get_meta(doctype).fields
	fields = [
		field
		for field in fields
		if field.fieldtype not in no_value_fields and field.fieldtype in allowed_fieldtypes
	]
	fields = [
		{
			"label": _(field.label),
			"fieldname": field.fieldname,
		}
		for field in fields
		if field.label and field.fieldname
	]

	standard_fields = [
		{"label": "Name", "fieldname": "name"},
		{"label": "Created On", "fieldname": "creation"},
		{"label": "Last Modified", "fieldname": "modified"},
		{"label": "Modified By", "fieldname": "modified_by"},
		{"label": "Owner", "fieldname": "owner"},
		{"label": "Like", "fieldname": "_liked_by"},
		{"label": "Assigned To", "fieldname": "_assign"},
		{"label": "Comments", "fieldname": "_comments"},
		{"label": "Created On", "fieldname": "creation"},
		{"label": "Modified On", "fieldname": "modified"},
	]

	for field in standard_fields:
		field["label"] = _(field["label"])
		fields.append(field)

	return fields


@frappe.whitelist()
def get_quick_filters(doctype: str, cached: bool = True):
	meta = frappe.get_meta(doctype, cached)
	quick_filters = []

	if global_settings := frappe.db.exists("CRM Global Settings", {"dt": doctype, "type": "Quick Filters"}):
		_quick_filters = frappe.db.get_value("CRM Global Settings", global_settings, "json")
		_quick_filters = json.loads(_quick_filters) or []

		fields = []

		for filter in _quick_filters:
			if filter == "name":
				fields.append({"label": "Name", "fieldname": "name", "fieldtype": "Data"})
			else:
				field = next((f for f in meta.fields if f.fieldname == filter), None)
				if field:
					fields.append(field)

	else:
		fields = [field for field in meta.fields if field.in_standard_filter]

	for field in fields:
		options = field.get("options")
		if field.get("fieldtype") == "Select" and options and isinstance(options, str):
			options = options.split("\n")
			options = [{"label": option, "value": option} for option in options]
			if not any([not option.get("value") for option in options]):
				options.insert(0, {"label": "", "value": ""})
		quick_filters.append(
			{
				"label": _(field.get("label")),
				"fieldname": field.get("fieldname"),
				"fieldtype": field.get("fieldtype"),
				"options": options,
			}
		)

	if doctype == "CRM Lead":
		quick_filters = [filter for filter in quick_filters if filter.get("fieldname") != "converted"]

	return quick_filters


@frappe.whitelist()
def update_quick_filters(quick_filters: str, old_filters: str, doctype: str):
	quick_filters = json.loads(quick_filters)
	old_filters = json.loads(old_filters)

	new_filters = [filter for filter in quick_filters if filter not in old_filters]
	removed_filters = [filter for filter in old_filters if filter not in quick_filters]

	# update or create global quick filter settings
	create_update_global_settings(doctype, quick_filters)

	# remove old filters
	for filter in removed_filters:
		update_in_standard_filter(filter, doctype, 0)

	# add new filters
	for filter in new_filters:
		update_in_standard_filter(filter, doctype, 1)


def create_update_global_settings(doctype, quick_filters):
	if global_settings := frappe.db.exists("CRM Global Settings", {"dt": doctype, "type": "Quick Filters"}):
		frappe.db.set_value("CRM Global Settings", global_settings, "json", json.dumps(quick_filters))
	else:
		# create CRM Global Settings doc
		doc = frappe.new_doc("CRM Global Settings")
		doc.dt = doctype
		doc.type = "Quick Filters"
		doc.json = json.dumps(quick_filters)
		doc.insert()


def update_in_standard_filter(fieldname, doctype, value):
	if property_name := frappe.db.exists(
		"Property Setter",
		{"doc_type": doctype, "field_name": fieldname, "property": "in_standard_filter"},
	):
		frappe.db.set_value("Property Setter", property_name, "value", value)
	else:
		make_property_setter(
			doctype,
			fieldname,
			"in_standard_filter",
			value,
			"Check",
			validate_fields_for_doctype=False,
		)


def royal_tag_filters(doctype, filters):
	"""Turn a filter on Tags into an exact `name in (...)` / `name not in (...)` filter.

	`_user_tags` is one comma separated text, so LIKE would also match "Hot" inside "Hot lead".
	Frappe keeps one Tag Link row per tag per record, so we read the matching record names from there.
	"""
	if not filters or "_user_tags" not in filters:
		return filters

	filters = frappe._dict(filters)
	cond = filters.pop("_user_tags")
	if isinstance(cond, (list, tuple)) and len(cond) >= 2:
		op, value = str(cond[0]).lower(), cond[1]
	else:
		op, value = "=", cond

	def tag_names(raw):
		items = raw if isinstance(raw, (list, tuple)) else [raw]
		return [str(t).strip("% ").strip() for t in items if t is not None and str(t).strip("% ").strip()]

	link_filters = {"document_type": doctype}
	if op == "is":
		has_any = str(value).lower() == "set"
		positive = has_any
	else:
		tags = tag_names(value)
		if not tags:
			return filters  # nothing chosen yet, do not filter
		link_filters["tag"] = ["in", tags]
		positive = op in ("like", "=", "in")

	names = frappe.get_all(
		"Tag Link", filters=link_filters, pluck="document_name", distinct=True, limit_page_length=0
	)
	names = [str(n) for n in names]

	existing = filters.get("name")
	if existing is None:
		filters["name"] = ["in" if positive else "not in", names]
	elif positive and (isinstance(existing, str) or isinstance(existing, int)):
		filters["name"] = ["in", [n for n in names if n == str(existing)]]
	elif positive and isinstance(existing, (list, tuple)) and existing and str(existing[0]).lower() == "in":
		wanted = {str(n) for n in existing[1]}
		filters["name"] = ["in", [n for n in names if n in wanted]]
	# any other mix with a name filter is rare; the name filter is kept as the user set it

	return filters


ROYAL_COLOR_DOCTYPES = ("CRM Task", "CRM Lead", "CRM Deal")
ROYAL_COLOR_KINDS = {"yellow": "today", "red": "overdue", "green": "future"}
ROYAL_DUP_SUFFIX = re.compile(r"__\d+$")


def royal_due_kind(due, today):
	"""Same rule as frontend/src/utils/dueColor.js: red passed, yellow today, green future."""
	if not due:
		return ""
	day = str(due)[:10]
	if day < today:
		return "overdue"
	if day == today:
		return "today"
	return "future"


ROYAL_COLOR_ORDER = ("today", "overdue", "future")  # yellow, red, green


def royal_color_kinds(doctype):
	"""{record name: "today" | "overdue" | "future"} for every record that has a color.
	Tasks use their own due date (Done / Canceled have no color). Leads and Deals use the
	LAST CREATED open task, like the Open Tasks circle."""
	today = str(frappe.utils.getdate(frappe.utils.nowdate()))
	out = {}
	if doctype == "CRM Task":
		for name, due in frappe.db.sql(
			"select name, due_date from `tabCRM Task` where status not in ('Done', 'Canceled')"
		):
			kind = royal_due_kind(due, today)
			if kind:
				out[str(name)] = kind
	else:
		last_due = {}
		for ref, due in frappe.db.sql(
			"select reference_docname, due_date from `tabCRM Task` "
			"where reference_doctype=%s and status not in ('Done', 'Canceled') order by creation asc",
			(doctype,),
		):
			last_due[str(ref)] = due
		for ref, due in last_due.items():
			kind = royal_due_kind(due, today)
			if kind:
				out[ref] = kind
	return out


def royal_color_picked(value):
	"""(positive, kinds) of one "Color is ..." filter. The value can be one color, a list,
	or "Yellow, Red, Green" (all colors)."""
	if isinstance(value, (list, tuple)) and len(value) >= 2:
		op, raw = str(value[0]).lower(), value[1]
	else:
		op, raw = "=", value
	items = raw if isinstance(raw, (list, tuple)) else [raw]
	kinds = set()
	for item in items:
		for part in str(item).split(","):
			kind = ROYAL_COLOR_KINDS.get(part.strip().lower())
			if kind:
				kinds.add(kind)
	return op in ("=", "in", "like"), kinds


def royal_color_filter(doctype, values):
	"""One name filter for all the Color filters on the screen.
	Colors you pick with Is are joined with OR (a record has only one color, so AND would
	always be empty). Is not removes its colors. When more than one color is shown, the
	list is sorted Yellow, then Red, then Green (frappe.local.royal_color_rank)."""
	kinds_of = royal_color_kinds(doctype)
	picked = [royal_color_picked(v) for v in values]
	show = set()
	for positive, kinds in picked:
		if positive:
			show |= kinds
	hide = set()
	for positive, kinds in picked:
		if not positive:
			hide |= kinds
	if not any(positive for positive, _ in picked):
		show = set(ROYAL_COLOR_ORDER)
	show -= hide
	names = [n for n, k in kinds_of.items() if k in show]
	if len(show) > 1:
		frappe.local.royal_color_rank = {n: ROYAL_COLOR_ORDER.index(kinds_of[n]) for n in names}
	return [doctype, "name", "in", names or [""]]


def royal_tag_names(doctype, value):
	"""Record names that have / do not have the chosen tag(s). Same rules as royal_tag_filters."""
	if isinstance(value, (list, tuple)) and len(value) >= 2:
		op, val = str(value[0]).lower(), value[1]
	else:
		op, val = "=", value
	link_filters = {"document_type": doctype}
	if op == "is":
		positive = str(val).lower() == "set"
	else:
		items = val if isinstance(val, (list, tuple)) else [val]
		tags = [str(t).strip("% ").strip() for t in items if t is not None and str(t).strip("% ").strip()]
		if not tags:
			return None
		link_filters["tag"] = ["in", tags]
		positive = op in ("like", "=", "in")
	names = frappe.get_all(
		"Tag Link", filters=link_filters, pluck="document_name", distinct=True, limit_page_length=0
	)
	return positive, [str(n) for n in names]


def royal_extra_filters(doctype, extras):
	"""Filters that need more than a plain column: the Color filter, and any filter that was
	added a second / third time (key `field__2`). Returned as list-style filters, which
	Frappe can repeat, unlike a dict."""
	frappe.local.royal_color_rank = None
	out = []
	colors = []
	for base, value in extras:
		if base == "_due_color" and doctype in ROYAL_COLOR_DOCTYPES:
			colors.append(value)
		elif base == "_user_tags":
			result = royal_tag_names(doctype, value)
			if result:
				positive, names = result
				out.append([doctype, "name", "in" if positive else "not in", names or [""]])
		else:
			out.append(make_filter_tuple(doctype, base, value))
	if colors:
		out.append(royal_color_filter(doctype, colors))
	return out


def royal_split_filters(filters):
	"""Split a filter dict into plain filters and the ones royal_extra_filters must handle."""
	plain, extras = frappe._dict(), []
	for key, value in (filters or {}).items():
		base = ROYAL_DUP_SUFFIX.sub("", key)
		if base != key or base == "_due_color":
			extras.append((base, value))
		else:
			plain[key] = value
	return plain, extras


def royal_list_filters(doctype, filters, extras):
	"""Everything get_data filters by, as one list (plain filters + extras)."""
	out = [make_filter_tuple(doctype, k, v) for k, v in (filters or {}).items()]
	return out + royal_extra_filters(doctype, extras)


ROYAL_NEGATIVE_OPS = ("!=", "not in", "not like", "not between")


def royal_all_filters(doctype, filters):
	"""All filters of a screen as one list. Universal rule (same as Odoo): filters on the SAME
	field are joined with OR when they say "is / has / contains"; filters that exclude
	("is not", "not in", "doesn't have tag") are always ANDed; different fields are ANDed.
	A field can be added as many times as needed (keys `field`, `field__2`, `field__3`)."""
	frappe.local.royal_color_rank = None
	groups = {}
	for key, value in (filters or {}).items():
		groups.setdefault(ROYAL_DUP_SUFFIX.sub("", key), []).append(value)

	out = []
	for base, values in groups.items():
		if base == "_due_color" and doctype in ROYAL_COLOR_DOCTYPES:
			out.append(royal_color_filter(doctype, values))
		elif base == "_user_tags":
			union = None
			for value in values:
				result = royal_tag_names(doctype, value)
				if not result:
					continue
				positive, names = result
				if positive:
					union = (union or set()) | set(names)
				else:
					out.append([doctype, "name", "not in", names or [""]])
			if union is not None:
				out.append([doctype, "name", "in", sorted(union) or [""]])
		else:
			conds = [make_filter_tuple(doctype, base, v) for v in values]
			positives = [c for c in conds if str(c[2]).lower() not in ROYAL_NEGATIVE_OPS]
			out += [c for c in conds if c not in positives]
			if len(positives) == 1:
				out += positives
			elif positives:
				names = set()
				for cond in positives:
					names |= {
						str(n)
						for n in frappe.get_all(doctype, filters=[cond], pluck="name", limit_page_length=0)
					}
				out.append([doctype, "name", "in", sorted(names) or [""]])
	return out


@frappe.whitelist()
def royal_resolve_filters(doctype: str, filters: str | dict):
	"""The same filters get_data uses, as a plain list, so Export gives the same rows as the screen."""
	filters = frappe.parse_json(filters) or {}
	for key in list(filters):
		value = filters[key]
		if value == "@me":
			filters[key] = frappe.session.user
	return royal_all_filters(doctype, filters)


@frappe.whitelist()
def get_data(
	doctype: str,
	filters: dict,
	order_by: str,
	page_length: int = 20,
	page_length_count: int = 20,
	column_field: str | None = None,
	title_field: str | None = None,
	columns: str | list | None = None,
	rows: str | list | None = None,
	kanban_columns: str | list | None = None,
	kanban_fields: str | list | None = None,
	view: str | dict | None = None,
	default_filters: dict | None = None,
):
	custom_view = False
	filters = frappe._dict(filters)
	rows = frappe.parse_json(rows or "[]")
	columns = frappe.parse_json(columns or "[]")
	kanban_fields = frappe.parse_json(kanban_fields or "[]")
	kanban_columns = frappe.parse_json(kanban_columns or "[]")

	custom_view_name = view.get("custom_view_name") if view else None
	view_type = view.get("view_type") if view else None
	group_by_field = view.get("group_by_field") if view else None

	for key in filters:
		value = filters[key]
		if isinstance(value, list):
			if "@me" in value:
				value[value.index("@me")] = frappe.session.user
			elif "%@me%" in value:
				index = [i for i, v in enumerate(value) if v == "%@me%"]
				for i in index:
					value[i] = "%" + frappe.session.user + "%"
		elif value == "@me":
			filters[key] = frappe.session.user

	if default_filters:
		default_filters = frappe.parse_json(default_filters)
		filters.update(default_filters)

	list_filters = royal_all_filters(doctype, filters)
	filters, _royal_extras = royal_split_filters(filters)
	filters = royal_tag_filters(doctype, filters)

	is_default = True
	data = []
	_list = get_controller(doctype)
	default_rows = []
	if hasattr(_list, "default_list_data"):
		default_rows = _list.default_list_data().get("rows")

	meta = frappe.get_meta(doctype)

	if view_type != "kanban":
		if columns or rows:
			custom_view = True
			is_default = False
			columns = frappe.parse_json(columns)
			rows = frappe.parse_json(rows)

		if not columns:
			columns = [
				{"label": "Name", "type": "Data", "key": "name", "width": "16rem"},
				{"label": "Last Modified", "type": "Datetime", "key": "modified", "width": "8rem"},
			]

		if not rows:
			rows = ["name"]

		default_view_filters = {
			"dt": doctype,
			"type": view_type or "list",
			"is_standard": 1,
			"user": frappe.session.user,
		}

		if not custom_view and frappe.db.exists("CRM View Settings", default_view_filters):
			list_view_settings = frappe.get_doc("CRM View Settings", default_view_filters)
			columns = frappe.parse_json(list_view_settings.columns)
			rows = frappe.parse_json(list_view_settings.rows)
			is_default = False
		elif not custom_view or (is_default and hasattr(_list, "default_list_data")):
			rows = default_rows
			columns = _list.default_list_data().get("columns")

		# check if rows has all keys from columns if not add them
		for column in columns:
			if column.get("key") not in rows:
				rows.append(column.get("key"))
			column["label"] = _(column.get("label"))

			# Royal: heading and data are centered together in every list
			if column.get("key") != "_liked_by":
				column["align"] = "center"

			if column.get("key") == "_liked_by" and column.get("width") == "10rem":
				column["width"] = "50px"

			# remove column if column.hidden is True
			column_meta = meta.get_field(column.get("key"))
			if column_meta and column_meta.get("hidden"):
				columns.remove(column)

		# check if rows has group_by_field if not add it
		if group_by_field and group_by_field not in rows:
			rows.append(group_by_field)

		if meta.track_seen and "_seen" not in rows:
			rows.append("_seen")

		# Royal: Notes / Open Tasks columns are counted, not stored in the table
		db_rows = [r for r in rows if r not in ROYAL_COUNT_COLUMNS]
		rank = getattr(frappe.local, "royal_color_rank", None)
		if rank:
			# Royal: all colors shown -> Yellow first, then Red, then Green (newest first in each)
			all_names = frappe.get_list(
				doctype,
				fields=["name"],
				filters=list_filters,
				order_by="modified desc",
				page_length=100000,
			)
			ordered = sorted(
				(str(r.name) for r in all_names),
				key=lambda n: rank.get(n, 9),
			)[:page_length]
			position = {n: i for i, n in enumerate(ordered)}
			data = frappe.get_list(
				doctype,
				fields=db_rows if "name" in db_rows else [*db_rows, "name"],
				filters=[*list_filters, [doctype, "name", "in", ordered or [""]]],
				order_by=order_by,
				page_length=page_length,
			)
			data = sorted(data or [], key=lambda r: position.get(str(r.get("name")), 9999))
		else:
			data = (
				frappe.get_list(
					doctype,
					fields=db_rows,
					filters=list_filters,
					order_by=order_by,
					page_length=page_length,
				)
				or []
			)
		data = parse_list_data(data, doctype)
		royal_add_counts(data, doctype, rows)

	if view_type == "kanban":
		if not rows:
			rows = default_rows

		if not kanban_columns and column_field:
			field_meta = frappe.get_meta(doctype).get_field(column_field)
			if field_meta.fieldtype == "Link":
				kanban_columns = frappe.get_all(
					field_meta.options,
					fields=["name"],
					order_by="modified asc",
				)
			elif field_meta.fieldtype == "Select":
				kanban_columns = [{"name": option} for option in field_meta.options.split("\n")]

		if not title_field:
			title_field = "name"
			if hasattr(_list, "default_kanban_settings"):
				title_field = _list.default_kanban_settings().get("title_field")

		if title_field not in rows:
			rows.append(title_field)

		if not kanban_fields:
			kanban_fields = ["name"]
			if hasattr(_list, "default_kanban_settings"):
				kanban_fields = json.loads(_list.default_kanban_settings().get("kanban_fields"))

		for field in kanban_fields:
			if field not in rows:
				rows.append(field)

		for kc in kanban_columns:
			column_filters = {column_field: kc.get("name")}
			order = kc.get("order")
			if (column_field in filters and filters.get(column_field) != kc.get("name")) or kc.get("delete"):
				column_data = []
			else:
				column_filters.update(filters.copy())
				column_page_length = kc.get("page_length", 20)

				if order:
					column_data = get_records_based_on_order(
						doctype, rows, column_filters, column_page_length, order
					)
				else:
					column_data = frappe.get_list(
						doctype,
						fields=rows,
						filters=convert_filter_to_tuple(doctype, column_filters),
						order_by=order_by,
						page_length=column_page_length,
					)

				new_filters = filters.copy()
				new_filters.update({column_field: kc.get("name")})

				all_count = frappe.get_list(
					doctype,
					filters=convert_filter_to_tuple(doctype, new_filters),
					fields=[COUNT_NAME],
				)[0].total_count

				kc["all_count"] = all_count
				kc["count"] = len(column_data)

				for d in column_data:
					getCounts(d, doctype)

			if order:
				column_data = sorted(
					column_data,
					key=lambda x: order.index(x.get("name")) if x.get("name") in order else len(order),
				)

			data.append({"column": kc, "fields": kanban_fields, "data": column_data})

	fields = frappe.get_meta(doctype).fields
	fields = [field for field in fields if field.fieldtype not in no_value_fields]
	fields = [
		{
			"label": _(field.label),
			"fieldtype": field.fieldtype,
			"fieldname": field.fieldname,
			"options": field.options,
		}
		for field in fields
		if field.label and field.fieldname
	]

	std_fields = [
		{"label": "Name", "fieldtype": "Data", "fieldname": "name"},
		{"label": "Created On", "fieldtype": "Datetime", "fieldname": "creation"},
		{"label": "Last Modified", "fieldtype": "Datetime", "fieldname": "modified"},
		{
			"label": "Modified By",
			"fieldtype": "Link",
			"fieldname": "modified_by",
			"options": "User",
		},
		{"label": "Assigned To", "fieldtype": "Text", "fieldname": "_assign"},
		{"label": "Owner", "fieldtype": "Link", "fieldname": "owner", "options": "User"},
		{"label": "Like", "fieldtype": "Data", "fieldname": "_liked_by"},
	]

	if doctype in ("CRM Lead", "CRM Deal"):
		std_fields += [
			{"label": "Open Tasks", "fieldtype": "Data", "fieldname": "_task_count"},
			{"label": "Notes", "fieldtype": "Data", "fieldname": "_note_count"},
		]

	for field in std_fields:
		if field.get("fieldname") in ROYAL_COUNT_COLUMNS:
			if field not in fields:
				field["label"] = _(field["label"])
				fields.append(field)
			continue
		if field.get("fieldname") not in rows:
			rows.append(field.get("fieldname"))
		if field not in fields:
			field["label"] = _(field["label"])
			fields.append(field)

	if not is_default and custom_view_name:
		is_default = frappe.db.get_value("CRM View Settings", custom_view_name, "load_default_columns")

	if group_by_field and view_type == "group_by":

		def get_options(type, options):
			if type == "Select":
				return [option for option in options.split("\n")]
			else:
				has_empty_values = any([not d.get(group_by_field) for d in data])
				options = list(set([d.get(group_by_field) for d in data]))
				options = [u for u in options if u]
				if has_empty_values:
					options.append("")

				if order_by and group_by_field in order_by:
					order_by_fields = order_by.split(",")
					order_by_fields = [
						(field.split(" ")[0], field.split(" ")[1]) for field in order_by_fields
					]
					if (group_by_field, "asc") in order_by_fields:
						options.sort()
					elif (group_by_field, "desc") in order_by_fields:
						options.sort(reverse=True)
				else:
					options.sort()
				return options

		for field in fields:
			if field.get("fieldname") == group_by_field:
				group_by_field = {
					"label": field.get("label"),
					"fieldname": field.get("fieldname"),
					"fieldtype": field.get("fieldtype"),
					"options": get_options(field.get("fieldtype"), field.get("options")),
				}

	return {
		"data": data,
		"columns": columns,
		"rows": rows,
		"fields": fields,
		"column_field": column_field,
		"title_field": title_field,
		"kanban_columns": kanban_columns,
		"kanban_fields": kanban_fields,
		"group_by_field": group_by_field,
		"page_length": page_length,
		"page_length_count": page_length_count,
		"is_default": is_default,
		"views": get_views(doctype),
		"total_count": frappe.get_list(doctype, filters=list_filters, fields=[COUNT_NAME])[0].total_count,
		"row_count": len(data),
		"form_script": get_form_script(doctype),
		"list_script": get_form_script(doctype, "List"),
		"view_type": view_type,
	}


def parse_list_data(data, doctype):
	_list = get_controller(doctype)
	if hasattr(_list, "parse_list_data"):
		data = _list.parse_list_data(data)
	return data


def convert_filter_to_tuple(doctype, filters):
	if isinstance(filters, dict):
		filters_items = filters.items()
		filters = []
		for key, value in filters_items:
			filters.append(make_filter_tuple(doctype, key, value))
	return filters


def get_records_based_on_order(doctype, rows, filters, page_length, order):
	records = []
	filters = convert_filter_to_tuple(doctype, filters)
	in_filters = filters.copy()
	in_filters.append([doctype, "name", "in", order[:page_length]])
	records = frappe.get_list(
		doctype,
		fields=rows,
		filters=in_filters,
		order_by="creation desc",
		page_length=page_length,
	)

	if len(records) < page_length:
		not_in_filters = filters.copy()
		not_in_filters.append([doctype, "name", "not in", order])
		remaining_records = frappe.get_list(
			doctype,
			fields=rows,
			filters=not_in_filters,
			order_by="creation desc",
			page_length=page_length - len(records),
		)
		for record in remaining_records:
			records.append(record)

	return records


@frappe.whitelist()
def remove_assignments(doctype: str, name: str, assignees: str | list, ignore_permissions: bool = False):
	assignees = frappe.parse_json(assignees)

	if not assignees:
		return

	for assign_to in assignees:
		set_status(
			doctype,
			name,
			todo=None,
			assign_to=assign_to,
			status="Cancelled",
			ignore_permissions=ignore_permissions,
		)


@frappe.whitelist()
def add_seen(doctype: str, name: str):
	doc = frappe.get_doc(doctype, name)
	doc.check_permission("read")
	doc.add_seen()


@frappe.whitelist()
def get_assigned_users(doctype: str, name: str | int, default_assigned_to: str | None = None):
	assigned_users = frappe.get_all(
		"ToDo",
		fields=["allocated_to"],
		filters={
			"reference_type": doctype,
			"reference_name": name,
			"status": ("not in", ("Closed", "Cancelled")),
		},
		pluck="allocated_to",
	)

	users = list(set(assigned_users))

	# if users is empty, add default_assigned_to
	if not users and default_assigned_to:
		users = [default_assigned_to]
	return users


@frappe.whitelist()
def get_fields(doctype: str, allow_all_fieldtypes: bool = False):
	not_allowed_fieldtypes = [*list(frappe.model.no_value_fields), "Read Only"]
	if allow_all_fieldtypes:
		not_allowed_fieldtypes = []
	fields = frappe.get_meta(doctype).fields

	_fields = []

	for field in fields:
		if field.fieldtype not in not_allowed_fieldtypes and field.fieldname:
			_fields.append(field)

	return _fields


ROYAL_COUNT_COLUMNS = ("_task_count", "_note_count")


def royal_add_counts(data, doctype, rows):
	"""Fill _task_count (open tasks) and _note_count when a list asks for them.
	Never breaks the list: on any error the cells show "-" and the error is logged."""
	if not data or not any(r in rows for r in ROYAL_COUNT_COLUMNS):
		return
	names = tuple(d.get("name") for d in data)

	def grouped(table, extra=""):
		return dict(
			frappe.db.sql(
				f"select reference_docname, count(*) from `tab{table}` "
				f"where reference_doctype=%s and reference_docname in %s {extra} "
				"group by reference_docname",
				(doctype, names),
			)
		)

	try:
		if "_task_count" in rows:
			counts = grouped("CRM Task", "and status not in ('Done', 'Canceled')")
			# due date of the LAST CREATED open task of each record (oldest first, last one wins)
			last_due = {}
			for ref, due in frappe.db.sql(
				"select reference_docname, due_date from `tabCRM Task` "
				"where reference_doctype=%s and reference_docname in %s "
				"and status not in ('Done', 'Canceled') order by creation asc",
				(doctype, names),
			):
				last_due[str(ref)] = str(due) if due else ""
			for d in data:
				d["_task_count"] = str(counts.get(str(d.get("name")), 0))
				d["_task_due"] = last_due.get(str(d.get("name")), "")
		if "_note_count" in rows:
			counts = grouped("FCRM Note")
			for d in data:
				d["_note_count"] = str(counts.get(str(d.get("name")), 0))
	except Exception:
		frappe.log_error(title="Royal counts failed")
		for d in data:
			d.setdefault("_task_count", "-")
			d.setdefault("_task_due", "")
			d.setdefault("_note_count", "-")


def getCounts(d, doctype):
	d["_email_count"] = (
		frappe.db.count(
			"Communication",
			filters={
				"reference_doctype": doctype,
				"reference_name": d.get("name"),
				"communication_type": "Communication",
			},
		)
		or 0
	)
	d["_email_count"] = d["_email_count"] + frappe.db.count(
		"Communication",
		filters={
			"reference_doctype": doctype,
			"reference_name": d.get("name"),
			"communication_type": "Automated Message",
		},
	)
	d["_comment_count"] = frappe.db.count(
		"Comment",
		filters={"reference_doctype": doctype, "reference_name": d.get("name"), "comment_type": "Comment"},
	)
	d["_task_count"] = frappe.db.count(
		"CRM Task", filters={"reference_doctype": doctype, "reference_docname": d.get("name")}
	)
	d["_note_count"] = frappe.db.count(
		"FCRM Note", filters={"reference_doctype": doctype, "reference_docname": d.get("name")}
	)
	return d


@frappe.whitelist()
def get_linked_docs_of_document(doctype: str, docname: str):
	try:
		doc = frappe.get_doc(doctype, docname)
	except frappe.DoesNotExistError:
		return []

	linked_docs = get_linked_docs(doc)
	dynamic_linked_docs = get_dynamic_linked_docs(doc)

	linked_docs.extend(dynamic_linked_docs)
	linked_docs = list({doc["reference_docname"]: doc for doc in linked_docs}.values())

	docs_data = []
	for doc in linked_docs:
		if not doc.get("reference_doctype") or not doc.get("reference_docname"):
			continue

		try:
			data = frappe.get_doc(doc["reference_doctype"], doc["reference_docname"])
		except (frappe.DoesNotExistError, frappe.ValidationError):
			continue

		title = data.get("title")
		if data.doctype == "CRM Call Log":
			title = f"Call from {data.get('from')} to {data.get('to')}"

		if data.doctype == "CRM Deal":
			title = data.get("organization")

		if data.doctype == "CRM Notification":
			title = data.get("message")

		docs_data.append(
			{
				"doc": data.doctype,
				"title": title or data.get("name"),
				"reference_docname": doc["reference_docname"],
				"reference_doctype": doc["reference_doctype"],
			}
		)
	return docs_data


def remove_doc_link(doctype, docname):
	if not doctype or not docname:
		return

	try:
		linked_doc_data = frappe.get_doc(doctype, docname)
		if doctype == "CRM Notification":
			delete_notification_type = {
				"notification_type_doctype": "",
				"notification_type_doc": "",
			}
			delete_references = {
				"reference_doctype": "",
				"reference_name": "",
			}
			if linked_doc_data.get("notification_type_doctype") == linked_doc_data.get("reference_doctype"):
				delete_references.update(delete_notification_type)

			linked_doc_data.update(delete_references)
		else:
			linked_doc_data.update(
				{
					"reference_doctype": "",
					"reference_docname": "",
				}
			)
		linked_doc_data.save(ignore_permissions=True)
	except (frappe.DoesNotExistError, frappe.ValidationError):
		pass


def remove_contact_link(doctype, docname):
	if not doctype or not docname:
		return

	try:
		linked_doc_data = frappe.get_doc(doctype, docname)
		linked_doc_data.update(
			{
				"contact": None,
				"contacts": [],
			}
		)
		linked_doc_data.save(ignore_permissions=True)
	except (frappe.DoesNotExistError, frappe.ValidationError):
		pass


@frappe.whitelist()
def remove_linked_doc_reference(items: str | list, remove_contact: bool = False, delete: bool = False):
	if isinstance(items, str):
		items = frappe.parse_json(items)

	for item in items:
		if not item.get("doctype") or not item.get("docname"):
			continue

		if not frappe.has_permission(item["doctype"], "write", item["docname"]):
			continue

		try:
			if remove_contact:
				remove_contact_link(item["doctype"], item["docname"])
			else:
				remove_doc_link(item["doctype"], item["docname"])
			if delete:
				frappe.delete_doc(item["doctype"], item["docname"])
		except (frappe.DoesNotExistError, frappe.ValidationError):
			# Skip if document doesn't exist or has validation errors
			continue

	return "success"


@frappe.whitelist()
def delete_bulk_docs(doctype: str, items: str | list, delete_linked: bool = False):
	from frappe.desk.reportview import delete_bulk

	if not doctype:
		frappe.throw(_("Doctype is required"))

	if not items:
		frappe.throw(_("Items are required"))

	items = frappe.parse_json(items)
	if not isinstance(items, list):
		frappe.throw(_("Items must be a list"))

	for doc in items:
		try:
			if not frappe.db.exists(doctype, doc):
				frappe.log_error(f"Document {doctype} {doc} does not exist", "Bulk Delete Error")
				continue

			linked_docs = get_linked_docs_of_document(doctype, doc)
			for linked_doc in linked_docs:
				if not linked_doc.get("reference_doctype") or not linked_doc.get("reference_docname"):
					continue

				remove_linked_doc_reference(
					[
						{
							"doctype": linked_doc["reference_doctype"],
							"docname": linked_doc["reference_docname"],
						}
					],
					remove_contact=doctype == "Contact",
					delete=delete_linked,
				)
		except Exception as e:
			frappe.log_error(f"Error processing linked docs for {doctype} {doc}: {e!s}", "Bulk Delete Error")

	if len(items) > 10:
		frappe.enqueue("frappe.desk.reportview.delete_bulk", doctype=doctype, items=items)
	else:
		delete_bulk(doctype, items)
	return "success"


def _royal_delete_one(doctype: str, name: str):
	if not frappe.has_permission(doctype, "delete", name):
		frappe.throw(_("You do not have permission to delete this record"), frappe.PermissionError)

	frappe.db.delete("CRM Notification", {"reference_doctype": doctype, "reference_name": name})
	frappe.db.delete(
		"CRM Notification", {"notification_type_doctype": doctype, "notification_type_doc": name}
	)

	if doctype in ("CRM Lead", "CRM Deal"):
		for child in ("CRM Task", "FCRM Note"):
			for child_name in frappe.get_all(
				child, filters={"reference_doctype": doctype, "reference_docname": name}, pluck="name"
			):
				frappe.delete_doc(child, child_name, force=True, ignore_permissions=True)

	frappe.delete_doc(doctype, name, force=True)


@frappe.whitelist(methods=["POST"])
def royal_delete(doctype: str, name: str | int):
	# Royal: one-click delete for Leads, Deals and Tasks. Removes what hangs off the record
	# (notifications, and for leads/deals their tasks and notes) so nothing blocks the delete.
	# Any failure is turned into a readable message instead of a bare "Internal Server Error".
	import traceback

	if doctype not in ("CRM Lead", "CRM Deal", "CRM Task"):
		frappe.throw(_("Not allowed for {0}").format(doctype), frappe.PermissionError)

	name = str(name)

	try:
		_royal_delete_one(doctype, name)
	except (frappe.PermissionError, frappe.ValidationError):
		raise
	except Exception as e:
		tb = traceback.format_exc()
		frappe.log_error(tb, f"Royal delete failed: {doctype} {name}")
		last = [line for line in tb.strip().splitlines() if line.strip()][-4:]
		frappe.throw(f"Delete failed: {type(e).__name__}: {e} | " + " | ".join(l.strip() for l in last))
	return "success"


@frappe.whitelist(methods=["POST"])
def royal_delete_bulk(doctype: str, items: str | list):
	items = frappe.parse_json(items) if isinstance(items, str) else items
	for name in items or []:
		royal_delete(doctype, name)
	return "success"
