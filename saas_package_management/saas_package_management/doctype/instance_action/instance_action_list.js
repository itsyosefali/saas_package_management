frappe.listview_settings['Instance Action'] = {
	onload: function(listview) {
		// Add custom buttons to the list view
		listview.page.add_menu_item(__("Execute All Pending"), function() {
			execute_all_pending_actions();
		});
		
		listview.page.add_menu_item(__("Refresh Instance Status"), function() {
			refresh_all_instance_status();
		});
	},
	
	get_indicator: function(doc) {
		// Color code the status indicators
		const status_colors = {
			'Pending': 'orange',
			'In Progress': 'blue',
			'Completed': 'green',
			'Failed': 'red',
			'Cancelled': 'grey'
		};
		
		return [__(doc.status), status_colors[doc.status], 'status,=,' + doc.status];
	},
	
	formatters: {
		// Custom formatter for action type
		action_type: function(value) {
			const action_icons = {
				'Start Instance': 'play',
				'Stop Instance': 'stop',
				'Restart Instance': 'refresh',
				'Backup Instance': 'download',
				'Restore Instance': 'upload',
				'Update Instance': 'update',
				'Monitor Instance': 'monitor',
				'Maintenance Mode': 'settings',
				'Site Management': 'sitemap'
			};
			
			const icon = action_icons[value] || 'gear';
			return `<i class="fa fa-${icon}"></i> ${value}`;
		},
		
		// Custom formatter for execution time
		execution_time: function(doc) {
			if (doc.start_time && doc.end_time) {
				const start = new Date(doc.start_time);
				const end = new Date(doc.end_time);
				const duration = Math.round((end - start) / 1000); // Duration in seconds
				return `${duration}s`;
			} else if (doc.start_time) {
				const start = new Date(doc.start_time);
				const now = new Date();
				const duration = Math.round((now - start) / 1000);
				return `${duration}s (running)`;
			}
			return '-';
		}
	},
	
	// Add custom columns to the list view
	add_fields: ['start_time', 'end_time'],
	
	// Custom filters
	filters: [
		['status', '=', 'Pending'],
		['status', '=', 'In Progress'],
		['status', '=', 'Completed'],
		['status', '=', 'Failed'],
		['action_type', '=', 'Site Management']
	]
};

// Function to execute all pending actions
function execute_all_pending_actions() {
	frappe.confirm(
		__('Are you sure you want to execute all pending actions?'),
		function() {
			frappe.call({
				method: 'frappe.client.get_list',
				args: {
					doctype: 'Instance Action',
					filters: {
						status: 'Pending'
					},
					fields: ['name']
				},
				callback: function(r) {
					if (r.message) {
						let promises = r.message.map(doc => {
							return frappe.call({
								method: 'execute_instance_action',
								args: {
									action_name: doc.name
								}
							});
						});
						
						Promise.all(promises).then(() => {
							frappe.msgprint(__('All pending actions have been executed'));
							frappe.listview.refresh();
						});
					}
				}
			});
		}
	);
}

// Function to refresh all instance status
function refresh_all_instance_status() {
	frappe.call({
		method: 'frappe.client.get_list',
		args: {
			doctype: 'Instance Action',
			filters: {
				status: ['in', ['Pending', 'In Progress']]
			},
			fields: ['name', 'instance']
		},
		callback: function(r) {
			if (r.message) {
				frappe.msgprint(__('Refreshing instance status for {0} actions', [r.message.length]));
				// Add your refresh logic here
				frappe.listview.refresh();
			}
		}
	});
}

// Custom row formatter
frappe.listview_settings['Instance Action'].formatters = {
	...frappe.listview_settings['Instance Action'].formatters,
	
	// Format the instance name with status
	instance: function(value, doc) {
		return `<strong>${value}</strong>`;
	},
	
	// Format the action details with tooltip
	action_details: function(value, doc) {
		if (value && value.length > 50) {
			return `<span title="${value}">${value.substring(0, 50)}...</span>`;
		}
		return value || '-';
	}
};
