# Copyright (c) 2026, Keenan Solomon and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class HorseManagementSettings(Document):
	def validate(self):
		if self.days_ahead_to_generate < 1:
			frappe.throw(_("Days Ahead to Generate must be at least 1."))
		self.validate_default_template()
		self.validate_default_stable()

	def validate_default_template(self):
		if not self.default_template:
			return
		if not frappe.db.get_value("Horse Care Template", self.default_template, "is_active"):
			frappe.throw(_("Default Care Template must be active."))

	def validate_default_stable(self):
		if not self.default_stable:
			return
		stable = frappe.db.get_value(
			"Yard Location",
			self.default_stable,
			["location_type", "is_active"],
			as_dict=True,
		)
		if not stable or stable.location_type != "Stable" or not stable.is_active:
			frappe.throw(_("Default Stable must be an active Stable."))
