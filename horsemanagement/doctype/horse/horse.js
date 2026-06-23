// Copyright (c) 2026, Keenan Solomon and contributors
// For license information, please see license.txt

frappe.ui.form.on("Horse", {
	setup(frm) {
		frm.set_query("current_stable", () => ({
			filters: {
				is_active: 1,
				location_type: "Stable",
			},
		}));
		frm.set_query("current_paddock", () => ({
			filters: {
				is_active: 1,
				location_type: "Paddock",
			},
		}));
		frm.set_query("current_location", () => ({
			filters: {
				is_active: 1,
			},
		}));
	},

	refresh(frm) {
		set_status_indicator(frm);
	},

	birth_date(frm) {
		if (!frm.doc.birth_date) {
			frm.set_value("age", null);
			return;
		}

		const birth_date = frappe.datetime.str_to_obj(frm.doc.birth_date);
		const current_date = frappe.datetime.str_to_obj(frappe.datetime.get_today());
		let age = current_date.getFullYear() - birth_date.getFullYear();
		const birthday_pending =
			current_date.getMonth() < birth_date.getMonth() ||
			(current_date.getMonth() === birth_date.getMonth() &&
				current_date.getDate() < birth_date.getDate());

		if (birthday_pending) {
			age -= 1;
		}
		frm.set_value("age", age);
	},

	primary_owner(frm) {
		if (frm.doc.primary_owner && !flt(frm.doc.primary_ownership_percentage)) {
			frm.set_value("primary_ownership_percentage", 100);
		} else if (!frm.doc.primary_owner) {
			frm.set_value("primary_ownership_percentage", 0);
		}
		update_ownership_total(frm);
	},
	primary_ownership_percentage: update_ownership_total,
	availability_status(frm) {
		if (!frm.is_new()) {
			frm.set_value("status_since", frappe.datetime.get_today());
		}
		set_status_indicator(frm);
	},
});

frappe.ui.form.on("Horse Ownership", {
	owner: update_ownership_total,
	ownership_percentage: update_ownership_total,
	shared_owners_remove: update_ownership_total,
});

function update_ownership_total(frm) {
	const primary_share = frm.doc.primary_owner
		? flt(frm.doc.primary_ownership_percentage)
		: 0;
	const shared_share = (frm.doc.shared_owners || []).reduce(
		(total, row) => total + flt(row.ownership_percentage),
		0
	);

	frm.set_value("total_ownership_percentage", primary_share + shared_share);
}

function set_status_indicator(frm) {
	const colors = {
		Available: "green",
		Resting: "blue",
		"Light Work": "orange",
		Injured: "red",
		"Veterinary Hold": "red",
		Retired: "gray",
		Sold: "gray",
	};
	const status = frm.doc.availability_status;

	if (status) {
		frm.page.set_indicator(__(status), colors[status] || "gray");
	}
}
