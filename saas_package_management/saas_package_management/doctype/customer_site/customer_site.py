import frappe
from frappe import _
from frappe.utils import today, add_days, get_datetime
from frappe.model.document import Document
from datetime import timedelta
import paramiko
import json
import time


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
        
        # Assign available instance if not already assigned
        if not hasattr(self, 'instance') or not self.instance:
            self.assign_available_instance()
    
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
    
    def assign_available_instance(self):
        """Assign an available instance to this customer site"""
        try:
            if not self.package:
                return
            
            # Find an available instance for this package
            available_instances = frappe.get_all(
                "Instance",
                filters={
                    "package": self.package,
                    "is_active": 1,
                    "deployment_status": ["in", ["Running", "Deployed"]]
                },
                fields=["name", "instance_name", "ram_gb", "cpu_cores", "storage_gb"],
                order_by="creation asc"
            )
            
            if available_instances:
                # Assign the first available instance
                instance = available_instances[0]
                self.instance = instance.name
                
                # Update instance status to deployed
                frappe.db.set_value("Instance", instance.name, "deployment_status", "Deployed")
                frappe.db.set_value("Instance", instance.name, "server_url", self.custom_domain or f"{self.site_name}.ibssaas.com")
                
                # Add instance info to site details
                instance_info = f"Instance: {instance.instance_name}\nRAM: {instance.ram_gb}GB\nCPU: {instance.cpu_cores} cores\nStorage: {instance.storage_gb}GB"
                if self.site_details:
                    self.site_details += f"\n\n{instance_info}"
                else:
                    self.site_details = instance_info
                    
                frappe.msgprint(f"Assigned instance: {instance.instance_name}")
            else:
                frappe.msgprint("No available instances found for this package", alert=True)
                
        except Exception as e:
            frappe.log_error(f"Error assigning instance: {str(e)}", "Instance Assignment Error")
    
    def check_site_health(self):
        """Check if the customer site is running and healthy"""
        try:
            if not self.instance:
                return {"status": "no_instance", "message": "No instance assigned"}
            
            instance_doc = frappe.get_doc("Instance", self.instance)
            
            # Basic health check - in a real implementation, this would ping the actual site
            if instance_doc.deployment_status == "Running":
                return {"status": "healthy", "message": "Site is running normally"}
            elif instance_doc.deployment_status == "Maintenance":
                return {"status": "maintenance", "message": "Site is under maintenance"}
            elif instance_doc.deployment_status == "Stopped":
                return {"status": "stopped", "message": "Site is stopped"}
            else:
                return {"status": "unknown", "message": f"Instance status: {instance_doc.deployment_status}"}
                
        except Exception as e:
            frappe.log_error(f"Error checking site health: {str(e)}", "Site Health Check Error")
            return {"status": "error", "message": "Error checking site status"}
    
    def check_expiry_status(self):
        """Check if the site is near expiry or expired"""
        try:
            if not self.expiry_date:
                return {"status": "no_expiry", "message": "No expiry date set"}
            
            from frappe.utils import getdate, today
            days_until_expiry = (getdate(self.expiry_date) - getdate(today())).days
            
            if days_until_expiry < 0:
                return {"status": "expired", "message": f"Site expired {abs(days_until_expiry)} days ago"}
            elif days_until_expiry <= 7:
                return {"status": "expiring_soon", "message": f"Site expires in {days_until_expiry} days"}
            else:
                return {"status": "active", "message": f"Site expires in {days_until_expiry} days"}
                
        except Exception as e:
            frappe.log_error(f"Error checking expiry status: {str(e)}", "Expiry Check Error")
            return {"status": "error", "message": "Error checking expiry status"}


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
        customer_site.custom_domain = f"{site_name}.ibssaas.com"
        
        # Insert the document first
        customer_site.insert()
        
        # Assign available instance after insertion
        customer_site.assign_available_instance()
        customer_site.save()
        
        return {
            "success": True,
            "message": f"Customer Site created successfully: {customer_site.name}",
            "site_name": customer_site.name,
            "instance_assigned": customer_site.instance if customer_site.instance else None
        }
        
    except Exception as e:
        frappe.log_error(f"Error creating site from request: {str(e)}", "Site Creation Error")
        return {
            "success": False,
            "message": str(e)
        }


@frappe.whitelist()
def test_password_decryption(instance_name):
    """Test password decryption for an instance"""
    try:
        instance_doc = frappe.get_doc("Instance", instance_name)
        
        # Test SSH password decryption
        try:
            ssh_password = instance_doc.get_password("password")
            ssh_password_status = "Success" if ssh_password else "Failed - Empty"
        except Exception as e:
            ssh_password_status = f"Failed - {str(e)}"
            ssh_password = None
        
        # Test database password decryption
        try:
            db_password = instance_doc.get_password("database_password")
            db_password_status = "Success" if db_password else "Failed - Empty"
        except Exception as e:
            db_password_status = f"Failed - {str(e)}"
            db_password = None
        
        return {
            "success": True,
            "message": "Password decryption test completed",
            "details": {
                "instance_ip": instance_doc.instance_ip,
                "ssh_user": instance_doc.user,
                "ssh_password_status": ssh_password_status,
                "ssh_password_length": len(ssh_password) if ssh_password else 0,
                "database_password_status": db_password_status,
                "database_password_length": len(db_password) if db_password else 0
            }
        }
        
    except Exception as e:
        frappe.log_error(f"Password decryption test failed: {str(e)}", "Password Test Error")
        return {
            "success": False,
            "message": str(e)
        }


@frappe.whitelist()
def test_ssh_connection(instance_name):
    """Test SSH connection to an instance"""
    try:
        instance_doc = frappe.get_doc("Instance", instance_name)
        
        # Test connection
        ssh_client = connect_ssh(instance_doc)
        
        if ssh_client:
            # Test basic commands
            stdin, stdout, stderr = ssh_client.exec_command('whoami')
            user = stdout.read().decode().strip()
            
            stdin, stdout, stderr = ssh_client.exec_command('pwd')
            current_dir = stdout.read().decode().strip()
            
            stdin, stdout, stderr = ssh_client.exec_command('ls -la')
            ls_output = stdout.read().decode().strip()
            
            ssh_client.close()
            
            return {
                "success": True,
                "message": "SSH connection successful",
                "details": {
                    "user": user,
                    "current_directory": current_dir,
                    "directory_listing": ls_output[:500] + "..." if len(ls_output) > 500 else ls_output
                }
            }
        else:
            return {
                "success": False,
                "message": "SSH connection failed"
            }
            
    except Exception as e:
        frappe.log_error(f"SSH test failed: {str(e)}", "SSH Test Error")
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


@frappe.whitelist()
def create_site(customer_site):
    """Create ERPNext site on the instance"""
    try:
        # Get customer site document
        customer_site_doc = frappe.get_doc("Customer Site", customer_site)
        
        # Validate required fields
        if not customer_site_doc.instance:
            return {"success": False, "message": "Instance not assigned"}
        
        if not customer_site_doc.custom_domain:
            return {"success": False, "message": "Custom domain not specified"}
        
        if not customer_site_doc.package:
            return {"success": False, "message": "Package not specified"}
        
        # Get instance information
        instance_doc = frappe.get_doc("Instance", customer_site_doc.instance)
        
        # Get package information for quota configuration
        package_doc = frappe.get_doc("Package", customer_site_doc.package)
        
        # Start site creation as background job
        frappe.enqueue(
            'saas_package_management.saas_package_management.doctype.customer_site.customer_site.create_site_background',
            customer_site=customer_site,
            instance=instance_doc.name,
            package=package_doc.name,
            queue='long',
            timeout=3600
        )
        
        return {"success": True, "message": "Site creation started"}
        
    except Exception as e:
        frappe.log_error(f"Error starting site creation: {str(e)}", "Site Creation Error")
        return {"success": False, "message": str(e)}


@frappe.whitelist(allow_guest=True)
def create_site_background(customer_site, instance, package):
    """Background site creation process"""
    try:
        # Get documents
        customer_site_doc = frappe.get_doc("Customer Site", customer_site)
        instance_doc = frappe.get_doc("Instance", instance)
        package_doc = frappe.get_doc("Package", package)
        
        # Update status to creating
        frappe.db.set_value("Customer Site", customer_site_doc.name, "status", "Creating Site")
        frappe.db.commit()
        
        # Connect to instance via SSH
        frappe.publish_realtime('site_creation_progress', {
            'progress': 5,
            'message': f'Connecting to instance {instance_doc.instance_ip}...'
        })
        
        ssh_client = connect_ssh(instance_doc)
        
        if not ssh_client:
            raise Exception("Failed to connect to instance via SSH")
        
        # Step 1: Create the site
        site_name = customer_site_doc.custom_domain  # Use full custom domain as site name
        
        # Get decrypted database password
        try:
            db_password = instance_doc.get_password("database_password")
            if not db_password:
                raise Exception("Database password is not set or could not be decrypted")
        except Exception as e:
            raise Exception(f"Failed to get database password: {str(e)}")
        
        create_site_command = f"bench new-site {site_name} --db-root-password {db_password} --admin-password adminpass"
        
        frappe.publish_realtime('site_creation_progress', {
            'progress': 10,
            'message': 'Creating site...'
        })
        
        stdin, stdout, stderr = ssh_client.exec_command(f"cd {instance_doc.bench} && {create_site_command}")
        
        # Wait for command to complete
        exit_status = stdout.channel.recv_exit_status()
        if exit_status != 0:
            error_output = stderr.read().decode()
            raise Exception(f"Site creation failed: {error_output}")
        
        frappe.publish_realtime('site_creation_progress', {
            'progress': 30,
            'message': 'Site created successfully'
        })
        
        # Step 2: Install ERPNext
        frappe.publish_realtime('site_creation_progress', {
            'progress': 40,
            'message': 'Installing ERPNext...'
        })
        
        install_erpnext_command = f"bench --site {site_name} install-app erpnext"
        stdin, stdout, stderr = ssh_client.exec_command(f"cd {instance_doc.bench} && {install_erpnext_command}")
        exit_status = stdout.channel.recv_exit_status()
        
        if exit_status != 0:
            error_output = stderr.read().decode()
            raise Exception(f"ERPNext installation failed: {error_output}")
        
        frappe.publish_realtime('site_creation_progress', {
            'progress': 60,
            'message': 'ERPNext installed successfully'
        })
        
        # Step 3: Install erpnext_quota
        frappe.publish_realtime('site_creation_progress', {
            'progress': 70,
            'message': 'Installing erpnext_quota...'
        })
        
        install_quota_command = f"bench --site {site_name} install-app erpnext_quota"
        stdin, stdout, stderr = ssh_client.exec_command(f"cd {instance_doc.bench} && {install_quota_command}")
        exit_status = stdout.channel.recv_exit_status()
        
        if exit_status != 0:
            error_output = stderr.read().decode()
            raise Exception(f"erpnext_quota installation failed: {error_output}")
        
        frappe.publish_realtime('site_creation_progress', {
            'progress': 80,
            'message': 'erpnext_quota installed successfully'
        })
        
        # Step 4: Configure quota
        frappe.publish_realtime('site_creation_progress', {
            'progress': 85,
            'message': 'Configuring quota limits...'
        })
        
        configure_quota(ssh_client, instance_doc, site_name, package_doc)
        
        # Step 5: Setup SSL with Let's Encrypt
        frappe.publish_realtime('site_creation_progress', {
            'progress': 90,
            'message': 'Setting up SSL certificate...'
        })
        
        setup_ssl_certificate(ssh_client, instance_doc, site_name, customer_site_doc.custom_domain)
        
        frappe.publish_realtime('site_creation_progress', {
            'progress': 100,
            'message': 'Site creation completed successfully!'
        })
        
        # Update customer site with success information
        site_details = f"""Site URL: https://{customer_site_doc.custom_domain}
Admin URL: https://{customer_site_doc.custom_domain}/app
Login Credentials:
- Username: Administrator
- Password: adminpass

Site Name: {site_name}
Instance: {instance_doc.instance_name}
Package: {package_doc.package_name}
Created: {get_datetime().strftime('%B %d, %Y at %I:%M %p')}"""
        
        frappe.db.set_value("Customer Site", customer_site_doc.name, "site_details", site_details)
        frappe.db.set_value("Customer Site", customer_site_doc.name, "status", "Active")
        frappe.db.commit()
        
        ssh_client.close()
        
    except Exception as e:
        frappe.log_error(f"Error in site creation background process: {str(e)}", "Site Creation Background Error")
        frappe.db.set_value("Customer Site", customer_site, "status", "Failed")
        frappe.db.set_value("Customer Site", customer_site, "admin_notes", f"Site creation failed: {str(e)}")
        frappe.db.commit()
        
        frappe.publish_realtime('site_creation_progress', {
            'progress': 0,
            'message': f'Site creation failed: {str(e)}'
        })


def connect_ssh(instance_doc):
    """Connect to instance via SSH"""
    try:
        # Log connection attempt for debugging
        frappe.log_error(f"Attempting SSH connection to {instance_doc.instance_ip} with user {instance_doc.user}", "SSH Connection Debug")
        
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        if not instance_doc.instance_ip:
            raise Exception("Instance IP is not set")
        if not instance_doc.user:
            raise Exception("SSH user is not set")
        
        try:
            password = instance_doc.get_password("password")
            if not password:
                raise Exception("SSH password is not set or could not be decrypted")
        except Exception as e:
            raise Exception(f"Failed to get SSH password: {str(e)}")
        
        ssh_client.connect(
            hostname=instance_doc.instance_ip,
            username=instance_doc.user,
            password=password,
            timeout=30,
            allow_agent=False,
            look_for_keys=False
        )
       
        # Test if connection is working
        stdin, stdout, stderr = ssh_client.exec_command('echo "SSH connection test successful"')
        test_output = stdout.read().decode().strip()
        
        if test_output != "SSH connection test successful":
            raise Exception("SSH connection test failed")
        
        frappe.log_error(f"SSH connection successful to {instance_doc.instance_ip}", "SSH Connection Success")
        return ssh_client
        
    except paramiko.AuthenticationException as e:
        error_msg = f"SSH Authentication failed for {instance_doc.instance_ip}: {str(e)}"
        frappe.log_error(error_msg, "SSH Authentication Error")
        raise Exception(error_msg)
    except paramiko.SSHException as e:
        error_msg = f"SSH connection error for {instance_doc.instance_ip}: {str(e)}"
        frappe.log_error(error_msg, "SSH Connection Error")
        raise Exception(error_msg)
    except Exception as e:
        error_msg = f"SSH connection failed for {instance_doc.instance_ip}: {str(e)}"
        frappe.log_error(error_msg, "SSH Connection Error")
        raise Exception(error_msg)


def configure_quota(ssh_client, instance_doc, site_name, package_doc):
    """Configure erpnext_quota based on package limits"""
    try:
        # Get package limits with proper defaults
        users_limit = package_doc.users_limit or 5
        invoices_limit = package_doc.invoices_limit or 10
        expenses_limit = package_doc.expenses_limit or 10
        
        # Create focused quota configuration based on available package limits
        quota_config = {
            "active_users": users_limit,
            "company": 2,  # Allow 2 companies by default
            "document_limit": {
                # Core Invoice Documents (based on invoices_limit)
                "Sales Invoice": {"limit": invoices_limit, "period": "Daily"},
                "Purchase Invoice": {"limit": invoices_limit, "period": "Daily"},
                
                # Core Financial Documents (based on invoices_limit)
                "Journal Entry": {"limit": invoices_limit, "period": "Monthly"},
                "Payment Entry": {"limit": invoices_limit, "period": "Monthly"},
                
                # Expense Documents (based on expenses_limit)
                "Expense Claim": {"limit": expenses_limit, "period": "Monthly"},
                "Advance Payment": {"limit": expenses_limit, "period": "Monthly"},
                
                # User-related Documents (based on users_limit)
                "Employee": {"limit": users_limit, "period": "Monthly"},
                "User": {"limit": users_limit, "period": "Monthly"}
            },
            "valid_till": (get_datetime() + timedelta(days=365)).strftime('%Y-%m-%d'),
            "package_name": package_doc.package_name,
            "package_price": package_doc.price or 0,
            "features": package_doc.features or "Standard ERPNext features"
        }
        
        # Log quota configuration for debugging
        frappe.log_error(f"Configuring quota for site {site_name} with package {package_doc.package_name}: {json.dumps(quota_config, indent=2)}", "Quota Configuration Debug")
        
        # Create site_config.json update command
        config_json = json.dumps(quota_config, indent=2)
        config_command = f"""
        # Create quota configuration file
        cat > /tmp/quota_config.json << 'EOF'
        {config_json}
        EOF
        
        # Backup existing site_config.json
        cp '{instance_doc.bench}/sites/{site_name}/site_config.json' '{instance_doc.bench}/sites/{site_name}/site_config.json.backup'
        
        # Update site_config.json with quota configuration
        python3 -c "
        import json
        import os
        import shutil
        
        site_config_path = '{instance_doc.bench}/sites/{site_name}/site_config.json'
        
        # Read existing config
        with open(site_config_path, 'r') as f:
            config = json.load(f)
        
        # Read quota config
        with open('/tmp/quota_config.json', 'r') as f:
            quota_config = json.load(f)
        
        # Add quota configuration
        config['quota'] = quota_config
        
        # Write updated config
        with open(site_config_path, 'w') as f:
            json.dump(config, f, indent=2)
        
        print('Quota configuration updated successfully')
        "
        
        # Verify the configuration was applied
        python3 -c "
        import json
        site_config_path = '{instance_doc.bench}/sites/{site_name}/site_config.json'
        with open(site_config_path, 'r') as f:
            config = json.load(f)
        if 'quota' in config:
            print('Quota configuration verified successfully')
            print(f'Active users limit: {{config[\"quota\"][\"active_users\"]}}')
            print(f'Document limits configured: {{len(config[\"quota\"][\"document_limit\"])}}')
        else:
            print('ERROR: Quota configuration not found')
            exit(1)
        "
        """
        
        stdin, stdout, stderr = ssh_client.exec_command(f"cd {instance_doc.bench} && {config_command}")
        exit_status = stdout.channel.recv_exit_status()
        
        if exit_status != 0:
            error_output = stderr.read().decode()
            frappe.log_error(f"Quota configuration failed: {error_output}", "Quota Configuration Error")
            raise Exception(f"Quota configuration failed: {error_output}")
        
        # Log success
        success_output = stdout.read().decode()
        frappe.log_error(f"Quota configuration successful for {site_name}: {success_output}", "Quota Configuration Success")
        
    except Exception as e:
        frappe.log_error(f"Error configuring quota for {site_name}: {str(e)}", "Quota Configuration Error")
        raise e


def setup_ssl_certificate(ssh_client, instance_doc, site_name, custom_domain):
    """Setup SSL certificate using Let's Encrypt"""
    try:
        # Log SSL setup attempt
        frappe.log_error(f"Setting up SSL certificate for {site_name} with domain {custom_domain}", "SSL Setup Debug")
        
        # Setup Let's Encrypt SSL certificate
        ssl_command = f"""
        # Setup Let's Encrypt SSL certificate
        sudo -H bench setup lets-encrypt {site_name}
        
        # Verify SSL certificate was created
        if [ -f "/etc/letsencrypt/live/{custom_domain}/fullchain.pem" ]; then
            echo "SSL certificate created successfully for {custom_domain}"
        else
            echo "WARNING: SSL certificate may not have been created properly"
        fi
        
        # Check if nginx is configured for SSL
        if [ -f "/etc/nginx/sites-available/{site_name}" ]; then
            echo "Nginx configuration found for {site_name}"
            # Test nginx configuration
            sudo nginx -t
            if [ $? -eq 0 ]; then
                echo "Nginx configuration is valid"
                # Reload nginx to apply SSL configuration
                sudo systemctl reload nginx
                echo "Nginx reloaded successfully"
            else
                echo "ERROR: Nginx configuration is invalid"
            fi
        else
            echo "WARNING: Nginx configuration not found for {site_name}"
        fi
        """
        
        stdin, stdout, stderr = ssh_client.exec_command(f"cd {instance_doc.bench} && {ssl_command}")
        exit_status = stdout.channel.recv_exit_status()
        
        if exit_status != 0:
            error_output = stderr.read().decode()
            frappe.log_error(f"SSL setup failed for {site_name}: {error_output}", "SSL Setup Error")
            # Don't raise exception as SSL setup failure shouldn't stop site creation
            frappe.log_error(f"SSL setup failed but continuing with site creation: {error_output}", "SSL Setup Warning")
        else:
            success_output = stdout.read().decode()
            frappe.log_error(f"SSL setup successful for {site_name}: {success_output}", "SSL Setup Success")
        
    except Exception as e:
        frappe.log_error(f"Error setting up SSL certificate for {site_name}: {str(e)}", "SSL Setup Error")
        # Don't raise exception as SSL setup failure shouldn't stop site creation
        frappe.log_error(f"SSL setup error but continuing with site creation: {str(e)}", "SSL Setup Warning")
