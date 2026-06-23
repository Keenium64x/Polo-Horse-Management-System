frappe.listview_settings["Daily Work Plan"] = {
	add_fields: ["workflow_state", "plan_date"],
	get_indicator(doc) {
		const published = doc.workflow_state === "HM Published";
		return [
			__(doc.workflow_state || "HM Draft"),
			published ? "green" : "blue",
			`workflow_state,=,${doc.workflow_state || "HM Draft"}`,
		];
	},
};
