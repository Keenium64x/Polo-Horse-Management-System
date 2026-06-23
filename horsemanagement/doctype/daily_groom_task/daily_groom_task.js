// Copyright (c) 2026, Keenan Solomon and contributors
// For license information, please see license.txt

frappe.ui.form.on("Daily Groom Task", {
	setup(frm) {
		frm.set_query("assigned_groom", () => ({
			query: "horsemanagement.horsemanagement.doctype.horse_care_template.horse_care_template.horse_groom_query",
		}));
	},

	refresh(frm) {
		if (frm.doc.docstatus === 1) return;

		if (frm.doc.status === "Pending") {
			frm.add_custom_button(__("Start Task"), () => {
				frm.set_value("status", "In Progress");
				frm.save();
			});
		}
	},
});
