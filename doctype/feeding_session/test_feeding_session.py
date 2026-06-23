# Copyright (c) 2026, Keenan Solomon and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase


# On IntegrationTestCase, the doctype test records and all
# link-field test record dependencies are recursively loaded
# Use these module variables to add/remove to/from that list
EXTRA_TEST_RECORD_DEPENDENCIES = []  # eg. ["User"]
IGNORE_TEST_RECORD_DEPENDENCIES = []  # eg. ["User"]



class IntegrationTestFeedingSession(IntegrationTestCase):
	"""
	Integration tests for FeedingSession.
	Use this class for testing interactions between multiple components.
	"""

	def test_feeding_session_can_be_submitted(self):
		suffix = frappe.generate_hash(length=8)
		horse = frappe.get_doc(
			{
				"doctype": "Horse",
				"horse_name": f"Session Horse {suffix}",
			}
		).insert(ignore_permissions=True)
		food = frappe.get_doc(
			{
				"doctype": "Food",
				"food_name": f"Session Feed {suffix}",
			}
		).insert(ignore_permissions=True)

		session = frappe.get_doc(
			{
				"doctype": "Feeding Session",
				"session_date": frappe.utils.today(),
				"session_time": "08:00:00",
				"horses_feeding": [
					{
						"horse": horse.name,
						"food": food.name,
						"quantity": 2.5,
						"unit": "kg",
					}
				],
			}
		)
		session.flags.ignore_permissions = True
		session.insert()
		session.submit()

		self.assertEqual(session.docstatus, 1)
		self.assertTrue(session.name.startswith("FEED-SESSION-"))
		self.assertEqual(session.horses_feeding[0].quantity, 2.5)
