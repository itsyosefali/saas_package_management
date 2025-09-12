# Copyright (c) 2024, Ebkar – Technology & Management Solutions and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import today, getdate, add_days
from frappe.website.website_generator import WebsiteGenerator


def get_context(context):
    """Get context for monitoring dashboard"""
    context.title = "Instance & Site Monitoring Dashboard"
    context.no_cache = 1
    
    # Get all instances with their status
    instances = frappe.get_all(
        "Instance",
        fields=[
            "name", "instance_name", "package", "ram_gb", "cpu_cores", 
            "storage_gb", "deployment_status", "server_url", "is_active",
            "deployment_date", "last_backup_date"
        ],
        order_by="creation desc"
    )
    
    # Get all customer sites with their status
    customer_sites = frappe.get_all(
        "Customer Site",
        fields=[
            "name", "site_name", "customer_name", "package", "instance",
            "custom_domain", "status", "creation_date", "expiry_date"
        ],
        order_by="creation desc"
    )
    
    # Get package information
    packages = frappe.get_all(
        "Package",
        fields=["name", "package_name", "price", "is_active"],
        filters={"is_active": 1}
    )
    
    # Calculate statistics
    total_instances = len(instances)
    active_instances = len([i for i in instances if i.is_active])
    running_instances = len([i for i in instances if i.deployment_status == "Running"])
    deployed_instances = len([i for i in instances if i.deployment_status == "Deployed"])
    
    total_sites = len(customer_sites)
    active_sites = len([s for s in customer_sites if s.status == "Active"])
    expired_sites = len([s for s in customer_sites if s.status == "Expired"])
    
    # Check for sites expiring soon (within 30 days)
    expiring_soon = []
    for site in customer_sites:
        if site.expiry_date:
            days_until_expiry = (getdate(site.expiry_date) - getdate(today())).days
            if 0 <= days_until_expiry <= 30:
                expiring_soon.append({
                    "site": site,
                    "days_until_expiry": days_until_expiry
                })
    
    # Check for sites that need attention
    sites_needing_attention = []
    for site in customer_sites:
        if site.expiry_date:
            days_until_expiry = (getdate(site.expiry_date) - getdate(today())).days
            if days_until_expiry < 0:  # Expired
                sites_needing_attention.append({
                    "site": site,
                    "issue": "expired",
                    "message": f"Expired {abs(days_until_expiry)} days ago"
                })
            elif days_until_expiry <= 7:  # Expiring soon
                sites_needing_attention.append({
                    "site": site,
                    "issue": "expiring_soon",
                    "message": f"Expires in {days_until_expiry} days"
                })
    
    context.instances = instances
    context.customer_sites = customer_sites
    context.packages = packages
    context.stats = {
        "total_instances": total_instances,
        "active_instances": active_instances,
        "running_instances": running_instances,
        "deployed_instances": deployed_instances,
        "total_sites": total_sites,
        "active_sites": active_sites,
        "expired_sites": expired_sites
    }
    context.expiring_soon = expiring_soon
    context.sites_needing_attention = sites_needing_attention
    
    return context


@frappe.whitelist(allow_guest=True)
def get_instance_status(instance_name):
    """Get real-time status of an instance"""
    try:
        instance = frappe.get_doc("Instance", instance_name)
        
        # In a real implementation, this would ping the actual server
        # For now, we'll return the stored status
        return {
            "success": True,
            "data": {
                "name": instance.name,
                "instance_name": instance.instance_name,
                "deployment_status": instance.deployment_status,
                "is_active": instance.is_active,
                "server_url": instance.server_url,
                "last_backup_date": instance.last_backup_date,
                "ram_gb": instance.ram_gb,
                "cpu_cores": instance.cpu_cores,
                "storage_gb": instance.storage_gb
            }
        }
    except frappe.DoesNotExistError:
        return {
            "success": False,
            "message": "Instance not found"
        }
    except Exception as e:
        frappe.log_error(f"Error getting instance status: {str(e)}", "Instance Status Error")
        return {
            "success": False,
            "message": "Error retrieving instance status"
        }


@frappe.whitelist(allow_guest=True)
def get_site_health(site_name):
    """Get health status of a customer site"""
    try:
        site = frappe.get_doc("Customer Site", site_name)
        
        # Get instance status if assigned
        instance_status = None
        if site.instance:
            instance = frappe.get_doc("Instance", site.instance)
            instance_status = {
                "name": instance.name,
                "instance_name": instance.instance_name,
                "deployment_status": instance.deployment_status,
                "is_active": instance.is_active
            }
        
        # Check expiry status
        expiry_status = site.check_expiry_status()
        
        return {
            "success": True,
            "data": {
                "site_name": site.site_name,
                "custom_domain": site.custom_domain,
                "status": site.status,
                "instance_status": instance_status,
                "expiry_status": expiry_status,
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
        frappe.log_error(f"Error getting site health: {str(e)}", "Site Health Error")
        return {
            "success": False,
            "message": "Error retrieving site health"
        }


@frappe.whitelist()
def refresh_all_statuses():
    """Refresh status of all instances and sites"""
    try:
        # Update instance statuses (in a real implementation, this would ping servers)
        instances = frappe.get_all("Instance", fields=["name"])
        for instance in instances:
            # This is where you would implement actual health checks
            pass
        
        # Check for expired sites
        expired_sites = frappe.get_all(
            "Customer Site",
            filters={
                "expiry_date": ["<", today()],
                "status": "Active"
            },
            fields=["name"]
        )
        
        for site in expired_sites:
            frappe.db.set_value("Customer Site", site.name, "status", "Expired")
        
        frappe.db.commit()
        
        return {
            "success": True,
            "message": "Status refresh completed",
            "expired_sites_updated": len(expired_sites)
        }
        
    except Exception as e:
        frappe.log_error(f"Error refreshing statuses: {str(e)}", "Status Refresh Error")
        return {
            "success": False,
            "message": "Error refreshing statuses"
        }
