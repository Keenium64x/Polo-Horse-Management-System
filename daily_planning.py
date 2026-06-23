import hashlib
from collections import defaultdict

import frappe
from frappe import _
from frappe.utils import (
	add_days,
	add_to_date,
	cint,
	get_datetime,
	get_time,
	getdate,
	now_datetime,
	nowtime,
	today,
)

from horsemanagement.permissions import OWNER_ROLES, has_any_role


WEEKDAY_FIELDS = (
	"monday",
	"tuesday",
	"wednesday",
	"thursday",
	"friday",
	"saturday",
	"sunday",
)


@frappe.whitelist()
def generate_daily_work_plans(plan_date=None, source="Manual"):
	require_owner_role()
	return generate_plans_for_date(plan_date or add_days(today(), 1), source=source)


def generate_plans_for_date(plan_date, source="Automatic"):
	plan_date = getdate(plan_date)
	settings = frappe.get_single("Horse Management Settings")
	templates = get_applicable_templates(plan_date, settings.default_template)
	task_snapshots = build_task_snapshots(templates, plan_date, settings.default_stable)
	snapshots_by_stable = defaultdict(list)

	for snapshot in task_snapshots:
		snapshots_by_stable[snapshot.stable].append(snapshot)

	created_plans = []
	for stable, snapshots in snapshots_by_stable.items():
		plan = get_or_create_plan(plan_date, stable, source)
		if plan.docstatus != 0 or plan.workflow_state != "HM Draft":
			continue

		created_count = create_missing_tasks(plan, snapshots)
		task_count = frappe.db.count("Daily Groom Task", {"daily_work_plan": plan.name})
		plan.db_set("task_count", task_count, update_modified=False)
		if created_count or plan.name not in created_plans:
			created_plans.append(plan.name)

	return created_plans


def get_applicable_templates(plan_date, default_template=None):
	template_names = frappe.get_all(
		"Horse Care Template",
		filters={
			"is_active": 1,
			"active_from": ["<=", plan_date],
		},
		pluck="name",
	)

	templates = [frappe.get_doc("Horse Care Template", name) for name in template_names]
	templates = [template for template in templates if is_active_on(template, plan_date)]

	latest_versions = {}
	for template in templates:
		current = latest_versions.get(template.template_name)
		if not current or cint(template.version_number) > cint(current.version_number):
			latest_versions[template.template_name] = template

	if not latest_versions and default_template:
		template = frappe.get_doc("Horse Care Template", default_template)
		if template.is_active and is_active_on(template, plan_date):
			latest_versions[template.template_name] = template

	return list(latest_versions.values())


def is_active_on(template, plan_date):
	return (
		getdate(template.active_from) <= plan_date
		and (not template.active_until or getdate(template.active_until) >= plan_date)
	)


def build_task_snapshots(templates, plan_date, default_stable=None):
	snapshots = []
	weekday_field = WEEKDAY_FIELDS[plan_date.weekday()]

	for template in templates:
		horses = get_target_horses(template)
		for item in template.items:
			if not cint(item.get(weekday_field)):
				continue

			for horse in horses:
				stable = get_task_stable(template, horse, default_stable)
				if not stable:
					frappe.throw(
						_("Horse {0} has no Current Stable and no Default Stable is configured.").format(
							frappe.bold(horse)
						)
					)

				planned_start = get_datetime(f"{plan_date} {item.start_time}")
				planned_end = add_to_date(planned_start, seconds=cint(item.duration))
				source_target = template.get(
					{
						"Horse": "horse",
						"Horse Group": "horse_group",
						"Stable": "stable",
					}[template.target_type]
				)
				generation_key = make_generation_key(plan_date, template.name, item.name, horse)

				snapshots.append(
					frappe._dict(
						stable=stable,
						horse=horse,
						assigned_groom=item.assigned_groom or template.default_groom,
						task_title=item.task_title,
						task_type=item.task_type,
						priority=item.priority,
						planned_start=planned_start,
						planned_end=planned_end,
						duration=item.duration,
						instructions=item.instructions,
						is_mandatory=item.is_mandatory,
						photograph_required=item.photograph_required,
						notes_required_on_exception=item.notes_required_on_exception,
						required_equipment=item.required_equipment,
						original_template=template.name,
						original_template_item=item.name,
						template_version=template.version_number,
						source_target_type=template.target_type,
						source_target=source_target,
						generation_key=generation_key,
					)
				)

	return snapshots


def get_target_horses(template):
	if template.target_type == "Horse":
		return [template.horse]
	if template.target_type == "Horse Group":
		return frappe.get_all(
			"Horse Group Member",
			filters={"parent": template.horse_group, "parenttype": "Horse Group"},
			pluck="horse",
		)
	if template.target_type == "Stable":
		return frappe.get_all("Horse", filters={"current_stable": template.stable}, pluck="name")
	return []


def get_task_stable(template, horse, default_stable):
	if template.target_type == "Stable":
		return template.stable
	return frappe.db.get_value("Horse", horse, "current_stable") or default_stable


def get_or_create_plan(plan_date, stable, source):
	generation_key = make_plan_key(plan_date, stable)
	existing = frappe.db.get_value("Daily Work Plan", {"generation_key": generation_key}, "name")
	if existing:
		return frappe.get_doc("Daily Work Plan", existing)

	return frappe.get_doc(
		{
			"doctype": "Daily Work Plan",
			"plan_date": plan_date,
			"stable": stable,
			"workflow_state": "HM Draft",
			"generation_source": source,
			"generated_at": now_datetime(),
			"generation_key": generation_key,
		}
	).insert(ignore_permissions=True)


def create_missing_tasks(plan, snapshots):
	created_count = 0
	for snapshot in snapshots:
		if frappe.db.exists("Daily Groom Task", {"generation_key": snapshot.generation_key}):
			continue

		frappe.get_doc(
			{
				"doctype": "Daily Groom Task",
				"daily_work_plan": plan.name,
				"horse": snapshot.horse,
				"assigned_groom": snapshot.assigned_groom,
				"status": "Pending",
				"task_title": snapshot.task_title,
				"task_type": snapshot.task_type,
				"priority": snapshot.priority,
				"planned_start": snapshot.planned_start,
				"planned_end": snapshot.planned_end,
				"duration": snapshot.duration,
				"instructions": snapshot.instructions,
				"is_mandatory": snapshot.is_mandatory,
				"photograph_required": snapshot.photograph_required,
				"notes_required_on_exception": snapshot.notes_required_on_exception,
				"required_equipment": snapshot.required_equipment,
				"original_template": snapshot.original_template,
				"original_template_item": snapshot.original_template_item,
				"template_version": snapshot.template_version,
				"source_target_type": snapshot.source_target_type,
				"source_target": snapshot.source_target,
				"generation_key": snapshot.generation_key,
			}
		).insert(ignore_permissions=True)
		created_count += 1

	return created_count


@frappe.whitelist()
def publish_daily_work_plans(plan_date=None):
	require_owner_role()
	return publish_plans_for_date(plan_date or add_days(today(), 1))


def publish_plans_for_date(plan_date):
	published = []
	plans = frappe.get_all(
		"Daily Work Plan",
		filters={
			"plan_date": getdate(plan_date),
			"docstatus": 0,
			"workflow_state": "HM Draft",
		},
		pluck="name",
	)
	for plan_name in plans:
		plan = frappe.get_doc("Daily Work Plan", plan_name)
		if not frappe.db.count("Daily Groom Task", {"daily_work_plan": plan.name}):
			continue
		plan.flags.ignore_permissions = True
		plan.submit()
		published.append(plan.name)

	return published


def process_daily_planning_schedule():
	settings = frappe.get_single("Horse Management Settings")
	current_time = get_time(nowtime())

	if settings.generate_plans_automatically and current_time >= get_time(settings.generation_time):
		for offset in range(1, cint(settings.days_ahead_to_generate) + 1):
			generate_plans_for_date(add_days(today(), offset), source="Automatic")

	if (
		settings.automatic_publication_enabled
		and current_time >= get_time(settings.publication_cutoff_time)
	):
		publish_plans_for_date(add_days(today(), 1))


def make_plan_key(plan_date, stable):
	return hashlib.sha256(f"{plan_date}|{stable or ''}".encode()).hexdigest()


def make_generation_key(plan_date, template, template_item, horse):
	value = f"{plan_date}|{template}|{template_item}|{horse}"
	return hashlib.sha256(value.encode()).hexdigest()


def require_owner_role():
	if frappe.session.user == "Administrator":
		return
	if not has_any_role(frappe.session.user, OWNER_ROLES | {"System Manager"}):
		frappe.throw(_("Only an owner or yard manager may manage Daily Work Plans."), frappe.PermissionError)
