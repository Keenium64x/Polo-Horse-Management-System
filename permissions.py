import frappe
from frappe import _
from frappe.utils import getdate, today


HORSE_GROOM_ROLE = "Horse Groom"
OWNER_ROLES = frozenset({"Horse Owner", "Horse Manager", "Yard Manager"})
ADMIN_ROLES = frozenset({"System Manager"})

DRAFT_STATE = "HM Draft"
PUBLISHED_STATE = "HM Published"
FINAL_TASK_STATES = frozenset({"Completed", "Not Completed", "Skipped"})
FINAL_REPORT_STATES = frozenset({"HM Submitted", "HM Reviewed"})

OPERATIONAL_DOCTYPES = frozenset({"Daily Work Plan", "Daily Groom Task", "Daily Groom Report"})


def get_permission_query_conditions(user=None, doctype=None):
	user = user or frappe.session.user
	if has_any_role(user, ADMIN_ROLES | OWNER_ROLES):
		return None
	if not has_role(user, HORSE_GROOM_ROLE):
		return "1=0"

	escaped_user = frappe.db.escape(user)
	if doctype == "Daily Groom Task":
		return f"`tabDaily Groom Task`.`assigned_groom` = {escaped_user}"
	if doctype == "Daily Groom Report":
		return f"`tabDaily Groom Report`.`groom` = {escaped_user}"
	if doctype == "Daily Work Plan":
		return (
			"`tabDaily Work Plan`.`workflow_state` = 'HM Published' "
			"and exists ("
			"select 1 from `tabDaily Groom Task` "
			"where `tabDaily Groom Task`.`daily_work_plan` = `tabDaily Work Plan`.`name` "
			f"and `tabDaily Groom Task`.`assigned_groom` = {escaped_user}"
			")"
		)

	return "1=0"


def has_operational_permission(doc, ptype="read", user=None, debug=False):
	user = user or frappe.session.user
	if user == "Administrator" or has_any_role(user, ADMIN_ROLES):
		return True
	if doc.doctype not in OPERATIONAL_DOCTYPES:
		return False

	if has_any_role(user, OWNER_ROLES):
		return owner_permission(doc, ptype)
	if has_role(user, HORSE_GROOM_ROLE):
		return groom_permission(doc, ptype, user)

	return False


def owner_permission(doc, ptype):
	if ptype in {"read", "print", "email", "report", "export", "share"}:
		return True
	if ptype in {"cancel", "amend"}:
		return bool(doc.docstatus == 1)
	if ptype == "delete":
		return bool(doc.docstatus == 0 and not is_final(doc))
	if doc.doctype == "Daily Work Plan":
		return ptype in {"create", "write", "submit"} and is_editable_future_plan(doc)
	if doc.doctype == "Daily Groom Task":
		if ptype == "submit":
			return doc.docstatus == 0 and doc.get("status") == "Skipped"
		if ptype == "write" and is_submit_action(doc) and doc.get("status") == "Skipped":
			return True
		if ptype == "write" and doc.docstatus == 0 and doc.get("status") == "Skipped":
			return True
		return ptype in {"create", "write"} and is_editable_future_task(doc)
	if doc.doctype == "Daily Groom Report":
		return ptype == "create" and bool(doc.get("amended_from"))

	return False


def groom_permission(doc, ptype, user):
	if ptype in {"cancel", "amend", "delete", "share", "export"}:
		return False

	if doc.doctype == "Daily Work Plan":
		if ptype not in {"read", "print"}:
			return False
		return is_published(doc) and groom_has_task_on_plan(doc.name, user)

	if doc.doctype == "Daily Groom Task":
		if doc.get("assigned_groom") != user:
			return False
		if ptype in {"read", "print"}:
			return True
		if ptype == "write":
			if is_submit_action(doc):
				return True
			return doc.docstatus == 0
		if ptype == "submit":
			return doc.docstatus == 0
		return ptype == "create"

	if doc.doctype == "Daily Groom Report":
		if doc.get("groom") != user:
			return False
		if ptype in {"read", "print"}:
			return True
		if ptype in {"create", "write", "submit"}:
			return doc.docstatus == 0 and not is_past_report(doc)

	return False


def validate_daily_work_plan(doc, method=None):
	if is_system_user():
		return
	if not has_any_role(frappe.session.user, OWNER_ROLES):
		frappe.throw(_("Only an owner or yard manager may edit a Daily Work Plan."), frappe.PermissionError)
	if getattr(doc, "_action", None) == "submit":
		if is_past_date(doc.get("plan_date")) or doc.get("workflow_state") != DRAFT_STATE:
			frappe.throw(_("Only a future draft Daily Work Plan may be published."))
		return
	if not is_editable_future_plan(doc):
		frappe.throw(_("Published or past Daily Work Plans are immutable."))


def validate_daily_groom_task(doc, method=None):
	if is_system_user():
		return

	old_doc = doc.get_doc_before_save() if not doc.is_new() else None
	if old_doc and old_doc.get("status") in FINAL_TASK_STATES and getattr(doc, "_action", None) != "submit":
		frappe.throw(_("Finalised Daily Groom Tasks are immutable."))

	user = frappe.session.user
	if has_role(user, HORSE_GROOM_ROLE):
		if doc.get("assigned_groom") != user:
			frappe.throw(_("You may only update tasks assigned to you."), frappe.PermissionError)
		return

	if has_any_role(user, OWNER_ROLES) and doc.get("status") == "Skipped":
		return

	if has_any_role(user, OWNER_ROLES) and is_editable_future_task(doc):
		return

	frappe.throw(_("Only the assigned groom may update a current task."), frappe.PermissionError)


def validate_daily_groom_report(doc, method=None):
	if is_system_user():
		return

	user = frappe.session.user
	if not has_role(user, HORSE_GROOM_ROLE) or doc.get("groom") != user:
		frappe.throw(_("Only the report's groom may edit it."), frappe.PermissionError)
	if is_past_report(doc):
		frappe.throw(_("Past Daily Groom Reports are immutable."))


def prevent_submitted_update(doc, method=None):
	frappe.throw(
		_("Submitted operational records cannot be edited. Cancel and amend the record instead."),
		frappe.PermissionError,
	)


def validate_owner_cancel(doc, method=None):
	if is_system_user():
		return
	if not has_any_role(frappe.session.user, OWNER_ROLES):
		frappe.throw(_("Only an owner or yard manager may cancel operational records."), frappe.PermissionError)


def validate_operational_delete(doc, method=None):
	if is_system_user():
		return
	if has_role(frappe.session.user, HORSE_GROOM_ROLE):
		frappe.throw(_("Horse Grooms cannot delete operational records."), frappe.PermissionError)
	if doc.docstatus != 0 or is_final(doc):
		frappe.throw(_("Final operational records cannot be deleted."))


def is_editable_future_plan(doc):
	return (
		doc.docstatus == 0
		and not is_published(doc)
		and not is_past_date(doc.get("plan_date"))
	)


def is_editable_future_task(doc):
	if doc.docstatus != 0 or is_final(doc):
		return False
	if not doc.get("daily_work_plan"):
		return False

	plan = frappe.db.get_value(
		"Daily Work Plan",
		doc.daily_work_plan,
		["plan_date", "workflow_state", "docstatus"],
		as_dict=True,
	)
	if not plan:
		return False

	return (
		plan.docstatus == 0
		and plan.workflow_state == DRAFT_STATE
		and not is_past_date(plan.plan_date)
	)


def is_published(doc):
	return doc.docstatus == 1 or doc.get("workflow_state") == PUBLISHED_STATE


def is_final(doc):
	state = doc.get("workflow_state") or doc.get("status")
	if doc.doctype == "Daily Groom Report":
		return doc.docstatus != 0 or state in FINAL_REPORT_STATES
	return doc.docstatus != 0 or state in FINAL_TASK_STATES


def is_past_report(doc):
	return is_past_date(doc.get("report_date") or doc.get("date"))


def is_past_date(value):
	return bool(value and getdate(value) < getdate(today()))


def groom_has_task_on_plan(plan_name, user):
	if not plan_name or not frappe.db.table_exists("Daily Groom Task"):
		return False
	return bool(
		frappe.db.exists(
			"Daily Groom Task",
			{
				"daily_work_plan": plan_name,
				"assigned_groom": user,
			},
		)
	)


def is_system_user():
	user = frappe.session.user
	return user == "Administrator" or has_any_role(user, ADMIN_ROLES)


def is_submit_action(doc):
	return getattr(doc, "_action", None) == "submit"


def has_role(user, role):
	return role in frappe.get_roles(user)


def has_any_role(user, roles):
	return bool(set(frappe.get_roles(user)) & set(roles))
