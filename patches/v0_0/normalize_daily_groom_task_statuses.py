import frappe


STATUS_MAP = {
	"HM In Progress": "In Progress",
	"HM Completed": "Completed",
	"HM Not Completed": "Not Completed",
	"HM Skipped": "Skipped",
}


def execute():
	if not frappe.db.table_exists("Daily Groom Task"):
		return

	for old_status, new_status in STATUS_MAP.items():
		frappe.db.sql(
			"""
			update `tabDaily Groom Task`
			set status = %s
			where status = %s
			""",
			(new_status, old_status),
		)
