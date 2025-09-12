# Copyright (c) 2024, itsyosefali and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def after_install():
	"""Populate initial package data after installation"""
	populate_package_data()


def populate_package_data():
	"""Populate initial package records"""
	packages = [
		{
			"package_name": "Ultimate",
			"price": 500.0,
			"users_limit": 1000,
			"invoices_limit": 10000,
			"expenses_limit": 5000,
			"features": "• Unlimited users\n• Unlimited invoices\n• Advanced reporting\n• API access\n• Priority support\n• Custom integrations\n• White-label options\n• Advanced analytics",
			"is_active": 1
		},
		{
			"package_name": "Standard",
			"price": 100.0,
			"users_limit": 10,
			"invoices_limit": 1000,
			"expenses_limit": 500,
			"features": "• Up to 10 users\n• Up to 1000 invoices\n• Basic reporting\n• Email support\n• Standard integrations\n• Mobile app access",
			"is_active": 1
		},
		{
			"package_name": "Professional",
			"price": 200.0,
			"users_limit": 25,
			"invoices_limit": 2500,
			"expenses_limit": 1250,
			"features": "• Up to 25 users\n• Up to 2500 invoices\n• Advanced reporting\n• Priority support\n• API access\n• Custom fields\n• Advanced analytics",
			"is_active": 1
		},
		{
			"package_name": "Premium",
			"price": 300.0,
			"users_limit": 50,
			"invoices_limit": 5000,
			"expenses_limit": 2500,
			"features": "• Up to 50 users\n• Up to 5000 invoices\n• Advanced reporting\n• Priority support\n• API access\n• Custom integrations\n• Advanced analytics\n• Workflow automation",
			"is_active": 1
		},
		{
			"package_name": "Elite",
			"price": 400.0,
			"users_limit": 100,
			"invoices_limit": 7500,
			"expenses_limit": 3750,
			"features": "• Up to 100 users\n• Up to 7500 invoices\n• Advanced reporting\n• Priority support\n• API access\n• Custom integrations\n• Advanced analytics\n• Workflow automation\n• White-label options",
			"is_active": 1
		}
	]
	
	for package_data in packages:
		# Check if package already exists
		if not frappe.db.exists("Package", {"package_name": package_data["package_name"]}):
			package_doc = frappe.new_doc("Package")
			package_doc.update(package_data)
			package_doc.insert(ignore_permissions=True)
			frappe.db.commit()
			print(f"Created package: {package_data['package_name']}")
		else:
			print(f"Package {package_data['package_name']} already exists, skipping...")
	
	print("Package data population completed!")
