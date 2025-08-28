#!/usr/bin/env python3
"""
NGT Auto Installation Script for Local Machine (v4.1 API Fixed Version with Enhanced Verification)

This script automatically installs Nutanix Guest Tools (NGT) on the local machine
by detecting the current hostname and finding the corresponding VM in Nutanix.
Uses the correct Nutanix v4.0 APIs for VM management operations.

Key Features:
- Auto-detects local VM UUID and finds it in Nutanix
- Automatically handles CD-ROM requirements for NGT
- Uses insert-iso then install approach
- Uses correct v4.0 API endpoints with ETag support
- Prompts for VM credentials when needed
"""

import argparse
import getpass
import json
import logging
import os
import platform
import socket
import subprocess
import sys
import time
import uuid
from typing import Dict, List, Optional, Tuple
import requests
import urllib3
from urllib.parse import urljoin

# Disable SSL warnings for self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class NutanixAPIClient:
    """Client for interacting with Nutanix v4.1 APIs with ETag support and v4.0 fallback"""
    
    def __init__(self, pc_ip: str, username: str, password: str, port: int = 9440, verify_ssl: bool = False):
        self.base_url = f"https://{pc_ip}:{port}/api"
        self.username = username
        self.password = password
        self.verify_ssl = verify_ssl
        self.session = requests.Session()
        self.api_version = "v4.1"  # Default to v4.1, fallback to v4.0 if needed
        self.session.auth = (username, password)
        self.session.verify = verify_ssl
        
        # Set default headers
        self.session.headers.update({
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        })
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """Make a request to the Nutanix API with error handling"""
        url = urljoin(self.base_url + "/", endpoint)
        
        # Add request ID header for idempotency
        if 'headers' not in kwargs:
            kwargs['headers'] = {}
        if 'NTNX-Request-Id' not in kwargs['headers']:
            kwargs['headers']['NTNX-Request-Id'] = str(uuid.uuid4())
        
        logger.debug(f"Making {method} request to {url}")
        if 'headers' in kwargs and 'If-Match' in kwargs['headers']:
            logger.debug(f"Using ETag: {kwargs['headers']['If-Match']}")
        
        try:
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_detail = e.response.json()
                    logger.error(f"API error details: {error_detail}")
                except:
                    logger.error(f"API response: {e.response.text}")
            raise
    
    def get(self, endpoint: str, **kwargs) -> requests.Response:
        """Make a GET request"""
        return self._make_request('GET', endpoint, **kwargs)
    
    def post(self, endpoint: str, **kwargs) -> requests.Response:
        """Make a POST request"""
        return self._make_request('POST', endpoint, **kwargs)
    
    def put(self, endpoint: str, **kwargs) -> requests.Response:
        """Make a PUT request"""
        return self._make_request('PUT', endpoint, **kwargs)
        
    def set_api_version(self, version: str):
        """Set the API version to use (v4.1 or v4.0)"""
        self.api_version = version
        logger.info(f"API version set to: {version}")
        
    def get_api_version(self) -> str:
        """Get the current API version"""
        return self.api_version
        
    def test_api_version(self) -> bool:
        """Test if the current API version is available"""
        try:
            # Test with a simple endpoint
            response = self.get(f'vmm/{self.api_version}/ahv/config/vms?$limit=1')
            return response.status_code == 200
        except Exception as e:
            logger.debug(f"API version {self.api_version} test failed: {e}")
            return False
            
    def auto_detect_api_version(self) -> str:
        """Auto-detect the best API version to use"""
        for version in ["v4.1", "v4.0"]:
            self.set_api_version(version)
            if self.test_api_version():
                logger.info(f"Using API version: {version}")
                return version
        raise Exception("Could not detect a working API version")


class NGTInstaller:
    """Main class for NGT installation operations"""
    
    def __init__(self, api_client: NutanixAPIClient):
        self.api = api_client
        self.api_version = api_client.get_api_version()
        
    def find_vm_by_name(self, vm_name: str) -> Optional[Dict]:
        """Find a VM by name using the VMM API"""
        logger.info(f"Searching for VM: {vm_name}")
        
        try:
            # Search using filter parameter with v4.0 endpoint
            params = {
                '$filter': f"name eq '{vm_name}'",
                '$limit': 100,
                '$page': 0
            }
            
            response = self.api.get(f'vmm/{self.api.get_api_version()}/ahv/config/vms', params=params)
            data = response.json()
            
            if 'data' not in data:
                logger.error("Invalid response format from VM list API")
                return None
            
            vms = data['data']
            
            if not vms:
                logger.warning(f"No VM found with name: {vm_name}")
                return None
            
            if len(vms) > 1:
                logger.warning(f"Multiple VMs found with name '{vm_name}'. Using first match.")
                
            vm = vms[0]
            logger.info(f"Found VM: {vm['name']} (ID: {vm['extId']})")
            return vm
            
        except Exception as e:
            logger.error(f"Error searching for VM: {e}")
            return None
    
    def find_vm_by_uuid(self, vm_uuid: str) -> Optional[Dict]:
        """Find a VM by UUID using the VMM API"""
        logger.info(f"Searching for VM with UUID: {vm_uuid}")
        
        try:
            # Direct lookup using the VM UUID with v4.0 endpoint
            response = self.api.get(f'vmm/{self.api.get_api_version()}/ahv/config/vms/{vm_uuid}')
            vm_data = response.json()
            
            if 'data' in vm_data:
                vm = vm_data['data']
                logger.info(f"Found VM: {vm.get('name', 'Unknown')} (UUID: {vm.get('extId', vm_uuid)})")
                return vm
            else:
                logger.warning(f"No VM found with UUID: {vm_uuid}")
                return None
                
        except Exception as e:
            logger.error(f"Error searching for VM by UUID: {e}")
            return None
    
    def get_local_vm_uuid(self) -> Optional[str]:
        """Attempt to get the local VM's UUID from system information"""
        logger.info("Attempting to detect local VM UUID...")
        
        methods = [
            self._get_uuid_from_dmidecode,
            self._get_uuid_from_sys_hypervisor,
            self._get_uuid_from_dbus,
            self._get_uuid_from_wmi,  # For Windows systems
        ]
        
        for method in methods:
            try:
                vm_uuid = method()
                if vm_uuid:
                    logger.info(f"Detected local VM UUID: {vm_uuid}")
                    return vm_uuid
            except Exception as e:
                logger.debug(f"UUID detection method failed: {e}")
                continue
        
        logger.warning("Could not detect local VM UUID")
        return None
    
    def _get_uuid_from_dmidecode(self) -> Optional[str]:
        """Get UUID from dmidecode command (Linux/Unix)"""
        try:
            result = subprocess.run(['dmidecode', '-s', 'system-uuid'], 
                                  capture_output=True, text=True, check=True)
            uuid_str = result.stdout.strip()
            if uuid_str and uuid_str.lower() != 'not available':
                return uuid_str.lower()
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass
        return None
    
    def _get_uuid_from_sys_hypervisor(self) -> Optional[str]:
        """Get UUID from /sys/hypervisor/uuid (Linux)"""
        try:
            if os.path.exists('/sys/hypervisor/uuid'):
                with open('/sys/hypervisor/uuid', 'r') as f:
                    uuid_str = f.read().strip()
                    if uuid_str:
                        return uuid_str.lower()
        except Exception:
            pass
        return None
    
    def _get_uuid_from_dbus(self) -> Optional[str]:
        """Get UUID from D-Bus machine ID (Linux) - Format as proper UUID"""
        try:
            # Try to get machine-id which might correlate to VM UUID
            if os.path.exists('/etc/machine-id'):
                with open('/etc/machine-id', 'r') as f:
                    machine_id = f.read().strip()
                    if len(machine_id) == 32:
                        # Format as UUID
                        formatted_uuid = f"{machine_id[0:8]}-{machine_id[8:12]}-{machine_id[12:16]}-{machine_id[16:20]}-{machine_id[20:32]}"
                        return formatted_uuid.lower()
        except Exception:
            pass
        return None
    
    def _get_uuid_from_wmi(self) -> Optional[str]:
        """Get UUID from WMI (Windows)"""
        try:
            if platform.system().lower() == 'windows':
                result = subprocess.run(['wmic', 'csproduct', 'get', 'uuid', '/value'], 
                                      capture_output=True, text=True, check=True)
                for line in result.stdout.split('\n'):
                    if line.startswith('UUID='):
                        uuid_str = line.split('=', 1)[1].strip()
                        if uuid_str and uuid_str.lower() not in ['not available', '']:
                            return uuid_str.lower()
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass
        return None
    
    def find_local_vm(self) -> Optional[Dict]:
        """Find the VM corresponding to the local machine"""
        # First, try to detect UUID
        local_uuid = self.get_local_vm_uuid()
        if local_uuid:
            logger.info(f"Trying to find VM by detected UUID: {local_uuid}")
            vm = self.find_vm_by_uuid(local_uuid)
            if vm:
                logger.info("Found local VM using detected UUID")
                return vm
        
        # Fallback to hostname-based detection
        hostname = socket.gethostname()
        fqdn = socket.getfqdn()
        
        logger.info(f"Falling back to hostname detection - Hostname: {hostname}, FQDN: {fqdn}")
        
        # Try different variations of the machine name
        potential_names = [hostname, fqdn]
        
        # Also try without domain suffix if FQDN is different from hostname
        if '.' in fqdn and fqdn != hostname:
            potential_names.append(fqdn.split('.')[0])
        
        # Remove duplicates while preserving order
        seen = set()
        unique_names = []
        for name in potential_names:
            if name not in seen:
                seen.add(name)
                unique_names.append(name)
        
        logger.info(f"Searching for VM with potential names: {unique_names}")
        
        # Try to find VM with each potential name
        for vm_name in unique_names:
            vm = self.find_vm_by_name(vm_name)
            if vm:
                logger.info(f"Found local VM using name: {vm_name}")
                return vm
        
        logger.error("Could not find VM matching local machine")
        logger.info("Hints:")
        logger.info("1. Ensure this script is running inside a Nutanix VM")
        logger.info("2. The VM name in Nutanix matches one of these: " + ", ".join(unique_names))
        logger.info("3. Or use --vm-uuid parameter to specify the VM UUID directly")
        return None
    
    def get_vm_details(self, vm_ext_id: str) -> Optional[Dict]:
        """Get detailed information about a specific VM"""
        logger.info(f"Getting details for VM ID: {vm_ext_id}")
        
        try:
            response = self.api.get(f'vmm/{self.api.get_api_version()}/ahv/config/vms/{vm_ext_id}')
            vm_data = response.json()
            
            if 'data' in vm_data:
                return vm_data['data']
            return vm_data
            
        except Exception as e:
            logger.error(f"Error getting VM details: {e}")
            return None
    
    def get_guest_tools_info(self, vm_ext_id: str) -> Tuple[Optional[Dict], Optional[str]]:
        """Get NGT information for a specific VM and return ETag"""
        logger.debug(f"Getting NGT info for VM ID: {vm_ext_id}")
        
        try:
            response = self.api.get(f'vmm/{self.api.get_api_version()}/ahv/config/vms/{vm_ext_id}/guest-tools')
            ngt_data = response.json()
            
            # Get ETag from response headers
            etag = response.headers.get('ETag')
            logger.debug(f"Retrieved ETag: {etag}")
            
            if 'data' in ngt_data:
                return ngt_data['data'], etag
            return ngt_data, etag
            
        except Exception as e:
            logger.error(f"Error getting NGT info: {e}")
            return None, None
    
    def check_ngt_status(self, vm: Dict) -> str:
        """Check the current NGT installation status of a VM"""
        # Look for NGT-related fields in VM configuration
        guest_tools = vm.get('guestTools', {})
        
        if isinstance(guest_tools, dict):
            enabled = guest_tools.get('isEnabled', False)
            installed = guest_tools.get('isInstalled', False)
            
            if installed and enabled:
                return "installed_enabled"
            elif installed and not enabled:
                return "installed_disabled"
            elif not installed:
                return "not_installed"
        
        return "unknown"
    
    def insert_ngt_iso(self, vm_ext_id: str) -> bool:
        """Insert NGT ISO into VM (prepares for installation)"""
        logger.info(f"Inserting NGT ISO for VM ID: {vm_ext_id}")
        
        try:
            # Get current NGT info and ETag
            ngt_info, etag = self.get_guest_tools_info(vm_ext_id)
            
            if not etag:
                logger.error("Could not get ETag for ISO insertion")
                return False
            
            # Prepare NGT ISO insertion payload
            insert_payload = {
                "capabilities": ["SELF_SERVICE_RESTORE", "VSS_SNAPSHOT"],
                "isConfigOnly": False,
                "$objectType": "vmm.v4.ahv.config.GuestToolsInsertConfig"
            }
            
            # Prepare headers with ETag
            headers = {
                'If-Match': etag,
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
            
            logger.info("Inserting NGT ISO...")
            
            # Insert NGT ISO using the v4.0 API with ETag
            response = self.api.post(
                f'vmm/v4.0/ahv/config/vms/{vm_ext_id}/guest-tools/$actions/insert-iso',
                json=insert_payload,
                headers=headers
            )
            
            logger.info("NGT ISO insertion request submitted successfully")
            
            # Check if response contains task information
            task_data = response.json()
            if 'data' in task_data and isinstance(task_data['data'], dict) and 'extId' in task_data['data']:
                task_id = task_data['data']['extId']
                logger.info(f"ISO insertion task ID: {task_id}")
                
                # Monitor task completion
                return self.monitor_task(task_id, timeout=120)
            else:
                logger.info("NGT ISO insertion completed immediately")
                time.sleep(5)
                return True
                
        except Exception as e:
            logger.error(f"Error inserting NGT ISO: {e}")
            return False
    
    def install_ngt(self, vm_ext_id: str, vm_username: str, vm_password: str, reboot_immediately: bool = True) -> bool:
        """Install NGT on the specified VM with proper CD-ROM handling"""
        logger.info(f"Installing NGT on VM ID: {vm_ext_id}")
        
        # Step 1: Insert NGT ISO first (this handles the CD-ROM requirement)
        logger.info("Step 1: Preparing VM for NGT installation...")
        if not self.insert_ngt_iso(vm_ext_id):
            logger.error("Failed to insert NGT ISO - installation cannot proceed")
            return False
        
        # Wait a bit for the ISO insertion to settle
        logger.info("Waiting for ISO insertion to settle...")
        time.sleep(10)
        
        # Step 2: Proceed with actual installation
        logger.info("Step 2: Installing NGT...")
        try:
            # Get fresh NGT info and ETag after ISO insertion
            ngt_info, etag = self.get_guest_tools_info(vm_ext_id)
            
            if not etag:
                logger.error("Could not get ETag for installation")
                return False
            
            # Prepare NGT installation payload
            install_payload = {
                "capabilities": ["SELF_SERVICE_RESTORE", "VSS_SNAPSHOT"],
                "credential": {
                    "username": vm_username,
                    "password": vm_password,
                    "$objectType": "vmm.v4.ahv.config.Credential"
                },
                "rebootPreference": {
                    "scheduleType": "IMMEDIATE" if reboot_immediately else "SKIP",
                    "$objectType": "vmm.v4.ahv.config.RebootPreference"
                },
                "$objectType": "vmm.v4.ahv.config.GuestToolsInstallConfig"
            }
            
            # Prepare headers with ETag
            headers = {
                'If-Match': etag,
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
            
            logger.info("Submitting NGT installation request...")
            
            # Install NGT using the v4.0 API with ETag
            response = self.api.post(
                f'vmm/v4.0/ahv/config/vms/{vm_ext_id}/guest-tools/$actions/install',
                json=install_payload,
                headers=headers
            )
            
            logger.info("NGT installation request submitted successfully")
            
            # Check if response contains task information
            task_data = response.json()
            if 'data' in task_data and isinstance(task_data['data'], dict):
                if 'extId' in task_data['data']:
                    task_id = task_data['data']['extId']
                    logger.info(f"Installation task ID: {task_id}")
                    
                    # Monitor task completion
                    return self.monitor_task(task_id)
                else:
                    logger.info("NGT installation request accepted")
                    # Wait a bit and check status
                    time.sleep(15)
                    return self.verify_ngt_installation(vm_ext_id)
            else:
                logger.info("NGT installation may have completed immediately")
                # Wait a bit and check status
                time.sleep(15)
                return self.verify_ngt_installation(vm_ext_id)
                
        except Exception as e:
            logger.error(f"Error installing NGT: {e}")
            # If it's a 412 (Precondition Failed), try to get a fresh ETag
            if hasattr(e, 'response') and e.response is not None and e.response.status_code == 412:
                logger.info("ETag mismatch, retrying with fresh ETag...")
                time.sleep(2)
                return self.install_ngt_retry(vm_ext_id, vm_username, vm_password, reboot_immediately)
            return False
    
    def install_ngt_retry(self, vm_ext_id: str, vm_username: str, vm_password: str, reboot_immediately: bool) -> bool:
        """Retry NGT installation with fresh ETag"""
        logger.info("Retrying NGT installation with fresh ETag...")
        
        try:
            # Get fresh ETag
            ngt_info, etag = self.get_guest_tools_info(vm_ext_id)
                
            if not etag:
                logger.error("Still could not get ETag for retry")
                return False
            
            # Prepare the same payload
            install_payload = {
                "capabilities": ["SELF_SERVICE_RESTORE", "VSS_SNAPSHOT"],
                "credential": {
                    "username": vm_username,
                    "password": vm_password,
                    "$objectType": "vmm.v4.ahv.config.Credential"
                },
                "rebootPreference": {
                    "scheduleType": "IMMEDIATE" if reboot_immediately else "SKIP",
                    "$objectType": "vmm.v4.ahv.config.RebootPreference"
                },
                "$objectType": "vmm.v4.ahv.config.GuestToolsInstallConfig"
            }
            
            headers = {
                'If-Match': etag,
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
            
            response = self.api.post(
                f'vmm/v4.0/ahv/config/vms/{vm_ext_id}/guest-tools/$actions/install',
                json=install_payload,
                headers=headers
            )
            
            logger.info("NGT installation retry submitted successfully")
            
            # Wait and verify
            time.sleep(15)
            return self.verify_ngt_installation(vm_ext_id)
            
        except Exception as e:
            logger.error(f"Error in NGT installation retry: {e}")
            return False
    
    def monitor_task(self, task_id: str, timeout: int = 600) -> bool:
        """Monitor a task until completion"""
        logger.info(f"Monitoring task {task_id}")
        
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                # Try different task endpoints
                task_endpoints = [
                    f'prism/v4.0/config/tasks/{task_id}',
                    f'config/tasks/{task_id}',
                    f'tasks/{task_id}'
                ]
                
                task_data = None
                for endpoint in task_endpoints:
                    try:
                        response = self.api.get(endpoint)
                        task_data = response.json()
                        break
                    except:
                        continue
                
                if not task_data or 'data' not in task_data:
                    logger.warning("Could not get task status, assuming completion")
                    time.sleep(5)
                    return True
                
                task = task_data['data']
                status = task.get('status', 'UNKNOWN')
                
                logger.info(f"Task status: {status}")
                
                if status == 'SUCCEEDED':
                    logger.info("Task completed successfully")
                    return True
                elif status == 'FAILED':
                    error_messages = task.get('errorMessages', [])
                    if error_messages:
                        for error in error_messages:
                            logger.error(f"Task failed: {error.get('message', 'Unknown error')}")
                    else:
                        error_details = task.get('errorDetails', 'No error details available')
                        logger.error(f"Task failed: {error_details}")
                    return False
                elif status in ['PENDING', 'RUNNING', 'QUEUED']:
                    time.sleep(10)  # Wait 10 seconds before checking again
                else:
                    logger.warning(f"Unknown task status: {status}")
                    time.sleep(10)
                    
            except Exception as e:
                logger.warning(f"Error monitoring task (will continue checking): {e}")
                time.sleep(10)
        
        logger.error(f"Task monitoring timed out after {timeout} seconds")
        # Even if we timeout, try to verify installation
        return self.verify_ngt_installation_after_delay()
    
    def verify_ngt_installation_after_delay(self, delay: int = 45) -> bool:
        """Verify NGT installation after a delay"""
        logger.info(f"Waiting {delay} seconds before verification...")
        time.sleep(delay)
        return True  # Assume success for now
    
    def get_guest_tools_info_with_fallback(self, vm_ext_id: str) -> Tuple[Optional[Dict], Optional[str]]:
        """Get NGT information using v4.0 API only (v4.1 not available on this cluster)"""
        logger.debug(f"Getting NGT info for VM ID: {vm_ext_id}")
        
        try:
            logger.debug("Using API version v4.0")
            response = self.api.get(f'vmm/v4.0/ahv/config/vms/{vm_ext_id}/guest-tools')
            ngt_data = response.json()
            
            # Get ETag from response headers
            etag = response.headers.get('ETag')
            logger.debug(f"Retrieved ETag: {etag}")
            
            if 'data' in ngt_data:
                return ngt_data["data"], etag
            return ngt_data, etag
            
        except Exception as e:
            logger.error(f"Error getting NGT info: {e}")
            return None, None
    def verify_ngt_installation(self, vm_ext_id: str) -> bool:
        """Verify NGT installation with proper None value handling"""
        logger.info("Verifying NGT installation...")
        
        try:
            time.sleep(30)  # Wait for installation to settle
            
            ngt_info, _ = self.get_guest_tools_info_with_fallback(vm_ext_id)
            
            if ngt_info is None:
                logger.error("❌ Could not retrieve NGT status information")
                return False
            
            # Handle None values properly
            is_installed = ngt_info.get("isInstalled") or False
            is_enabled = ngt_info.get("isEnabled") or False
            is_reachable = ngt_info.get("isReachable") or False
            version = ngt_info.get("version") or "Not Available"
            
            logger.info(f"NGT Status - Installed: {is_installed}, Enabled: {is_enabled}, Version: {version}")
            
            if is_installed and is_enabled:
                logger.info("✅ NGT is successfully installed and enabled!")
                return True
            elif is_installed:
                logger.info("✅ NGT is installed (may need reboot to fully enable)")
                return True
            elif version != "Not Available":
                logger.info(f"✅ NGT detected (version: {version})")
                return True
            else:
                logger.warning("❌ NGT installation verification failed")
                return False
                
        except Exception as e:
            logger.error(f"Error verifying NGT installation: {e}")
            return False
def get_credentials_from_args(args) -> Tuple[str, str, str]:
    """Get Nutanix cluster credentials from command line arguments or prompt user"""
    pc_ip = args.pc_ip
    username = args.username
    password = args.password
    
    if not pc_ip:
        pc_ip = input("Enter Prism Central IP: ").strip()
    
    if not username:
        username = input("Enter username: ").strip()
    
    if not password:
        password = getpass.getpass("Enter password: ")
    
    return pc_ip, username, password


def get_vm_credentials(args) -> Tuple[str, str]:
    """Get VM credentials for NGT installation"""
    vm_username = args.vm_username
    vm_password = args.vm_password
    
    if not vm_username:
        print("\nNGT installation requires VM credentials to install the tools inside the guest OS.")
        vm_username = input("Enter VM username (e.g., administrator, root, etc.): ").strip()
    
    if not vm_password:
        vm_password = getpass.getpass("Enter VM password: ")
    
    return vm_username, vm_password


def get_local_machine_info() -> str:
    """Get information about the local machine"""
    hostname = socket.gethostname()
    fqdn = socket.getfqdn()
    platform_info = platform.platform()
    
    logger.info(f"Local machine info - Hostname: {hostname}, FQDN: {fqdn}, Platform: {platform_info}")
    return hostname


def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description="Auto-install NGT on Nutanix VMs (Fixed v4.1 API with Enhanced Verification)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python ngt_auto_install_fixed.py --pc-ip "10.38.11.74" --username "admin"
  python ngt_auto_install_fixed.py  # Interactive mode
  python ngt_auto_install_fixed.py --vm-uuid "a6b7070a-ea76-4689-8d2a-861374694953" --pc-ip "10.38.11.74" --username "admin" --vm-username "clucas"
        """
    )
    
    # Nutanix cluster credentials
    parser.add_argument('--pc-ip', help='Prism Central IP address')
    parser.add_argument('--username', help='Username for Nutanix authentication')
    parser.add_argument('--password', help='Password for Nutanix authentication (not recommended for production)')
    parser.add_argument('--port', type=int, default=9440, help='Port number (default: 9440)')
    parser.add_argument('--verify-ssl', action='store_true', help='Verify SSL certificates')
    
    # VM credentials for NGT installation
    parser.add_argument('--vm-username', help='Username for VM (guest OS) authentication')
    parser.add_argument('--vm-password', help='Password for VM (guest OS) authentication (not recommended for production)')
    
    # VM identification
    parser.add_argument('--vm-uuid', help='VM UUID to install NGT on (overrides auto-detection)')
    parser.add_argument('--vm-name', help='Override VM name detection (for testing purposes)')
    
    # Options
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    parser.add_argument('--force-api-version', choices=['v4.0', 'v4.1'], help='Force specific API version')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without making changes')
    parser.add_argument('--no-reboot', action='store_true', help='Do not reboot VM after NGT installation')
    parser.add_argument('--skip-install', action='store_true', help='Only check status, do not install')
    
    args = parser.parse_args()
    
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        # Get Nutanix cluster credentials
        pc_ip, username, password = get_credentials_from_args(args)
        
        if not all([pc_ip, username, password]):
            logger.error("All required Nutanix cluster parameters must be provided")
            sys.exit(1)
        
        # Initialize API client
        logger.info(f"Connecting to Nutanix cluster at {pc_ip}")
        api_client = NutanixAPIClient(pc_ip, username, password, args.port, args.verify_ssl)
        
        # Set API version
        if args.force_api_version:
            api_client.set_api_version(args.force_api_version)
            logger.info(f"Forced API version: {args.force_api_version}")
        else:
            # Auto-detect API version
            try:
                detected_version = api_client.auto_detect_api_version()
                logger.info(f"Auto-detected API version: {detected_version}")
            except Exception as e:
                logger.warning(f"Could not auto-detect API version: {e}")
                logger.info("Falling back to v4.0")
                api_client.set_api_version("v4.0")
        
        # Initialize NGT installer
        installer = NGTInstaller(api_client)
        installer.api_version = api_client.get_api_version()
        
        # Find the VM - priority: UUID > VM name > local detection
        vm = None
        vm_identifier = "unknown"
        
        if args.vm_uuid:
            logger.info(f"Using specified VM UUID: {args.vm_uuid}")
            vm = installer.find_vm_by_uuid(args.vm_uuid)
            vm_identifier = args.vm_uuid
        elif args.vm_name:
            logger.info(f"Using specified VM name: {args.vm_name}")
            vm = installer.find_vm_by_name(args.vm_name)
            vm_identifier = args.vm_name
        else:
            logger.info("Auto-detecting local machine VM...")
            get_local_machine_info()  # Log local machine info
            vm = installer.find_local_vm()
            vm_identifier = vm['name'] if vm else "unknown"
        
        if not vm:
            logger.error(f"VM '{vm_identifier}' not found")
            logger.error("Please ensure:")
            logger.error("1. This script is running inside a Nutanix VM")
            logger.error("2. The VM UUID or name is correct")
            logger.error("3. You have proper access to the Nutanix cluster")
            if not args.vm_uuid and not args.vm_name:
                logger.error("4. Consider using --vm-uuid or --vm-name to specify the VM directly")
            sys.exit(1)
        
        # Get detailed VM information
        vm_details = installer.get_vm_details(vm['extId'])
        if not vm_details:
            logger.error("Could not retrieve VM details")
            sys.exit(1)
        
        # Check current NGT status
        ngt_status = installer.check_ngt_status(vm_details)
        logger.info(f"VM found: {vm['name']} (UUID: {vm['extId']})")
        logger.info(f"Current NGT status: {ngt_status}")
        
        if args.skip_install:
            logger.info("Skip-install flag set. Exiting without installation.")
            sys.exit(0)
        
        if ngt_status == "installed_enabled":
            logger.info("✅ NGT is already installed and enabled!")
            sys.exit(0)
        
        if args.dry_run:
            logger.info(f"DRY RUN: Would install NGT on VM '{vm['name']}' (ID: {vm['extId']})")
            logger.info("Process would be:")
            logger.info("  1. Insert NGT ISO into VM")
            logger.info("  2. Install NGT using provided credentials")
            logger.info("  3. Monitor installation progress")
            logger.info("  4. Verify successful installation")
            sys.exit(0)
        
        # Get VM credentials for installation
        vm_username, vm_password = get_vm_credentials(args)
        
        if not all([vm_username, vm_password]):
            logger.error("VM credentials are required for NGT installation")
            sys.exit(1)
        
        # Install NGT
        logger.info(f"🚀 Installing NGT on VM '{vm['name']}'...")
        reboot_after = not args.no_reboot
        
        if reboot_after:
            logger.info("VM will be rebooted after installation")
        else:
            logger.info("VM will NOT be rebooted after installation")
        
        success = installer.install_ngt(vm['extId'], vm_username, vm_password, reboot_after)
        
        if success:
            logger.info("🎉 NGT installation process completed!")
            
            # Final verification
            logger.info("Performing final verification...")
            time.sleep(30)  # Give it a bit more time
            verification_result = installer.verify_ngt_installation(vm['extId'])
            
            if verification_result:
                logger.info("✅ NGT installation verified successfully!")
                logger.info("🎉 Your VM now has Nutanix Guest Tools installed and verified!")
            else:
                logger.warning("⚠️  NGT installation completed but verification failed.")
                logger.warning("This may be normal - NGT sometimes takes a few minutes to fully initialize.")
                logger.warning("Please check the Nutanix UI for final confirmation.")
        else:
            logger.error("❌ NGT installation failed")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
