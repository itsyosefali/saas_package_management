import frappe
from frappe import _
from frappe.utils import today, add_days, get_datetime
from frappe.model.document import Document


class CustomerSite(Document):
    """Customer Site DocType controller"""
    
    def validate(self):
        """Validate Customer Site data"""
        self.validate_customer_request()
        self.validate_site_name()
        self.validate_custom_domain()
        self.validate_dates()
        self.set_default_values()
    
    def validate_customer_request(self):
        """Validate that customer request exists and is approved"""
        if self.customer_request:
            try:
                customer_request = frappe.get_doc("Customer Request", self.customer_request)
                if customer_request.status != "Approved":
                    frappe.throw(_("Customer Request must be approved before creating a Customer Site"))
                
                # Auto-fill customer name and package from customer request
                if not self.customer_name:
                    self.customer_name = customer_request.customer_name
                if not self.package:
                    self.package = customer_request.package
                    
            except frappe.DoesNotExistError:
                frappe.throw(_("Customer Request {0} does not exist").format(self.customer_request))
    
    def validate_site_name(self):
        """Validate site name uniqueness and format"""
        if self.site_name:
            # Check for duplicate site names
            existing_sites = frappe.get_all(
                "Customer Site",
                filters={"site_name": self.site_name},
                fields=["name"]
            )
            
            # Exclude current document from check if updating
            if self.name:
                existing_sites = [site for site in existing_sites if site.name != self.name]
            
            if existing_sites:
                frappe.throw(_("Site name '{0}' already exists").format(self.site_name))
            
            # Validate site name format (alphanumeric, hyphens, underscores only)
            import re
            if not re.match(r'^[a-zA-Z0-9_-]+$', self.site_name):
                frappe.throw(_("Site name can only contain letters, numbers, hyphens, and underscores"))
    
    def validate_custom_domain(self):
        """Validate custom domain format"""
        if self.custom_domain:
            # Basic domain validation
            import re
            domain_pattern = r'^[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$'
            if not re.match(domain_pattern, self.custom_domain):
                frappe.throw(_("Invalid custom domain format"))
            
            # Check for duplicate domains
            existing_sites = frappe.get_all(
                "Customer Site",
                filters={"custom_domain": self.custom_domain},
                fields=["name"]
            )
            
            # Exclude current document from check if updating
            if self.name:
                existing_sites = [site for site in existing_sites if site.name != self.name]
            
            if existing_sites:
                frappe.throw(_("Custom domain '{0}' is already in use").format(self.custom_domain))
    
    def validate_dates(self):
        """Validate date fields"""
        if self.expiry_date and self.creation_date:
            if self.expiry_date <= self.creation_date:
                frappe.throw(_("Expiry date must be after creation date"))
        
        if self.approval_date and self.creation_date:
            if self.approval_date < self.creation_date:
                frappe.throw(_("Approval date cannot be before creation date"))
    
    def set_default_values(self):
        """Set default values for various fields"""
        if not self.creation_date:
            self.creation_date = today()
        
        if not self.status:
            self.status = "Active"
        
        # Set expiry date based on package if not specified
        if not self.expiry_date and self.package:
            try:
                package_doc = frappe.get_doc("Package", self.package)
                # Default to 1 year from creation date
                self.expiry_date = add_days(self.creation_date, 365)
            except frappe.DoesNotExistError:
                pass
    
    def before_save(self):
        """Actions before saving the document"""
        self.update_admin_notes()
    
    def update_admin_notes(self):
        """Update admin notes with system information"""
        admin_notes = []
        
        if self.is_new():
            admin_notes.append(f"Customer Site created on {get_datetime().strftime('%B %d, %Y at %I:%M %p')}")
        else:
            admin_notes.append(f"Customer Site updated on {get_datetime().strftime('%B %d, %Y at %I:%M %p')}")
        
        if self.approval_date and not self.admin_notes:
            admin_notes.append(f"Site approved on {self.approval_date.strftime('%B %d, %Y')}")
        
        if admin_notes:
            existing_notes = self.admin_notes or ""
            self.admin_notes = existing_notes + "\n\n" + "\n".join(admin_notes) if existing_notes else "\n".join(admin_notes)
    
    def on_submit(self):
        """Actions when document is submitted"""
        self.send_notification_email()
        self.update_customer_request_status()
    
    def send_notification_email(self):
        """Send notification email to customer"""
        try:
            if self.customer_name:
                customer_email = frappe.db.get_value("Customer", self.customer_name, "email_id")
                if customer_email:
                    subject = f"Your Site is Ready - {self.site_name}"
                    message = f"""
                    <h3>Congratulations! Your site is now active.</h3>
                    <p>Your package request has been approved and your site is ready for use.</p>
                    
                    <table border="1" style="border-collapse: collapse; width: 100%;">
                        <tr>
                            <td><strong>Site Name:</strong></td>
                            <td>{self.site_name}</td>
                        </tr>
                        <tr>
                            <td><strong>Custom Domain:</strong></td>
                            <td>{self.custom_domain or 'Not configured'}</td>
                        </tr>
                        <tr>
                            <td><strong>Package:</strong></td>
                            <td>{self.package}</td>
                        </tr>
                        <tr>
                            <td><strong>Status:</strong></td>
                            <td>{self.status}</td>
                        </tr>
                        <tr>
                            <td><strong>Creation Date:</strong></td>
                            <td>{self.creation_date}</td>
                        </tr>
                        <tr>
                            <td><strong>Expiry Date:</strong></td>
                            <td>{self.expiry_date or 'Not set'}</td>
                        </tr>
                    </table>
                    
                    <p>You can now access your site and start using your selected package features.</p>
                    <p>If you have any questions, please contact our support team.</p>
                    """
                    
                    frappe.sendmail(
                        recipients=[customer_email],
                        subject=subject,
                        message=message,
                        delayed=False
                    )
        except Exception as e:
            frappe.log_error(f"Error sending customer notification: {str(e)}", "Customer Site Notification Error")
    
    def update_customer_request_status(self):
        """Update the related customer request status"""
        try:
            if self.customer_request:
                customer_request = frappe.get_doc("Customer Request", self.customer_request)
                customer_request.admin_notes = f"Customer Site created: {self.name} on {get_datetime().strftime('%B %d, %Y at %I:%M %p')}"
                customer_request.save(ignore_permissions=True)
        except Exception as e:
            frappe.log_error(f"Error updating customer request: {str(e)}", "Customer Request Update Error")


@frappe.whitelist()
def create_site_from_request(customer_request_name):
    """Create a Customer Site from an approved Customer Request"""
    try:
        # Get the customer request
        customer_request = frappe.get_doc("Customer Request", customer_request_name)
        
        if customer_request.status != "Approved":
            frappe.throw(_("Customer Request must be approved before creating a Customer Site"))
        
        # Check if site already exists for this request
        existing_sites = frappe.get_all(
            "Customer Site",
            filters={"customer_request": customer_request_name},
            fields=["name"]
        )
        
        if existing_sites:
            frappe.throw(_("Customer Site already exists for this request"))
        
        # Generate site name from customer name
        customer_name = customer_request.customer_name
        site_name = customer_name.lower().replace(" ", "-").replace(".", "").replace(",", "")
        
        # Ensure site name is unique
        counter = 1
        original_site_name = site_name
        while frappe.db.exists("Customer Site", {"site_name": site_name}):
            site_name = f"{original_site_name}-{counter}"
            counter += 1
        
        # Create the customer site
        customer_site = frappe.new_doc("Customer Site")
        customer_site.customer_request = customer_request_name
        customer_site.customer_name = customer_request.customer_name
        customer_site.site_name = site_name
        customer_site.package = customer_request.package
        customer_site.status = "Active"
        customer_site.creation_date = today()
        customer_site.approval_date = today()
        
        # Set default custom domain
        customer_site.custom_domain = f"{site_name}.cnitsolution.cloud"
        
        customer_site.insert()
        
        return {
            "success": True,
            "message": f"Customer Site created successfully: {customer_site.name}",
            "site_name": customer_site.name
        }
        
    except Exception as e:
        frappe.log_error(f"Error creating site from request: {str(e)}", "Site Creation Error")
        return {
            "success": False,
            "message": str(e)
        }


@frappe.whitelist()
def get_site_status(site_name):
    """Get the status of a customer site"""
    try:
        site = frappe.get_doc("Customer Site", site_name)
        return {
            "success": True,
            "data": {
                "name": site.name,
                "site_name": site.site_name,
                "custom_domain": site.custom_domain,
                "status": site.status,
                "customer_name": site.customer_name,
                "package": site.package,
                "creation_date": site.creation_date,
                "expiry_date": site.expiry_date
            }
        }
    except frappe.DoesNotExistError:
        return {
            "success": False,
            "message": "Site not found"
        }
    except Exception as e:
        frappe.log_error(f"Error getting site status: {str(e)}", "Site Status Error")
        return {
            "success": False,
            "message": "Error retrieving site information"
        }
