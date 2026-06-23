// Copyright (c) 2026, Keenan Solomon and contributors
// For license information, please see license.txt

frappe.ui.form.on("Horse Care Template", {
	setup(frm) {
		const groom_query = {
			query: "horsemanagement.horsemanagement.doctype.horse_care_template.horse_care_template.horse_groom_query",
		};
		frm.set_query("default_groom", () => groom_query);
		frm.set_query("assigned_groom", "items", () => groom_query);
		frm.set_query("stable", () => ({
			filters: {
				is_active: 1,
				location_type: "Stable",
			},
		}));
		frm.set_query("horse_group", () => ({
			filters: {
				is_active: 1,
			},
		}));
	},

	target_type(frm) {
		clear_unused_targets(frm);
	},
});

function clear_unused_targets(frm) {
	const target_fields = {
		Horse: "horse",
		"Horse Group": "horse_group",
		Stable: "stable",
	};

	Object.values(target_fields).forEach((fieldname) => {
		if (fieldname !== target_fields[frm.doc.target_type]) {
			frm.set_value(fieldname, null);
		}
	});
}
