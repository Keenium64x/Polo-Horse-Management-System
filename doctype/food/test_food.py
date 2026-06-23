# Copyright (c) 2026, Keenan Solomon and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase


# On IntegrationTestCase, the doctype test records and all
# link-field test record dependencies are recursively loaded
# Use these module variables to add/remove to/from that list
EXTRA_TEST_RECORD_DEPENDENCIES = []  # eg. ["User"]
IGNORE_TEST_RECORD_DEPENDENCIES = []  # eg. ["User"]



class IntegrationTestFood(IntegrationTestCase):
	"""
	Integration tests for Food.
	Use this class for testing interactions between multiple components.
	"""

	def test_food_uses_its_name_as_document_name(self):
		food_name = f"Test Feed {frappe.generate_hash(length=8)}"
		food = frappe.get_doc(
			{
				"doctype": "Food",
				"food_name": food_name,
			}
		).insert(ignore_permissions=True)

		self.assertEqual(food.name, food_name)
