# Copyright (c) 2026, Keenan Solomon and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase


# On IntegrationTestCase, the doctype test records and all
# link-field test record dependencies are recursively loaded
# Use these module variables to add/remove to/from that list
EXTRA_TEST_RECORD_DEPENDENCIES = []  # eg. ["User"]
IGNORE_TEST_RECORD_DEPENDENCIES = []  # eg. ["User"]



class IntegrationTestFeeding(IntegrationTestCase):
	"""
	Integration tests for Feeding.
	Use this class for testing interactions between multiple components.
	"""

	def test_quantity_must_be_greater_than_zero(self):
		feeding = frappe.get_doc(
			{
				"doctype": "Feeding",
				"quantity": 0,
				"unit": "kg",
			}
		)

		self.assertRaises(frappe.ValidationError, feeding.validate)

	def test_quantity_remains_numeric(self):
		feeding = frappe.get_doc(
			{
				"doctype": "Feeding",
				"quantity": 2.5,
				"unit": "kg",
			}
		)

		feeding.validate()

		self.assertEqual(feeding.quantity, 2.5)
		self.assertEqual(feeding.unit, "kg")
