import frappe
import unittest
from frappe.tests.utils import FrappeTestCase


class TestInstanceAction(FrappeTestCase):
	def setUp(self):
		"""Set up test data"""
		# Create a test instance
		self.test_instance = frappe.get_doc({
			"doctype": "Instance",
			"instance_name": "Test Instance",
			"instance_ip": "192.168.1.100",
			"package": "Test Package",
			"ram_gb": 4,
			"cpu_cores": 2,
			"storage_gb": 100,
			"operating_system": "Ubuntu 24.04",
			"database_type": "MariaDB",
			"user": "testuser",
			"password": "testpass",
			"bench": "test-bench",
			"deployment_status": "Running"
		})
		self.test_instance.insert()
		
		# Create a test customer site
		self.test_site = frappe.get_doc({
			"doctype": "Customer Site",
			"naming_series": "CS-.YYYY.-.#####",
			"customer_name": "Test Customer",
			"site_name": "test-site",
			"package": "Test Package",
			"instance": self.test_instance.name,
			"status": "Active",
			"creation_date": frappe.utils.today()
		})
		self.test_site.insert()
	
	def tearDown(self):
		"""Clean up test data"""
		# Delete test documents
		if frappe.db.exists("Customer Site", self.test_site.name):
			self.test_site.delete()
		if frappe.db.exists("Instance", self.test_instance.name):
			self.test_instance.delete()
	
	def test_create_instance_action(self):
		"""Test creating an instance action"""
		action = frappe.get_doc({
			"doctype": "Instance Action",
			"action_name": "Test Action",
			"instance": self.test_instance.name,
			"action_type": "Start Instance",
			"status": "Pending",
			"action_details": "Test action for starting instance"
		})
		
		action.insert()
		self.assertEqual(action.action_name, "Test Action")
		self.assertEqual(action.instance, self.test_instance.name)
		self.assertEqual(action.action_type, "Start Instance")
		self.assertEqual(action.status, "Pending")
		
		# Clean up
		action.delete()
	
	def test_instance_action_validation(self):
		"""Test instance action validation"""
		# Test without instance
		action = frappe.get_doc({
			"doctype": "Instance Action",
			"action_name": "Test Action Without Instance",
			"action_type": "Start Instance",
			"status": "Pending"
		})
		
		with self.assertRaises(frappe.ValidationError):
			action.insert()
	
	def test_site_actions_table(self):
		"""Test adding site actions to the table"""
		action = frappe.get_doc({
			"doctype": "Instance Action",
			"action_name": "Test Site Management Action",
			"instance": self.test_instance.name,
			"action_type": "Site Management",
			"status": "Pending"
		})
		
		# Add site action
		action.append("site_actions", {
			"site": self.test_site.name,
			"site_name": self.test_site.site_name,
			"action": "Start Site",
			"status": "Pending"
		})
		
		action.insert()
		
		# Verify site action was added
		self.assertEqual(len(action.site_actions), 1)
		self.assertEqual(action.site_actions[0].site, self.test_site.name)
		self.assertEqual(action.site_actions[0].action, "Start Site")
		
		# Clean up
		action.delete()
	
	def test_action_type_options(self):
		"""Test that all action types are available"""
		action_types = [
			"Start Instance", "Stop Instance", "Restart Instance",
			"Backup Instance", "Restore Instance", "Update Instance",
			"Monitor Instance", "Maintenance Mode", "Site Management"
		]
		
		for action_type in action_types:
			action = frappe.get_doc({
				"doctype": "Instance Action",
				"action_name": f"Test {action_type}",
				"instance": self.test_instance.name,
				"action_type": action_type,
				"status": "Pending"
			})
			
			action.insert()
			self.assertEqual(action.action_type, action_type)
			
			# Clean up
			action.delete()
	
	def test_status_states(self):
		"""Test that all status states work correctly"""
		statuses = ["Pending", "In Progress", "Completed", "Failed", "Cancelled"]
		
		for status in statuses:
			action = frappe.get_doc({
				"doctype": "Instance Action",
				"action_name": f"Test {status} Action",
				"instance": self.test_instance.name,
				"action_type": "Start Instance",
				"status": status
			})
			
			action.insert()
			self.assertEqual(action.status, status)
			
			# Clean up
			action.delete()
	
	def test_get_instance_sites_function(self):
		"""Test the get_instance_sites function"""
		from saas_package_management.saas_package_management.doctype.instance_action.instance_action import get_instance_sites
		
		sites = get_instance_sites(self.test_instance.name)
		self.assertIsInstance(sites, list)
		self.assertGreaterEqual(len(sites), 1)
		
		# Check that our test site is in the results
		site_names = [site.get('site_name') for site in sites]
		self.assertIn(self.test_site.site_name, site_names)
	
	def test_get_instance_status_function(self):
		"""Test the get_instance_status function"""
		from saas_package_management.saas_package_management.doctype.instance_action.instance_action import get_instance_status
		
		status = get_instance_status(self.test_instance.name)
		self.assertIsInstance(status, dict)
		self.assertEqual(status['instance_name'], self.test_instance.instance_name)
		self.assertEqual(status['deployment_status'], self.test_instance.deployment_status)


if __name__ == '__main__':
	unittest.main()