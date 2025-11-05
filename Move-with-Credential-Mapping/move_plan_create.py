#!/usr/bin/env python3
"""
Interactive Move API Migration Manager

This script connects to the Nutanix Move API and provides an interactive interface
to browse environments, select source/target providers, and list VMs for migration.
Based on the official OpenAPI specification.
"""

import requests
import sys
import getpass
import urllib3
from urllib.parse import urljoin
import argparse
import json
from datetime import datetime
import time
import math
import os

# Disable SSL warnings for self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class MoveAPIClient:
    """Interactive Move API client for managing migrations"""
    
    def __init__(self, server, username, password, port=443, verify_ssl=False):
        # Build base URL
        if '://' in server:
            self.base_url = server
            if not self.base_url.endswith(f":{port}") and port != 443:
                self.base_url = f"{self.base_url}:{port}"
        else:
            self.base_url = f"https://{server}:{port}"
        
        self.session = requests.Session()
        self.session.verify = verify_ssl
        self.session.timeout = (10, 30)
        
        # Authenticate and get token
        self.authenticate(username, password)
    
    def authenticate(self, username, password):
        """Authenticate with Move API using official token endpoint"""
        token_endpoint = "/move/v2/token"
        full_url = urljoin(self.base_url, token_endpoint)
        
        form_data = {
            'grantType': 'PASSWORD',
            'username': username,
            'password': password
        }
        
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        try:
            response = self.session.post(full_url, data=form_data, headers=headers, timeout=(10, 30))
            
            if response.status_code == 200:
                result = response.json()
                access_token = result.get('AccessToken')
                api_version = result.get('APIVersion')
                
                if access_token:
                    self.session.headers.update({
                        'Authorization': f'Bearer {access_token}',
                        'Accept': 'application/json',
                        'Content-Type': 'application/json'
                    })
                    print(f"✅ Successfully authenticated to Move API v{api_version}")
                    return
                else:
                    raise Exception("No access token received")
            else:
                raise Exception(f"Authentication failed: {response.status_code} - {response.text}")
                
        except Exception as e:
            raise Exception(f"Failed to authenticate: {e}")
    
    def list_providers(self, refresh_inventory=False, entity_type=None):
        """List all providers/environments using the official API endpoint"""
        list_endpoint = "/move/v2/providers/list"
        full_url = urljoin(self.base_url, list_endpoint)
        
        # Build request payload per OpenAPI spec
        payload = {
            "RefreshInventory": refresh_inventory,
            "UpdateInventoryToPlans": True
        }
        
        # Add optional filters
        if entity_type:
            payload["EntityType"] = entity_type
        
        try:
            response = self.session.post(full_url, json=payload, timeout=(10, 60))
            
            if response.status_code == 200:
                result = response.json()
                return result.get('Entities', []), result.get('MetaData', {})
            else:
                raise Exception(f"Failed to list providers: {response.status_code} - {response.text}")
                
        except Exception as e:
            raise Exception(f"Error listing providers: {e}")
    
    def list_provider_vms(self, provider_uuid, limit=50, refresh_inventory=False, query="", show_vms="all"):
        """List VMs/workloads from a specific provider using pagination
        
        Args:
            provider_uuid: Provider UUID to get VMs from
            limit: Number of VMs per page (max 100)
            refresh_inventory: Whether to refresh inventory
            query: Search query string
            show_vms: 'all', 'eligiblevms', 'ineligiblevms'
        
        Returns:
            (vms_list, metadata, filters)
        """
        workloads_endpoint = f"/move/v2/providers/{provider_uuid}/workloads/list"
        full_url = urljoin(self.base_url, workloads_endpoint)
        
        # Build search filter payload per OpenAPI spec
        payload = {
            "RefreshInventory": refresh_inventory,
            "UpdateInventoryToPlans": True,
            "ShowVMS": show_vms,
            "Limit": min(limit, 100),
            "SortBy": "VMName",
            "SortOrderDesc": False
        }
        
        if query:
            payload["Query"] = query
        
        try:
            response = self.session.post(full_url, json=payload, timeout=(10, 120))
            
            if response.status_code in [200, 202]:  # 202 is also success for this endpoint
                result = response.json()
                
                # Extract VMs from different possible response formats
                vms = []
                filters = {}
                metadata = result.get('MetaData', {})
                
                if 'Entities' in result:
                    vms = result['Entities']
                elif 'VMs' in result:
                    vms = result['VMs']
                elif 'Workloads' in result:
                    vms = result['Workloads']
                
                # Extract filter information if available
                if 'Filters' in result:
                    filters = result['Filters']
                
                return vms, metadata, filters
            else:
                raise Exception(f"Failed to list VMs: {response.status_code} - {response.text}")
                
        except Exception as e:
            raise Exception(f"Error listing VMs: {e}")
    
    def get_provider_details(self, provider_uuid):
        """Get detailed information about a specific provider"""
        detail_endpoint = f"/move/v2/providers/{provider_uuid}"
        full_url = urljoin(self.base_url, detail_endpoint)
        
        try:
            response = self.session.get(full_url, timeout=(10, 30))
            
            if response.status_code == 200:
                return response.json()
            else:
                raise Exception(f"Failed to get provider details: {response.status_code} - {response.text}")
                
        except Exception as e:
            raise Exception(f"Error getting provider details: {e}")
    
    def validate_provider(self, provider_uuid):
        """Validate a provider connection"""
        validate_endpoint = f"/move/v2/providers/{provider_uuid}/validate"
        full_url = urljoin(self.base_url, validate_endpoint)
        
        try:
            response = self.session.post(full_url, json={}, timeout=(10, 60))
            
            if response.status_code in [200, 202]:
                return response.json()
            else:
                raise Exception(f"Failed to validate provider: {response.status_code} - {response.text}")
                
        except Exception as e:
            raise Exception(f"Error validating provider: {e}")


def clear_screen():
    """Clear the terminal screen"""
    import os
    os.system('clear' if os.name == 'posix' else 'cls')


def display_header():
    """Display the application header"""
    print("=" * 80)
    print("NUTANIX MOVE - INTERACTIVE MIGRATION MANAGER")
    print("=" * 80)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()


def display_providers_table(providers, selected_source=None, selected_target=None):
    """Display providers in a formatted table with selection indicators"""
    if not providers:
        print("No providers/environments found.")
        return
    
    print(f"{'#':<3} {'Name':<25} {'Type':<15} {'Status':<12} {'IP/FQDN':<20} {'Role':<10}")
    print(f"{'-'*3} {'-'*25} {'-'*15} {'-'*12} {'-'*20} {'-'*10}")
    
    for i, provider in enumerate(providers, 1):
        spec = provider.get('Spec', {})
        metadata_info = provider.get('MetaData', {})
        uuid = metadata_info.get('UUID')
        name = spec.get('Name', 'N/A')
        provider_type = spec.get('Type', 'Unknown')
        
        # Get IP from access info
        ip_or_fqdn = 'N/A'
        if 'AOSAccessInfo' in spec:
            ip_or_fqdn = spec['AOSAccessInfo'].get('IPorFQDN', 'N/A')
        elif 'VCenterAccessInfo' in spec:
            ip_or_fqdn = spec['VCenterAccessInfo'].get('IPorFQDN', 'N/A')
        elif 'AWSAccessInfo' in spec:
            ip_or_fqdn = spec['AWSAccessInfo'].get('Region', 'N/A')
        elif 'AzureAccessInfo' in spec:
            ip_or_fqdn = spec['AzureAccessInfo'].get('ResourceGroupName', 'N/A')
        
        # Get status
        status = 'Unknown'
        if 'Status' in provider:
            status = provider['Status'].get('State', 'Unknown')
        elif 'State' in spec:
            status = spec['State']
        
        # Determine role
        role = ""
        if uuid == selected_source:
            role = "SOURCE"
        elif uuid == selected_target:
            role = "TARGET"
        
        print(f"{i:<3} {name[:24]:<25} {provider_type[:14]:<15} {status[:11]:<12} {ip_or_fqdn[:19]:<20} {role:<10}")


def display_vms_page(vms, page, page_size, selected_vms=None):
    """Display a page of VMs with selection status"""
    if selected_vms is None:
        selected_vms = set()
    
    start_idx = page * page_size
    end_idx = min(start_idx + page_size, len(vms))
    
    print(f"\n--- VMs (Page {page + 1}, showing {start_idx + 1}-{end_idx} of {len(vms)}) ---")
    print(f"{'Sel':<3} {'#':<4} {'VM Name':<30} {'Power State':<12} {'CPU':<3} {'RAM(GB)':<8} {'OS':<20}")
    print("-" * 85)
    
    for i in range(start_idx, end_idx):
        vm = vms[i]
        vm_name = get_vm_name(vm)
        selected = "✓" if vm_name in selected_vms else " "
        
        # Get VM properties from different possible formats
        power_state = get_vm_property(vm, 'PowerState', 'power_state', 'State', default='Unknown')
        cpu_cores = get_vm_property(vm, 'NumCPU', 'NumCpus', 'cpu_cores', default=0)
        memory_mb = get_vm_property(vm, 'MemoryMB', 'memory_mb', 'MemoryBytes', default=0)
        
        # Convert memory to GB if it's in MB or bytes
        if memory_mb > 1024*1024:  # Likely bytes
            memory_gb = memory_mb / (1024*1024*1024)
        elif memory_mb > 1024:  # Likely MB
            memory_gb = memory_mb / 1024
        else:  # Already GB or very small
            memory_gb = memory_mb
        
        os_info = get_vm_property(vm, 'GuestOS', 'os', 'OperatingSystem', 'OSType', default='Unknown')
        
        print(f"{selected:<3} {i+1:<4} {vm_name[:29]:<30} {str(power_state)[:11]:<12} {cpu_cores:<3} {memory_gb:.1f}{'GB':<5} {str(os_info)[:19]:<20}")


def get_vm_name(vm):
    """Extract VM name from different VM data formats"""
    if isinstance(vm, dict):
        # Try different possible name fields in order of preference
        for field in ['VMName', 'Name', 'name', 'DisplayName', 'display_name']:
            if field in vm and vm[field]:
                return vm[field]
        
        # Try nested in Spec
        if 'Spec' in vm:
            spec = vm['Spec']
            for field in ['VMName', 'Name', 'name', 'DisplayName']:
                if field in spec and spec[field]:
                    return spec[field]
    
    return str(vm)  # Fallback


def get_vm_property(vm, *field_names, default=None):
    """Get a property from VM data trying multiple field names"""
    if not isinstance(vm, dict):
        return default
    
    # Try direct fields first
    for field in field_names:
        if field in vm and vm[field] is not None:
            return vm[field]
    
    # Try in Spec section
    if 'Spec' in vm:
        spec = vm['Spec']
        for field in field_names:
            if field in spec and spec[field] is not None:
                return spec[field]
    
    # Try in Resources section
    if 'Resources' in vm:
        resources = vm['Resources']
        for field in field_names:
            if field in resources and resources[field] is not None:
                return resources[field]
    
    # Try in nested Spec.Resources
    if 'Spec' in vm and 'Resources' in vm['Spec']:
        resources = vm['Spec']['Resources']
        for field in field_names:
            if field in resources and resources[field] is not None:
                return resources[field]
    
    return default
    
    # Try direct fields first
    for field in field_names:
        if field in vm:
            return vm[field]
    
    # Try in Spec section
    if 'Spec' in vm:
        spec = vm['Spec']
        for field in field_names:
            if field in spec:
                return spec[field]
    
    # Try in Resources section
    if 'Resources' in vm:
        resources = vm['Resources']
        for field in field_names:
            if field in resources:
                return resources[field]
    
    # Try in nested Spec.Resources
    if 'Spec' in vm and 'Resources' in vm['Spec']:
        resources = vm['Spec']['Resources']
        for field in field_names:
            if field in resources:
                return resources[field]
    
    return default


def select_source_target(providers):
    """Interactive selection of source and target providers"""
    if len(providers) < 2:
        print("Need at least 2 providers to create a migration plan.")
        return None, None
    
    while True:
        clear_screen()
        display_header()
        print("SELECT SOURCE AND TARGET PROVIDERS")
        print("=" * 40)
        
        display_providers_table(providers)
        
        print(f"\nSelect SOURCE provider (1-{len(providers)}): ", end="")
        try:
            source_idx = int(input()) - 1
            if 0 <= source_idx < len(providers):
                source_uuid = providers[source_idx]['MetaData']['UUID']
                source_name = providers[source_idx]['Spec']['Name']
                
                print(f"\nSelected SOURCE: {source_name}")
                
                # Show available targets (exclude source)
                print(f"\nSelect TARGET provider (1-{len(providers)}, not {source_idx + 1}): ", end="")
                target_idx = int(input()) - 1
                
                if 0 <= target_idx < len(providers) and target_idx != source_idx:
                    target_uuid = providers[target_idx]['MetaData']['UUID']
                    target_name = providers[target_idx]['Spec']['Name']
                    
                    print(f"Selected TARGET: {target_name}")
                    
                    # Confirm selection
                    print(f"\nMigration Plan:")
                    print(f"  SOURCE: {source_name}")
                    print(f"  TARGET: {target_name}")
                    
                    confirm = input("\nConfirm selection? (y/n): ").strip().lower()
                    if confirm.startswith('y'):
                        return source_uuid, target_uuid
                    else:
                        continue
                else:
                    print("Invalid target selection or same as source.")
                    input("Press Enter to try again...")
            else:
                print("Invalid selection.")
                input("Press Enter to try again...")
        except ValueError:
            print("Invalid input. Please enter a number.")
            input("Press Enter to try again...")
        except KeyboardInterrupt:
            return None, None


def vm_browser_menu(client, source_uuid, source_name, target_uuid=None, target_name=None):
    """Interactive VM browser for source provider"""
    global migration_plan_workflow  # Ensure the function is accessible
    page_size = 20
    current_page = 0
    selected_vms = set()
    all_vms = []
    last_query = ""
    
    while True:
        try:
            clear_screen()
            display_header()
            print(f"VM BROWSER - SOURCE: {source_name}")
            print("=" * 60)
            
            # Load VMs if not already loaded or if refreshing
            if not all_vms:
                print("Loading VMs...")
                vms, metadata, filters = client.list_provider_vms(source_uuid, limit=1000)
                all_vms = vms
                print(f"Loaded {len(all_vms)} VMs")
                time.sleep(1)
            
            if not all_vms:
                print("No VMs found in source provider.")
                input("Press Enter to return...")
                break
            
            # Display current page
            total_pages = math.ceil(len(all_vms) / page_size)
            display_vms_page(all_vms, current_page, page_size, selected_vms)
            
            print(f"\nPage {current_page + 1}/{total_pages} | Selected: {len(selected_vms)} VMs")
            print(f"\nCommands:")
            print(f"  <number>     - Toggle VM selection (e.g., '5')")
            print(f"  <range>      - Toggle range selection (e.g., '1-10')")
            print(f"  n/next       - Next page")
            print(f"  p/prev       - Previous page")
            print(f"  a/all        - Select all VMs on page")
            print(f"  c/clear      - Clear page selections")
            print(f"  s/show       - Show selected VMs")
            print(f"  f/filter     - Filter VMs by name")
            print(f"  r/refresh    - Refresh VM list")
            print(f"  m/migrate    - Create migration plan (does not migrate)")
            print(f"  b/back       - Back to provider selection")
            
            command = input(f"\nEnter command: ").strip().lower()
            
            if command in ['b', 'back']:
                break
            elif command in ['n', 'next']:
                if current_page < total_pages - 1:
                    current_page += 1
                else:
                    print("Already on last page.")
                    time.sleep(1)
            elif command in ['p', 'prev']:
                if current_page > 0:
                    current_page -= 1
                else:
                    print("Already on first page.")
                    time.sleep(1)
            elif command in ['a', 'all']:
                start_idx = current_page * page_size
                end_idx = min(start_idx + page_size, len(all_vms))
                for i in range(start_idx, end_idx):
                    vm_name = get_vm_name(all_vms[i])
                    selected_vms.add(vm_name)
                print(f"Selected all VMs on page {current_page + 1}")
                time.sleep(1)
            elif command in ['c', 'clear']:
                start_idx = current_page * page_size
                end_idx = min(start_idx + page_size, len(all_vms))
                for i in range(start_idx, end_idx):
                    vm_name = get_vm_name(all_vms[i])
                    selected_vms.discard(vm_name)
                print(f"Cleared selections on page {current_page + 1}")
                time.sleep(1)
            elif command in ['s', 'show']:
                if selected_vms:
                    print(f"\nSelected VMs ({len(selected_vms)}):")
                    for i, vm_name in enumerate(sorted(selected_vms), 1):
                        print(f"  {i}. {vm_name}")
                else:
                    print("No VMs selected.")
                input("Press Enter to continue...")
            elif command in ['f', 'filter']:
                query = input("Enter search term (VM name): ").strip()
                if query:
                    print(f"Filtering VMs with '{query}'...")
                    filtered_vms, _, _ = client.list_provider_vms(source_uuid, limit=1000, query=query)
                    all_vms = filtered_vms
                    current_page = 0
                    last_query = query
                    print(f"Found {len(all_vms)} VMs matching '{query}'")
                else:
                    print("Loading all VMs...")
                    all_vms, _, _ = client.list_provider_vms(source_uuid, limit=1000)
                    current_page = 0
                    last_query = ""
                time.sleep(1)
            elif command in ['r', 'refresh']:
                print("Refreshing VM inventory...")
                all_vms, _, _ = client.list_provider_vms(source_uuid, limit=1000, refresh_inventory=True, query=last_query)
                current_page = 0
                print(f"Refreshed! Found {len(all_vms)} VMs")
                time.sleep(1)
            elif command in ['m', 'migrate']:
                if selected_vms:
                    if target_uuid and target_name:
                        print(f"\nProceeding with migration plan for {len(selected_vms)} VMs...")
                        selected_vm_names = list(selected_vms)
                        
                        migration_plan_workflow(client, source_uuid, target_uuid, selected_vm_names, source_name, target_name)
                        # After migration workflow, reload VMs to reflect any changes
                        all_vms = []
                    else:
                        print("❌ No target provider selected. Please go back and select source/target first.")
                        input("Press Enter to continue...")
                else:
                    print("No VMs selected for migration.")
                    input("Press Enter to continue...")
            elif "-" in command:  # Range selection
                try:
                    start_str, end_str = command.split("-")
                    start_num = int(start_str.strip())
                    end_num = int(end_str.strip())
                    
                    start_idx = current_page * page_size
                    for vm_num in range(start_num, end_num + 1):
                        if 1 <= vm_num <= len(all_vms):
                            vm_idx = start_idx + vm_num - 1 - start_idx
                            if start_idx <= vm_idx < min(start_idx + page_size, len(all_vms)):
                                vm_name = get_vm_name(all_vms[vm_idx])
                                if vm_name in selected_vms:
                                    selected_vms.remove(vm_name)
                                else:
                                    selected_vms.add(vm_name)
                    print(f"Toggled selection for VMs {start_num}-{end_num}")
                    time.sleep(1)
                except (ValueError, IndexError):
                    print("Invalid range format. Use: start-end (e.g., '1-10')")
                    time.sleep(1)
            elif command.isdigit():  # Single VM selection
                vm_num = int(command)
                start_idx = current_page * page_size
                page_vm_num = vm_num
                
                if 1 <= page_vm_num <= min(page_size, len(all_vms) - start_idx):
                    vm_idx = start_idx + page_vm_num - 1
                    vm_name = get_vm_name(all_vms[vm_idx])
                    
                    if vm_name in selected_vms:
                        selected_vms.remove(vm_name)
                        print(f"Deselected: {vm_name}")
                    else:
                        selected_vms.add(vm_name)
                        print(f"Selected: {vm_name}")
                    time.sleep(1)
                else:
                    print(f"Invalid VM number. Enter 1-{min(page_size, len(all_vms) - start_idx)}")
                    time.sleep(1)
            else:
                print("Unknown command.")
                time.sleep(1)
                
        except KeyboardInterrupt:
            print("\nReturning to provider selection...")
            break
        except Exception as e:
            print(f"\nError: {e}")
            input("Press Enter to continue...")


def interactive_menu(client):
    """Main interactive menu loop"""
    source_uuid = None
    target_uuid = None
    
    while True:
        try:
            clear_screen()
            display_header()
            print("🛠️  MIGRATION PLAN CREATOR - Creates plans only, does not migrate")
            print("=" * 60)
            
            print("Loading providers...")
            providers, metadata = client.list_providers()
            
            if not providers:
                print("No providers found.")
                input("\nPress Enter to refresh...")
                continue
            
            print(f"Found {len(providers)} environment(s):")
            print()
            
            # Find current source/target names for display
            source_name = None
            target_name = None
            if source_uuid:
                for p in providers:
                    if p['MetaData']['UUID'] == source_uuid:
                        source_name = p['Spec']['Name']
                    elif p['MetaData']['UUID'] == target_uuid:
                        target_name = p['Spec']['Name']
            
            display_providers_table(providers, source_uuid, target_uuid)
            
            if source_uuid and target_uuid:
                print(f"\nCurrent Migration Plan:")
                print(f"  SOURCE: {source_name}")
                print(f"  TARGET: {target_name}")
            
            print(f"\nOptions:")
            print(f"  1-{len(providers)}: View provider details")
            print(f"  s: Select source and target providers")
            if source_uuid:
                print(f"  v: Browse VMs in source ({source_name}) to CREATE MIGRATION plan")
            print(f"  r: Refresh provider list")
            print(f"  R: Refresh with inventory update")
            print(f"  j: Show raw JSON")
            print(f"  q: Quit")
            
            choice = input(f"\nEnter your choice: ").strip().lower()
            
            if choice == 'q':
                print("Goodbye!")
                break
            elif choice == 's':
                print("Starting provider selection...")
                new_source, new_target = select_source_target(providers)
                if new_source and new_target:
                    source_uuid = new_source
                    target_uuid = new_target
                    print("✅ Source and target selected!")
                    time.sleep(1)
            elif choice == 'v' and source_uuid:
                vm_browser_menu(client, source_uuid, source_name, target_uuid, target_name)
            elif choice == 'r':
                print("Refreshing provider list...")
                continue
            elif choice == 'R':
                print("Refreshing provider list with inventory update...")
                providers, metadata = client.list_providers(refresh_inventory=True)
                print("✅ Inventory refreshed!")
                input("Press Enter to continue...")
            elif choice == 'j':
                clear_screen()
                print("RAW JSON DATA:")
                print("=" * 40)
                result = {"Entities": providers, "MetaData": metadata}
                print(json.dumps(result, indent=2))
                input("Press Enter to continue...")
            elif choice.isdigit():
                # View provider details (existing functionality)
                try:
                    idx = int(choice) - 1
                    if 0 <= idx < len(providers):
                        clear_screen()
                        display_provider_details(client, providers[idx])
                        input("Press Enter to continue...")
                    else:
                        print("Invalid selection")
                        input("Press Enter to continue...")
                except (ValueError, IndexError):
                    print("Invalid selection")
                    input("Press Enter to continue...")
            else:
                print("Invalid choice")
                input("Press Enter to continue...")
                
        except KeyboardInterrupt:
            print("\n\nExiting...")
            break
        except Exception as e:
            print(f"\nError: {e}")
            input("Press Enter to continue...")


def display_provider_details(client, provider):
    """Display detailed information about a specific provider"""
    spec = provider.get('Spec', {})
    metadata_info = provider.get('MetaData', {})
    
    print("\n" + "="*60)
    print(f"PROVIDER DETAILS: {spec.get('Name', 'Unknown')}")
    print("="*60)
    
    print(f"UUID: {metadata_info.get('UUID', 'N/A')}")
    print(f"Name: {spec.get('Name', 'N/A')}")
    print(f"Type: {spec.get('Type', 'Unknown')}")
    print(f"Version: {spec.get('Version', 'N/A')}")
    
    # Show type-specific information
    if 'AOSAccessInfo' in spec:
        aos_info = spec['AOSAccessInfo']
        print(f"\nAOS/Prism Information:")
        print(f"  Address: {aos_info.get('IPorFQDN', 'N/A')}")
        print(f"  Port: {aos_info.get('Port', 'N/A')}")
        print(f"  Username: {aos_info.get('Username', 'N/A')}")
        if 'ClusterUUID' in spec:
            print(f"  Cluster UUID: {spec['ClusterUUID']}")
    
    # Additional provider type handling...
    print("\n" + "-"*60)




def prepare_plan(client, plan_uuid, vms, guest_prep_mode="auto", 
                 install_ngt=True, uninstall_guest_tools=True, skip_ip_retention=False):
    """Prepare VMs for migration
    
    Args:
        client: MoveAPIClient instance
        plan_uuid: Plan UUID
        vms: List of VM objects with UUID and VMId
        guest_prep_mode: "auto" or "manual"
        install_ngt: Install Nutanix Guest Tools on target VMs (default: True)
        uninstall_guest_tools: Uninstall VMware Tools/Hyper-V IC (default: True)
        skip_ip_retention: Skip IP address retention (default: False)
    
    Returns:
        True if successful, False otherwise
    """
    print(f"\n{'='*60}")
    print(f"STEP: Preparing VMs for Migration")
    print(f"{'='*60}")
    print(f"Prep Mode: {guest_prep_mode}")
    
    # Build query parameters
    query_params = []
    if uninstall_guest_tools:
        query_params.append("UninstallGuestTools=true")
        print(f"✅ Will uninstall existing guest tools (VMware Tools/Hyper-V IC)")
    if install_ngt:
        query_params.append("InstallNGT=true")
        print(f"✅ Will install Nutanix Guest Tools (NGT)")
    if skip_ip_retention:
        query_params.append("SkipIPRetention=true")
        print(f"⚠️  IP retention will be skipped")
    
    # Build full URL with query parameters
    base_prepare_url = urljoin(client.base_url, f"/move/v2/plans/{plan_uuid}/prepare")
    if query_params:
        prepare_url = f"{base_prepare_url}?{'&'.join(query_params)}"
    else:
        prepare_url = base_prepare_url
    
    # Build VMs list for prepare payload
    vm_list = []
    for vm in vms:
        vm_list.append({
            "UUID": vm.get('UUID'),
            "VMId": vm.get('VMId')
        })
    
    payload = {
        "GuestPrepMode": guest_prep_mode,
        "VMs": vm_list
    }
    
    print(f"\nSending prepare request...")
    try:
        response = client.session.post(prepare_url, json=payload, timeout=(10, 120))
        
        if response.status_code in [200, 202]:
            result = response.json()
            print(f"✅ Prepare request submitted successfully")
            
            # If manual mode, display scripts
            if guest_prep_mode == "manual":
                guest_script = result.get('Status', {}).get('Result', {}).get('GuestScript', {})
                if guest_script:
                    print(f"\n⚠️  MANUAL MODE: You must run the following scripts on your VMs:")
                    
                    linux_script = guest_script.get('LinuxGuestScript')
                    windows_script = guest_script.get('WindowsGuestScript')
                    
                    if linux_script:
                        print(f"\n📜 Linux Script:\n{linux_script[:500]}...")
                    if windows_script:
                        print(f"\n📜 Windows Script:\n{windows_script[:500]}...")
                    
                    print(f"\n⚠️  After running scripts on VMs, press Enter to continue...")
                    input()
            
            return True
        else:
            print(f"❌ Prepare failed: HTTP {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Exception during prepare: {e}")
        return False


def check_readiness(client, plan_uuid):
    """Perform readiness checks on migration plan
    
    Args:
        client: MoveAPIClient instance
        plan_uuid: Plan UUID
    
    Returns:
        True if all checks passed, False otherwise
    """
    print(f"\n{'='*60}")
    print(f"STEP: Checking Migration Readiness")
    print(f"{'='*60}")
    
    readiness_url = urljoin(client.base_url, f"/move/v2/plans/{plan_uuid}/readiness")
    
    print(f"\nRunning readiness checks...")
    try:
        response = client.session.post(readiness_url, json={}, timeout=(10, 60))
        
        if response.status_code == 200:
            result = response.json()
            status = result.get('Status', {})
            
            passed = status.get('Passed', []) or []
            failed = status.get('Failed', []) or []
            
            print(f"\n✅ Readiness Check Results:")
            print(f"   Passed: {len(passed)} checks")
            print(f"   Failed: {len(failed)} checks")
            
            if passed and len(passed) > 0:
                print(f"\n✅ Passed Checks:")
                for check in passed[:5]:  # Show first 5
                    print(f"   - {check.get('CheckType')}: {check.get('Message')}")
                if len(passed) > 5:
                    print(f"   ... and {len(passed) - 5} more")
            
            if failed and len(failed) > 0:
                print(f"\n❌ Failed Checks:")
                for check in failed:
                    print(f"   - {check.get('CheckType')}: {check.get('Message')}")
                return False
            
            return True
        else:
            print(f"❌ Readiness check failed: HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Exception during readiness check: {e}")
        return False


def start_migration(client, plan_uuid, snapshot_frequency=None):
    """Start the migration plan
    
    Args:
        client: MoveAPIClient instance
        plan_uuid: Plan UUID
        snapshot_frequency: Optional snapshot frequency in minutes
    
    Returns:
        True if successful, False otherwise
    """
    print(f"\n{'='*60}")
    print(f"STEP: Starting Migration Plan")
    print(f"{'='*60}")
    
    start_url = urljoin(client.base_url, f"/move/v2/plans/{plan_uuid}/start")
    
    payload = {}
    if snapshot_frequency:
        payload = {
            "Spec": {
                "Frequency": snapshot_frequency
            }
        }
        print(f"Snapshot frequency: {snapshot_frequency} minutes")
    
    print(f"\nStarting migration...")
    try:
        response = client.session.post(start_url, json=payload, timeout=(10, 60))
        
        if response.status_code in [200, 202]:
            print(f"✅ Migration started successfully")
            print(f"\n⏳ Migration is now in progress...")
            print(f"   Data sync will begin and VMs will eventually reach 'Cutover Ready' state")
            print(f"   This can take several minutes to hours depending on VM size")
            return True
        else:
            print(f"❌ Start migration failed: HTTP {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Exception starting migration: {e}")
        return False


def monitor_workloads(client, plan_uuid):
    """Monitor workload status
    
    Args:
        client: MoveAPIClient instance
        plan_uuid: Plan UUID
    
    Returns:
        List of workloads with their current state
    """
    print(f"\n{'='*60}")
    print(f"STEP: Checking Workload Status")
    print(f"{'='*60}")
    
    workloads_url = urljoin(client.base_url, f"/move/v2/plans/{plan_uuid}/workloads/list")
    
    try:
        response = client.session.post(workloads_url, json={}, timeout=(10, 30))
        
        if response.status_code == 200:
            result = response.json()
            workloads = result.get('Entities', [])
            
            print(f"\n📊 Workload Status:")
            for i, workload in enumerate(workloads, 1):
                metadata = workload.get('MetaData', {})
                status = workload.get('Status', {})
                
                vm_name = metadata.get('Name', 'Unknown')
                state = metadata.get('StateString', metadata.get('StatusString', 'Unknown'))
                progress = status.get('PercentageComplete', 0)
                
                print(f"   {i}. {vm_name}")
                print(f"      State: {state}")
                print(f"      Progress: {progress}%")
            
            return workloads
        else:
            print(f"❌ Failed to get workload status: HTTP {response.status_code}")
            return []
            
    except Exception as e:
        print(f"❌ Exception monitoring workloads: {e}")
        return []


def perform_workload_action(client, plan_uuid, workload_uuid, action):
    """Perform action on a workload (test, cutover, etc.)
    
    Args:
        client: MoveAPIClient instance
        plan_uuid: Plan UUID
        workload_uuid: Workload UUID
        action: Action to perform (test, retest, undotest, cutover, etc.)
    
    Returns:
        True if successful, False otherwise
    """
    print(f"\n{'='*60}")
    print(f"STEP: Performing Workload Action: {action.upper()}")
    print(f"{'='*60}")
    
    action_url = urljoin(client.base_url, f"/move/v2/plans/{plan_uuid}/workloads/{workload_uuid}/action")
    
    payload = {
        "Spec": {
            "Action": action
        }
    }
    
    print(f"\nSubmitting {action} action...")
    try:
        response = client.session.post(action_url, json=payload, timeout=(10, 60))
        
        if response.status_code in [200, 202]:
            print(f"✅ {action.capitalize()} action submitted successfully")
            
            if action == "test":
                print(f"\n📝 Test migration initiated:")
                print(f"   - VM will boot on target cluster")
                print(f"   - Source VM remains running")
                print(f"   - You can verify functionality on target")
                print(f"   - Use 'undotest' to rollback when done")
            elif action == "cutover":
                print(f"\n📝 Cutover initiated:")
                print(f"   - Source VM will be shut down")
                print(f"   - Target VM will be powered on")
                print(f"   - Migration will be complete")
            
            return True
        else:
            print(f"❌ Action failed: HTTP {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Exception performing action: {e}")
        return False


def test_migration_workflow(client, plan_uuid, selected_vms):
    """Interactive test migration workflow
    
    Args:
        client: MoveAPIClient instance
        plan_uuid: Plan UUID
        selected_vms: List of selected VM objects
    
    Returns:
        None
    """
    print(f"\n{'='*60}")
    print(f"TEST MIGRATION WORKFLOW")
    print(f"{'='*60}")
    print(f"\nYou can now proceed with the test migration workflow:")
    print(f"1. Prepare VMs")
    print(f"2. Check readiness")
    print(f"3. Start migration")
    print(f"4. Monitor progress")
    print(f"5. Perform test cutover")
    
    while True:
        print(f"\n{'='*60}")
        choice = input("\nDo you want to proceed with test migration workflow? (yes/no): ").strip().lower()
        
        if choice in ['no', 'n']:
            print(f"\n✅ Skipping test migration workflow")
            print(f"   You can perform these steps later via Move UI")
            return
        elif choice not in ['yes', 'y']:
            print(f"❌ Please enter 'yes' or 'no'")
            continue
        
        break
    
    # Step 1: Prepare
    prep_mode = "auto"
    prep_choice = input(f"\nVM Preparation mode (auto/manual) [auto]: ").strip().lower()
    if prep_choice == "manual":
        prep_mode = "manual"
    
    # Ask about NGT and guest tools
    print(f"\n📝 Guest Tools Configuration:")
    print(f"   1. Install Nutanix Guest Tools (NGT) - Recommended")
    print(f"   2. Uninstall existing guest tools (VMware Tools/Hyper-V IC)")
    print(f"   3. Retain IP addresses")
    
    install_ngt = True
    ngt_choice = input(f"\nInstall NGT on target VMs? (yes/no) [yes]: ").strip().lower()
    if ngt_choice in ['no', 'n']:
        install_ngt = False
    
    uninstall_tools = True
    uninstall_choice = input(f"Uninstall existing guest tools? (yes/no) [yes]: ").strip().lower()
    if uninstall_choice in ['no', 'n']:
        uninstall_tools = False
    
    skip_ip = False
    ip_choice = input(f"Skip IP retention? (yes/no) [no]: ").strip().lower()
    if ip_choice in ['yes', 'y']:
        skip_ip = True
    
    if not prepare_plan(client, plan_uuid, selected_vms, prep_mode, 
                       install_ngt, uninstall_tools, skip_ip):
        print(f"\n❌ Prepare failed. Workflow stopped.")
        input("\nPress Enter to continue...")
        return
    
    input("\nPress Enter to continue to readiness check...")
    
    # Step 2: Readiness check
    if not check_readiness(client, plan_uuid):
        print(f"\n❌ Readiness check failed. Please fix issues and try again via Move UI.")
        input("\nPress Enter to continue...")
        return
    
    input("\nPress Enter to continue to start migration...")
    
    # Step 3: Start migration
    freq_input = input(f"\nSnapshot frequency in minutes (press Enter to skip): ").strip()
    snapshot_freq = None
    if freq_input.isdigit():
        snapshot_freq = int(freq_input)
    
    if not start_migration(client, plan_uuid, snapshot_freq):
        print(f"\n❌ Failed to start migration. Workflow stopped.")
        input("\nPress Enter to continue...")
        return
    
    print(f"\n⏳ Migration is now running. VMs need to reach 'Cutover Ready' state.")
    print(f"   This typically takes several minutes to hours.")
    print(f"\n💡 You can:")
    print(f"   - Check status now (may still be syncing)")
    print(f"   - Come back later via Move UI")
    print(f"   - Run test/cutover actions when ready")
    
    check_now = input(f"\nCheck workload status now? (yes/no): ").strip().lower()
    if check_now in ['yes', 'y']:
        workloads = monitor_workloads(client, plan_uuid)
        
        if not workloads:
            print(f"\n⚠️  No workloads found or unable to retrieve status")
        else:
            print(f"\n💡 To perform test or cutover actions:")
            print(f"   1. Wait for VMs to reach 'Cutover Ready' state")
            print(f"   2. Use Move UI or re-run this script with action options")
    
    print(f"\n✅ Test migration workflow initiated!")
    print(f"\n📝 Next steps:")
    print(f"   1. Wait for data sync to complete (check Move UI)")
    print(f"   2. When ready, use Move UI to perform Test or Cutover")
    print(f"   3. Test: Boots VM on target (source stays running)")
    print(f"   4. Cutover: Final migration (shuts down source)")
    
    input("\nPress Enter to continue...")


def main():
    parser = argparse.ArgumentParser(
        description="Interactive Nutanix Move API migration PLAN creator (creates plans, does not migrate)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive mode (default)
  python3 move_plan_create.py --server 10.38.18.23 --username nutanix
  
  # Non-interactive mode (original behavior)
  python3 move_plan_create.py --server 10.38.18.23 --username nutanix --no-interactive
        """
    )
    
    parser.add_argument("--server", help="Move server IP or FQDN")
    parser.add_argument("--port", type=int, default=443, help="Move server port (default: 443)")
    parser.add_argument("--username", help="Move username")
    parser.add_argument("--password", help="Move password (will prompt if not provided)")
    parser.add_argument("--verify-ssl", action="store_true", help="Verify SSL certificates")
    parser.add_argument("--no-interactive", action="store_true", help="Disable interactive mode")
    
    args = parser.parse_args()
    
    # Get inputs interactively if not provided
    server = args.server or input("Move server IP/FQDN: ")
    username = args.username or input("Username: ")
    password = args.password or getpass.getpass("Password: ")
    
    try:
        print(f"Connecting to Move API at {server}:{args.port}...")
        client = MoveAPIClient(server, username, password, args.port, args.verify_ssl)
        
        if args.no_interactive:
            # Simple provider listing for non-interactive mode
            providers, metadata = client.list_providers()
            if providers:
                print(f"\nFound {len(providers)} provider(s):")
                display_providers_table(providers)
            else:
                print("No providers found.")
        else:
            # Interactive mode
            print("Starting interactive migration manager...")
            time.sleep(1)
            interactive_menu(client)
        
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)



def prompt_for_test_network(source_name, target_net, target_networks):
    """Prompt user for test network (must be different from production)
    
    Returns:
        Test network UUID or None if skipped
    """
    print(f"\n📝 Test Network for '{source_name}':")
    print(f"   Test network must be DIFFERENT from production network")
    print(f"   (Press Enter to skip test actions)")
    
    test_input = input(f"Test Network [number, UUID, name, or Enter to skip]: ").strip()
    
    if not test_input:
        print("⏭️  Skipping test network (test actions will not be available)")
        return None
    
    # Parse input
    if test_input.isdigit():
        # Number selection
        idx = int(test_input) - 1
        if 0 <= idx < len(target_networks):
            test_uuid = target_networks[idx]['UUID']
            test_name = target_networks[idx]['Name']
            if test_uuid == target_net:
                print(f"❌ Test network cannot be same as production network")
                return None
            print(f"✅ Test network: {test_name}")
            return test_uuid
        else:
            print(f"❌ Invalid number")
            return None
    elif '-' in test_input:
        # UUID
        if test_input == target_net:
            print(f"❌ Test network cannot be same as production network")
            return None
        print(f"✅ Test network UUID: {test_input}")
        return test_input
    else:
        # Network name
        for net in target_networks:
            if net['Name'].lower() == test_input.lower():
                if net['UUID'] == target_net:
                    print(f"❌ Test network cannot be same as production network")
                    return None
                print(f"✅ Test network: {net['Name']}")
                return net['UUID']
        print(f"❌ Network '{test_input}' not found")
        return None


def migration_plan_workflow(client, source_uuid, target_uuid, selected_vm_names, source_name, target_name):
    """Complete migration plan workflow with credential mapping and network setup
    
    Args:
        client: MoveAPIClient instance
        source_info: Source provider info dict with ProviderUUID and optional AOSProviderAttrs
        target_uuid: Target provider UUID
        selected_vm_names: List of selected VM names
        source_name: Source provider name
        target_name: Target provider name
    """
    
    # Initialize plan_name to avoid undefined variable errors
    plan_name = "Unknown Plan"
    
    clear_screen()
    display_header()
    print("MIGRATION PLAN CREATION (NO ACTUAL MIGRATION)")
    print("=" * 50)
    
    print(f"Source: {source_name}")
    print(f"Target: {target_name}")
    print(f"Selected VMs: {len(selected_vm_names)}")
    for i, vm_name in enumerate(selected_vm_names[:10], 1):
        print(f"  {i}. {vm_name}")
    if len(selected_vm_names) > 10:
        print(f"  ... and {len(selected_vm_names) - 10} more VMs")
    
    print("\n" + "-" * 50)
    
    # Step 1: Get target provider details (Cluster and Container UUIDs)
    try:
        target_details = client.get_provider_details(target_uuid)
        
        # Get the correct Type from Spec
        provider_type = target_details.get('Spec', {}).get('Type', 'Unknown')
        print(f"Target Provider Type: {provider_type}")
        
        # Extract target configuration based on provider type
        target_info = {"ProviderUUID": target_uuid}
        
        if provider_type in ['AOS_PC', 'AOS_AHV_PE']:
            # For AOS targets, we need ClusterUUID and ContainerUUID
            clusters = target_details.get('Spec', {}).get('AOSProperties', {}).get('Clusters', [])
            # Get containers from the first cluster (since this is typically single-cluster)
            containers = clusters[0].get('Containers', []) if clusters else []
            
            if clusters:
                # Auto-select if only one cluster available
                if len(clusters) == 1:
                    selected_cluster = clusters[0]
                    cluster_uuid = selected_cluster.get('UUID')
                    print(f"\n✅ Auto-selected cluster: {selected_cluster.get('Name')} ({cluster_uuid})")
                else:
                    print(f"\nTarget provider '{target_name}' has multiple clusters.")
                    print(f"Select which cluster to migrate to:")
                    for i, cluster in enumerate(clusters, 1):
                        print(f"  {i}. {cluster.get('Name', 'Unnamed')} ({cluster.get('UUID', 'No UUID')})")
                    
                    while True:
                        try:
                            choice = input("Select target cluster number: ").strip()
                            cluster_idx = int(choice) - 1
                            if 0 <= cluster_idx < len(clusters):
                                selected_cluster = clusters[cluster_idx]
                                cluster_uuid = selected_cluster.get('UUID')
                                print(f"Selected cluster: {selected_cluster.get('Name')} ({cluster_uuid})")
                                break
                            else:
                                print(f"Please enter a number between 1 and {len(clusters)}")
                        except ValueError:
                            print("Please enter a valid number")
            else:
                print("⚠️  No clusters found in target provider")
                cluster_uuid = input("Enter target Cluster UUID manually (or press Enter to skip): ").strip()
            
            if containers:
                # Auto-select if only one container available
                if len(containers) == 1:
                    selected_container = containers[0]
                    container_uuid = selected_container.get('UUID')
                    print(f"✅ Auto-selected container: {selected_container.get('Name')} ({container_uuid})")
                else:
                    print(f"\nSelect target storage container:")
                    for i, container in enumerate(containers, 1):
                        print(f"  {i}. {container.get('Name', 'Unnamed')} ({container.get('UUID', 'No UUID')})")
                    
                    while True:
                        try:
                            choice = input("Select target storage container number: ").strip()
                            container_idx = int(choice) - 1
                            if 0 <= container_idx < len(containers):
                                selected_container = containers[container_idx]
                                container_uuid = selected_container.get('UUID')
                                print(f"Selected container: {selected_container.get('Name')} ({container_uuid})")
                                break
                            else:
                                print(f"Please enter a number between 1 and {len(containers)}")
                        except ValueError:
                            print("Please enter a valid number")
            else:
                print("⚠️  No storage containers found in target provider")
                container_uuid = input("Enter target Container UUID manually (or press Enter to skip): ").strip()
            
            # Build AOS provider attributes
            if cluster_uuid or container_uuid:
                target_info["AOSProviderAttrs"] = {}
                if cluster_uuid:
                    target_info["AOSProviderAttrs"]["ClusterUUID"] = cluster_uuid
                if container_uuid:
                    target_info["AOSProviderAttrs"]["ContainerUUID"] = container_uuid
        
        print(f"✅ Target configuration ready")
        
    except Exception as e:
        print(f"❌ Error getting target details: {e}")
        print("Proceeding with basic target configuration...")
        target_info = {"ProviderUUID": target_uuid}
    

    # Step 1b: Get source provider details for source cluster UUID
    try:
        source_details = client.get_provider_details(source_uuid)
        source_provider_type = source_details.get('Spec', {}).get('Type', 'Unknown')
        print(f"Source Provider Type: {source_provider_type}")
        
        # Initialize SourceInfo
        source_info = {"ProviderUUID": source_uuid}
        
        # For AOS providers, add cluster UUID to SourceInfo
        if source_provider_type in ['AOS_PC', 'AOS_AHV_PE']:
            source_clusters = source_details.get('Spec', {}).get('AOSProperties', {}).get('Clusters', [])
            if source_clusters:
                # Use the first cluster
                source_cluster_uuid = source_clusters[0].get('UUID')
                if source_cluster_uuid:
                    source_info["AOSProviderAttrs"] = {"ClusterUUID": source_cluster_uuid}
                    print(f"✅ Source Cluster UUID: {source_cluster_uuid}")
                else:
                    print(f"⚠️  No source cluster UUID found")
            else:
                print(f"⚠️  No source clusters found")
        
        
    except Exception as e:
        print(f"❌ Error getting source details: {e}")
        print("Using basic source configuration...")
        source_info = {"ProviderUUID": source_uuid}

    # Step 2: Get VM objects for the selected names
    print("\nStep 2: Retrieving VM details...")
    try:
        all_vms, _, _ = client.list_provider_vms(source_uuid, limit=1000)
        selected_vms = []
        
        for vm_name in selected_vm_names:
            for vm in all_vms:
                if get_vm_name(vm) == vm_name:
                    selected_vms.append(vm)
                    break
        
        print(f"✅ Found {len(selected_vms)}/{len(selected_vm_names)} VMs")
        
        if len(selected_vms) != len(selected_vm_names):
            print("⚠️  Some VMs could not be found. Continuing with available VMs.")
            
    except Exception as e:
        print(f"❌ Error getting VM details: {e}")
        input("Press Enter to continue...")
        return
    
    
    # Step 3: Network Mapping Configuration
    print("\nStep 3: Network mapping configuration...")
    print("Note: Network mappings are required when VMs have networks attached")
    
    network_mappings = []
    
    # Extract unique networks from selected VMs
    vm_networks = set()
    for vm in selected_vms:
        networks = vm.get('Networks', [])
        for network in networks:
            network_id = network.get('ID')
            network_name = network.get('Name')
            if network_id:
                vm_networks.add((network_id, network_name))
    
    print(f"\nFound {len(vm_networks)} unique networks used by selected VMs:")
    for net_id, net_name in vm_networks:
        print(f"  - {net_name} ({net_id})")
    
    if vm_networks:
        print("\nAutomatic network mapping options:")
        print("1. Auto-map to same network names on target (recommended)")  
        print("2. Manual network mapping configuration")
        print("3. Skip network mapping (may cause errors)")
        
        mapping_choice = input("Choose option (1/2/3): ").strip()
        
        if mapping_choice == "1":
            # Auto-map to same network names
            print("\nAuto-mapping networks by name...")
            
            # Get target networks
            try:
                target_networks = target_details.get('Spec', {}).get('AOSProperties', {}).get('Clusters', [{}])[0].get('Networks', [])
                target_network_map = {net['Name']: net['UUID'] for net in target_networks}
                
                print(f"Available target networks: {list(target_network_map.keys())}")
                
                for source_id, source_name in vm_networks:
                    if source_name in target_network_map:
                        mapping = {
                            "SourceNetworkID": source_id,
                            "TargetNetworkID": target_network_map[source_name]
                        }
                    # Prompt for test network
                    test_net_uuid = prompt_for_test_network(source_name, target_net, target_networks)
                    if test_net_uuid:
                        mapping["TestNetworkID"] = test_net_uuid
                    
                        network_mappings.append(mapping)
                        print(f"✅ Mapped: {source_name} -> {source_name}")
                    else:
                        print(f"⚠️  No matching target network found for '{source_name}'")
                        
            except Exception as e:
                print(f"❌ Error getting target networks: {e}")
                print("Falling back to manual configuration...")
                mapping_choice = "2"
        
        if mapping_choice == "2":
            # Manual mapping with numbered selection
            print("\nManual network mapping configuration:")
            
            # Show available target networks with numbers
            try:
                target_networks = target_details.get('Spec', {}).get('AOSProperties', {}).get('Clusters', [{}])[0].get('Networks', [])
                if target_networks:
                    print("\nAvailable target networks:")
                    for i, net in enumerate(target_networks, 1):
                        print(f"  {i}. {net.get('Name')} (UUID: {net.get('UUID')})")
                    print()
                else:
                    print("⚠️  No target networks found")
                    target_networks = []
            except:
                target_networks = []
                pass
            
            for source_id, source_name in vm_networks:
                while True:
                    target_net = input(f"Target Network for '{source_name}' [number, UUID, or 'auto']: ").strip()
                    
                    if target_net.lower() == 'auto':
                        # Try auto-mapping by name
                        try:
                            target_network_map = {net['Name']: net['UUID'] for net in target_networks}
                            if source_name in target_network_map:
                                target_net = target_network_map[source_name]
                                print(f"✅ Auto-mapped: {source_name} -> {source_name} ({target_net})")
                                mapping = {
                                    "SourceNetworkID": source_id,
                                    "TargetNetworkID": target_net
                                }
                            # Prompt for test network
                            test_net_uuid = prompt_for_test_network(source_name, target_net, target_networks)
                            if test_net_uuid:
                                mapping["TestNetworkID"] = test_net_uuid
                            
                                network_mappings.append(mapping)
                                break
                            else:
                                print(f"❌ No matching network named '{source_name}' on target")
                                print("   Please enter a network number, UUID, or 'auto'")
                                continue
                        except:
                            print("❌ Could not auto-map, please enter number or UUID")
                            continue
                    
                    elif target_net.isdigit():
                        # User entered a number - select from the list
                        net_idx = int(target_net) - 1
                        if 0 <= net_idx < len(target_networks):
                            selected_net = target_networks[net_idx]
                            target_net = selected_net.get('UUID')
                            net_name = selected_net.get('Name')
                            print(f"✅ Selected: {net_name} ({target_net})")
                            mapping = {
                                "SourceNetworkID": source_id,
                                "TargetNetworkID": target_net
                            }
                        # Prompt for test network
                        test_net_uuid = prompt_for_test_network(source_name, target_net, target_networks)
                        if test_net_uuid:
                            mapping["TestNetworkID"] = test_net_uuid
                        
                            network_mappings.append(mapping)
                            break
                        else:
                            print(f"❌ Invalid number. Please enter 1-{len(target_networks)}")
                            continue
                    
                    elif target_net:
                        # Check if input looks like a UUID (has dashes) or a name
                        if '-' not in target_net:
                            # Likely a network name, try to look it up
                            print(f"⚠️  '{target_net}' looks like a network name, not a UUID")
                            try:
                                target_network_map = {net['Name']: net['UUID'] for net in target_networks}
                                if target_net in target_network_map:
                                    resolved_uuid = target_network_map[target_net]
                                    print(f"   Found network: {target_net} -> {resolved_uuid}")
                                    confirm = input(f"   Use this network? (y/n): ").strip().lower()
                                    if confirm == 'y':
                                        target_net = resolved_uuid
                                        print(f"✅ Mapped: {source_name} -> {target_net}")
                                        mapping = {
                                            "SourceNetworkID": source_id,
                                            "TargetNetworkID": target_net
                                        }
                                    # Prompt for test network
                                    test_net_uuid = prompt_for_test_network(source_name, target_net, target_networks)
                                    if test_net_uuid:
                                        mapping["TestNetworkID"] = test_net_uuid
                                    
                                        network_mappings.append(mapping)
                                        break
                                    else:
                                        print("   Please enter the UUID or type 'auto'")
                                        continue
                                else:
                                    print(f"   Network '{target_net}' not found. Please enter UUID.")
                                    continue
                            except:
                                print("   Could not resolve network name. Please enter UUID.")
                                continue
                        else:
                            # Looks like a UUID, accept it
                            mapping = {
                                "SourceNetworkID": source_id,
                                "TargetNetworkID": target_net
                            }
                        # Prompt for test network
                        test_net_uuid = prompt_for_test_network(source_name, target_net, target_networks)
                        if test_net_uuid:
                            mapping["TestNetworkID"] = test_net_uuid
                        
                            network_mappings.append(mapping)
                            print(f"✅ Added mapping: {source_name} -> {target_net}")
                            break
                    else:
                        print(f"⚠️  Network mapping required! Enter UUID or type 'auto'")
                        continue
        
        elif mapping_choice == "3":
            print("⚠️  Skipping network mapping - this may cause API errors")
            
        print(f"\n✅ Configured {len(network_mappings)} network mappings")
    else:
        print("No networks found on selected VMs - no mapping needed")
    
    # Step 4: Load credential mapping
    print("\nStep 4: Loading VM credential mapping...")
    credentials = read_credential_mapping()
    
    if not credentials:
        print("❌ No credentials loaded. Migration plan creation cancelled.")
        input("Press Enter to continue...")
        return
    
    # Step 5: Get plan name from user  
    print("\nStep 5: Migration plan configuration...")
    while True:
        plan_name = input("Enter migration plan name: ").strip()
        if plan_name:
            break
        print("❌ Plan name cannot be empty. Please try again.")
    
    
    # Step 4: Create the migration plan
    print(f"\nStep 4: Creating migration plan '{plan_name}'...")
    
    
    plan_uuid = create_migration_plan(
        client, 
        plan_name, 
        source_info, 
        target_info,  # Pass the complete target info instead of just UUID
        selected_vms,  # Use selected_vms instead of selected_vm_objects
        credentials,
        network_mappings
    )
    
    
    # Step 5: Display results
    print("\n" + "=" * 50)
    print("MIGRATION PLAN CREATION RESULTS")
    print("=" * 50)
    
    if plan_uuid:
        print(f"✅ Migration plan '{plan_name}' created successfully!")
        print(f"🆔 Plan UUID: {plan_uuid}")
        print(f"📊 Plan includes {len(selected_vms)} VMs")
        print(f"📤 Source: {source_name}")
        print(f"📥 Target: {target_name}")
        
        print("\n" + "=" * 50)
        print("ℹ️  NOTE: This script only CREATES migration plans.")
        print("   No VMs have been migrated yet.")
        
        print("\n📝 NEXT STEPS (Manual):")
        print("1. 🔍 Review the migration plan in the Move UI")
        print("2. ✅ Perform readiness checks on selected VMs")
        print("3. 🔧 Prepare VMs for migration (install agents, etc.)")
        print("4. ▶️  Execute the migration when ready")
        print("5. ✔️  Verify migration success and cleanup")
        
        # Optionally proceed with test migration workflow
        test_migration_workflow(client, plan_uuid, selected_vms)
    else:
        print("\n❌ Migration plan creation failed!")
        print(f"Plan Name: {plan_name}")
        
    input("\nPress Enter to continue...")


def read_credential_mapping(csv_file_path="./credential-mapping.csv"):
    """Read VM credential mapping from CSV file
    
    Args:
        csv_file_path: Path to CSV file with format: servername,username,password
        
    Returns:
        Dictionary mapping server names to credentials
    """
    credentials = {}
    
    # Check if file exists, if not prompt user
    if not os.path.exists(csv_file_path):
        print(f"❌ Credential mapping file '{csv_file_path}' not found")
        
        while True:
            user_path = input("Enter path to credential mapping CSV file (or 'skip' to continue without credentials): ").strip()
            
            if user_path.lower() == 'skip':
                print("⚠️  Continuing without credentials - VMs may not have login information")
                return {}
            
            if os.path.exists(user_path):
                csv_file_path = user_path
                break
            else:
                print(f"❌ File '{user_path}' not found. Please try again.")
    
    try:
        with open(csv_file_path, 'r', newline='', encoding='utf-8') as file:
            import csv
            reader = csv.reader(file)
            
            # Check if first row is a header or data
            first_row = next(reader, None)
            if not first_row:
                return credentials
            
            # If first row looks like a header (contains "servername", "username", "password"), skip it
            # Otherwise, process it as data
            if first_row[0].lower() in ['servername', 'server', 'vm', 'vmname', 'hostname']:
                # It's a header, start from row 2
                row_num = 2
            else:
                # It's data, process it first
                if len(first_row) >= 3:
                    server_name = first_row[0].strip()
                    username = first_row[1].strip()
                    password = first_row[2].strip()
                    if server_name and username and password:
                        credentials[server_name] = {
                            'username': username,
                            'password': password
                        }
                        print(f"  Loaded credentials for: {server_name}")
                row_num = 2
            
            # Process remaining data rows
            for row in reader:
                if len(row) >= 3:
                    server_name = row[0].strip()
                    username = row[1].strip()
                    password = row[2].strip()
                    
                    if server_name and username and password:
                        credentials[server_name] = {
                            'username': username,
                            'password': password
                        }
                        print(f"  Loaded credentials for: {server_name}")
                    else:
                        print(f"  Warning: Incomplete data on row {row_num}")
                else:
                    print(f"  Warning: Invalid format on row {row_num}")
                row_num += 1
        
        print(f"✅ Loaded credentials for {len(credentials)} VMs from {csv_file_path}")
        return credentials
        
    except Exception as e:
        print(f"❌ Error reading credential mapping file: {e}")
        return {}


def create_migration_plan(client, plan_name, source_info, target_info, selected_vms, vm_credentials, network_mappings=None):
    """Create a migration plan using the Move API with full configuration
    
    Args:
        client: MoveAPIClient instance
        plan_name: Name for the migration plan
        source_info: Source provider info dict with ProviderUUID and optional AOSProviderAttrs
        target_info: Target provider info dict with ProviderUUID and optional AOSProviderAttrs
        selected_vms: List of selected VM objects
        vm_credentials: Dictionary mapping VM names to credentials
        network_mappings: List of network mapping dicts (optional)
        
    Returns:
        Created plan UUID or None if failed
    """
    print(f"Creating migration plan: {plan_name}")
    print(f"Source: {source_info.get('ProviderUUID', 'Unknown')}")
    print(f"Target: {target_info.get('ProviderUUID', 'Unknown')}")
    if target_info.get('AOSProviderAttrs'):
        aos_attrs = target_info['AOSProviderAttrs']
        if aos_attrs.get('ClusterUUID'):
            print(f"Target Cluster: {aos_attrs['ClusterUUID']}")
        if aos_attrs.get('ContainerUUID'):
            print(f"Target Container: {aos_attrs['ContainerUUID']}")
    print(f"VMs: {len(selected_vms)}")
    if network_mappings:
        print(f"Network Mappings: {len(network_mappings)}")
        for mapping in network_mappings:
            print(f"  {mapping['SourceNetworkID']} -> {mapping['TargetNetworkID']}")
    
    # Build VM list with references
    vm_workloads = []
    vms_with_credentials = 0
    
    for vm in selected_vms:
        vm_name = get_vm_name(vm)
        vm_uuid = get_vm_property(vm, 'VMUuid', 'UUID', 'VmID', default='')
        vm_id = get_vm_property(vm, 'VmID', 'VMUuid', 'RecID', default='')
        
        # Create VM workload entry
        vm_workload = {
            "VMReference": {
                "UUID": vm_uuid,
                "VMID": str(vm_id) if vm_id else vm_uuid
            },
            "VMCustomizeType": "replicate",  # Default customization
            "GuestPrepMode": "auto"     # Automatic guest preparation (lowercase)
        }
        
        # Add credentials if available
        if vm_name in vm_credentials:
            creds = vm_credentials[vm_name]
            vm_workload["VMCustomizationConfig"] = {
                "GuestCredentials": {
                    "UUID": vm_uuid,
                    "VMId": str(vm_id) if vm_id else vm_uuid,
                    "UserName": creds['username'],
                    "Password": creds['password']
                }
            }
            vms_with_credentials += 1
            print(f"  ✅ VM '{vm_name}' - credentials mapped")
        else:
            print(f"  ⚠️  VM '{vm_name}' - no credentials found in mapping file")
        
        vm_workloads.append(vm_workload)
    
    print(f"VMs with credentials: {vms_with_credentials}/{len(selected_vms)}")
    
    # Build migration plan payload
    plan_payload = {
        "Spec": {
            "Name": plan_name,
            "SourceInfo": source_info,
            "TargetInfo": target_info,  # Use the complete target info
            "Workload": {
                "Type": "VM",
                "VMs": vm_workloads
            },
            "NetworkMappings": network_mappings or []  # Use provided network mappings
        }
    }
    
    try:
        plans_endpoint = "/move/v2/plans"
        full_url = urljoin(client.base_url, plans_endpoint)
        
        print("\n" + "="*50)
        print("Sending migration plan creation request...")
        response = client.session.post(full_url, json=plan_payload, timeout=(10, 120))
        
        print(f"Response Status Code: {response.status_code}")
        
        if response.status_code in [200, 201]:
            result = response.json()
            print(f"\n✅ API RESPONSE (SUCCESS):")
            print(json.dumps(result, indent=2))
            
            plan_uuid = result.get('MetaData', {}).get('UUID')
            plan_status = result.get('Status', {})
            
            if plan_uuid:
                print(f"\n✅ Migration plan created successfully!")
                print(f"Plan UUID: {plan_uuid}")
                print(f"Plan Name: {plan_name}")
                if plan_status:
                    print(f"Status: {plan_status.get('State', 'Unknown')}")
                    
                # Verify the plan was actually created by listing plans
                print(f"\n🔍 Verifying plan creation...")
                try:
                    list_url = urljoin(client.base_url, "/move/v2/plans/list")
                    # Use POST with empty payload to list plans
                    list_response = client.session.post(list_url, json={}, timeout=(10, 30))
                    if list_response.status_code == 200:
                        plans_data = list_response.json()
                        plans = plans_data.get('Entities', [])
                        found_plan = None
                        for plan in plans:
                            if plan.get('MetaData', {}).get('UUID') == plan_uuid:
                                found_plan = plan
                                break
                        
                        if found_plan:
                            # Plan name is in MetaData, not Spec
                            plan_name = found_plan.get('MetaData', {}).get('Name', 'Unknown')
                            # State is in MetaData.StateString or MetaData.StatusString
                            state = found_plan.get('MetaData', {}).get('StateString', 
                                    found_plan.get('MetaData', {}).get('StatusString', 'Unknown'))
                            print(f"✅ Plan verified in Move: {plan_name}")
                            print(f"   State: {state}")
                        else:
                            print(f"⚠️  Plan UUID {plan_uuid} not found in plan list")
                            print(f"   Total plans found: {len(plans)}")
                    else:
                        print(f"⚠️  Could not verify plan (list plans failed: {list_response.status_code})")
                        
                except Exception as verify_e:
                    print(f"⚠️  Could not verify plan creation: {verify_e}")
                    
                return plan_uuid
            else:
                print(f"❌ Plan created but no UUID returned")
                print(f"Response: {json.dumps(result, indent=2)}")
                return None
                
        else:
            print(f"\n❌ API RESPONSE (FAILED):")
            print(f"Status Code: {response.status_code}")
            try:
                error_detail = response.json()
                print(f"Error Detail: {json.dumps(error_detail, indent=2)}")
            except:
                print(f"Raw Error Response: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Exception creating migration plan: {e}")
        return None




if __name__ == "__main__":
    main()



