frappe.listview_settings["Daily Groom Task"] = {
	add_fields: ["status", "priority"],
	get_indicator(doc) {
		const colors = {
			Pending: "gray",
			"In Progress": "blue",
			Completed: "green",
			"Not Completed": "red",
			Skipped: "orange",
		};
		return [__(doc.status || "Pending"), colors[doc.status] || "gray", `status,=,${doc.status}`];
	},
};
