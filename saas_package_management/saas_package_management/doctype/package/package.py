# Copyright (c) 2024, itsyosefali and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class Package(Document):
	def validate(self):
		"""Validate package data"""
		if self.price and self.price < 0:
			frappe.throw(_("Price cannot be negative"))
		
		if self.users_limit and self.users_limit < 0:
			frappe.throw(_("Users limit cannot be negative"))
		
		if self.invoices_limit and self.invoices_limit < 0:
			frappe.throw(_("Invoices limit cannot be negative"))
		
		if self.expenses_limit and self.expenses_limit < 0:
			frappe.throw(_("Expenses limit cannot be negative"))
	
	def before_save(self):
		"""Set default values"""
		if not self.users_limit:
			self.users_limit = 0
		if not self.invoices_limit:
			self.invoices_limit = 0
		if not self.expenses_limit:
			self.expenses_limit = 0
