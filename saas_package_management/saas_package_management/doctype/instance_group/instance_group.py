# Copyright (c) 2024, Ebkar – Technology & Management Solutions and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class InstanceGroup(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		description: DF.LongText | None
		instance_group_name: DF.Data
		is_active: DF.Check
		package: DF.Link

	# end: auto-generated types
	pass
