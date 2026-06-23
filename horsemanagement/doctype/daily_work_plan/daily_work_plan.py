# Copyright (c) 2026, Keenan Solomon and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, now_datetime, today


TODO_PRIORITY = {
	"Urgent": "High",
	"High": "High",
	"Medium": "Medium",
	"Low": "Low",
}


class DailyWorkPlan(Document):
	def before_insert(self):
		self.workflow_state = self.workflow_state or "HM Draft"

	def validate(self):
		if getdate(self.plan_date) < getdate(today()):
			frappe.throw(_("A Daily Work Plan cannot be created for a past date."))
		if self.docstatus == 0 and self.workflow_state not in {"HM Draft", "HM Published"}:
			frappe.throw(_("A draft Daily Work Plan must use the HM Draft state."))

	def before_submit(self):
		if getdate(self.plan_date) < getdate(today()):
			frappe.throw(_("A past Daily Work Plan cannot be published."))

		tasks = frappe.get_all(
			"Daily Groom Task",
			filters={"daily_work_plan": self.name},
			fields=["name", "assigned_groom"],
		)
		task_count = len(tasks)
		if not task_count:
			frappe.throw(_("Add at least one Daily Groom Task before publishing the plan."))
		missing_groom = [task.name for task in tasks if not task.assigned_groom]
		if missing_groom:
			frappe.throw(
				_("Every Daily Groom Task must have an Assigned Groom before publication.")
			)

		self.task_count = task_count
		self.workflow_state = "HM Published"
		self.published_at = now_datetime()
		self.published_by = frappe.session.user

	def on_submit(self):
		create_todos_for_plan(self.name)


def create_todos_for_plan(plan_name):
	tasks = frappe.get_all(
		"Daily Groom Task",
		filters={"daily_work_plan": plan_name},
		fields=[
			"name",
			"task_title",
			"horse",
			"assigned_groom",
			"planned_start",
			"priority",
			"todo",
		],
	)

	for task in tasks:
		todo_name = get_or_create_task_todo(task)
		if task.todo != todo_name:
			frappe.db.set_value(
				"Daily Groom Task",
				task.name,
				"todo",
				todo_name,
				update_modified=False,
			)


def get_or_create_task_todo(task):
	existing = task.todo or frappe.db.get_value(
		"ToDo",
		{
			"reference_type": "Daily Groom Task",
			"reference_name": task.name,
			"allocated_to": task.assigned_groom,
		},
		"name",
	)
	if existing:
		if frappe.db.get_value("ToDo", existing, "status") == "Cancelled":
			frappe.db.set_value("ToDo", existing, "status", "Open", update_modified=False)
		return existing

	description = _("Daily Groom Task: {0} for {1}").format(
		task.task_title,
		task.horse,
	)
	todo = frappe.get_doc(
		{
			"doctype": "ToDo",
			"status": "Open",
			"priority": TODO_PRIORITY.get(task.priority, "Medium"),
			"date": getdate(task.planned_start),
			"allocated_to": task.assigned_groom,
			"description": description,
			"reference_type": "Daily Groom Task",
			"reference_name": task.name,
			"assigned_by": frappe.session.user,
		}
	)
	todo.insert(ignore_permissions=True)
	return todo.name
