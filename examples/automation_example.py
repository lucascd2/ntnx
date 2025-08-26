#!/usr/bin/env python3
"""
NGT Auto Installation - Automation Example
==========================================

This example demonstrates how to integrate the NGT auto-installation script
into larger automation workflows or infrastructure-as-code scenarios.
"""

import subprocess
import sys
import logging
import json
from typing import Dict, List, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class NGTAutomationManager:
    """Manager class for automating NGT installations across multiple VMs"""
    
    def __init__(self, prism_central_ip: str, username: str, password: str):
        self.pc_ip = prism_central_ip
        self.username = username
        self.password = password
        self.ngt_script = "./ngt_auto_install.py"
    
    def check_ngt_status(self, vm_uuid: str = None) -> Dict:
        """Check NGT status for a VM"""
        cmd = [
            "python3", self.ngt_script,
            "--pc-ip", self.pc_ip,
            "--username", self.username,
            "--password", self.password,
            "--skip-install"
        ]
        
        if vm_uuid:
            cmd.extend(["--vm-uuid", vm_uuid])
            
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr,
                "vm_uuid": vm_uuid
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "vm_uuid": vm_uuid
            }
    
    def install_ngt(self, vm_uuid: str, vm_username: str, vm_password: str, 
                   no_reboot: bool = False) -> Dict:
        """Install NGT on a specific VM"""
        cmd = [
            "python3", self.ngt_script,
            "--pc-ip", self.pc_ip,
            "--username", self.username, 
            "--password", self.password,
            "--vm-uuid", vm_uuid,
            "--vm-username", vm_username,
            "--vm-password", vm_password
        ]
        
        if no_reboot:
            cmd.append("--no-reboot")
            
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr,
                "vm_uuid": vm_uuid
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "vm_uuid": vm_uuid
            }
    
    def bulk_install(self, vm_configs: List[Dict]) -> List[Dict]:
        """Install NGT on multiple VMs"""
        results = []
        
        for vm_config in vm_configs:
            logger.info(f"Installing NGT on VM: {vm_config.get('uuid', 'unknown')}")
            
            result = self.install_ngt(
                vm_uuid=vm_config['uuid'],
                vm_username=vm_config['username'],
                vm_password=vm_config['password'],
                no_reboot=vm_config.get('no_reboot', False)
            )
            
            results.append({
                **result,
                "vm_name": vm_config.get('name', 'unknown')
            })
            
            if result['success']:
                logger.info(f"✅ NGT installed successfully on {vm_config.get('name', 'VM')}")
            else:
                logger.error(f"❌ NGT installation failed on {vm_config.get('name', 'VM')}: {result.get('error', 'Unknown error')}")
        
        return results


def example_single_vm():
    """Example: Install NGT on current local VM"""
    logger.info("Example: Installing NGT on local VM")
    
    # Configuration
    config = {
        "prism_central_ip": "10.38.11.74",
        "admin_username": "admin",
        "admin_password": "your-admin-password",  # Use secure credential management
        "vm_username": "administrator",  # or root for Linux
        "vm_password": "your-vm-password"
    }
    
    manager = NGTAutomationManager(
        config["prism_central_ip"],
        config["admin_username"], 
        config["admin_password"]
    )
    
    # First check current status
    logger.info("Checking current NGT status...")
    status = manager.check_ngt_status()
    
    if status['success']:
        logger.info("NGT status check completed")
    else:
        logger.error(f"Failed to check NGT status: {status['error']}")
        return
    
    # Install NGT
    result = manager.install_ngt(
        vm_uuid=None,  # Auto-detect current VM
        vm_username=config["vm_username"],
        vm_password=config["vm_password"],
        no_reboot=False
    )
    
    if result['success']:
        logger.info("✅ NGT installation completed successfully!")
    else:
        logger.error(f"❌ NGT installation failed: {result['error']}")


def example_bulk_installation():
    """Example: Install NGT on multiple VMs"""
    logger.info("Example: Bulk NGT installation")
    
    # Configuration
    nutanix_config = {
        "prism_central_ip": "10.38.11.74",
        "admin_username": "admin",
        "admin_password": "your-admin-password"
    }
    
    # VM configurations
    vm_configs = [
        {
            "uuid": "vm-uuid-1",
            "name": "web-server-01",
            "username": "administrator",
            "password": "vm-password-1",
            "no_reboot": False
        },
        {
            "uuid": "vm-uuid-2", 
            "name": "db-server-01",
            "username": "root",
            "password": "vm-password-2",
            "no_reboot": True  # Don't reboot database server
        },
        {
            "uuid": "vm-uuid-3",
            "name": "app-server-01", 
            "username": "administrator",
            "password": "vm-password-3",
            "no_reboot": False
        }
    ]
    
    manager = NGTAutomationManager(**nutanix_config)
    
    # Perform bulk installation
    results = manager.bulk_install(vm_configs)
    
    # Report results
    successful = sum(1 for r in results if r['success'])
    failed = len(results) - successful
    
    logger.info(f"Bulk installation completed: {successful} successful, {failed} failed")
    
    # Log detailed results
    for result in results:
        vm_name = result.get('vm_name', 'Unknown')
        if result['success']:
            logger.info(f"✅ {vm_name}: Installation successful")
        else:
            logger.error(f"❌ {vm_name}: Installation failed - {result.get('error', 'Unknown error')}")
    
    return results


def example_infrastructure_as_code():
    """Example: Integration with Infrastructure-as-Code workflow"""
    logger.info("Example: Infrastructure-as-Code integration")
    
    # This could be integrated with Terraform, Ansible, or other IaC tools
    # The NGT installation would be part of the VM provisioning process
    
    def provision_vm_with_ngt(vm_spec: Dict) -> Dict:
        """Provision a VM and install NGT as part of the process"""
        
        # 1. Create VM (using your IaC tool)
        logger.info(f"Provisioning VM: {vm_spec['name']}")
        # vm_uuid = create_vm_via_terraform_or_api(vm_spec)
        vm_uuid = vm_spec.get('uuid', 'simulated-uuid')  # Simulated for example
        
        # 2. Wait for VM to be ready
        logger.info("Waiting for VM to be ready...")
        # wait_for_vm_ready(vm_uuid)
        
        # 3. Install NGT
        logger.info("Installing NGT...")
        manager = NGTAutomationManager(
            vm_spec['nutanix']['pc_ip'],
            vm_spec['nutanix']['username'],
            vm_spec['nutanix']['password']
        )
        
        ngt_result = manager.install_ngt(
            vm_uuid=vm_uuid,
            vm_username=vm_spec['vm']['username'],
            vm_password=vm_spec['vm']['password']
        )
        
        return {
            "vm_uuid": vm_uuid,
            "ngt_installed": ngt_result['success'],
            "ngt_error": ngt_result.get('error') if not ngt_result['success'] else None
        }
    
    # Example VM specification
    vm_spec = {
        "name": "production-web-01",
        "uuid": "existing-vm-uuid",  # If VM already exists
        "nutanix": {
            "pc_ip": "10.38.11.74",
            "username": "admin",
            "password": "admin-password"
        },
        "vm": {
            "username": "administrator",
            "password": "vm-password"
        }
    }
    
    result = provision_vm_with_ngt(vm_spec)
    logger.info(f"VM provisioning result: {result}")


if __name__ == "__main__":
    print("NGT Automation Examples")
    print("======================")
    print("1. Single VM installation")
    print("2. Bulk installation")
    print("3. Infrastructure-as-Code integration")
    print()
    
    choice = input("Select example to run (1-3): ")
    
    if choice == "1":
        example_single_vm()
    elif choice == "2":
        example_bulk_installation() 
    elif choice == "3":
        example_infrastructure_as_code()
    else:
        print("Invalid choice. Please run the script again and select 1, 2, or 3.")
        sys.exit(1)
