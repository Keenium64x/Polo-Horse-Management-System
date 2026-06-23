from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, today

from horsemanagement import permissions


class IntegrationTestHorseManagementSecurity(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.groom_user = cls.make_user("security-groom@example.com", "Horse Groom")
		cls.other_groom_user = cls.make_user("security-other-groom@example.com", "Horse Groom")
		cls.owner_user = cls.make_user("security-owner@example.com", "Horse Owner")

	@classmethod
	def make_user(cls, email, role):
		if not frappe.db.exists("User", email):
			frappe.get_doc(
				{
					"doctype": "User",
					"email": email,
					"first_name": email.split("@")[0],
					"enabled": 1,
					"send_welcome_email": 0,
					"user_type": "System User",
				}
			).insert(ignore_permissions=True)

		user = frappe.get_doc("User", email)
		user.add_roles(role)
		return email

	def setUp(self):
		frappe.set_user("Administrator")

	def tearDown(self):
		frappe.set_user("Administrator")

	def test_security_roles_and_workflow_states_are_installed(self):
		self.assertTrue(frappe.db.exists("Role", "Horse Owner"))
		self.assertTrue(frappe.db.exists("Role", "Horse Groom"))
		self.assertFalse(frappe.db.exists("Role", "Groom"))

		for state in (
			"HM Draft",
			"HM Published",
			"HM In Progress",
			"HM Completed",
			"HM Not Completed",
			"HM Skipped",
			"HM Submitted",
			"HM Reviewed",
			"HM Overdue",
		):
			self.assertTrue(frappe.db.exists("Workflow State", state))

	def test_groom_can_read_but_cannot_edit_horse(self):
		self.assertIn("Horse Groom", frappe.get_roles(self.groom_user))
		self.assertNotIn("Horse Owner", frappe.get_roles(self.groom_user))
		self.assertNotIn("System Manager", frappe.get_roles(self.groom_user))

		horse_name = frappe.get_doc(
			{
				"doctype": "Horse",
				"horse_name": f"Permission Horse {frappe.generate_hash(length=8)}",
			}
		).insert(ignore_permissions=True).name
		horse = frappe.get_doc("Horse", horse_name)

		self.assertTrue(horse.has_permission("read", user=self.groom_user))
		self.assertFalse(horse.has_permission("write", user=self.groom_user))

		with self.set_user(self.groom_user):
			horse = frappe.get_doc("Horse", horse_name)
			horse.description = "A groom must not be able to save this."
			self.assertRaises(frappe.PermissionError, horse.save)

	def test_groom_cannot_read_ownership_or_settings(self):
		with self.set_user(self.groom_user):
			self.assertFalse(frappe.has_permission("Horse Owner", "read"))
			self.assertFalse(frappe.has_permission("Horse Management Settings", "read"))

			horse = frappe.new_doc("Horse")
			self.assertFalse(horse.has_permlevel_access_to("primary_owner", permission_type="read"))
			self.assertFalse(horse.has_permlevel_access_to("passport_number", permission_type="read"))

	def test_owner_can_edit_horse_and_settings(self):
		self.assertTrue(frappe.has_permission("Horse", "create", user=self.owner_user))
		self.assertTrue(frappe.has_permission("Horse", "write", user=self.owner_user))
		self.assertTrue(frappe.has_permission("Horse Management Settings", "write", user=self.owner_user))

		with self.set_user(self.owner_user):
			horse = frappe.new_doc("Horse")
			self.assertTrue(horse.has_permlevel_access_to("primary_owner", permission_type="write"))
			self.assertTrue(horse.has_permlevel_access_to("passport_number", permission_type="write"))

	def test_groom_task_query_is_filtered_to_assigned_user(self):
		condition = permissions.get_permission_query_conditions(
			self.groom_user,
			doctype="Daily Groom Task",
		)

		self.assertIn("assigned_groom", condition)
		self.assertIn(self.groom_user, condition)

	def test_groom_cannot_access_another_grooms_task(self):
		task = frappe._dict(
			doctype="Daily Groom Task",
			docstatus=0,
			assigned_groom=self.other_groom_user,
			status="Pending",
		)

		self.assertFalse(
			permissions.has_operational_permission(
				task,
				ptype="read",
				user=self.groom_user,
			)
		)
		self.assertFalse(
			permissions.has_operational_permission(
				task,
				ptype="write",
				user=self.groom_user,
			)
		)

	def test_assigned_groom_can_update_current_but_not_final_task(self):
		task = frappe._dict(
			doctype="Daily Groom Task",
			docstatus=0,
			assigned_groom=self.groom_user,
			status="Pending",
		)
		self.assertTrue(
			permissions.has_operational_permission(
				task,
				ptype="write",
				user=self.groom_user,
			)
		)

		task.status = "Completed"
		self.assertTrue(
			permissions.has_operational_permission(
				task,
				ptype="write",
				user=self.groom_user,
			)
		)
		self.assertTrue(
			permissions.has_operational_permission(
				task,
				ptype="submit",
				user=self.groom_user,
			)
		)

		task.docstatus = 1
		self.assertFalse(
			permissions.has_operational_permission(
				task,
				ptype="write",
				user=self.groom_user,
			)
		)
		self.assertFalse(
			permissions.has_operational_permission(
				task,
				ptype="cancel",
				user=self.groom_user,
			)
		)

	def test_owner_must_amend_instead_of_editing_submitted_records(self):
		submitted_task = frappe._dict(
			doctype="Daily Groom Task",
			docstatus=1,
			status="Completed",
		)

		self.assertFalse(
			permissions.has_operational_permission(
				submitted_task,
				ptype="write",
				user=self.owner_user,
			)
		)
		self.assertTrue(
			permissions.has_operational_permission(
				submitted_task,
				ptype="cancel",
				user=self.owner_user,
			)
		)
		self.assertTrue(
			permissions.has_operational_permission(
				submitted_task,
				ptype="amend",
				user=self.owner_user,
			)
		)

	def test_published_plan_and_past_report_are_immutable(self):
		published_plan = frappe._dict(
			doctype="Daily Work Plan",
			docstatus=1,
			workflow_state="HM Published",
			plan_date=add_days(today(), 1),
		)
		past_report = frappe._dict(
			doctype="Daily Groom Report",
			docstatus=0,
			groom=self.groom_user,
			report_date=add_days(today(), -1),
			workflow_state="HM Draft",
		)

		self.assertFalse(permissions.owner_permission(published_plan, "write"))
		self.assertFalse(permissions.groom_permission(past_report, "write", self.groom_user))

	def test_groom_cannot_cancel_or_amend(self):
		task = frappe._dict(
			doctype="Daily Groom Task",
			docstatus=1,
			assigned_groom=self.groom_user,
			status="Completed",
		)

		for permission_type in ("cancel", "amend"):
			self.assertFalse(
				permissions.has_operational_permission(
					task,
					ptype=permission_type,
					user=self.groom_user,
				)
			)

	def test_groom_can_only_read_published_assigned_plan(self):
		plan = frappe._dict(
			doctype="Daily Work Plan",
			name="TEST-PLAN",
			docstatus=1,
			workflow_state="HM Published",
		)

		with patch("horsemanagement.permissions.groom_has_task_on_plan", return_value=True):
			self.assertTrue(permissions.groom_permission(plan, "read", self.groom_user))
			self.assertFalse(permissions.groom_permission(plan, "write", self.groom_user))

	def test_settings_reject_zero_generation_horizon(self):
		settings = frappe.get_doc("Horse Management Settings")
		settings.days_ahead_to_generate = 0

		self.assertRaises(frappe.ValidationError, settings.save, ignore_permissions=True)
