import frappe
from frappe import _
from frappe.utils import today, format_datetime


def get_context(context):
    """Get context for check status page"""
    context.title = "Check Request Status"
    
    context.meta_description = "Check the status of your package request at Ebkar Technology & Management Solutions"
    context.meta_keywords = "request status, package request, tracking, customer service"
    
    context.search_type = ""
    context.search_value = ""
    context.request_found = False
    context.error = ""
    
    
    if frappe.request.method == "POST":
        handle_status_lookup(context)
    
    return context


def handle_status_lookup(context):
    """Handle status lookup via POST"""
    try:
        search_type = frappe.form_dict.get('search_type')
        search_value = frappe.form_dict.get('search_value')
        
        if not search_type:
            context.error = "Please select a search method"
            return
            
        if not search_value:
            context.error = f"Please enter {search_type.replace('_', ' ')}"
            context.search_type = search_type
            context.search_value = search_value
            return
        
        if search_type == "request_id":
            request = search_by_request_id(search_value)
        elif search_type == "customer_name":
            request = search_by_customer_name(search_value)
        else:
            context.error = "Invalid search method"
            return
        
        if request:
            context.request_found = True
            context.request = format_request_data(request)
        else:
            context.error = f"No request found with the provided {search_type.replace('_', ' ')}"
            context.search_type = search_type
            context.search_value = search_value
            
    except Exception as e:
        frappe.log_error(f"Error in status lookup: {str(e)}", "Status Check Error")
        context.error = "An error occurred while searching for your request. Please try again."
        context.search_type = frappe.form_dict.get('search_type', '')
        context.search_value = frappe.form_dict.get('search_value', '')


def search_by_request_id(request_id):
    """Search for request by ID"""
    try:
        request_id = request_id.strip()
        
        request = frappe.get_doc("Customer Request", request_id)
        return request
    except frappe.DoesNotExistError:
        return None
    except Exception as e:
        frappe.log_error(f"Error searching by request ID: {str(e)}", "Request ID Search Error")
        return None


def search_by_customer_name(customer_name):
    """Search for request by customer name"""
    try:
        customer_name = customer_name.strip()
        
        requests = frappe.get_all(
            "Customer Request",
            filters={"customer_name": ["like", f"%{customer_name}%"]},
            fields=["name"],
            order_by="creation desc",
            limit=1
        )
        
        if requests:
            request = frappe.get_doc("Customer Request", requests[0].name)
            return request
        
        return None
        
    except Exception as e:
        frappe.log_error(f"Error searching by customer name: {str(e)}", "Customer Name Search Error")
        return None


def format_request_data(request):
    """Format request data for display"""
    try:
        package_name = request.package
        if package_name:
            try:
                package_doc = frappe.get_doc("Package", package_name)
                package_display = f"{package_doc.package_name} ({package_doc.price} LYD)"
            except:
                package_display = package_name
        else:
            package_display = "Not specified"
        
        request_date = request.request_date.strftime("%B %d, %Y") if request.request_date else "Not specified"
        creation_date = format_datetime(request.creation, "MMMM dd, yyyy 'at' h:mm a") if request.creation else "Not specified"
        modified_date = format_datetime(request.modified, "MMMM dd, yyyy 'at' h:mm a") if request.modified else "Not specified"
        
        customer_name = request.customer_name or "Not specified"
        
        status = request.status or "Pending"
        
        return {
            "name": request.name,
            "customer_name": customer_name,
            "package": package_display,
            "request_date": request_date,
            "status": status,
            "notes": request.notes or "",
            "admin_notes": request.admin_notes or "",
            "creation": creation_date,
            "modified": modified_date
        }
        
    except Exception as e:
        frappe.log_error(f"Error formatting request data: {str(e)}", "Request Data Formatting Error")
        return None


@frappe.whitelist(allow_guest=True)
def get_request_status(request_id):
    """API endpoint to get request status"""
    try:
        request = search_by_request_id(request_id)
        if request:
            formatted_data = format_request_data(request)
            return {
                "success": True,
                "data": formatted_data
            }
        else:
            return {
                "success": False,
                "message": "Request not found"
            }
    except Exception as e:
        frappe.log_error(f"Error in get_request_status API: {str(e)}", "Request Status API Error")
        return {
            "success": False,
            "message": "Error retrieving request status"
        }


@frappe.whitelist(allow_guest=True)
def search_requests_by_customer(customer_name):
    """API endpoint to search requests by customer name"""
    try:
        request = search_by_customer_name(customer_name)
        if request:
            formatted_data = format_request_data(request)
            return {
                "success": True,
                "data": formatted_data
            }
        else:
            return {
                "success": False,
                "message": "No requests found for this customer"
            }
    except Exception as e:
        frappe.log_error(f"Error in search_requests_by_customer API: {str(e)}", "Customer Search API Error")
        return {
            "success": False,
            "message": "Error searching for requests"
        }
