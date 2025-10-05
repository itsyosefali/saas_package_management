import frappe
from frappe.model.document import Document
from frappe import _


class InstanceActionSite(Document):
	def validate(self):
		"""Validate the site action"""
		# Site name is always required
		if not self.site_name:
			frappe.throw(_("Site Name is required"))
		
		# Get site name from the linked Customer Site if available
		if self.site and not self.site_name:
			site_doc = frappe.get_doc("Customer Site", self.site)
			self.site_name = site_doc.site_name
	
	def before_save(self):
		"""Actions to perform before saving"""
		# Set default action details if not provided
		if not self.action_details and self.action:
			self.action_details = self.get_action_description()
	
	def get_action_description(self):
		"""Get description for the selected action"""
		descriptions = {
			'Start Site': 'Start the site and make it accessible to users',
			'Stop Site': 'Stop the site and make it inaccessible to users',
			'Restart Site': 'Restart the site services and clear cache',
			'Backup Site': 'Create a backup of the site data and database',
			'Update Site': 'Update the site with latest changes and patches'
		}
		
		return descriptions.get(self.action, 'Custom action to be performed on the site')
	
	def execute_action(self):
		"""Execute the site action"""
		try:
			self.status = "In Progress"
			self.save()
			
			# Get the site document
			site = frappe.get_doc("Customer Site", self.site)
			
			if self.action == "Start Site":
				self.start_site(site)
			elif self.action == "Stop Site":
				self.stop_site(site)
			elif self.action == "Restart Site":
				self.restart_site(site)
			elif self.action == "Backup Site":
				self.backup_site(site)
			elif self.action == "Update Site":
				self.update_site(site)
			
			# Mark as completed
			self.status = "Completed"
			self.execution_log = f"Site action '{self.action}' completed successfully for site '{self.site_name}'"
			self.save()
			
		except Exception as e:
			# Mark as failed
			self.status = "Failed"
			self.execution_log = f"Site action '{self.action}' failed for site '{self.site_name}': {str(e)}"
			self.save()
			frappe.log_error(f"Site Action Failed: {str(e)}", "Site Action Error")
	
	def start_site(self, site):
		"""Start the site"""
		self.execution_log = f"Starting site {site.site_name}..."
		# Add your site start logic here
		# This could involve SSH commands, API calls, etc.
		pass
	
	def stop_site(self, site):
		"""Stop the site"""
		self.execution_log = f"Stopping site {site.site_name}..."
		# Add your site stop logic here
		pass
	
	def restart_site(self, site):
		"""Restart the site"""
		self.execution_log = f"Restarting site {site.site_name}..."
		# Add your site restart logic here
		pass
	
	def backup_site(self, site):
		"""Backup the site"""
		self.execution_log = f"Creating backup for site {site.site_name}..."
		# Add your site backup logic here
		pass
	
	def update_site(self, site):
		"""Update the site"""
		self.execution_log = f"Updating site {site.site_name}..."
		# Add your site update logic here
		pass
