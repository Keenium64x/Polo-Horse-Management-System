import frappe
from frappe.model.rename_doc import rename_doc


OLD_ROLE = "Groom"
NEW_ROLE = "Horse Groom"


def execute():
	if not frappe.db.exists("Role", OLD_ROLE):
		return

	if not frappe.db.exists("Role", NEW_ROLE):
		rename_doc("Role", OLD_ROLE, NEW_ROLE, force=True, ignore_permissions=True)
		return

	for user in frappe.get_all(
		"Has Role",
		filters={"role": OLD_ROLE, "parenttype": "User"},
		pluck="parent",
	):
		user_doc = frappe.get_doc("User", user)
		if NEW_ROLE not in frappe.get_roles(user):
			user_doc.add_roles(NEW_ROLE)

	frappe.delete_doc("Role", OLD_ROLE, ignore_permissions=True)
