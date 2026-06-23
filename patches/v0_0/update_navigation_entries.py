import frappe


SIDEBAR_ITEMS = [
	{
		"label": "Daily Operations",
		"type": "Section Break",
		"link_type": "DocType",
		"icon": "calendar",
		"child": 0,
		"indent": 1,
		"collapsible": 1,
		"keep_closed": 0,
		"show_arrow": 0,
	},
	{"label": "Daily Work Plans", "link_to": "Daily Work Plan", "child": 1},
	{"label": "Daily Groom Tasks", "link_to": "Daily Groom Task", "child": 1},
	{"label": "Feeding Sessions", "link_to": "Feeding Session", "child": 1},
	{
		"label": "Care Setup",
		"type": "Section Break",
		"link_type": "DocType",
		"icon": "file-text",
		"child": 0,
		"indent": 1,
		"collapsible": 1,
		"keep_closed": 0,
		"show_arrow": 0,
	},
	{"label": "Care Templates", "link_to": "Horse Care Template", "child": 1},
	{"label": "Horse Groups", "link_to": "Horse Group", "child": 1},
	{
		"label": "Horse Registry",
		"type": "Section Break",
		"link_type": "DocType",
		"icon": "heart-pulse",
		"child": 0,
		"indent": 1,
		"collapsible": 1,
		"keep_closed": 0,
		"show_arrow": 0,
	},
	{"label": "Horses", "link_to": "Horse", "child": 1},
	{"label": "Horse Owners", "link_to": "Horse Owner", "child": 1},
	{"label": "Yard Locations", "link_to": "Yard Location", "child": 1},
	{"label": "Foods", "link_to": "Food", "child": 1},
	{
		"label": "Administration",
		"type": "Section Break",
		"link_type": "DocType",
		"icon": "settings",
		"child": 0,
		"indent": 1,
		"collapsible": 1,
		"keep_closed": 0,
		"show_arrow": 0,
	},
	{"label": "Horse Management Settings", "link_to": "Horse Management Settings", "child": 1},
]

DESKTOP_ROLES = (
	"Horse Groom",
	"Horse Manager",
	"Horse Owner",
	"System Manager",
	"Veterinarian",
	"Yard Manager",
)


def execute():
	update_desktop_icon()
	update_workspace_sidebar()


def update_desktop_icon():
	if not frappe.db.exists("Desktop Icon", "HorseManagement"):
		return

	icon = frappe.get_doc("Desktop Icon", "HorseManagement")
	icon.label = "Horse Management"
	icon.link_to = "Horse Management"
	icon.link_type = "Workspace Sidebar"
	icon.sidebar = "Horse Management"
	icon.hidden = 0
	icon.standard = 1
	icon.set("roles", [])
	for role in DESKTOP_ROLES:
		icon.append("roles", {"role": role})
	icon.save(ignore_permissions=True)


def update_workspace_sidebar():
	if not frappe.db.exists("Workspace Sidebar", "Horse Management"):
		return

	sidebar = frappe.get_doc("Workspace Sidebar", "Horse Management")
	sidebar.app = "horsemanagement"
	sidebar.title = "Horse Management"
	sidebar.header_icon = "heart-pulse"
	sidebar.standard = 1
	sidebar.set("items", [])
	for item in SIDEBAR_ITEMS:
		sidebar.append("items", normalized_sidebar_item(item))
	sidebar.save(ignore_permissions=True)


def normalized_sidebar_item(item):
	if item.get("type") == "Section Break":
		return item

	return {
		"label": item["label"],
		"type": "Link",
		"link_type": "DocType",
		"link_to": item["link_to"],
		"child": item.get("child", 0),
		"indent": 0,
		"collapsible": 1,
		"keep_closed": 0,
		"show_arrow": 0,
	}
