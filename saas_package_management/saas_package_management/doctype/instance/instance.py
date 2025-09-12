# Copyright (c) 2024, Ebkar – Technology & Management Solutions and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class Instance(Document):
	def validate(self):
		if self.instance_group and self.package:
			instance_group_doc = frappe.get_doc("Instance Group", self.instance_group)
			if instance_group_doc.package != self.package:
				frappe.throw(f"Instance Group '{self.instance_group}' does not belong to Package '{self.package}'")
	
	def before_save(self):
		if self.instance_group and not self.package:
			instance_group_doc = frappe.get_doc("Instance Group", self.instance_group)
			self.package = instance_group_doc.package