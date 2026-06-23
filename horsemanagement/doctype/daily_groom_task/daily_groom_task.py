# Copyright (c) 2026, Keenan Solomon and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, get_datetime, now_datetime

from horsemanagement.permissions import ADMIN_ROLES, OWNER_ROLES, has_any_role


STATUSES = frozenset({"Pending", "In Progress", "Completed", "Not Completed", "Skipped"})
FINAL_STATUSES = frozenset({"Completed", "Not Completed", "Skipped"})
EXCEPTION_STATUSES = frozenset({"Not Completed", "Skipped"})
GROOM_FINAL_STATUSES = frozenset({"Completed", "Not Completed"})


class DailyGroomTask(Document):
	def validate(self):
		if self.status not in STATUSES:
			frappe.throw(_("Invalid Daily Groom Task status: {0}").format(self.status))
		if flt(self.duration) <= 0:
			frappe.throw(_("Duration must be greater than zero."))
		if get_datetime(self.planned_end) <= get_datetime(self.planned_start):
			frappe.throw(_("Planned End must be after Planned Start."))

		plan = frappe.db.get_value(
			"Daily Work Plan",
			self.daily_work_plan,
			["plan_date", "stable"],
			as_dict=True,
		)
		if plan:
			self.plan_date = plan.plan_date
			self.stable = plan.stable

		if self.status in FINAL_STATUSES and getattr(self, "_action", None) != "submit":
			self.validate_completion_permission()
		self.set_completion_timestamps()
		self.validate_completion_requirements()

	def on_update(self):
		if self.docstatus == 0 and self.status in FINAL_STATUSES and not self.flags.in_auto_submit:
			self.flags.in_auto_submit = True
			self.flags.ignore_permissions = True
			self.submit()

	def before_submit(self):
		if self.status not in FINAL_STATUSES:
			frappe.throw(_("Select a final status before submitting a Daily Groom Task."))
		self.validate_completion_permission()
		self.set_completion_timestamps()
		self.validate_completion_requirements()

	def on_submit(self):
		close_linked_todo(self)

	def set_completion_timestamps(self):
		if self.status == "In Progress" and not self.started_at:
			self.started_at = now_datetime()
		if self.status in FINAL_STATUSES:
			if not self.started_at:
				self.started_at = now_datetime()
			if not self.completed_at:
				self.completed_at = now_datetime()

	def validate_completion_requirements(self):
		if self.status in EXCEPTION_STATUSES and not self.exception_reason:
			frappe.throw(_("{0} requires an Exception Reason.").format(self.status))
		if (
			self.status == "Completed"
			and self.photograph_required
			and not self.completion_photographs
		):
			frappe.throw(_("At least one photograph is required to complete this task."))

	def validate_completion_permission(self):
		user = frappe.session.user
		if user == "Administrator" or has_any_role(user, ADMIN_ROLES):
			return

		if self.status in GROOM_FINAL_STATUSES:
			if self.assigned_groom != user:
				frappe.throw(
					_("Only the assigned groom can complete or mark this task not completed."),
					frappe.PermissionError,
				)
			return

		if self.status == "Skipped":
			if not has_any_role(user, OWNER_ROLES):
				frappe.throw(
					_("Only an owner or yard manager may skip a Daily Groom Task."),
					frappe.PermissionError,
				)
			return

		frappe.throw(_("You are not permitted to finalise this Daily Groom Task."), frappe.PermissionError)


def close_linked_todo(task):
	todo_names = set(
		frappe.get_all(
			"ToDo",
			filters={
				"reference_type": "Daily Groom Task",
				"reference_name": task.name,
				"status": ["!=", "Closed"],
			},
			pluck="name",
		)
	)
	if task.todo:
		todo_names.add(task.todo)

	for todo_name in todo_names:
		if frappe.db.exists("ToDo", todo_name):
			frappe.db.set_value("ToDo", todo_name, "status", "Closed", update_modified=False)
