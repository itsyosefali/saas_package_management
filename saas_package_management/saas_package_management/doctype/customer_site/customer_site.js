frappe.ui.form.on('Customer Site', {
    refresh: function(frm) {
        // Add Create Site button when conditions are met
        if (frm.doc.status === 'Active' ) {
            frm.add_custom_button(__('Create Site'), function() {
                create_site_with_progress(frm);
            }, __('Actions'));
        }
    }
});

function create_site_with_progress(frm) {
    // Validate required fields
    if (!frm.doc.custom_domain) {
        frappe.msgprint(__('Custom Domain is required to create site'));
        return;
    }
    
    if (!frm.doc.instance) {
        frappe.msgprint(__('Instance is required to create site'));
        return;
    }
    
    if (!frm.doc.package) {
        frappe.msgprint(__('Package is required to create site'));
        return;
    }
    
    // Show confirmation dialog
    frappe.confirm(
        __('Are you sure you want to create the site? This process may take several minutes.'),
        function() {
            start_site_creation(frm);
        }
    );
}

function start_site_creation(frm) {
    // Create progress dialog
    let progress_dialog = new frappe.ui.Dialog({
        title: __('Creating Site'),
        fields: [
            {
                fieldtype: 'HTML',
                fieldname: 'progress_html',
                options: `
                    <div id="site-creation-progress">
                        <div class="progress-container">
                            <div class="progress-bar" id="progress-bar" style="width: 0%"></div>
                        </div>
                        <div class="progress-text" id="progress-text">Initializing...</div>
                        <div class="progress-log" id="progress-log"></div>
                    </div>
                    <style>
                        .progress-container {
                            width: 100%;
                            height: 20px;
                            background-color: #f0f0f0;
                            border-radius: 10px;
                            overflow: hidden;
                            margin: 10px 0;
                        }
                        .progress-bar {
                            height: 100%;
                            background-color: #007bff;
                            transition: width 0.3s ease;
                        }
                        .progress-text {
                            font-weight: bold;
                            margin: 10px 0;
                        }
                        .progress-log {
                            max-height: 200px;
                            overflow-y: auto;
                            background-color: #f8f9fa;
                            border: 1px solid #dee2e6;
                            border-radius: 4px;
                            padding: 10px;
                            font-family: monospace;
                            font-size: 12px;
                            white-space: pre-wrap;
                        }
                    </style>
                `
            }
        ],
        primary_action_label: __('Close'),
        primary_action: function() {
            progress_dialog.hide();
        }
    });
    
    progress_dialog.show();
    
    // Listen for real-time progress updates
    frappe.realtime.on('site_creation_progress', function(data) {
        update_progress(data.progress || 0, data.message || '', progress_dialog);
        
        if (data.progress === 100) {
            frm.reload_doc();
            frappe.show_alert({
                message: __('Site created successfully!'),
                indicator: 'green'
            });
        } else if (data.progress === 0 && data.message.includes('failed')) {
            frappe.show_alert({
                message: __('Site creation failed: ' + data.message),
                indicator: 'red'
            });
        }
    });
    
    // Start the site creation process
    frappe.call({
        method: 'saas_package_management.saas_package_management.doctype.customer_site.customer_site.create_site',
        args: {
            customer_site: frm.doc.name
        },
        callback: function(r) {
            if (r.message && r.message.success) {
                update_progress(5, 'Site creation process started...', progress_dialog);
            } else {
                update_progress(0, 'Failed to start site creation: ' + (r.message.message || 'Unknown error'), progress_dialog);
                frappe.show_alert({
                    message: __('Failed to start site creation: ' + (r.message.message || 'Unknown error')),
                    indicator: 'red'
                });
            }
        }
    });
}

function update_progress(percentage, message, dialog) {
    let progress_bar = dialog.fields_dict.progress_html.$wrapper.find('#progress-bar');
    let progress_text = dialog.fields_dict.progress_html.$wrapper.find('#progress-text');
    let progress_log = dialog.fields_dict.progress_html.$wrapper.find('#progress-log');
    
    progress_bar.css('width', percentage + '%');
    progress_text.text(message);
    
    // Add to log
    let timestamp = new Date().toLocaleTimeString();
    let log_entry = `[${timestamp}] ${message}\n`;
    progress_log.append(log_entry);
    progress_log.scrollTop(progress_log[0].scrollHeight);
}
