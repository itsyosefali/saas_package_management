# Copyright (c) 2024, itsyosefali and contributors
# For license information, please see license.txt

import frappe
from frappe import _


@frappe.whitelist()
def create_customer_request(data):
	"""Create a new customer request from portal"""
	frappe.log_error(frappe.get_traceback(), "Customer Request Creation Error")
	try:
		required_fields = ['customer_name', 'package', 'request_date']
		for field in required_fields:
			if not data.get(field):
				frappe.throw(_(f"Field {field} is required"))
		
		if not frappe.db.exists("Customer", data.customer_name):
			frappe.throw(_("Customer does not exist"))
		
		if not frappe.db.exists("Package", data.package):
			frappe.throw(_("Package does not exist"))
		
		package_doc = frappe.get_doc("Package", data.package)
		if not package_doc.is_active:
			frappe.throw(_("Selected package is not active"))
		
		request_doc = frappe.new_doc("Customer Request")
		request_doc.customer_name = data.customer_name
		request_doc.package = data.package
		request_doc.request_date = data.request_date
		request_doc.notes = data.get('notes', '')
		request_doc.status = "Pending"
		
		request_doc.insert(ignore_permissions=True)
		request_doc.submit()
		
		frappe.db.commit()
		
		return {
			"status": "success",
			"message": _("Package request submitted successfully"),
			"name": request_doc.name
		}
		
	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "Customer Request Creation Error")
		frappe.throw(_(f"Error creating customer request: {str(e)}"))


@frappe.whitelist()
def get_customer_requests(customer_name=None):
	"""Get customer requests for a specific customer"""
	try:
		filters = {}
		if customer_name:
			filters["customer_name"] = customer_name
		
		requests = frappe.get_all(
			"Customer Request",
			filters=filters,
			fields=[
				"name", "customer_name", "package", "request_date", 
				"status", "notes", "admin_notes", "creation"
			],
			order_by="creation desc"
		)
		
		return requests
		
	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "Get Customer Requests Error")
		frappe.throw(_(f"Error fetching customer requests: {str(e)}"))


@frappe.whitelist()
def update_request_status(name, status, admin_notes=None):
	"""Update customer request status (admin only)"""
	try:
		if "System Manager" not in frappe.get_roles():
			frappe.throw(_("You don't have permission to update request status"))
		
		request_doc = frappe.get_doc("Customer Request", name)
		request_doc.status = status
		if admin_notes:
			request_doc.admin_notes = admin_notes
		
		request_doc.save()
		frappe.db.commit()
		
		return {
			"status": "success",
			"message": _("Request status updated successfully")
		}
		
	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "Update Request Status Error")
		frappe.throw(_(f"Error updating request status: {str(e)}"))
