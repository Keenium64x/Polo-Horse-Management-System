# Copyright (c) 2026, Keenan Solomon and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt, getdate


WEEKDAY_FIELDS = (
	"monday",
	"tuesday",
	"wednesday",
	"thursday",
	"friday",
	"saturday",
	"sunday",
)

TARGET_FIELDS = {
	"Horse": "horse",
	"Horse Group": "horse_group",
	"Stable": "stable",
}


class HorseCareTemplate(Document):
	def validate(self):
		self.validate_active_dates()
		self.validate_target()
		self.validate_version()
		self.validate_groom(self.default_groom, _("Default Groom"))
		self.validate_items()

	def validate_active_dates(self):
		if self.active_from and self.active_until:
			if getdate(self.active_until) < getdate(self.active_from):
				frappe.throw(_("Active Until cannot be before Active From."))

	def validate_target(self):
		expected_field = TARGET_FIELDS.get(self.target_type)
		if not expected_field:
			frappe.throw(_("Select a valid Target Type."))

		for fieldname in TARGET_FIELDS.values():
			if fieldname == expected_field:
				if not self.get(fieldname):
					frappe.throw(
						_("{0} is required when Target Type is {1}.").format(
							self.meta.get_label(fieldname),
							frappe.bold(self.target_type),
						)
					)
			else:
				self.set(fieldname, None)

		if self.target_type == "Horse Group":
			if not frappe.db.get_value("Horse Group", self.horse_group, "is_active"):
				frappe.throw(_("The selected Horse Group must be active."))

		if self.target_type == "Stable":
			stable = frappe.db.get_value(
				"Yard Location",
				self.stable,
				["location_type", "is_active"],
				as_dict=True,
			)
			if not stable or stable.location_type != "Stable":
				frappe.throw(_("The selected location must be a Stable."))
			if not stable.is_active:
				frappe.throw(_("The selected Stable must be active."))

	def validate_version(self):
		if cint(self.version_number) < 1:
			frappe.throw(_("Version Number must be at least 1."))

		filters = {
			"template_name": self.template_name,
			"version_number": self.version_number,
			"name": ["!=", self.name or ""],
		}
		if frappe.db.exists("Horse Care Template", filters):
			frappe.throw(
				_("Version {0} already exists for template {1}.").format(
					self.version_number,
					frappe.bold(self.template_name),
				)
			)

		if not self.previous_version:
			return
		if self.previous_version == self.name:
			frappe.throw(_("A template cannot reference itself as its previous version."))

		previous = frappe.db.get_value(
			"Horse Care Template",
			self.previous_version,
			["template_name", "version_number"],
			as_dict=True,
		)
		if not previous:
			return
		if previous.template_name != self.template_name:
			frappe.throw(_("Previous Version must belong to the same template name."))
		if cint(previous.version_number) >= cint(self.version_number):
			frappe.throw(_("Previous Version must have a lower version number."))

	def validate_items(self):
		if not self.items:
			frappe.throw(_("Add at least one care template item."))

		for row in self.items:
			if flt(row.duration) <= 0:
				frappe.throw(_("Duration must be greater than zero in row {0}.").format(row.idx))
			if not any(cint(row.get(fieldname)) for fieldname in WEEKDAY_FIELDS):
				frappe.throw(_("Select at least one weekday in row {0}.").format(row.idx))
			self.validate_groom(
				row.assigned_groom,
				_("Assigned Groom in row {0}").format(row.idx),
			)

	def validate_groom(self, user, field_label):
		if not user:
			return
		if not frappe.db.get_value("User", user, "enabled"):
			frappe.throw(_("{0} must be an enabled user.").format(field_label))
		if "Horse Groom" not in frappe.get_roles(user):
			frappe.throw(_("{0} must have the Horse Groom role.").format(field_label))


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def horse_groom_query(doctype, txt, searchfield, start, page_len, filters):
	return frappe.db.sql(
		"""
		select distinct `tabUser`.name, `tabUser`.full_name
		from `tabUser`
		inner join `tabHas Role`
			on `tabHas Role`.parent = `tabUser`.name
			and `tabHas Role`.parenttype = 'User'
		where `tabUser`.enabled = 1
			and `tabUser`.user_type = 'System User'
			and `tabHas Role`.role = 'Horse Groom'
			and (`tabUser`.name like %(txt)s or `tabUser`.full_name like %(txt)s)
		order by `tabUser`.name
		limit %(start)s, %(page_len)s
		""",
		{
			"txt": f"%{txt}%",
			"start": start,
			"page_len": page_len,
		},
	)
