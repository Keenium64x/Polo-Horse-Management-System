import re
from decimal import Decimal, InvalidOperation

import frappe


NUMBER_PATTERN = re.compile(r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)")


def execute():
	normalize_column("Horse", "weight")
	normalize_column("Feeding", "qauntity")
	normalize_column("Feeding", "quantity")


def normalize_column(doctype: str, fieldname: str) -> None:
	table = f"tab{doctype}"
	if not frappe.db.table_exists(doctype) or not frappe.db.has_column(doctype, fieldname):
		return

	rows = frappe.db.sql(
		f"select name, `{fieldname}` from `{table}` where `{fieldname}` is not null",
		as_dict=True,
	)
	for row in rows:
		value = parse_number(row[fieldname])
		frappe.db.sql(
			f"update `{table}` set `{fieldname}` = %s where name = %s",
			(value, row.name),
		)


def parse_number(value) -> Decimal:
	if isinstance(value, Decimal):
		return value
	if isinstance(value, int | float):
		return Decimal(str(value))

	match = NUMBER_PATTERN.search(str(value))
	if not match:
		return Decimal("0")

	try:
		return Decimal(match.group())
	except InvalidOperation:
		return Decimal("0")
