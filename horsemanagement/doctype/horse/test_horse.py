# Copyright (c) 2026, Keenan Solomon and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, add_years, today


# On IntegrationTestCase, the doctype test records and all
# link-field test record dependencies are recursively loaded
# Use these module variables to add/remove to/from that list
EXTRA_TEST_RECORD_DEPENDENCIES = []  # eg. ["User"]
IGNORE_TEST_RECORD_DEPENDENCIES = []  # eg. ["User"]



class IntegrationTestHorse(IntegrationTestCase):
	"""
	Integration tests for Horse.
	Use this class for testing interactions between multiple components.
	"""

	def test_horse_uses_its_name_as_document_name(self):
		horse_name = f"Test Horse {frappe.generate_hash(length=8)}"
		horse = frappe.get_doc(
			{
				"doctype": "Horse",
				"horse_name": horse_name,
				"weight": 475.5,
			}
		).insert(ignore_permissions=True)

		self.assertEqual(horse.name, horse_name)
		self.assertEqual(horse.weight, 475.5)

	def test_horse_name_is_required(self):
		horse = frappe.get_doc({"doctype": "Horse"})

		self.assertRaises(frappe.ValidationError, horse.insert, ignore_permissions=True)

	def test_foundation_records_are_installed(self):
		for role in ("Horse Manager", "Yard Manager", "Horse Owner", "Groom", "Veterinarian"):
			self.assertTrue(frappe.db.exists("Role", role))

		self.assertTrue(frappe.db.exists("Workspace", "Horse Management"))

	def test_complete_profile_calculates_age_and_ownership(self):
		suffix = frappe.generate_hash(length=8)
		primary_owner = self.make_owner(f"Primary Owner {suffix}")
		shared_owner = self.make_owner(f"Shared Owner {suffix}")
		stable = self.make_location(f"Stable {suffix}", "Stable")
		paddock = self.make_location(f"Paddock {suffix}", "Paddock")

		horse = frappe.get_doc(
			{
				"doctype": "Horse",
				"horse_name": f"Profile Horse {suffix}",
				"registered_name": f"Registered Profile Horse {suffix}",
				"birth_date": add_years(today(), -7),
				"sex": "Mare",
				"breed": "Thoroughbred",
				"colour": "Bay",
				"height": 15.3,
				"height_unit": "hh",
				"passport_number": f"PASS-{suffix}",
				"microchip_number": f"CHIP-{suffix}",
				"registration_number": f"REG-{suffix}",
				"primary_owner": primary_owner.name,
				"primary_ownership_percentage": 60,
				"shared_owners": [
					{
						"owner": shared_owner.name,
						"ownership_percentage": 40,
					}
				],
				"current_stable": stable.name,
				"current_paddock": paddock.name,
				"current_location": stable.name,
				"temperament": "Calm",
				"speed": 8,
				"acceleration": 7,
				"turning": 9,
				"stopping": 8,
				"stamina": 7,
				"rideability": 9,
				"availability_status": "Available",
			}
		).insert(ignore_permissions=True)

		self.assertEqual(horse.age, 7)
		self.assertEqual(horse.total_ownership_percentage, 100)
		self.assertEqual(horse.current_location, stable.name)
		self.assertEqual(horse.status_since, today())

	def test_future_birth_date_is_rejected(self):
		horse = frappe.get_doc(
			{
				"doctype": "Horse",
				"horse_name": f"Future Horse {frappe.generate_hash(length=8)}",
				"birth_date": add_days(today(), 1),
			}
		)

		self.assertRaises(frappe.ValidationError, horse.insert, ignore_permissions=True)

	def test_playing_characteristics_are_limited_to_ten(self):
		horse = frappe.get_doc(
			{
				"doctype": "Horse",
				"horse_name": f"Fast Horse {frappe.generate_hash(length=8)}",
				"speed": 11,
			}
		)

		self.assertRaises(frappe.ValidationError, horse.insert, ignore_permissions=True)

	def test_ownership_cannot_exceed_one_hundred_percent(self):
		suffix = frappe.generate_hash(length=8)
		primary_owner = self.make_owner(f"Majority Owner {suffix}")
		shared_owner = self.make_owner(f"Minority Owner {suffix}")
		horse = frappe.get_doc(
			{
				"doctype": "Horse",
				"horse_name": f"Overowned Horse {suffix}",
				"primary_owner": primary_owner.name,
				"primary_ownership_percentage": 80,
				"shared_owners": [
					{
						"owner": shared_owner.name,
						"ownership_percentage": 30,
					}
				],
			}
		)

		self.assertRaises(frappe.ValidationError, horse.insert, ignore_permissions=True)

	def test_stable_and_paddock_types_are_enforced(self):
		suffix = frappe.generate_hash(length=8)
		paddock = self.make_location(f"Wrong Stable {suffix}", "Paddock")
		horse = frappe.get_doc(
			{
				"doctype": "Horse",
				"horse_name": f"Misplaced Horse {suffix}",
				"current_stable": paddock.name,
			}
		)

		self.assertRaises(frappe.ValidationError, horse.insert, ignore_permissions=True)

	def test_status_since_updates_when_availability_changes(self):
		horse = frappe.get_doc(
			{
				"doctype": "Horse",
				"horse_name": f"Status Horse {frappe.generate_hash(length=8)}",
				"availability_status": "Available",
			}
		).insert(ignore_permissions=True)
		frappe.db.set_value("Horse", horse.name, "status_since", "2020-01-01")

		horse.reload()
		horse.availability_status = "Resting"
		horse.save(ignore_permissions=True)

		self.assertEqual(horse.status_since, today())

	def make_owner(self, owner_name):
		return frappe.get_doc(
			{
				"doctype": "Horse Owner",
				"owner_name": owner_name,
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
