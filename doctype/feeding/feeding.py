import frappe
from frappe import _
from frappe.model.document import Document

class Feeding(Document):
	def validate(self):
		if self.quantity is not None and self.quantity <= 0:
			frappe.throw(_("Quantity must be greater than zero."))
