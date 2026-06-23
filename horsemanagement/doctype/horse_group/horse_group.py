# Copyright (c) 2026, Keenan Solomon and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class HorseGroup(Document):
	def validate(self):
		horses = [row.horse for row in self.horses]
		if len(horses) != len(set(horses)):
			frappe.throw(_("A horse may only appear once in a Horse Group."))
