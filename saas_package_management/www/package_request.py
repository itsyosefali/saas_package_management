import frappe
from frappe import _
from frappe.utils import today, now


def get_context(context):
    """Get context for package request page"""
    context.title = "Package Request"
    context.packages = get_active_packages()
    context.today = today()
    
    # Add meta information
    context.meta_description = "Request a package from Ebkar Technology & Management Solutions"
    context.meta_keywords = "package request, SaaS, ERP, business solutions"
    
    # Handle POST request (form submission)
    if frappe.request.method == "POST":
        handle_form_submission(context)
    
    return context


def handle_form_submission(context):
    """Handle form submission via POST"""
    try:
        # Get form data
        customer_name = frappe.form_dict.get('customer_name')
        customer_email = frappe.form_dict.get('customer_email')
        company_name = frappe.form_dict.get('company_name')
        package = frappe.form_dict.get('package')
        request_date = frappe.form_dict.get('request_date')
        custom_domain = frappe.form_dict.get('custom_domain', '')
        notes = frappe.form_dict.get('notes', '')
        
        # Validate required fields
        if not customer_name:
            context.error = "Customer name is required"
            context.customer_name = customer_name
            context.customer_email = customer_email
            context.selected_package = package
            context.request_date = request_date
            context.notes = notes
            return
            
        if not customer_email:
            context.error = "Customer email is required"
            context.customer_name = customer_name
            context.customer_email = customer_email
            context.selected_package = package
            context.request_date = request_date
            context.notes = notes
            return
            
        if not package:
            context.error = "Package selection is required"
            context.customer_name = customer_name
            context.customer_email = customer_email
            context.selected_package = package
            context.request_date = request_date
            context.notes = notes
            return
            
        if not request_date:
            context.error = "Request date is required"
            context.customer_name = customer_name
            context.customer_email = customer_email
            context.selected_package = package
            context.request_date = request_date
            context.notes = notes
            return
        
        if not company_name:
            context.error = "Company name is required"
            context.customer_name = customer_name
            context.customer_email = customer_email
            context.selected_package = package
            context.request_date = request_date
            context.notes = notes
            return
        
        # Validate package exists and is active
        try:
            package_doc = frappe.get_doc("Package", package)
            if not package_doc.is_active:
                context.error = "Selected package is not available"
                context.customer_name = customer_name
                context.customer_email = customer_email
                context.selected_package = package
                context.request_date = request_date
                context.notes = notes
                return
        except frappe.DoesNotExistError:
            context.error = "Selected package does not exist"
            context.customer_name = customer_name
            context.customer_email = customer_email
            context.selected_package = package
            context.request_date = request_date
            context.notes = notes
            return
        
        # Check if customer exists, if not create a basic customer record
        customer = get_or_create_customer(customer_name)
        
        # Validate custom domain format if provided
        if custom_domain:
            import re
            if not re.match(r'^[a-zA-Z0-9-]+$', custom_domain):
                context.error = "Custom domain can only contain letters, numbers, and hyphens"
                context.customer_name = customer_name
                context.customer_email = customer_email
                context.selected_package = package
                context.request_date = request_date
                context.custom_domain = custom_domain
                context.notes = notes
                return
        
        # Create customer request document
        customer_request = frappe.new_doc("Customer Request")
        customer_request.customer_name = customer
        customer_request.customer_email = customer_email
        customer_request.company_name = company_name
        customer_request.package = package
        customer_request.request_date = request_date
        customer_request.custom_domain = custom_domain
        customer_request.status = "Pending"
        customer_request.notes = notes
        customer_request.admin_notes = f"Request submitted via web form on {now()}"
        customer_request.insert(ignore_permissions=True)
        
        # Send notification email to admin (optional)
        send_admin_notification(customer_request)
        
        # Set success state
        context.submitted = True
        context.request_id = customer_request.name
        
    except Exception as e:
        frappe.log_error(f"Error submitting package request: {str(e)}", "Package Request Submit Error")
        context.error = "An error occurred while submitting your request. Please try again."
        context.customer_name = frappe.form_dict.get('customer_name', '')
        context.customer_email = frappe.form_dict.get('customer_email', '')
        context.company_name = frappe.form_dict.get('company_name', '')
        context.selected_package = frappe.form_dict.get('package', '')
        context.request_date = frappe.form_dict.get('request_date', '')
        context.custom_domain = frappe.form_dict.get('custom_domain', '')
        context.notes = frappe.form_dict.get('notes', '')


def get_active_packages():
    """Get all active packages for the form"""
    try:
        packages = frappe.get_all(
            "Package",
            filters={"is_active": 1},
            fields=["name", "package_name", "price", "users_limit", "invoices_limit", "expenses_limit", "features"],
            order_by="price asc"
        )
        return packages
    except Exception as e:
        frappe.log_error(f"Error fetching packages: {str(e)}", "Package Request Error")
        return []


def get_or_create_customer(customer_name):
    """Get existing customer or create a basic customer record"""
    try:
        # Try to find existing customer by name
        customers = frappe.get_all(
            "Customer",
            filters={"customer_name": ["like", f"%{customer_name}%"]},
            fields=["name"]
        )
        
        if customers:
            return customers[0].name
        
        # Create new customer if not found
        customer = frappe.new_doc("Customer")
        customer.customer_name = customer_name
        customer.customer_type = "Individual"
        customer.customer_group = "All Customer Groups"
        customer.territory = "All Territories"
        customer.insert(ignore_permissions=True)
        
        return customer.name
        
    except Exception as e:
        frappe.log_error(f"Error creating customer: {str(e)}", "Customer Creation Error")
        # Return a generic customer if creation fails
        return "Guest Customer"


def send_admin_notification(customer_request):
    """Send notification email to system administrators"""
    try:
        # Get system managers email addresses
        system_managers = frappe.get_all(
            "Has Role",
            filters={"role": "System Manager"},
            fields=["parent"]
        )
        
        if system_managers:
            # Create email content
            subject = f"New Package Request: {customer_request.name}"
            message = f"""
            <h3>New Package Request Received</h3>
            <p>A new package request has been submitted via the web form:</p>
            
            <table border="1" style="border-collapse: collapse; width: 100%;">
                <tr>
                    <td><strong>Request ID:</strong></td>
                    <td>{customer_request.name}</td>
                </tr>
                <tr>
                    <td><strong>Customer:</strong></td>
                    <td>{customer_request.customer_name}</td>
                </tr>
                <tr>
                    <td><strong>Email:</strong></td>
                    <td>{customer_request.customer_email}</td>
                </tr>
                <tr>
                    <td><strong>Package:</strong></td>
                    <td>{customer_request.package}</td>
                </tr>
                <tr>
                    <td><strong>Request Date:</strong></td>
                    <td>{customer_request.request_date}</td>
                </tr>
                <tr>
                    <td><strong>Status:</strong></td>
                    <td>{customer_request.status}</td>
                </tr>
                <tr>
                    <td><strong>Notes:</strong></td>
                    <td>{customer_request.notes or 'None'}</td>
                </tr>
            </table>
            
            <p>Please review and process this request in the ERPNext system.</p>
            """
            
            # Send email to system managers
            for manager in system_managers:
                user_email = frappe.db.get_value("User", manager.parent, "email")
                if user_email:
                    frappe.sendmail(
                        recipients=[user_email],
                        subject=subject,
                        message=message,
                        delayed=False
                    )
                    
    except Exception as e:
        frappe.log_error(f"Error sending admin notification: {str(e)}", "Admin Notification Error")


@frappe.whitelist(allow_guest=True)
def get_package_details(package_name):
    """Get detailed information about a specific package"""
    try:
        package = frappe.get_doc("Package", package_name)
        return {
            "success": True,
            "data": {
                "name": package.name,
                "package_name": package.package_name,
                "price": package.price,
                "users_limit": package.users_limit,
                "invoices_limit": package.invoices_limit,
                "expenses_limit": package.expenses_limit,
                "features": package.features,
                "is_active": package.is_active
            }
        }
    except frappe.DoesNotExistError:
        return {
            "success": False,
            "message": "Package not found"
        }
    except Exception as e:
        frappe.log_error(f"Error getting package details: {str(e)}", "Package Details Error")
        return {
            "success": False,
            "message": "Error retrieving package information"
        }