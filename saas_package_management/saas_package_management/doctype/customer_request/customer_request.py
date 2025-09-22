# Copyright (c) 2024, itsyosefali and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import today, add_days, get_datetime


class CustomerRequest(Document):
	def validate(self):
		"""Validate customer request data"""
		# Validate that the selected package exists and is active
		if self.package:
			if not frappe.db.exists("Package", self.package):
				frappe.throw(_("Package '{0}' does not exist").format(self.package))
			
			package_doc = frappe.get_doc("Package", self.package)
			if not package_doc.is_active:
				frappe.throw(_("Package '{0}' is not active").format(self.package))
		
		# Validate customer exists
		if self.customer_name:
			if not frappe.db.exists("Customer", self.customer_name):
				frappe.throw(_("Customer '{0}' does not exist").format(self.customer_name))
	
	def before_save(self):
		"""Set default values and permissions"""
		# Set admin notes as read-only for customers
		if frappe.session.user != "Administrator" and "System Manager" not in frappe.get_roles():
			self.admin_notes = ""
	
	def on_submit(self):
		"""Actions when request is submitted"""
		# Send notification to admin
		self.send_notification_to_admin()
	
	def on_update_after_submit(self):
		"""Actions when request is updated after submission"""
		# Check if status changed to approved
		if self.status == "Approved":
			self.create_customer_site()
	
	def create_customer_site(self):
		"""Create Customer Site when request is approved"""
		try:
			# Check if Customer Site already exists for this request
			existing_site = frappe.get_all(
				"Customer Site",
				filters={"customer_request": self.name},
				fields=["name"]
			)
			
			if existing_site:
				frappe.msgprint(_("Customer Site already exists for this request"))
				return
			
			# Check if there are available instances for this package
			available_instances = frappe.get_all(
				"Instance",
				filters={
					"package": self.package,
					"is_active": 1,
					"deployment_status": ["in", ["Running", "Deployed"]]
				},
				fields=["name"]
			)
			
			if not available_instances:
				frappe.throw(_("No available instances found for package '{0}'. Please create an instance first or contact administrator.").format(self.package))
			
			# Generate site name from customer name
			customer_name = self.customer_name
			site_name = customer_name.lower().replace(" ", "-").replace(".", "").replace(",", "").replace("_", "-")
			
			# Ensure site name is unique
			counter = 1
			original_site_name = site_name
			while frappe.db.exists("Customer Site", {"site_name": site_name}):
				site_name = f"{original_site_name}-{counter}"
				counter += 1
			
			# Create the customer site
			customer_site = frappe.new_doc("Customer Site")
			customer_site.customer_request = self.name
			customer_site.customer_name = self.customer_name
			customer_site.site_name = site_name
			customer_site.package = self.package
			customer_site.status = "Active"
			
			# Use custom domain from request if provided, otherwise generate default
			if self.custom_domain:
				# If custom domain is provided, append .cnitsolution.cloud if not already present
				if not self.custom_domain.endswith('.cnitsolution.cloud'):
					customer_site.custom_domain = f"{self.custom_domain}.cnitsolution.cloud"
				else:
					customer_site.custom_domain = self.custom_domain
			else:
				customer_site.custom_domain = f"{site_name}.cnitsolution.cloud"
			
			customer_site.insert()
			customer_site.submit()
			
			# Update admin notes
			self.admin_notes = f"Customer Site created automatically: {customer_site.name} on {frappe.utils.now()}"
			self.save()
			
			frappe.msgprint(_("Customer Site created successfully: {0}").format(customer_site.name))
			
		except Exception as e:
			frappe.log_error(f"Error creating Customer Site: {str(e)}", "Customer Site Creation Error")
			frappe.msgprint(_("Error creating Customer Site: {0}").format(str(e)))
	
@frappe.whitelist()
def create_customer_site(customer_request_name):
	"""API method to create Customer Site from Customer Request"""
	try:
		# Get the customer request
		customer_request = frappe.get_doc("Customer Request", customer_request_name)
		
		if customer_request.status != "Approved":
			return {
				"success": False,
				"message": "Customer Request must be approved before creating a Customer Site"
			}
		
		# Check if Customer Site already exists
		existing_sites = frappe.get_all(
			"Customer Site",
			filters={"customer_request": customer_request_name},
			fields=["name"]
		)
		
		if existing_sites:
			return {
				"success": False,
				"message": "Customer Site already exists for this request"
			}
		
		# Check if there are available instances for this package
		available_instances = frappe.get_all(
			"Instance",
			filters={
				"package": customer_request.package,
				"is_active": 1,
				"deployment_status": ["in", ["Running", "Deployed"]]
			},
			fields=["name"]
		)
		
		if not available_instances:
			return {
				"success": False,
				"message": f"No available instances found for package '{customer_request.package}'. Please create an instance first or contact administrator."
			}
		
		# Generate site name from customer name
		customer_name = customer_request.customer_name
		site_name = customer_name.lower().replace(" ", "-").replace(".", "").replace(",", "").replace("_", "-")
		
		# Ensure site name is unique
		counter = 1
		original_site_name = site_name
		while frappe.db.exists("Customer Site", {"site_name": site_name}):
			site_name = f"{original_site_name}-{counter}"
			counter += 1
		
		# Create the customer site
		customer_site = frappe.new_doc("Customer Site")
		customer_site.customer_request = customer_request_name
		customer_site.customer_name = customer_request.customer_name
		customer_site.site_name = site_name
		customer_site.package = customer_request.package
		customer_site.status = "Active"
		customer_site.creation_date = get_datetime(today())
		customer_site.approval_date = get_datetime(today())	
		customer_site.expiry_date = add_days(get_datetime(today()), 365)  # 1 year from today
		
		# Use custom domain from request if provided
		if customer_request.custom_domain:
			if not customer_request.custom_domain.endswith('.cnitsolution.cloud'):
				customer_site.custom_domain = f"{customer_request.custom_domain}.cnitsolution.cloud"
			else:
				customer_site.custom_domain = customer_request.custom_domain
		else:
			customer_site.custom_domain = f"{site_name}.cnitsolution.cloud"
		
		customer_site.insert()
		customer_site.submit()
		
		# Update admin notes using frappe.db.set_value to avoid timestamp conflicts
		frappe.db.set_value(
			"Customer Request", 
			customer_request_name, 
			"admin_notes", 
			f"Customer Site created manually: {customer_site.name} on {frappe.utils.now()}"
		)
		
		return {
			"success": True,
			"message": f"Customer Site created successfully: {customer_site.name}",
			"site_name": customer_site.name
		}
		
	except frappe.TimestampMismatchError:
		# Handle document modification conflict
		frappe.log_error("Document modification conflict during Customer Site creation", "Customer Site API Creation Error")
		return {
			"success": False,
			"message": "Document has been modified. Please refresh and try again."
		}
	except Exception as e:
		frappe.log_error(f"Error creating Customer Site via API: {str(e)}", "Customer Site API Creation Error")
		return {
			"success": False,
			"message": str(e)
		}
	
	def send_notification_to_admin(self):
		"""Send notification to system managers about new request"""
		subject = f"New Package Request: {self.package} from {self.customer_name}"
		message = f"""
		New package request received:
		
		Customer: {self.customer_name}
		Package: {self.package}
		Request Date: {self.request_date}
		Notes: {self.notes or 'None'}
		
		Please review and update the status.
		"""
		
		# Get all system managers
		system_managers = frappe.get_all("User", 
			filters={"role_profile_name": "System Manager"}, 
			fields=["email"]
		)
		
		for manager in system_managers:
			if manager.email:
				frappe.sendmail(
					recipients=[manager.email],
					subject=subject,
					message=message
				)
