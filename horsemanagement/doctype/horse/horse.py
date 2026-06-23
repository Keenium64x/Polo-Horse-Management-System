# Copyright (c) 2026, Keenan Solomon and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate, today


PLAYING_CHARACTERISTICS = (
	"speed",
	"acceleration",
	"turning",
	"stopping",
	"stamina",
	"rideability",
)


class Horse(Document):
	def validate(self):
		self.set_age()
		self.clean_identifiers()
		self.validate_playing_characteristics()
		self.validate_ownership()
		self.validate_locations()
		self.set_status_since()

	def set_age(self):
		if not self.birth_date:
			self.age = None
			return

		birth_date = getdate(self.birth_date)
		current_date = getdate(today())
		if birth_date > current_date:
			frappe.throw(_("Birth Date cannot be in the future."))

		self.age = current_date.year - birth_date.year - (
			(current_date.month, current_date.day) < (birth_date.month, birth_date.day)
		)

	def clean_identifiers(self):
		for fieldname in ("passport_number", "microchip_number", "registration_number"):
			if value := self.get(fieldname):
				self.set(fieldname, value.strip())

	def validate_playing_characteristics(self):
		for fieldname in PLAYING_CHARACTERISTICS:
			rating = self.get(fieldname) or 0
			if not 0 <= rating <= 10:
				frappe.throw(
					_("{0} must be between 1 and 10, or zero when not assessed.").format(
						self.meta.get_label(fieldname)
					)
				)

	def validate_ownership(self):
		owners = set()
		total = 0.0

		if self.primary_owner:
			owners.add(self.primary_owner)
			primary_share = flt(self.primary_ownership_percentage)
			if not 0 < primary_share <= 100:
				frappe.throw(_("Primary Ownership must be greater than zero and no more than 100%."))
			total += primary_share
		else:
			self.primary_ownership_percentage = 0

		for row in self.shared_owners:
			if row.owner in owners:
				frappe.throw(_("Owner {0} is listed more than once.").format(frappe.bold(row.owner)))

			share = flt(row.ownership_percentage)
			if not 0 < share <= 100:
				frappe.throw(
					_("Ownership for {0} must be greater than zero and no more than 100%.").format(
						frappe.bold(row.owner)
					)
				)

			owners.add(row.owner)
			total += share

		if total > 100:
			frappe.throw(_("Recorded ownership cannot exceed 100%."))

		self.total_ownership_percentage = total

	def validate_locations(self):
		self.validate_location_type("current_stable", "Stable")
		self.validate_location_type("current_paddock", "Paddock")
		self.validate_location_type("current_location")

	def validate_location_type(self, fieldname, expected_type=None):
		location = self.get(fieldname)
		if not location:
			return

		location_details = frappe.db.get_value(
			"Yard Location",
			location,
			["location_type", "is_active"],
			as_dict=True,
		)
		if not location_details:
			return
		if not location_details.is_active:
			frappe.throw(_("{0} is not an active Yard Location.").format(frappe.bold(location)))
		if expected_type and location_details.location_type != expected_type:
			frappe.throw(
				_("{0} must be a Yard Location of type {1}.").format(
					self.meta.get_label(fieldname),
					frappe.bold(expected_type),
				)
			)

	def set_status_since(self):
		if self.is_new():
			self.status_since = self.status_since or today()
			return

		previous = self.get_doc_before_save()
		if previous and previous.availability_status != self.availability_status:
			self.status_since = today()
