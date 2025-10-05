frappe.ui.form.on('Instance Action', {
	refresh: function(frm) {
		// Add custom buttons based on status and action type
		if (frm.doc.status === "Pending" && !frm.doc.__islocal) {
			frm.add_custom_button(__('Execute Action'), function() {
				frappe.call({
					method: 'saas_package_management.saas_package_management.doctype.instance_action.instance_action.execute_instance_action',
					args: {
						action_name: frm.doc.name
					}
				}).then(() => {
					frm.reload_doc();
				});
			}, __('Actions'));
		}
		
		if (frm.doc.status === "In Progress") {
			frm.add_custom_button(__('Cancel Action'), function() {
				frm.set_value('status', 'Cancelled');
				frm.set_value('end_time', frappe.datetime.now_datetime());
				frm.set_value('execution_log', frm.doc.execution_log + '\nAction cancelled by user.');
				frm.save();
			}, __('Actions'));
		}
		
		// Add button to get instance status and save to execution info
		if (frm.doc.instance) {
			frm.add_custom_button(__('Get Instance Status'), function() {
				frappe.call({
					method: 'saas_package_management.saas_package_management.doctype.instance_action.instance_action.get_instance_status',
					args: {
						instance: frm.doc.instance
					}
				}).then((r) => {
					if (r.message) {
						// Save status to execution info
						frappe.call({
							method: 'saas_package_management.saas_package_management.doctype.instance_action.instance_action.save_instance_status_to_execution_info',
							args: {
								action_name: frm.doc.name,
								status_data: r.message
							}
						}).then((save_result) => {
							if (save_result.message && save_result.message.status === 'success') {
								frappe.show_alert({
									message: 'Instance status saved to execution info',
									indicator: 'green'
								});
								frm.reload_doc();
							}
						});
						
						// Show status in dialog
						frappe.msgprint({
							title: __('Instance Status'),
							message: frappe.render_template('instance_status_template', r.message)
						});
					}
				});
			}, __('Actions'));
			
		}
		
		// Add button to refresh sites list
		if (frm.doc.instance) {
			frm.add_custom_button(__('Refresh Sites'), function() {
				frappe.call({
					method: 'saas_package_management.saas_package_management.doctype.instance_action.instance_action.get_instance_sites',
					args: {
						instance: frm.doc.instance
					}
				}).then((r) => {
				if (r.message && r.message.length > 0) {
					// Clear existing site actions
					frm.clear_table('site_actions');
					
					// Add sites to the table
					r.message.forEach(site => {
						// Check if this site already exists in the table
						let existing_row = frm.doc.site_actions.find(row => row.site_name === site.site_name);
						if (existing_row) {
							return; // Skip if already exists
						}
						
						let row = frm.add_child('site_actions');
						
						// Only link to Customer Site if it exists
						if (site.customer_site) {
							row.site = site.customer_site;
							row.site_name = site.site_name;
						} else {
							// For sites not in Customer Site doctype, just use site name
							row.site_name = site.site_name;
							// Don't set the site field if no Customer Site record exists
						}
						
						row.action = 'Start Site'; // Default action
					});
					
					frm.refresh_field('site_actions');
					
					// Save the form to persist site actions
					frm.save().then(() => {
						frappe.show_alert({
							message: `Found ${r.message.length} sites on the server and saved to Instance Action`,
							indicator: 'green'
						});
					});
					} else {
						frappe.show_alert({
							message: 'No sites found on this instance. Check if bench directory exists and sites are properly configured.',
							indicator: 'orange'
						});
					}
				}).catch((error) => {
					frappe.show_alert({
						message: 'Failed to get sites from server. Check server connection and credentials.',
						indicator: 'red'
					});
					console.error('Error getting sites:', error);
				});
			}, __('Actions'));
		}
		
		// Add maintenance mode toggle for site actions
		if (frm.doc.site_actions && frm.doc.site_actions.length > 0) {
			frm.add_custom_button(__('Toggle Maintenance Mode'), function() {
				// Show dialog to select site and action
				let d = new frappe.ui.Dialog({
					title: __('Toggle Maintenance Mode'),
					fields: [
						{
							fieldtype: 'Select',
							fieldname: 'site_name',
							label: __('Site'),
							options: frm.doc.site_actions.map(row => row.site_name).join('\n'),
							reqd: 1
						},
						{
							fieldtype: 'Select',
							fieldname: 'action',
							label: __('Action'),
							options: [
								{value: 'enable', label: __('Enable Maintenance Mode')},
								{value: 'disable', label: __('Disable Maintenance Mode')}
							],
							reqd: 1
						}
					],
					primary_action_label: __('Execute'),
					primary_action: function(values) {
						frappe.call({
							method: 'saas_package_management.saas_package_management.doctype.instance_action.instance_action.toggle_site_maintenance_mode',
							args: {
								instance: frm.doc.instance,
								site_name: values.site_name,
								enable: values.action === 'enable'
							}
						}).then((r) => {
							if (r.message.status === 'success') {
								frappe.show_alert({
									message: r.message.message,
									indicator: 'green'
								});
							} else {
								frappe.show_alert({
									message: r.message.message,
									indicator: 'red'
								});
							}
						});
						d.hide();
					}
				});
				d.show();
			}, __('Site Actions'));
		}
	},
	
	instance: function(frm) {
		// When instance is selected, load available sites
		if (frm.doc.instance) {
			frappe.call({
				method: 'saas_package_management.saas_package_management.doctype.instance_action.instance_action.get_instance_sites',
				args: {
					instance: frm.doc.instance
				}
			}).then((r) => {
				if (r.message && r.message.length > 0) {
					// Clear existing site actions
					frm.clear_table('site_actions');
					
					// Add sites to the table
					r.message.forEach(site => {
						// Check if this site already exists in the table
						let existing_row = frm.doc.site_actions.find(row => row.site_name === site.site_name);
						if (existing_row) {
							return; // Skip if already exists
						}
						
						let row = frm.add_child('site_actions');
						
						// Only link to Customer Site if it exists
						if (site.customer_site) {
							row.site = site.customer_site;
							row.site_name = site.site_name;
						} else {
							// For sites not in Customer Site doctype, just use site name
							row.site_name = site.site_name;
							// Don't set the site field if no Customer Site record exists
						}
						
						row.action = 'Start Site'; // Default action
					});
					
					frm.refresh_field('site_actions');
					
					// Save the form to persist site actions
					frm.save().then(() => {
						frappe.show_alert({
							message: `Found ${r.message.length} sites on the server and saved to Instance Action`,
							indicator: 'green'
						});
					});
				} else {
					frappe.show_alert({
						message: 'No sites found on this instance. Check if bench directory exists and sites are properly configured.',
						indicator: 'orange'
					});
				}
			}).catch((error) => {
				frappe.show_alert({
					message: 'Failed to get sites from server. Check server connection and credentials.',
					indicator: 'red'
				});
				console.error('Error getting sites:', error);
			});
		}
	},
	
	action_type: function(frm) {
		// Update action details based on action type
		if (frm.doc.action_type) {
			let details = get_action_details(frm.doc.action_type);
			frm.set_value('action_details', details);
		}
	}
});

// Helper function to get action details based on action type
function get_action_details(action_type) {
	const action_details = {
		'Start Instance': 'Start the instance and all associated services',
		'Stop Instance': 'Stop the instance and all associated services',
		'Restart Instance': 'Restart the instance and all associated services',
		'Backup Instance': 'Create a backup of the instance and all its data',
		'Restore Instance': 'Restore the instance from a previous backup',
		'Update Instance': 'Update the instance with latest patches and updates',
		'Monitor Instance': 'Check instance health and performance metrics',
		'Maintenance Mode': 'Enable or disable maintenance mode for the instance',
		'Site Management': 'Manage individual sites on the instance'
	};
	
	return action_details[action_type] || 'Custom action to be performed on the instance';
}

// Custom template for instance status display
frappe.templates.instance_status_template = `
<div class="instance-status">
	<h4>{{ instance_name }}</h4>
	<p><strong>Connection Status:</strong> {{ connection_status }}</p>
	<p><strong>Deployment Status:</strong> {{ deployment_status }}</p>
	<p><strong>Server URL:</strong> {{ server_url || 'Not configured' }}</p>
	<p><strong>Last Backup:</strong> {{ last_backup_date || 'Never' }}</p>
	{% if system_status %}
	<div class="system-info">
		<h5>System Information</h5>
		<p><strong>Uptime:</strong> {{ system_status.uptime }}</p>
		<p><strong>Memory:</strong> {{ system_status.memory }}</p>
		<p><strong>Disk:</strong> {{ system_status.disk }}</p>
	</div>
	{% endif %}
	{% if bench_status %}
	<div class="bench-info">
		<h5>Bench Information</h5>
		<p><strong>Status:</strong> {{ bench_status.status }}</p>
		<p><strong>Version:</strong> {{ bench_status.version }}</p>
	</div>
	{% endif %}
	<div class="sites-info">
		<h5>Sites Information</h5>
		<p><strong>Total Sites:</strong> {{ total_sites }}</p>
		<p><strong>Active Sites:</strong> {{ active_sites }}</p>
		<p><strong>Inactive Sites:</strong> {{ inactive_sites }}</p>
	</div>
	{% if error %}
	<div class="error-info">
		<p><strong>Error:</strong> {{ error }}</p>
	</div>
	{% endif %}
</div>
`;

// Site Actions child table events
frappe.ui.form.on('Instance Action Site', {
	site: function(frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		if (row.site) {
			// Get site details and update site_name
			frappe.db.get_value('Customer Site', row.site, 'site_name').then((r) => {
				if (r.message && r.message.site_name) {
					frm.set_value(cdt, cdn, 'site_name', r.message.site_name);
				}
			});
		}
	},
	
	action: function(frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		// Update action details based on selected action
		if (row.action) {
			let details = get_site_action_details(row.action);
			frm.set_value(cdt, cdn, 'action_details', details);
		}
	}
});

// Helper function to get site action details
function get_site_action_details(action) {
	const action_details = {
		'Start Site': 'Start the site and make it accessible',
		'Stop Site': 'Stop the site and make it inaccessible',
		'Restart Site': 'Restart the site services',
		'Backup Site': 'Create a backup of the site data',
		'Update Site': 'Update the site with latest changes'
	};
	
	return action_details[action] || 'Custom action to be performed on the site';
}
