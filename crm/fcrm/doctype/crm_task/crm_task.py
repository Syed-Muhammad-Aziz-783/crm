# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from frappe.desk.form.assign_to import add as assign
from frappe.desk.form.assign_to import remove as unassign
from frappe.model.document import Document


class CRMTask(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		assigned_to: DF.Link | None
		description: DF.TextEditor | None
		due_date: DF.Datetime | None
		name: DF.Int | None
		priority: DF.Literal["Low", "Medium", "High"]
		reference_docname: DF.DynamicLink | None
		reference_doctype: DF.Link | None
		start_date: DF.Date | None
		status: DF.Literal["Backlog", "Todo", "In Progress", "Done", "Canceled"]
		title: DF.Data
	# end: auto-generated types

	def before_validate(self):
		# Royal: tasks are only Todo or Done. Anything else (old default Backlog) becomes Todo.
		if self.status not in ("Todo", "Done"):
			self.status = "Todo"

		# Royal: title is optional on the form. Auto-fill it from the description.
		if not (self.title or "").strip():
			from frappe.utils import strip_html

			text = " ".join(strip_html(self.description or "").split())
			self.title = text[:80] or self.get("lead_name") or "Task"

	def after_insert(self):
		self.assign_to()

	def validate_required(self):
		# Royal: a task needs a due date and an assignee. Old tasks that never had
		# them can still be edited (for example marked Done); only new tasks, or
		# clearing a value that was set, are blocked.
		import frappe
		from frappe import _

		before = None if self.is_new() else self.get_doc_before_save()
		for fieldname, label in (("due_date", "Due Date"), ("assigned_to", "Assigned To")):
			if self.get(fieldname):
				continue
			if self.is_new() or (before and before.get(fieldname)):
				frappe.throw(_("{0} is required").format(_(label)), frappe.MandatoryError)

	def validate(self):
		self.validate_required()
		if self.is_new() or not self.assigned_to:
			return

		if self.get_doc_before_save().assigned_to != self.assigned_to:
			self.unassign_from_previous_user(self.get_doc_before_save().assigned_to)
			self.assign_to()

	def unassign_from_previous_user(self, user: str | None):
		if user:
			unassign(self.doctype, self.name, user)

	def assign_to(self):
		if self.assigned_to:
			assign(
				{
					"assign_to": [self.assigned_to],
					"doctype": self.doctype,
					"name": self.name,
					"description": self.title or self.description,
				}
			)

	@staticmethod
	def default_list_data():
		# Royal: Due Date, Lead Name, Phone, Description, Status, Assigned To
		columns = [
			{"label": "Due Date", "type": "Date", "key": "due_date", "width": "8rem"},
			{"label": "Lead Name", "type": "Data", "key": "lead_name", "width": "14rem"},
			{"label": "Phone", "type": "Data", "key": "lead_phone", "width": "10rem"},
			{"label": "Description", "type": "Text Editor", "key": "description", "width": "16rem"},
			{"label": "Status", "type": "Select", "key": "status", "width": "8rem"},
			{"label": "Assigned To", "type": "Link", "key": "assigned_to", "width": "10rem"},
		]

		rows = [
			"name",
			"lead_name",
			"lead_phone",
			"title",
			"description",
			"assigned_to",
			"due_date",
			"status",
			"priority",
			"reference_doctype",
			"reference_docname",
			"modified",
		]
		return {"columns": columns, "rows": rows}

	@staticmethod
	def default_kanban_settings():
		return {
			"column_field": "status",
			"title_field": "title",
			"kanban_fields": '["description", "priority", "creation"]',
		}
