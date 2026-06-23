# Copyright (c) 2026, Keenan Solomon and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase


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
		for role in ("Horse Manager", "Yard Manager", "Horse Owner", "Horse Groom", "Veterinarian"):
			self.assertTrue(frappe.db.exists("Role", role))

		self.assertTrue(frappe.db.exists("Workspace", "Horse Management"))
