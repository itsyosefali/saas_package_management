frappe.listview_settings['Customer Site'] = {
    add_fields: ["status", "custom_domain", "expiry_date"],
    get_indicator: function(doc) {
        var colors = {
            "Active": "green",
            "Suspended": "orange",
            "Expired": "red",
            "Cancelled": "darkgrey"
        };
        return [__(doc.status), colors[doc.status], "status,=," + doc.status];
    },
    onload: function(listview) {
        // Add custom button to create site from approved request
        listview.page.add_menu_item(__("Create from Approved Request"), function() {
            frappe.prompt([
                {
                    "fieldtype": "Link",
                    "label": "Customer Request",
                    "fieldname": "customer_request",
                    "options": "Customer Request",
                    "reqd": 1,
                    "get_query": function() {
                        return {
                            filters: {
                                "status": "Approved"
                            }
                        };
                    }
                }
            ], function(values) {
                frappe.call({
                    method: "saas_package_management.saas_package_management.doctype.customer_site.customer_site.create_site_from_request",
                    args: {
                        customer_request_name: values.customer_request
                    },
                    callback: function(response) {
                        if (response.message.success) {
                            frappe.msgprint({
                                title: __("Success"),
                                message: __("Customer Site created successfully: {0}", [response.message.site_name]),
                                indicator: "green"
                            });
                            listview.refresh();
                        } else {
                            frappe.msgprint({
                                title: __("Error"),
                                message: response.message.message,
                                indicator: "red"
                            });
                        }
                    }
                });
            });
        });
        
        // Add custom button to check site status
        listview.page.add_menu_item(__("Check Site Status"), function() {
            var selected_docs = listview.get_checked_items();
            if (selected_docs.length === 0) {
                frappe.msgprint(__("Please select a site to check status"));
                return;
            }
            
            var site_name = selected_docs[0].name;
            frappe.call({
                method: "saas_package_management.saas_package_management.doctype.customer_site.customer_site.get_site_status",
                args: {
                    site_name: site_name
                },
                callback: function(response) {
                    if (response.message.success) {
                        var data = response.message.data;
                        var message = `
                            <div style="padding: 10px;">
                                <h4>Site Status Information</h4>
                                <table class="table table-bordered">
                                    <tr>
                                        <td><strong>Site Name:</strong></td>
                                        <td>${data.site_name}</td>
                                    </tr>
                                    <tr>
                                        <td><strong>Custom Domain:</strong></td>
                                        <td>${data.custom_domain || 'Not configured'}</td>
                                    </tr>
                                    <tr>
                                        <td><strong>Status:</strong></td>
                                        <td><span class="badge badge-${data.status === 'Active' ? 'success' : data.status === 'Suspended' ? 'warning' : 'danger'}">${data.status}</span></td>
                                    </tr>
                                    <tr>
                                        <td><strong>Customer:</strong></td>
                                        <td>${data.customer_name}</td>
                                    </tr>
                                    <tr>
                                        <td><strong>Package:</strong></td>
                                        <td>${data.package}</td>
                                    </tr>
                                    <tr>
                                        <td><strong>Creation Date:</strong></td>
                                        <td>${data.creation_date}</td>
                                    </tr>
                                    <tr>
                                        <td><strong>Expiry Date:</strong></td>
                                        <td>${data.expiry_date || 'Not set'}</td>
                                    </tr>
                                </table>
                            </div>
                        `;
                        
                        frappe.msgprint({
                            title: __("Site Status"),
                            message: message,
                            indicator: "blue"
                        });
                    } else {
                        frappe.msgprint({
                            title: __("Error"),
                            message: response.message.message,
                            indicator: "red"
                        });
                    }
                }
            });
        });
    },
    formatters: {
        custom_domain: function(value) {
            if (value) {
                return `<a href="https://${value}" target="_blank" class="text-primary">${value}</a>`;
            }
            return __("Not configured");
        },
        expiry_date: function(value) {
            if (value) {
                var date = moment(value);
                var now = moment();
                var diff = date.diff(now, 'days');
                
                if (diff < 0) {
                    return `<span class="text-danger">${frappe.datetime.str_to_user(value)} (Expired)</span>`;
                } else if (diff < 30) {
                    return `<span class="text-warning">${frappe.datetime.str_to_user(value)} (${diff} days left)</span>`;
                } else {
                    return frappe.datetime.str_to_user(value);
                }
            }
            return __("Not set");
        }
    },
    refresh: function(listview) {
        // Add custom filters
        listview.page.add_inner_button(__("Active Sites"), function() {
            listview.filter_area.add([[listview.doctype, "status", "=", "Active"]]);
        });
        
        listview.page.add_inner_button(__("Expired Sites"), function() {
            listview.filter_area.add([[listview.doctype, "status", "=", "Expired"]]);
        });
        
        listview.page.add_inner_button(__("Suspended Sites"), function() {
            listview.filter_area.add([[listview.doctype, "status", "=", "Suspended"]]);
        });
        
        // Add expiry warning for sites expiring soon
        var today = frappe.datetime.get_today();
        var warning_date = frappe.datetime.add_days(today, 30);
        
        listview.page.add_inner_button(__("Expiring Soon"), function() {
            listview.filter_area.add([
                [listview.doctype, "expiry_date", "<=", warning_date],
                [listview.doctype, "expiry_date", ">=", today],
                [listview.doctype, "status", "=", "Active"]
            ]);
        });
    }
};
