// Copyright (c) 2025, itsyosefali and contributors
// For license information, please see license.txt

frappe.ui.form.on("Instance", {
	refresh(frm) {
		// Add Test Password Decryption button
		if (frm.doc.instance_ip && frm.doc.user) {
			frm.add_custom_button(__('Test Password Decryption'), function() {
				test_password_decryption(frm);
			}, __('Actions'));
		}
		
		// Add Test SSH Connection button
		if (frm.doc.instance_ip && frm.doc.user && frm.doc.password) {
			frm.add_custom_button(__('Test SSH Connection'), function() {
				test_ssh_connection(frm);
			}, __('Actions'));
		}
	},
});

function test_password_decryption(frm) {
	frappe.call({
		method: 'saas_package_management.saas_package_management.doctype.customer_site.customer_site.test_password_decryption',
		args: {
			instance_name: frm.doc.name
		},
		callback: function(r) {
			if (r.message && r.message.success) {
				let details = r.message.details;
				let message = `
					<h4>Password Decryption Test Results</h4>
					<p><strong>Instance IP:</strong> ${details.instance_ip}</p>
					<p><strong>SSH User:</strong> ${details.ssh_user}</p>
					<p><strong>SSH Password Status:</strong> ${details.ssh_password_status}</p>
					<p><strong>SSH Password Length:</strong> ${details.ssh_password_length} characters</p>
					<p><strong>Database Password Status:</strong> ${details.database_password_status}</p>
					<p><strong>Database Password Length:</strong> ${details.database_password_length} characters</p>
				`;
				
				frappe.msgprint({
					title: __('Password Decryption Test'),
					message: message,
					indicator: details.ssh_password_status.includes('Success') && details.database_password_status.includes('Success') ? 'green' : 'orange'
				});
			} else {
				frappe.msgprint({
					title: __('Password Decryption Test Failed'),
					message: r.message.message || 'Unknown error',
					indicator: 'red'
				});
			}
		}
	});
}

function test_ssh_connection(frm) {
	frappe.call({
		method: 'saas_package_management.saas_package_management.doctype.customer_site.customer_site.test_ssh_connection',
		args: {
			instance_name: frm.doc.name
		},
		callback: function(r) {
			if (r.message && r.message.success) {
				let details = r.message.details;
				let message = `
					<h4>SSH Connection Test Successful!</h4>
					<p><strong>User:</strong> ${details.user}</p>
					<p><strong>Current Directory:</strong> ${details.current_directory}</p>
					<p><strong>Directory Listing:</strong></p>
					<pre style="background: #f5f5f5; padding: 10px; border-radius: 4px; max-height: 200px; overflow-y: auto;">${details.directory_listing}</pre>
				`;
				
				frappe.msgprint({
					title: __('SSH Connection Test'),
					message: message,
					indicator: 'green'
				});
			} else {
				frappe.msgprint({
					title: __('SSH Connection Test Failed'),
					message: r.message.message || 'Unknown error',
					indicator: 'red'
				});
			}
		}
	});
}
