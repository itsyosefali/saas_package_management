frappe.ui.form.on('Customer Request', {
    refresh: function(frm) {
        // Add custom buttons based on request status
        if (frm.doc.status === 'Approved') {
            // Check if Customer Site already exists
            frappe.call({
                method: 'frappe.client.get_list',
                args: {
                    doctype: 'Customer Site',
                    filters: {
                        'customer_request': frm.doc.name
                    },
                    fields: ['name']
                },
                callback: function(response) {
                    if (response && response.message && response.message.length > 0) {
                        // Customer Site already exists
                        frm.add_custom_button(__('View Customer Site'), function() {
                            frappe.set_route('Form', 'Customer Site', response.message[0].name);
                        }, __('Actions'));
                        
                        frm.add_custom_button(__('Open Site'), function() {
                            frappe.call({
                                method: 'frappe.client.get_value',
                                args: {
                                    doctype: 'Customer Site',
                                    fieldname: 'custom_domain',
                                    filters: {
                                        'name': response.message[0].name
                                    }
                                },
                                callback: function(domain_response) {
                                    if (domain_response && domain_response.message && domain_response.message.custom_domain) {
                                        window.open(`https://${domain_response.message.custom_domain}`, '_blank');
                                    } else {
                                        frappe.msgprint(__('Custom domain not configured for this site'));
                                    }
                                },
                                error: function(err) {
                                    console.error('Error getting domain:', err);
                                    frappe.msgprint(__('Error getting site domain'));
                                }
                            });
                        }, __('Actions'));
                    } else {
                        // No Customer Site exists, show create button
                        frm.add_custom_button(__('Create Customer Site'), function() {
                            create_customer_site(frm);
                        }, __('Actions'));
                    }
                },
                error: function(err) {
                    console.error('Error checking for existing Customer Site:', err);
                }
            });
        }
        
        // Add domain preview for custom domain field
        if (frm.doc.custom_domain) {
            show_domain_preview(frm);
        }
        
        // Set custom domain field as read-only for non-admin users
        if (!frappe.user.has_role('System Manager') && !frappe.user.has_role('Administrator')) {
            frm.set_df_property('custom_domain', 'read_only', 1);
            frm.set_df_property('admin_notes', 'read_only', 1);
        }
    },
    
    custom_domain: function(frm) {
        // Show domain preview when custom domain changes
        show_domain_preview(frm);
    },
    
    status: function(frm) {
        // Auto-create Customer Site when status changes to Approved
        if (frm.doc.status === 'Approved' && !frm.doc.__islocal) {
            // Check if this is a real status change (not just form load)
            if (frm.doc.__unsaved === 0) {
                setTimeout(function() {
                    check_and_create_site(frm);
                }, 1000);
            }
        }
    },
    
    customer_name: function(frm) {
        // Auto-suggest custom domain based on customer name
        if (frm.doc.customer_name && !frm.doc.custom_domain) {
            var suggested_domain = frm.doc.customer_name.toLowerCase()
                .replace(/\s+/g, '-')
                .replace(/[^a-zA-Z0-9-]/g, '')
                .substring(0, 20); // Limit length
            
            if (suggested_domain) {
                frm.set_value('custom_domain', suggested_domain);
                show_domain_preview(frm);
            }
        }
    }
});

function create_customer_site(frm) {
    frappe.confirm(
        __('Are you sure you want to create a Customer Site for this approved request?'),
        function() {
            frappe.show_alert({
                message: __('Creating Customer Site...'),
                indicator: 'blue'
            });
            
            frappe.call({
                method: 'saas_package_management.saas_package_management.doctype.customer_request.customer_request.create_customer_site',
                args: {
                    customer_request_name: frm.doc.name
                },
                callback: function(response) {
                    if (response && response.message && response.message.success) {
                        frappe.show_alert({
                            message: __('Customer Site created successfully!'),
                            indicator: 'green'
                        });
                        
                        // Refresh the form to get the latest document state
                        frm.reload_doc();
                        
                        if (response.message.site_name) {
                            frappe.confirm(
                                __('Customer Site {0} has been created successfully. Do you want to view it?', [response.message.site_name]),
                                function() {
                                    frappe.set_route('Form', 'Customer Site', response.message.site_name);
                                },
                                function() {
                                    // User cancelled, do nothing
                                }
                            );
                        }
                    } else {
                        frappe.msgprint({
                            title: __('Error'),
                            message: (response && response.message && response.message.message) || __('Failed to create Customer Site'),
                            indicator: 'red'
                        });
                    }
                },
                error: function(err) {
                    console.error('Error creating Customer Site:', err);
                    frappe.msgprint({
                        title: __('Error'),
                        message: __('An error occurred while creating Customer Site'),
                        indicator: 'red'
                    });
                }
            });
        },
        function() {
            // User cancelled, do nothing
        }
    );
}

function show_domain_preview(frm) {
    var existing_preview = document.querySelector('.custom-domain-preview');
    if (existing_preview) {
        existing_preview.remove();
    }
    
    if (frm.doc.custom_domain) {
        var full_domain = frm.doc.custom_domain;
        if (!full_domain.endsWith('.ibssaas.com')) {
            full_domain = full_domain + '.ibssaas.com';
        }
        
        var preview_html = `
            <div class="custom-domain-preview" style="margin-top: 5px;">
                <small class="text-muted">
                    <i class="fa fa-globe"></i> 
                    Full Domain: <strong>${full_domain}</strong>
                </small>
            </div>
        `;
        
        var custom_domain_field = document.querySelector('[data-fieldname="custom_domain"]');
        if (custom_domain_field) {
            custom_domain_field.insertAdjacentHTML('beforeend', preview_html);
        }
    }
}

function check_and_create_site(frm) {
    // Check if Customer Site already exists
    frappe.call({
        method: 'frappe.client.get_list',
        args: {
            doctype: 'Customer Site',
            filters: {
                'customer_request': frm.doc.name
            },
            fields: ['name']
        },
        callback: function(response) {
            if (response && (!response.message || response.message.length === 0)) {
                frappe.confirm(
                    __('This request has been approved. Do you want to create a Customer Site automatically?'),
                    function() {
                        create_customer_site(frm);
                    },
                    function() {
                        // User cancelled, do nothing
                    }
                );
            }
        },
        error: function(err) {
            console.error('Error checking for existing Customer Site in auto-create:', err);
        }
    });
}

$(document).ready(function() {
    if (!$('#custom-domain-preview-styles').length) {
        $('<style id="custom-domain-preview-styles">')
            .prop('type', 'text/css')
            .html(`
                .custom-domain-preview {
                    padding: 5px 10px;
                    background-color: #f8f9fa;
                    border: 1px solid #dee2e6;
                    border-radius: 4px;
                    margin-top: 5px;
                }
                .custom-domain-preview .fa-globe {
                    color: #007bff;
                }
            `)
            .appendTo('head');
    }
});
