import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, getdate, today

from horsemanagement.daily_planning import (
	generate_plans_for_date,
	process_daily_planning_schedule,
	publish_plans_for_date,
)


class IntegrationTestDailyWorkPlan(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.groom_user = cls.make_user("daily-plan-groom@example.com", "Horse Groom")
		cls.other_groom_user = cls.make_user("daily-plan-other-groom@example.com", "Horse Groom")
		cls.owner_user = cls.make_user("daily-plan-owner@example.com", "Horse Owner")
		cls.date_offset = 10

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
		frappe.clear_cache(user=email)
		return email

	def setUp(self):
		frappe.set_user("Administrator")
		self.suffix = frappe.generate_hash(length=8)
		self.__class__.date_offset += 1
		self.plan_date = getdate(add_days(today(), self.__class__.date_offset))
		self.stable = self.make_location(f"Plan Stable {self.suffix}", "Stable")
		self.horse = self.make_horse(f"Plan Horse {self.suffix}", self.stable.name)

	def tearDown(self):
		frappe.set_user("Administrator")

	def test_generation_creates_plan_and_snapshot_task(self):
		template = self.make_template(
			template_name=f"Snapshot Care {self.suffix}",
			horse=self.horse.name,
			instructions="Original instructions",
		)

		plans = generate_plans_for_date(self.plan_date, source="Manual")
		self.assertEqual(len(plans), 1)

		plan = frappe.get_doc("Daily Work Plan", plans[0])
		tasks = frappe.get_all(
			"Daily Groom Task",
			filters={"daily_work_plan": plan.name},
			fields=["name"],
		)
		self.assertEqual(plan.plan_date, self.plan_date)
		self.assertEqual(plan.stable, self.stable.name)
		self.assertEqual(plan.task_count, 1)
		self.assertEqual(len(tasks), 1)

		task = frappe.get_doc("Daily Groom Task", tasks[0].name)
		self.assertEqual(task.horse, self.horse.name)
		self.assertEqual(task.assigned_groom, self.groom_user)
		self.assertEqual(task.instructions, "Original instructions")
		self.assertEqual(task.original_template, template.name)
		self.assertEqual(task.original_template_item, template.items[0].name)
		self.assertEqual(task.template_version, 1)
		self.assertEqual(task.duration, 1800)

		template.items[0].instructions = "Changed after generation"
		template.save(ignore_permissions=True)
		task.reload()
		self.assertEqual(task.instructions, "Original instructions")

	def test_generation_is_idempotent(self):
		self.make_template(template_name=f"Idempotent Care {self.suffix}", horse=self.horse.name)

		first_plans = generate_plans_for_date(self.plan_date)
		second_plans = generate_plans_for_date(self.plan_date)

		self.assertEqual(first_plans, second_plans)
		self.assertEqual(
			frappe.db.count("Daily Work Plan", {"plan_date": self.plan_date, "stable": self.stable.name}),
			1,
		)
		self.assertEqual(
			frappe.db.count("Daily Groom Task", {"daily_work_plan": first_plans[0]}),
			1,
		)

	def test_horse_group_and_stable_templates_expand_to_individual_tasks(self):
		second_horse = self.make_horse(f"Second Plan Horse {self.suffix}", self.stable.name)
		group = frappe.get_doc(
			{
				"doctype": "Horse Group",
				"group_name": f"Plan Group {self.suffix}",
				"horses": [
					{"horse": self.horse.name},
					{"horse": second_horse.name},
				],
			}
		).insert(ignore_permissions=True)
		self.make_template(
			template_name=f"Group Plan {self.suffix}",
			target_type="Horse Group",
			horse_group=group.name,
			horse=None,
		)
		self.make_template(
			template_name=f"Stable Plan {self.suffix}",
			target_type="Stable",
			stable=self.stable.name,
			horse=None,
		)

		plans = generate_plans_for_date(self.plan_date)
		tasks = frappe.get_all(
			"Daily Groom Task",
			filters={"daily_work_plan": plans[0]},
			fields=["horse", "source_target_type"],
		)

		self.assertEqual(len(tasks), 4)
		self.assertEqual({task.horse for task in tasks}, {self.horse.name, second_horse.name})
		self.assertEqual(
			{task.source_target_type for task in tasks},
			{"Horse Group", "Stable"},
		)

	def test_only_latest_active_template_version_generates(self):
		version_one = self.make_template(
			template_name=f"Versioned Plan {self.suffix}",
			horse=self.horse.name,
			instructions="Version one",
		)
		self.make_template(
			template_name=f"Versioned Plan {self.suffix}",
			version_number=2,
			previous_version=version_one.name,
			horse=self.horse.name,
			instructions="Version two",
		)

		plans = generate_plans_for_date(self.plan_date)
		tasks = frappe.get_all(
			"Daily Groom Task",
			filters={"daily_work_plan": plans[0]},
			fields=["instructions", "template_version"],
		)

		self.assertEqual(len(tasks), 1)
		self.assertEqual(tasks[0].instructions, "Version two")
		self.assertEqual(tasks[0].template_version, 2)

	def test_inactive_expired_and_wrong_weekday_items_do_not_generate(self):
		expired = self.make_template(
			template_name=f"Expired Plan {self.suffix}",
			horse=self.horse.name,
			active_from=today(),
			active_until=today(),
		)
		inactive = self.make_template(
			template_name=f"Inactive Plan {self.suffix}",
			horse=self.horse.name,
			is_active=0,
		)
		wrong_weekday = self.make_template(
			template_name=f"Wrong Weekday Plan {self.suffix}",
			horse=self.horse.name,
		)
		for weekday in (
			"monday",
			"tuesday",
			"wednesday",
			"thursday",
			"friday",
			"saturday",
			"sunday",
		):
			wrong_weekday.items[0].set(weekday, 0)
		wrong_weekday.items[0].set(
			("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")[
				(self.plan_date.weekday() + 1) % 7
			],
			1,
		)
		wrong_weekday.save(ignore_permissions=True)

		plans = generate_plans_for_date(self.plan_date)

		self.assertEqual(plans, [])
		self.assertTrue(expired.name)
		self.assertTrue(inactive.name)

	def test_default_stable_is_used_when_horse_has_no_stable(self):
		unstabled_horse = self.make_horse(f"Unstabled Horse {self.suffix}", None)
		self.make_template(
			template_name=f"Default Stable Plan {self.suffix}",
			horse=unstabled_horse.name,
		)
		settings = frappe.get_single("Horse Management Settings")
		settings.default_stable = self.stable.name
		settings.save(ignore_permissions=True)

		plans = generate_plans_for_date(self.plan_date)

		self.assertEqual(len(plans), 1)
		self.assertEqual(frappe.db.get_value("Daily Work Plan", plans[0], "stable"), self.stable.name)

	def test_scheduler_can_generate_and_publish_automatically(self):
		scheduler_date = getdate(add_days(today(), 1))
		self.make_template(
			template_name=f"Scheduled Plan {self.suffix}",
			horse=self.horse.name,
			active_from=scheduler_date,
			active_until=scheduler_date,
		)
		settings = frappe.get_single("Horse Management Settings")
		settings.generate_plans_automatically = 1
		settings.days_ahead_to_generate = 1
		settings.generation_time = "00:00:00"
		settings.automatic_publication_enabled = 1
		settings.publication_cutoff_time = "00:00:00"
		settings.save(ignore_permissions=True)

		process_daily_planning_schedule()

		plan = frappe.get_all(
			"Daily Work Plan",
			filters={"plan_date": scheduler_date, "stable": self.stable.name},
			fields=["name", "docstatus", "workflow_state", "generation_source"],
			limit=1,
		)[0]
		self.assertEqual(plan.docstatus, 1)
		self.assertEqual(plan.workflow_state, "HM Published")
		self.assertEqual(plan.generation_source, "Automatic")

	def test_owner_can_edit_draft_tasks_and_publish_plan(self):
		self.make_template(template_name=f"Editable Plan {self.suffix}", horse=self.horse.name)
		plan_name = generate_plans_for_date(self.plan_date)[0]
		task_name = frappe.db.get_value("Daily Groom Task", {"daily_work_plan": plan_name}, "name")

		with self.set_user(self.owner_user):
			task = frappe.get_doc("Daily Groom Task", task_name)
			task.instructions = "Owner-adjusted instructions"
			task.save()

			published = publish_plans_for_date(self.plan_date)
			self.assertEqual(published, [plan_name])

			task = frappe.get_doc("Daily Groom Task", task_name)
			task.instructions = "This change must be rejected"
			self.assertRaises(frappe.PermissionError, task.save)

			plan = frappe.get_doc("Daily Work Plan", plan_name)
		self.assertEqual(plan.docstatus, 1)
		self.assertEqual(plan.workflow_state, "HM Published")
		self.assertEqual(plan.published_by, self.owner_user)

		task.reload()
		self.assertTrue(task.todo)
		todo = frappe.get_doc("ToDo", task.todo)
		self.assertEqual(todo.status, "Open")
		self.assertEqual(todo.allocated_to, self.groom_user)
		self.assertEqual(todo.reference_type, "Daily Groom Task")
		self.assertEqual(todo.reference_name, task.name)
		self.assertEqual(todo.priority, "High")
		self.assertEqual(todo.date, self.plan_date)

	def test_publish_creates_linked_todo_for_each_task(self):
		self.make_template(template_name=f"ToDo Plan {self.suffix}", horse=self.horse.name)
		plan_name = generate_plans_for_date(self.plan_date)[0]

		published = publish_plans_for_date(self.plan_date)

		self.assertEqual(published, [plan_name])
		task = frappe.get_doc(
			"Daily Groom Task",
			frappe.db.get_value("Daily Groom Task", {"daily_work_plan": plan_name}, "name"),
		)
		self.assertTrue(task.todo)

		todo = frappe.get_doc("ToDo", task.todo)
		self.assertEqual(todo.allocated_to, self.groom_user)
		self.assertEqual(todo.reference_type, "Daily Groom Task")
		self.assertEqual(todo.reference_name, task.name)
		self.assertEqual(todo.status, "Open")

	def test_closing_todo_does_not_complete_operational_task(self):
		task = self.make_published_task("Manual ToDo Close")
		frappe.db.set_value("ToDo", task.todo, "status", "Closed")

		task.reload()

		self.assertEqual(task.status, "Pending")
		self.assertEqual(task.docstatus, 0)
		self.assertFalse(task.completed_at)

	def test_assigned_groom_can_start_and_complete_task(self):
		task = self.make_published_task("Groom Completion")

		with self.set_user(self.groom_user):
			task = frappe.get_doc("Daily Groom Task", task.name)
			task.status = "In Progress"
			task.save()
			self.assertTrue(task.started_at)

			task.status = "Completed"
			task.completion_notes = "Horse groomed and settled."
			task.append(
				"completion_photographs",
				{
					"photograph": "/files/grooming-evidence.jpg",
					"caption": "Completed grooming evidence",
				},
			)
			task.save()

		task.reload()
		self.assertEqual(task.status, "Completed")
		self.assertEqual(task.docstatus, 1)
		self.assertTrue(task.completed_at)
		self.assertEqual(frappe.db.get_value("ToDo", task.todo, "status"), "Closed")

	def test_not_completed_requires_exception_reason(self):
		task = self.make_published_task("Not Completed")

		with self.set_user(self.groom_user):
			task = frappe.get_doc("Daily Groom Task", task.name)
			task.status = "Not Completed"
			self.assertRaises(frappe.ValidationError, task.save)

			task.reload()
			task.status = "Not Completed"
			task.exception_reason = "Horse was unavailable for handling."
			task.save()

		task.reload()
		self.assertEqual(task.status, "Not Completed")
		self.assertEqual(task.docstatus, 1)
		self.assertTrue(task.completed_at)
		self.assertEqual(frappe.db.get_value("ToDo", task.todo, "status"), "Closed")

	def test_task_cannot_be_submitted_before_final_status(self):
		task = self.make_published_task("Pending Submit")

		with self.set_user(self.groom_user):
			task = frappe.get_doc("Daily Groom Task", task.name)
			self.assertRaises((frappe.ValidationError, frappe.PermissionError), task.submit)

	def test_only_assigned_groom_can_complete_task(self):
		task = self.make_published_task("Assigned Groom Only")

		with self.set_user(self.other_groom_user):
			task = frappe.get_doc("Daily Groom Task", task.name)
			task.status = "Completed"
			task.completion_notes = "Attempted by wrong groom."
			task.append(
				"completion_photographs",
				{
					"photograph": "/files/wrong-groom.jpg",
					"caption": "Wrong groom evidence",
				},
			)
			self.assertRaises(frappe.PermissionError, task.save)

	def test_skipped_requires_reason_and_owner_permission(self):
		task = self.make_published_task("Skipped Task")

		with self.set_user(self.groom_user):
			task = frappe.get_doc("Daily Groom Task", task.name)
			task.status = "Skipped"
			task.exception_reason = "Owner requested skip."
			self.assertRaises(frappe.PermissionError, task.save)

		with self.set_user(self.owner_user):
			task = frappe.get_doc("Daily Groom Task", task.name)
			task.status = "Skipped"
			self.assertRaises(frappe.ValidationError, task.save)

			task.reload()
			task.status = "Skipped"
			task.exception_reason = "Owner authorised skip."
			task.save()

		task.reload()
		self.assertEqual(task.status, "Skipped")
		self.assertEqual(task.docstatus, 1)
		self.assertEqual(frappe.db.get_value("ToDo", task.todo, "status"), "Closed")

	def test_plan_without_tasks_cannot_be_published(self):
		plan = frappe.get_doc(
			{
				"doctype": "Daily Work Plan",
				"plan_date": self.plan_date,
				"stable": self.stable.name,
				"generation_key": frappe.generate_hash(length=32),
			}
		).insert(ignore_permissions=True)
		plan.flags.ignore_permissions = True

		self.assertRaises(frappe.ValidationError, plan.submit)

	def make_template(
		self,
		template_name,
		horse=None,
		target_type="Horse",
		horse_group=None,
		stable=None,
		version_number=1,
		previous_version=None,
		instructions="Morning care instructions",
		active_until=None,
		active_from=None,
		is_active=1,
	):
		active_from = active_from or self.plan_date
		active_until = self.plan_date if active_until is None else active_until
		return frappe.get_doc(
			{
				"doctype": "Horse Care Template",
				"template_name": template_name,
				"version_number": version_number,
				"previous_version": previous_version,
				"is_active": is_active,
				"active_from": active_from,
				"active_until": active_until,
				"target_type": target_type,
				"horse": horse,
				"horse_group": horse_group,
				"stable": stable,
				"default_groom": self.groom_user,
				"items": [
					{
						"task_title": "Morning Care",
						"task_type": "Grooming",
						"start_time": "06:00:00",
						"duration": 1800,
						"priority": "High",
						"instructions": instructions,
						"is_mandatory": 1,
						"photograph_required": 1,
						"notes_required_on_exception": 1,
						"monday": 1,
						"tuesday": 1,
						"wednesday": 1,
						"thursday": 1,
						"friday": 1,
						"saturday": 1,
						"sunday": 1,
					}
				],
			}
		).insert(ignore_permissions=True)

	def make_horse(self, horse_name, stable):
		return frappe.get_doc(
			{
				"doctype": "Horse",
				"horse_name": horse_name,
				"current_stable": stable,
			}
		).insert(ignore_permissions=True)

	def make_published_task(self, template_prefix):
		self.make_template(template_name=f"{template_prefix} {self.suffix}", horse=self.horse.name)
		plan_name = generate_plans_for_date(self.plan_date)[0]
		publish_plans_for_date(self.plan_date)
		return frappe.get_doc(
			"Daily Groom Task",
			frappe.db.get_value("Daily Groom Task", {"daily_work_plan": plan_name}, "name"),
		)

	def make_location(self, location_name, location_type):
		return frappe.get_doc(
			{
				"doctype": "Yard Location",
				"location_name": location_name,
				"location_type": location_type,
			}
		).insert(ignore_permissions=True)
