// Copyright (c) 2026, Keenan Solomon and contributors
// For license information, please see license.txt

frappe.ui.form.on("Horse Management Settings", {
	refresh(frm) {
		frm.add_custom_button(__("Generate Plans"), () => {
			frappe.call({
				method: "horsemanagement.daily_planning.generate_daily_work_plans",
				freeze: true,
				callback() {
					frappe.show_alert({ message: __("Daily plans generated"), indicator: "green" });
				},
			});
		});
		frm.add_custom_button(__("Publish Tomorrow's Plans"), () => {
			frappe.call({
				method: "horsemanagement.daily_planning.publish_daily_work_plans",
				freeze: true,
				callback() {
					frappe.show_alert({ message: __("Tomorrow's plans published"), indicator: "green" });
				},
			});
		});
	},
});
