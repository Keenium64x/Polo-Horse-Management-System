// Copyright (c) 2026, Keenan Solomon and contributors
// For license information, please see license.txt

frappe.ui.form.on("Daily Work Plan", {
	refresh(frm) {
		if (frm.doc.docstatus === 0 && frm.doc.workflow_state === "HM Draft" && !frm.is_new()) {
			frm.add_custom_button(__("Publish Plan"), () => frm.savesubmit(), __("Actions"));
		}

		if (!frm.is_new()) {
			frm.add_custom_button(
				__("View Tasks"),
				() => {
					frappe.set_route("List", "Daily Groom Task", {
						daily_work_plan: frm.doc.name,
					});
				},
				__("Actions")
			);
		}
	},
});
