import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, today


class IntegrationTestHorseCareTemplate(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.groom_user = cls.make_user("care-template-groom@example.com", "Horse Groom")
		cls.owner_user = cls.make_user("care-template-owner@example.com", "Horse Owner")

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
		self.horse = self.make_horse(f"Template Horse {self.suffix}")
		self.stable = self.make_location(f"Template Stable {self.suffix}", "Stable")

	def tearDown(self):
		frappe.set_user("Administrator")

	def test_horse_template_stores_schedule_and_requirements(self):
		template = self.make_template(
			target_type="Horse",
			horse=self.horse.name,
			default_groom=self.groom_user,
		)

		self.assertTrue(template.name.startswith("CARE-TPL-"))
		self.assertEqual(template.target_type, "Horse")
		self.assertEqual(template.horse, self.horse.name)
		self.assertEqual(template.version_number, 1)
		self.assertEqual(template.items[0].start_time, "06:00:00")
		self.assertEqual(template.items[0].duration, 1800)
		self.assertEqual(template.items[0].photograph_required, 1)
		self.assertEqual(template.items[0].is_mandatory, 1)
		self.assertEqual(template.items[0].sunday, 0)

	def test_group_and_stable_targets_are_supported(self):
		group = frappe.get_doc(
			{
				"doctype": "Horse Group",
				"group_name": f"Morning Group {self.suffix}",
				"horses": [{"horse": self.horse.name}],
			}
		).insert(ignore_permissions=True)

		group_template = self.make_template(
			template_name=f"Group Care {self.suffix}",
			target_type="Horse Group",
			horse_group=group.name,
		)
		stable_template = self.make_template(
			template_name=f"Stable Care {self.suffix}",
			target_type="Stable",
			stable=self.stable.name,
		)

		self.assertEqual(group_template.horse_group, group.name)
		self.assertEqual(stable_template.stable, self.stable.name)

	def test_invalid_active_date_range_is_rejected(self):
		template = self.new_template(
			active_from=today(),
			active_until=add_days(today(), -1),
		)

		self.assertRaises(frappe.ValidationError, template.insert, ignore_permissions=True)

	def test_target_must_match_target_type(self):
		template = self.new_template(target_type="Horse", horse=None)

		self.assertRaises(frappe.ValidationError, template.insert, ignore_permissions=True)

	def test_stable_target_must_be_a_stable(self):
		paddock = self.make_location(f"Template Paddock {self.suffix}", "Paddock")
		template = self.new_template(target_type="Stable", stable=paddock.name)

		self.assertRaises(frappe.ValidationError, template.insert, ignore_permissions=True)

	def test_item_requires_positive_duration_and_a_weekday(self):
		template = self.new_template()
		template.items[0].duration = 0
		self.assertRaises(frappe.ValidationError, template.insert, ignore_permissions=True)

		template = self.new_template()
		for weekday in (
			"monday",
			"tuesday",
			"wednesday",
			"thursday",
			"friday",
			"saturday",
			"sunday",
		):
			template.items[0].set(weekday, 0)
		self.assertRaises(frappe.ValidationError, template.insert, ignore_permissions=True)

	def test_assigned_user_must_be_a_horse_groom(self):
		template = self.new_template(default_groom=self.owner_user)

		self.assertRaises(frappe.ValidationError, template.insert, ignore_permissions=True)

	def test_version_reference_requires_same_template_and_lower_version(self):
		version_one = self.make_template()
		version_two = self.make_template(
			version_number=2,
			previous_version=version_one.name,
		)

		self.assertEqual(version_two.previous_version, version_one.name)

		duplicate_version = self.new_template(version_number=2)
		self.assertRaises(
			frappe.ValidationError,
			duplicate_version.insert,
			ignore_permissions=True,
		)

		different_template = self.make_template(
			template_name=f"Different Template {self.suffix}",
		)
		invalid_reference = self.new_template(
			version_number=3,
			previous_version=different_template.name,
		)
		self.assertRaises(
			frappe.ValidationError,
			invalid_reference.insert,
			ignore_permissions=True,
		)

	def test_group_rejects_duplicate_horses(self):
		group = frappe.get_doc(
			{
				"doctype": "Horse Group",
				"group_name": f"Duplicate Group {self.suffix}",
				"horses": [
					{"horse": self.horse.name},
					{"horse": self.horse.name},
				],
			}
		)

		self.assertRaises(frappe.ValidationError, group.insert, ignore_permissions=True)

	def test_groom_cannot_read_or_edit_templates(self):
		self.assertFalse(frappe.has_permission("Horse Care Template", "read", user=self.groom_user))
		self.assertFalse(frappe.has_permission("Horse Care Template", "write", user=self.groom_user))

	def make_template(self, **overrides):
		return self.new_template(**overrides).insert(ignore_permissions=True)

	def new_template(self, **overrides):
		values = {
			"doctype": "Horse Care Template",
			"template_name": f"Daily Care {self.suffix}",
			"version_number": 1,
			"is_active": 1,
			"active_from": today(),
			"target_type": "Horse",
			"horse": self.horse.name,
			"items": [
				{
					"task_title": "Morning Groom",
					"task_type": "Grooming",
					"start_time": "06:00:00",
					"duration": 1800,
					"priority": "High",
					"instructions": "Groom thoroughly and inspect the legs.",
					"is_mandatory": 1,
					"photograph_required": 1,
					"notes_required_on_exception": 1,
					"monday": 1,
					"tuesday": 1,
					"wednesday": 1,
					"thursday": 1,
					"friday": 1,
					"saturday": 1,
					"sunday": 0,
				}
			],
		}
		values.update(overrides)
		return frappe.get_doc(values)

	def make_horse(self, horse_name):
		return frappe.get_doc(
			{
				"doctype": "Horse",
				"horse_name": horse_name,
			}
		).insert(ignore_permissions=True)

	def make_location(self, location_name, location_type):
		return frappe.get_doc(
			{
				"doctype": "Yard Location",
				"location_name": location_name,
				"location_type": location_type,
			}
		).insert(ignore_permissions=True)
