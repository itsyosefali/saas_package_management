// Copyright (c) 2024, itsyosefali and contributors
// For license information, please see license.txt

frappe.listview_settings['Customer Request'] = {
	onload: function(listview) {
		// Add custom button for bulk status update
		listview.page.add_menu_item(__("Bulk Update Status"), function() {
			let selected_docs = listview.get_checked_items();
			if (selected_docs.length === 0) {
				frappe.msgprint(__("Please select at least one request"));
				return;
			}
			
			let d = new frappe.ui.Dialog({
				title: __('Bulk Update Status'),
				fields: [
					{
						'fieldtype': 'Select',
						'fieldname': 'status',
						'label': __('Status'),
						'options': 'Pending\nApproved\nRejected',
						'reqd': 1
					},
					{
						'fieldtype': 'Small Text',
						'fieldname': 'admin_notes',
						'label': __('Admin Notes')
					}
				],
				primary_action_label: __('Update'),
				primary_action: function(values) {
					let promises = selected_docs.map(doc => {
						return frappe.call({
							method: 'saas_package_management.saas_package_management.api.customer_request.update_request_status',
							args: {
								name: doc.name,
								status: values.status,
								admin_notes: values.admin_notes
							}
						});
					});
					
					Promise.all(promises).then(() => {
						frappe.msgprint(__('Status updated for {0} requests', [selected_docs.length]));
						listview.refresh();
						d.hide();
					});
				}
			});
			d.show();
		});
	},
	
	get_indicator: function(doc) {
		const colors = {
			"Pending": "orange",
			"Approved": "green", 
			"Rejected": "red"
		};
		return [__(doc.status), colors[doc.status], "status,=," + doc.status];
	}
};
