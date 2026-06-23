app_name = "horsemanagement"
app_title = "HorseManagement"
app_publisher = "Keenan Solomon"
app_description = "An App to Manage Horses"
app_email = "7keenan7@gmail.com"
app_license = "mit"

# Standard records owned by this app.
fixtures = [
	{
		"dt": "Role",
		"filters": [
			[
				"role_name",
				"in",
				[
					"Horse Manager",
					"Yard Manager",
					"Horse Owner",
					"Horse Groom",
					"Veterinarian",
				],
			]
		],
	},
	{
		"dt": "Workflow State",
		"filters": [
			[
				"workflow_state_name",
				"in",
				[
					"HM Draft",
					"HM Published",
					"HM In Progress",
					"HM Completed",
					"HM Not Completed",
					"HM Skipped",
					"HM Submitted",
					"HM Reviewed",
					"HM Overdue",
				],
			]
		],
	},
]

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "horsemanagement",
# 		"logo": "/assets/horsemanagement/logo.png",
# 		"title": "HorseManagement",
# 		"route": "/horsemanagement",
# 		"has_permission": "horsemanagement.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/horsemanagement/css/horsemanagement.css"
# app_include_js = "/assets/horsemanagement/js/horsemanagement.js"

# include js, css files in header of web template
# web_include_css = "/assets/horsemanagement/css/horsemanagement.css"
# web_include_js = "/assets/horsemanagement/js/horsemanagement.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "horsemanagement/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "horsemanagement/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# automatically load and sync documents of this doctype from downstream apps
# importable_doctypes = [doctype_1]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "horsemanagement.utils.jinja_methods",
# 	"filters": "horsemanagement.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "horsemanagement.install.before_install"
# after_install = "horsemanagement.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "horsemanagement.uninstall.before_uninstall"
# after_uninstall = "horsemanagement.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "horsemanagement.utils.before_app_install"
# after_app_install = "horsemanagement.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "horsemanagement.utils.before_app_uninstall"
# after_app_uninstall = "horsemanagement.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "horsemanagement.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

permission_query_conditions = {
	"Daily Work Plan": "horsemanagement.permissions.get_permission_query_conditions",
	"Daily Groom Task": "horsemanagement.permissions.get_permission_query_conditions",
	"Daily Groom Report": "horsemanagement.permissions.get_permission_query_conditions",
}

has_permission = {
	"Daily Work Plan": "horsemanagement.permissions.has_operational_permission",
	"Daily Groom Task": "horsemanagement.permissions.has_operational_permission",
	"Daily Groom Report": "horsemanagement.permissions.has_operational_permission",
}

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
	"Daily Work Plan": {
		"before_save": "horsemanagement.permissions.validate_daily_work_plan",
		"before_update_after_submit": "horsemanagement.permissions.prevent_submitted_update",
		"before_cancel": "horsemanagement.permissions.validate_owner_cancel",
		"on_trash": "horsemanagement.permissions.validate_operational_delete",
	},
	"Daily Groom Task": {
		"before_save": "horsemanagement.permissions.validate_daily_groom_task",
		"before_update_after_submit": "horsemanagement.permissions.prevent_submitted_update",
		"before_cancel": "horsemanagement.permissions.validate_owner_cancel",
		"on_trash": "horsemanagement.permissions.validate_operational_delete",
	},
	"Daily Groom Report": {
		"before_save": "horsemanagement.permissions.validate_daily_groom_report",
		"before_update_after_submit": "horsemanagement.permissions.prevent_submitted_update",
		"before_cancel": "horsemanagement.permissions.validate_owner_cancel",
		"on_trash": "horsemanagement.permissions.validate_operational_delete",
	},
}

# Scheduled Tasks
# ---------------

scheduler_events = {
	"cron": {
		"*/5 * * * *": [
			"horsemanagement.daily_planning.process_daily_planning_schedule",
		]
	},
# 	"all": [
# 		"horsemanagement.tasks.all"
# 	],
# 	"daily": [
# 		"horsemanagement.tasks.daily"
# 	],
# 	"hourly": [
# 		"horsemanagement.tasks.hourly"
# 	],
# 	"weekly": [
# 		"horsemanagement.tasks.weekly"
# 	],
# 	"monthly": [
# 		"horsemanagement.tasks.monthly"
# 	],
}

# Testing
# -------

# before_tests = "horsemanagement.install.before_tests"

# Extend DocType Class
# ------------------------------
#
# Specify custom mixins to extend the standard doctype controller.
# extend_doctype_class = {
# 	"Task": "horsemanagement.custom.task.CustomTaskMixin"
# }

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "horsemanagement.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "horsemanagement.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["horsemanagement.utils.before_request"]
# after_request = ["horsemanagement.utils.after_request"]

# Job Events
# ----------
# before_job = ["horsemanagement.utils.before_job"]
# after_job = ["horsemanagement.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"horsemanagement.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

# Translation
# ------------
# List of apps whose translatable strings should be excluded from this app's translations.
# ignore_translatable_strings_from = []
