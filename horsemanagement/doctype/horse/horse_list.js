frappe.listview_settings.Horse = {
	add_fields: ["availability_status", "has_handling_warning"],
	get_indicator(doc) {
		const colors = {
			Available: "green",
			Resting: "blue",
			"Light Work": "orange",
			Injured: "red",
			"Veterinary Hold": "red",
			Retired: "gray",
			Sold: "gray",
		};
		const status = doc.availability_status || "Available";

		return [
			__(status),
			colors[status] || "gray",
			`availability_status,=,${status}`,
		];
	},
};
