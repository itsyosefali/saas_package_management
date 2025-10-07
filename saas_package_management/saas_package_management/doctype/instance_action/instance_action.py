import frappe
from frappe.model.document import Document
from frappe import _
import subprocess
import json
import time
from datetime import datetime


class InstanceAction(Document):
	def validate(self):
		"""Validate the instance action before saving"""
		if not self.instance:
			frappe.throw(_("Instance is required"))
		
		# Validate instance exists and is active
		instance = frappe.get_doc("Instance", self.instance)
		if not instance:
			frappe.throw(_("Instance not found"))
		
		# Set default action name if not provided
		if not self.action_name:
			self.action_name = f"{self.action_type} - {instance.instance_name} - {frappe.utils.now()}"
	
	def before_save(self):
		"""Actions to perform before saving"""
		# Set start time when status changes to "In Progress"
		if self.status == "In Progress" and not self.start_time:
			self.start_time = frappe.utils.now()
	
	def on_submit(self):
		"""Actions to perform when submitting the document"""
		if self.status == "Pending":
			self.status = "In Progress"
			self.start_time = frappe.utils.now()
			self.save()
			# Execute the action
			self.execute_action()
	
	def execute_action(self):
		"""Execute the instance action based on action type"""
		try:
			instance = frappe.get_doc("Instance", self.instance)
			
			if self.action_type == "Start Instance":
				self.start_instance(instance)
			elif self.action_type == "Stop Instance":
				self.stop_instance(instance)
			elif self.action_type == "Restart Instance":
				self.restart_instance(instance)
			elif self.action_type == "Backup Instance":
				self.backup_instance(instance)
			elif self.action_type == "Restore Instance":
				self.restore_instance(instance)
			elif self.action_type == "Update Instance":
				self.update_instance(instance)
			elif self.action_type == "Monitor Instance":
				self.monitor_instance(instance)
			elif self.action_type == "Maintenance Mode":
				self.toggle_maintenance_mode(instance)
			elif self.action_type == "Site Management":
				self.manage_sites(instance)
			
			# Mark as completed
			self.status = "Completed"
			self.end_time = frappe.utils.now()
			self.execution_log = f"Action completed successfully at {self.end_time}"
			self.save()
			
		except Exception as e:
			# Mark as failed
			self.status = "Failed"
			self.end_time = frappe.utils.now()
			self.execution_log = f"Action failed: {str(e)}"
			self.save()
			frappe.log_error(f"Instance Action Failed: {str(e)}", "Instance Action Error")
	
	def start_instance(self, instance):
		"""Start the instance"""
		self.execution_log = f"Starting instance {instance.instance_name}..."
		execute_server_command(instance, "supervisorctl start all")
		self.execution_log += f"\nInstance {instance.instance_name} started successfully"
	
	def stop_instance(self, instance):
		"""Stop the instance"""
		self.execution_log = f"Stopping instance {instance.instance_name}..."
		execute_server_command(instance, "supervisorctl stop all")
		self.execution_log += f"\nInstance {instance.instance_name} stopped successfully"
	
	def restart_instance(self, instance):
		"""Restart the instance"""
		self.execution_log = f"Restarting instance {instance.instance_name}..."
		execute_server_command(instance, "supervisorctl restart all")
		self.execution_log += f"\nInstance {instance.instance_name} restarted successfully"
	
	def backup_instance(self, instance):
		"""Backup the instance"""
		self.execution_log = f"Creating backup for instance {instance.instance_name}..."
		execute_server_command(instance, f"cd {instance.bench} && bench backup")
		self.execution_log += f"\nBackup created successfully for instance {instance.instance_name}"
	
	def restore_instance(self, instance):
		"""Restore the instance from backup"""
		self.execution_log = f"Restoring instance {instance.instance_name}..."
		# This would need backup file selection - for now just log
		self.execution_log += f"\nRestore functionality needs backup file selection"
	
	def update_instance(self, instance):
		"""Update the instance"""
		self.execution_log = f"Updating instance {instance.instance_name}..."
		execute_server_command(instance, f"cd {instance.bench} && bench update")
		self.execution_log += f"\nInstance {instance.instance_name} updated successfully"
	
	def monitor_instance(self, instance):
		"""Monitor instance health and status"""
		self.execution_log = f"Monitoring instance {instance.instance_name}..."
		# Get system status
		status = get_server_status(instance)
		
		# Store the comprehensive monitoring results in execution_info
		system_status = status.get('system_status', {})
		bench_status = status.get('bench_status', {})
		
		self.execution_info = f"""
=== INSTANCE MONITORING REPORT ===
Instance: {status.get('instance_name', 'Unknown')}
Server URL: {status.get('server_url', 'Unknown')}
Connection Status: {status.get('connection_status', 'Unknown')}
Deployment Status: {status.get('deployment_status', 'Unknown')}
Last Backup: {status.get('last_backup_date', 'Never')}
Server Time: {status.get('server_time', 'Unknown')}

=== SYSTEM STATUS ===
Uptime: {system_status.get('uptime', 'Unknown')}
Memory: {system_status.get('memory', 'Unknown')}
Disk Usage: {system_status.get('disk', 'Unknown')}

=== BENCH STATUS ===
Status: {bench_status.get('status', 'Unknown')}
Version: {bench_status.get('version', 'Unknown')}
Supervisor: {bench_status.get('supervisor', 'Unknown')}

=== SITES INFORMATION ===
Total Sites: {status.get('total_sites', 0)}
Active Sites: {status.get('active_sites', 0)}
Inactive Sites: {status.get('inactive_sites', 0)}

=== DISCOVERED SITES ===
"""
		
		# Add discovered sites information and handle maintenance mode
		sites = connect_to_server_and_get_sites(instance)
		for site in sites:
			site_name = site.get('site_name', 'Unknown')
			site_status = site.get('status', 'Unknown')
			
			self.execution_info += f"- {site_name} ({site_status}) - {site.get('package', 'Unknown')}\n"
			if site.get('customer_site'):
				self.execution_info += f"  └─ Customer Site: {site.get('customer_site')} (Customer: {site.get('customer_name', 'Unknown')})\n"
			else:
				self.execution_info += f"  └─ Standalone Site (No Customer Site record)\n"
			
			# Handle maintenance mode based on site status
			if site_status == 'Inactive' or site_status == 'Stopped':
				try:
					set_maintenance_mode_for_site(instance, site_name, True)
					self.execution_info += f"  └─ Maintenance mode enabled for stopped site\n"
				except Exception as e:
					self.execution_info += f"  └─ Failed to set maintenance mode: {str(e)}\n"
			elif site_status == 'Active' or site_status == 'Running':
				try:
					set_maintenance_mode_for_site(instance, site_name, False)
					self.execution_info += f"  └─ Maintenance mode disabled for active site\n"
				except Exception as e:
					self.execution_info += f"  └─ Failed to disable maintenance mode: {str(e)}\n"
		
		# Save discovered sites to child table
		save_discovered_sites_to_child_table(self, sites)
		
		self.execution_log += f"\nMonitoring completed. Status: {status.get('connection_status', 'Unknown')}"
		self.execution_log += f"\nFound {status.get('total_sites', 0)} sites on the instance"
		
		# Update the instance with latest information
		update_instance_with_status(instance, status)
	
	def toggle_maintenance_mode(self, instance):
		"""Toggle maintenance mode for the instance"""
		self.execution_log = f"Toggling maintenance mode for instance {instance.instance_name}..."
		execute_server_command(instance, f"cd {instance.bench} && bench set-maintenance-mode")
		self.execution_log += f"\nMaintenance mode toggled for instance {instance.instance_name}"
	
	def manage_sites(self, instance):
		"""Manage sites on the instance"""
		self.execution_log = f"Managing sites on instance {instance.instance_name}..."
		# Get all sites for this instance
		sites = frappe.get_all("Customer Site", 
			filters={"instance": self.instance, "status": "Active"},
			fields=["name", "site_name", "status"]
		)
		
		# Process each site action
		for site_action in self.site_actions:
			site = frappe.get_doc("Customer Site", site_action.site)
			if site_action.action == "Start Site":
				self.start_site(site)
			elif site_action.action == "Stop Site":
				self.stop_site(site)
			elif site_action.action == "Restart Site":
				self.restart_site(site)
			elif site_action.action == "Backup Site":
				self.backup_site(site)
			elif site_action.action == "Update Site":
				self.update_site(site)
	
	def start_site(self, site):
		"""Start a specific site"""
		self.execution_log += f"\nStarting site {site.site_name}..."
		instance = frappe.get_doc("Instance", self.instance)
		execute_server_command(instance, f"cd {instance.bench} && bench --site {site.site_name} start")
		self.execution_log += f"\nSite {site.site_name} started successfully"
	
	def stop_site(self, site):
		"""Stop a specific site"""
		self.execution_log += f"\nStopping site {site.site_name}..."
		instance = frappe.get_doc("Instance", self.instance)
		execute_server_command(instance, f"cd {instance.bench} && bench --site {site.site_name} stop")
		self.execution_log += f"\nSite {site.site_name} stopped successfully"
	
	def restart_site(self, site):
		"""Restart a specific site"""
		self.execution_log += f"\nRestarting site {site.site_name}..."
		instance = frappe.get_doc("Instance", self.instance)
		execute_server_command(instance, f"cd {instance.bench} && bench --site {site.site_name} restart")
		self.execution_log += f"\nSite {site.site_name} restarted successfully"
	
	def backup_site(self, site):
		"""Backup a specific site"""
		self.execution_log += f"\nBacking up site {site.site_name}..."
		instance = frappe.get_doc("Instance", self.instance)
		execute_server_command(instance, f"cd {instance.bench} && bench --site {site.site_name} backup")
		self.execution_log += f"\nSite {site.site_name} backed up successfully"
	
	def update_site(self, site):
		"""Update a specific site"""
		self.execution_log += f"\nUpdating site {site.site_name}..."
		instance = frappe.get_doc("Instance", self.instance)
		execute_server_command(instance, f"cd {instance.bench} && bench --site {site.site_name} update")
		self.execution_log += f"\nSite {site.site_name} updated successfully"


def execute_server_command(instance, command, timeout=300):
	"""Execute a command on the server via SSH with proper handling"""
	import paramiko
	import time
	import socket
	import select
	
	def is_ip_reachable(ip, timeout=3):
		try:
			socket.setdefaulttimeout(timeout)
			s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			s.connect((ip, 22))
			s.close()
			return True
		except Exception:
			return False
	
	output = ""
	status = "Failed"
	
	# Check if server is reachable
	if not is_ip_reachable(instance.instance_ip):
		error_msg = f"Server {instance.instance_ip} is not reachable on port 22 (SSH). Check network or firewall."
		frappe.log_error(error_msg, "SSH Connection Error")
		raise Exception(error_msg)
	
	try:
		# Get the password securely
		password = instance.get_password("password")
		
		# Create SSH connection
		ssh = paramiko.SSHClient()
		ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
		ssh.connect(
			hostname=instance.instance_ip,
			username=instance.user,
			password=password,
			port=22,
			timeout=300
		)
		
		# Get transport and create channel
		transport = ssh.get_transport()
		channel = transport.open_session()
		channel.get_pty()
		channel.exec_command(command)
		
		start_time = time.time()
		password_sent = False
		out = ''
		err = ''
		
		# Read output in real-time
		while not channel.exit_status_ready():
			rl, _, _ = select.select([channel], [], [], 0.5)
			if channel.recv_ready():
				out = channel.recv(4096).decode()
				if out:
					output += out
			else:
				out = ''
				
			if channel.recv_stderr_ready():
				err = channel.recv_stderr(4096).decode()
				if err:
					output += err
			else:
				err = ''
			
			# Handle prompts
			if out:
				if not password_sent and "[sudo] password for" in out:
					channel.send(f"{password}\n")
					password_sent = True
					time.sleep(1)
					continue
				if "[y/N]" in out:
					channel.send("y\n")
					time.sleep(1)
					continue
				if "Select the appropriate number [1-2]" in out:
					channel.send("2\n")
					time.sleep(1)
					continue
					
			if err:
				if not password_sent and "[sudo] password for" in err:
					channel.send(f"{password}\n")
					password_sent = True
					time.sleep(1)
					continue
				if "[y/N]" in err:
					channel.send("y\n")
					time.sleep(1)
					continue
				if "Select the appropriate number [1-2]" in err:
					channel.send("2\n")
					time.sleep(1)
					continue
			
			# Check timeout
			if time.time() - start_time > timeout:
				output += "\n[Timeout Exceeded]"
				break
		
		# Flush any remaining output
		while channel.recv_ready():
			out = channel.recv(4096).decode()
			if out:
				output += out
				
		while channel.recv_stderr_ready():
			err = channel.recv_stderr(4096).decode()
			if err:
				output += err
		
		# Get exit status
		exit_status = channel.recv_exit_status()
		status = "Success" if exit_status == 0 else "Failed"
		
		# Close SSH connection
		ssh.close()
		
		if status == "Failed":
			raise Exception(f"Command failed with exit status {exit_status}: {output}")
		
		return output
		
	except Exception as e:
		error_msg = f"SSH Command Error: {str(e)}"
		frappe.log_error(error_msg, "SSH Command Error")
		raise Exception(error_msg)


@frappe.whitelist()
def get_instance_sites(instance):
	"""Get all sites for a given instance by connecting to the server"""
	try:
		# Get instance details
		instance_doc = frappe.get_doc("Instance", instance)
		
		# Connect to the server and get sites
		sites = connect_to_server_and_get_sites(instance_doc)
		
		return sites
		
	except Exception as e:
		frappe.log_error(f"Error getting sites from instance {instance}: {str(e)}", "Instance Sites Error")
		return []


def save_discovered_sites_to_child_table(action_doc, sites):
	"""Save discovered sites to the child table"""
	try:
		# Clear existing site actions
		action_doc.site_actions = []
		
		for site in sites:
			# Create new child row
			child_row = action_doc.append('site_actions', {
				'site_name': site.get('site_name', 'Unknown'),
				'action': 'Start Site',  # Default action
				'status': 'Pending'  # Default status
			})
			
			# Link to Customer Site if exists
			if site.get('customer_site'):
				child_row.site = site.get('customer_site')
			
			# Add maintenance mode info
			if site.get('maintenance_mode'):
				child_row.status = 'Maintenance Mode Enabled'
		
		# Don't save here - let the caller save the document
		# This prevents issues with nested saves
		
	except Exception as e:
		frappe.log_error(f"Error saving sites to child table: {str(e)}", "Site Actions Save Error")


def connect_to_server_and_get_sites(instance_doc):
	"""Connect to the server and get all sites - optimized for speed"""
	sites = []
	
	try:
		# Use a single command to get sites and basic info
		combined_cmd = f"""
		cd {instance_doc.bench} 2>/dev/null || cd /home/*/erp15 2>/dev/null || cd /home/*/frappe-bench 2>/dev/null;
		BENCH_PATH=$(pwd);
		echo "BENCH_PATH:$BENCH_PATH";
		ls sites/ | grep -v '^apps\\|^assets\\|^common_site_config\\|^apps.json\\|^apps.txt' | while read site; do
			if [[ "$site" == *.* ]]; then
				echo "SITE:$site";
				# Quick status check
				if [ -f "sites/$site/site_config.json" ]; then
					echo "STATUS:$site:Active";
				else
					echo "STATUS:$site:Unknown";
				fi;
			fi;
		done
		"""
		
		output = execute_server_command(instance_doc, combined_cmd)
		print(f"Combined command output: {output}")
		
		# Parse the output
		bench_path = None
		site_data = {}
		
		for line in output.split('\n'):
			line = line.strip()
			if line.startswith('BENCH_PATH:'):
				bench_path = line.replace('BENCH_PATH:', '')
			elif line.startswith('SITE:'):
				site_name = line.replace('SITE:', '')
				site_data[site_name] = {'name': site_name, 'site_name': site_name}
			elif line.startswith('STATUS:'):
				parts = line.replace('STATUS:', '').split(':')
				if len(parts) == 2:
					site_name, status = parts
					if site_name in site_data:
						site_data[site_name]['status'] = status
		
		# Get all Customer Sites in one query for efficiency
		site_names = list(site_data.keys())
		customer_sites = {}
		if site_names:
			try:
				customer_site_records = frappe.get_all("Customer Site",
					filters={"custom_domain": ["in", site_names]},
					fields=["name", "customer_name", "package", "status", "instance", "custom_domain"]
				)
				# Create a lookup dictionary
				for record in customer_site_records:
					customer_sites[record.custom_domain] = record
			except Exception as e:
				frappe.log_error(f"Error getting Customer Sites: {str(e)}", "Customer Site Lookup Error")
		
		# Process sites
		for site_name, site_info in site_data.items():
			try:
				# Get Customer Site from lookup
				customer_site = customer_sites.get(site_name)
				
				# Construct server URL
				server_url = f"https://{site_name}"
				
				# Check site status and handle maintenance mode accordingly
				site_status = site_info.get('status', 'Unknown')
				maintenance_mode = 0  # Default to 0 (accessible)
				
				if site_status == 'Inactive' or site_status == 'Stopped':
					# Set maintenance mode to 1 for stopped sites
					result = set_maintenance_mode_for_site(instance_doc, site_name, True)
					maintenance_mode = result if result is not None else 0
				elif site_status == 'Active' or site_status == 'Running':
					# Set maintenance mode to 0 for active sites
					result = set_maintenance_mode_for_site(instance_doc, site_name, False)
					maintenance_mode = result if result is not None else 0
				
				sites.append({
					"name": site_name,
					"site_name": site_name,
					"status": site_status,
					"package": "Unknown",  # Skip package detection for speed
					"server_url": server_url,
					"customer_site": customer_site.get("name") if customer_site else None,
					"customer_name": customer_site.get("customer_name") if customer_site else None,
					"is_customer_site": customer_site is not None,
					"maintenance_mode": maintenance_mode
				})
			except Exception as e:
				frappe.log_error(f"Error processing site {site_name}: {str(e)}", "Site Processing Error")
		
	except Exception as e:
		frappe.log_error(f"Error getting sites from server: {str(e)}", "Site Discovery Error")
	
	return sites


def get_site_status_robust(instance_doc, site_name):
	"""Get the status of a specific site using robust SSH"""
	try:
		# Check if site is active using multiple methods
		methods = [
			f"cd {instance_doc.bench} && bench --site {site_name} status",
			f"cd {instance_doc.bench} && supervisorctl status erp15-{site_name}",
			f"cd {instance_doc.bench} && ps aux | grep {site_name} | grep -v grep"
		]
		
		for method in methods:
			try:
				output = execute_server_command(instance_doc, method)
				if output:
					if any(keyword in output.lower() for keyword in ["active", "running", "started"]):
						return "Active"
					elif any(keyword in output.lower() for keyword in ["inactive", "stopped", "failed"]):
						return "Inactive"
			except:
				continue
		
		# If no method worked, try a simple check
		try:
			check_cmd = f"cd {instance_doc.bench} && test -f sites/{site_name}/site_config.json && echo 'Site exists' || echo 'Site not found'"
			result = execute_server_command(instance_doc, check_cmd)
			if "Site exists" in result:
				return "Active"  # Assume active if site config exists
		except:
			pass
			
		return "Unknown"
			
	except Exception as e:
		frappe.log_error(f"Error getting site status for {site_name}: {str(e)}", "Site Status Error")
		return "Unknown"


def get_site_package(instance_doc, site_name):
	"""Get the package/apps installed for a specific site"""
	try:
		# Try to get package info from site config
		command = f"cd {instance_doc.bench} && cat sites/{site_name}/site_config.json | grep -o '\"app_name\":[^,]*' | head -1"
		output = execute_server_command(instance_doc, command)
		
		if output and "app_name" in output:
			# Extract app name from the output
			app_name = output.split(':')[1].strip().strip('"')
			return app_name
		
		# Try alternative method
		command = f"cd {instance_doc.bench} && bench --site {site_name} list-apps 2>/dev/null | head -1"
		output = execute_server_command(instance_doc, command)
		
		if output and output.strip():
			return output.strip()
		
		return "Unknown"
		
	except Exception as e:
		frappe.log_error(f"Error getting package for {site_name}: {str(e)}", "Package Detection Error")
		return "Unknown"


def get_customer_site_for_site_name(site_name):
	"""Check if a site exists in Customer Site doctype and return its details"""
	try:
		customer_sites = frappe.get_all("Customer Site",
			filters={"custom_domain": site_name},
			fields=["name", "customer_name", "package", "status", "instance", "custom_domain"]
		)
		
		if customer_sites:
			return customer_sites[0]
		return None
		
	except Exception as e:
		frappe.log_error(f"Error checking Customer Site for {site_name}: {str(e)}", "Customer Site Lookup Error")
		return None


def set_maintenance_mode_for_site(instance_doc, site_name, enable=True):
	"""Set maintenance mode for a specific site"""
	try:
		# Get the current site config
		config_cmd = f"cd {instance_doc.bench} && cat sites/{site_name}/site_config.json"
		config_output = execute_server_command(instance_doc, config_cmd)
		
		# Parse the JSON config
		import json
		site_config = json.loads(config_output)
		
		# Update maintenance mode
		# In Frappe: 1 = maintenance mode enabled (site not accessible), 0 = maintenance mode disabled (site accessible)
		maintenance_mode_value = 1 if enable else 0
		site_config["maintenance_mode"] = maintenance_mode_value
		
		# Write the updated config back using Python heredoc to avoid escaping issues
		config_json = json.dumps(site_config, indent=2)
		# Escape single quotes in JSON for bash
		config_json_escaped = config_json.replace("'", "'\\''")
		
		# Use cat with heredoc instead of echo to avoid escaping issues
		update_cmd = f"cd {instance_doc.bench} && cat > sites/{site_name}/site_config.json << 'EOF'\n{config_json}\nEOF"
		execute_server_command(instance_doc, update_cmd)
		
		# Log the action
		action = "enabled" if enable else "disabled"
		frappe.log_error(f"Maintenance mode {action} for site {site_name} (set to {maintenance_mode_value})", "Maintenance Mode")
		
		# Return the actual maintenance mode value (1 or 0), not just True/False
		return maintenance_mode_value
		
	except Exception as e:
		frappe.log_error(f"Error setting maintenance mode for {site_name}: {str(e)}", "Maintenance Mode Error")
		return None  # Return None on error to indicate failure


@frappe.whitelist()
def toggle_site_maintenance_mode(instance, site_name, enable=True):
	"""Toggle maintenance mode for a specific site"""
	try:
		# Convert enable to boolean (frappe.whitelist can pass values as strings or integers)
		frappe.log_error(f"toggle_site_maintenance_mode called with enable={enable}, type={type(enable)}", "Maintenance Mode Debug")
		
		if isinstance(enable, str):
			# Handle string values: 'true', 'True', '1', 'yes' etc.
			enable = enable.lower() in ['true', '1', 'yes']
		elif isinstance(enable, int):
			# Handle integer values: 1 = True, 0 = False
			enable = bool(enable)
		else:
			# Handle actual boolean values
			enable = bool(enable)
		
		frappe.log_error(f"After conversion, enable={enable}, type={type(enable)}", "Maintenance Mode Debug")
		
		instance_doc = frappe.get_doc("Instance", instance)
		maintenance_mode_value = set_maintenance_mode_for_site(instance_doc, site_name, enable)
		
		# set_maintenance_mode_for_site returns the maintenance mode value (1 or 0)
		# Check if it's not None (which would indicate an error)
		if maintenance_mode_value is not None:
			action = "enabled" if enable else "disabled"
			return {
				"status": "success", 
				"message": f"Maintenance mode {action} for site {site_name}"
			}
		else:
			return {
				"status": "error", 
				"message": f"Failed to toggle maintenance mode for site {site_name}"
			}
	except Exception as e:
		return {
			"status": "error", 
			"message": f"Error toggling maintenance mode: {str(e)}"
		}


@frappe.whitelist()
def save_instance_status_to_execution_info(action_name, status_data):
	"""Save instance status data to execution info"""
	try:
		action = frappe.get_doc("Instance Action", action_name)
		
		# Format the status data for execution info
		status_info = f"""
=== INSTANCE STATUS REPORT ===
Timestamp: {frappe.utils.now_datetime()}

Instance: {status_data.get('instance_name', 'Unknown')}
Server URL: {status_data.get('server_url', 'Unknown')}
Deployment Status: {status_data.get('deployment_status', 'Unknown')}
Connection Status: {status_data.get('connection_status', 'Unknown')}
Last Backup: {status_data.get('last_backup_date', 'Never')}

=== SYSTEM STATUS ===
"""
		
		# Add system status
		if status_data.get('system_status'):
			sys_status = status_data['system_status']
			if isinstance(sys_status, dict):
				status_info += f"Uptime: {sys_status.get('uptime', 'Unknown')}\n"
				status_info += f"Memory: {sys_status.get('memory', 'Unknown')}\n"
				status_info += f"Disk: {sys_status.get('disk', 'Unknown')}\n"
			else:
				status_info += f"System Status: {sys_status}\n"
		
		# Add bench status
		if status_data.get('bench_status'):
			bench_status = status_data['bench_status']
			if isinstance(bench_status, dict):
				status_info += f"\n=== BENCH STATUS ===\n"
				status_info += f"Status: {bench_status.get('status', 'Unknown')}\n"
				status_info += f"Version: {bench_status.get('version', 'Unknown')}\n"
				status_info += f"Supervisor: {bench_status.get('supervisor', 'Unknown')}\n"
			else:
				status_info += f"Bench Status: {bench_status}\n"
		
		# Add site statistics
		status_info += f"\n=== SITE STATISTICS ===\n"
		status_info += f"Total Sites: {status_data.get('total_sites', 0)}\n"
		status_info += f"Active Sites: {status_data.get('active_sites', 0)}\n"
		status_info += f"Inactive Sites: {status_data.get('inactive_sites', 0)}\n"
		
		# Update execution info
		action.execution_info = (action.execution_info or "") + status_info
		action.save()
		
		return {"status": "success", "message": "Instance status saved to execution info"}
		
	except Exception as e:
		frappe.log_error(f"Error saving instance status: {str(e)}", "Instance Status Save Error")
		return {"status": "error", "message": f"Failed to save status: {str(e)}"}


@frappe.whitelist()
def execute_instance_action(action_name):
	"""Execute an instance action"""
	action = frappe.get_doc("Instance Action", action_name)
	action.execute_action()
	return {"status": "success", "message": "Action executed successfully"}


@frappe.whitelist()
def create_monitoring_action(instance):
	"""Create a monitoring action for an instance to save comprehensive status"""
	try:
		# Get instance details
		instance_doc = frappe.get_doc("Instance", instance)
		
		# Create a monitoring action
		action = frappe.get_doc({
			"doctype": "Instance Action",
			"action_name": f"Monitor {instance_doc.instance_name} - {frappe.utils.now()}",
			"instance": instance,
			"action_type": "Monitor Instance",
			"status": "Pending",
			"action_details": "Comprehensive monitoring of instance health, system status, and sites information"
		})
		
		action.insert()
		
		# Execute the monitoring action immediately
		action.execute_action()
		
		return {
			"status": "success", 
			"message": "Monitoring action created and executed successfully",
			"action_name": action.name
		}
		
	except Exception as e:
		frappe.log_error(f"Error creating monitoring action: {str(e)}", "Monitoring Action Error")
		return {"status": "error", "message": str(e)}


@frappe.whitelist()
def get_instance_status(instance):
	"""Get the current status of an instance by connecting to the server"""
	try:
		# Get instance details
		instance_doc = frappe.get_doc("Instance", instance)
		
		# Connect to server and get real-time status
		status_info = get_server_status(instance_doc)
		
		return status_info
		
	except Exception as e:
		frappe.log_error(f"Error getting instance status for {instance}: {str(e)}", "Instance Status Error")
		# Return basic info if connection fails
		instance_doc = frappe.get_doc("Instance", instance)
		return {
			"instance_name": instance_doc.instance_name,
			"deployment_status": instance_doc.deployment_status,
			"server_url": instance_doc.server_url,
			"last_backup_date": instance_doc.last_backup_date,
			"connection_status": "Failed to connect",
			"error": str(e)
		}


def get_server_status(instance_doc):
	"""Get real-time status from the server using robust SSH - optimized for speed"""
	try:
		import concurrent.futures
		
		# Run system status, bench status, and sites discovery in parallel
		with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
			# Submit all tasks in parallel
			system_future = executor.submit(get_system_status_robust, instance_doc)
			bench_future = executor.submit(get_bench_status_robust, instance_doc)
			sites_future = executor.submit(connect_to_server_and_get_sites, instance_doc)
			
			# Wait for all results
			system_status = system_future.result()
			bench_status = bench_future.result()
			sites = sites_future.result()
		
		# Count active sites
		active_sites = len([s for s in sites if s.get('status') == 'Active'])
		
		return {
			"instance_name": instance_doc.instance_name,
			"deployment_status": instance_doc.deployment_status,
			"server_url": instance_doc.server_url,
			"last_backup_date": instance_doc.last_backup_date,
			"connection_status": "Connected",
			"system_status": system_status,
			"bench_status": bench_status,
			"total_sites": len(sites),
			"active_sites": active_sites,
			"inactive_sites": len(sites) - active_sites,
			"server_time": frappe.utils.now()
		}
		
	except Exception as e:
		frappe.log_error(f"Error connecting to server: {str(e)}", "Server Connection Error")
		raise e


def get_system_status_robust(instance_doc):
	"""Get system status (CPU, Memory, Disk) using robust SSH - optimized"""
	try:
		# Get all system info in one command
		output = execute_server_command(instance_doc, "uptime && free -h && df -h")
		
		# Parse system info
		lines = output.strip().split('\n')
		uptime = lines[0] if lines else "Unknown"
		
		# Get memory info
		memory_info = "Unknown"
		for line in lines[1:]:
			if "Mem:" in line:
				memory_info = line
				break
		
		# Get disk info
		disk_info = "Unknown"
		for line in lines:
			if "/" in line and ("G" in line or "T" in line):
				disk_info = line
				break
		
		return {
			"uptime": uptime,
			"memory": memory_info,
			"disk": disk_info
		}
		
	except Exception as e:
		frappe.log_error(f"Error getting system status: {str(e)}", "System Status Error")
		return {"error": str(e)}


def get_bench_status_robust(instance_doc):
	"""Get bench status using robust SSH - optimized"""
	try:
		# Get bench and supervisor status in one command
		combined_cmd = f"""
		cd {instance_doc.bench} 2>/dev/null && bench version 2>/dev/null || echo "BENCH_ERROR";
		supervisorctl status 2>/dev/null || echo "SUPERVISOR_ERROR"
		"""
		
		output = execute_server_command(instance_doc, combined_cmd)
		
		# Parse the combined output
		lines = output.strip().split('\n')
		bench_output = ""
		supervisor_output = ""
		
		for line in lines:
			if "BENCH_ERROR" in line:
				bench_output = "Error: Bench not found"
			elif "SUPERVISOR_ERROR" in line:
				supervisor_output = "Error: Supervisor not accessible"
			elif not line.startswith("SUPERVISOR_ERROR") and not line.startswith("BENCH_ERROR"):
				if not bench_output:
					bench_output = line
				else:
					supervisor_output += line + "\n"
		
		return {
			"status": "Running" if "bench" in bench_output.lower() and "Error" not in bench_output else "Stopped",
			"version": bench_output.strip(),
			"supervisor": supervisor_output.strip()
		}
		
	except Exception as e:
		frappe.log_error(f"Error getting bench status: {str(e)}", "Bench Status Error")
		return {"status": "Error", "error": str(e)}


def update_instance_with_status(instance_doc, status_info):
	"""Update the instance doctype with latest status information"""
	try:
		# Update deployment status based on connection
		if status_info.get('connection_status') == 'Connected':
			instance_doc.deployment_status = 'Running'
		else:
			instance_doc.deployment_status = 'Failed'
		
		# Update last backup date if available
		if status_info.get('last_backup_date'):
			instance_doc.last_backup_date = status_info.get('last_backup_date')
		
		# Save the instance
		instance_doc.save()
		frappe.db.commit()
		
	except Exception as e:
		frappe.log_error(f"Error updating instance status: {str(e)}", "Instance Update Error")
