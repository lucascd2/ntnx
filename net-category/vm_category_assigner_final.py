#!/usr/bin/env python3
"""
VM Network Category Assigner - FINAL WORKING VERSION
Assigns categories to VMs based on network/subnet connections using v3 API.
"""

import sys
import requests
import json
import urllib3
import getpass
import time
from requests.auth import HTTPBasicAuth

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class PrismCentralClient:
    def __init__(self, ip, username, password):
        self.base_url = f"https://{ip}:9440/api"
        self.auth = HTTPBasicAuth(username, password)

class VMNetworkCategoryAssigner:
    def __init__(self, client):
        self.client = client
        
    def get_all_subnets(self):
        """Get all subnets with proper pagination"""
        print("Fetching all subnets...")
        all_subnets = []
        page = 0
        limit = 100
        
        while True:
            try:
                params = {"$page": page, "$limit": limit}
                response = requests.get(
                    f"{self.client.base_url}/networking/v4.2/config/subnets",
                    auth=self.client.auth,
                    verify=False,
                    params=params,
                    timeout=30
                )
                response.raise_for_status()
                
                subnets = response.json().get("data", [])
                if not subnets or len(subnets) < limit:
                    all_subnets.extend(subnets)
                    break
                    
                all_subnets.extend(subnets)
                page += 1
                
            except Exception as e:
                print(f"Error fetching subnets: {e}")
                break
        
        print(f"Found {len(all_subnets)} subnets")
        return all_subnets
    
    def get_ui_visible_categories(self):
        """Get UI-visible category keys only (ADGroup to XYZ-Team)"""
        print("Fetching UI-visible categories...")
        all_categories = []
        page = 0
        limit = 100
        
        while True:
            try:
                params = {"$page": page, "$limit": limit}
                response = requests.get(
                    f"{self.client.base_url}/prism/v4.2/config/categories",
                    auth=self.client.auth,
                    verify=False,
                    params=params,
                    timeout=30
                )
                response.raise_for_status()
                
                categories = response.json().get("data", [])
                if not categories or len(categories) < limit:
                    all_categories.extend(categories)
                    break
                    
                all_categories.extend(categories)
                page += 1
                
            except Exception as e:
                print(f"Error fetching categories: {e}")
                break
        
        # Extract unique keys and filter to UI-visible range
        unique_keys = set()
        for cat in all_categories:
            key = cat.get("key", "")
            if key:
                unique_keys.add(key)
        
        all_keys = sorted(list(unique_keys))
        
        # Find XYZ-Team index (UI cutoff)
        xyz_index = -1
        if "XYZ-Team" in all_keys:
            xyz_index = all_keys.index("XYZ-Team")
        
        ui_visible_keys = all_keys[:xyz_index + 1] if xyz_index >= 0 else all_keys
        print(f"Found {len(ui_visible_keys)} UI-visible category keys")
        
        return ui_visible_keys
    
    def get_existing_values_for_key(self, category_key):
        """Get existing values for a specific category key"""
        print(f"Fetching existing values for category '{category_key}'...")
        all_categories = []
        page = 0
        limit = 100
        
        while True:
            try:
                params = {
                    "$page": page,
                    "$limit": limit,
                    "$filter": f"key eq '{category_key}'"
                }
                response = requests.get(
                    f"{self.client.base_url}/prism/v4.2/config/categories",
                    auth=self.client.auth,
                    verify=False,
                    params=params,
                    timeout=30
                )
                response.raise_for_status()
                
                categories = response.json().get("data", [])
                if not categories or len(categories) < limit:
                    all_categories.extend(categories)
                    break
                    
                all_categories.extend(categories)
                page += 1
                
            except Exception as e:
                print(f"Error fetching category values: {e}")
                break
        
        # Extract unique values
        unique_values = set()
        for cat in all_categories:
            value = cat.get("value", "")
            if value:
                unique_values.add(value)
        
        sorted_values = sorted(list(unique_values))
        print(f"Found {len(sorted_values)} existing values for '{category_key}'")
        
        return sorted_values
    
    def get_vms_on_subnet_v3(self, subnet_id):
        """Get VMs connected to a specific subnet using v3 API"""
        print(f"Finding VMs connected to subnet...")
        
        try:
            # Get all VMs via v3 API
            response = requests.post(
                f"{self.client.base_url}/nutanix/v3/vms/list",
                auth=self.client.auth,
                verify=False,
                json={"length": 500},
                timeout=30
            )
            response.raise_for_status()
            
            all_vms = response.json().get("entities", [])
            matching_vms = []
            
            # Filter VMs connected to our subnet
            for vm in all_vms:
                nics = vm.get("spec", {}).get("resources", {}).get("nic_list", [])
                for nic in nics:
                    subnet_ref = nic.get("subnet_reference", {})
                    if subnet_ref.get("uuid") == subnet_id:
                        matching_vms.append(vm)
                        break
            
            print(f"Found {len(matching_vms)} VMs connected to subnet")
            return matching_vms
            
        except Exception as e:
            print(f"Error finding VMs: {e}")
            return []
    
    def assign_category_to_vm_v3(self, vm_uuid, category_key, category_value):
        """Assign category to VM using v3 API with full metadata preservation"""
        try:
            # Get complete VM data
            response = requests.get(
                f"{self.client.base_url}/nutanix/v3/vms/{vm_uuid}",
                auth=self.client.auth,
                verify=False,
                timeout=30
            )
            response.raise_for_status()
            
            vm_data = response.json()
            
            # Update categories in metadata
            current_categories = vm_data.get("metadata", {}).get("categories", {})
            current_categories[category_key] = category_value
            vm_data["metadata"]["categories"] = current_categories
            
            # Remove read-only status field
            if "status" in vm_data:
                del vm_data["status"]
            
            # Send update with ALL metadata fields
            update_response = requests.put(
                f"{self.client.base_url}/nutanix/v3/vms/{vm_uuid}",
                auth=self.client.auth,
                verify=False,
                json=vm_data,
                timeout=30
            )
            
            if update_response.status_code in [200, 202]:
                return True
            else:
                print(f"  Error {update_response.status_code}: {update_response.text[:100]}")
                return False
                
        except Exception as e:
            print(f"  Error: {e}")
            return False
    
    def run_interactive_assignment(self):
        """Interactive workflow for assigning categories to VMs"""
        
        print("=== VM Network Category Assigner (v3 API) ===")
        
        # Step 1: Get all subnets
        subnets = self.get_all_subnets()
        if not subnets:
            print("No subnets found!")
            return
        
        # Display subnets
        print(f"\nAvailable Subnets:")
        print("-" * 60)
        for i, subnet in enumerate(subnets):
            name = subnet.get("name", "Unnamed")
            ext_id = subnet.get("extId", "N/A")
            print(f"{i+1:3d}. {name} ({ext_id})")
        
        # Get subnet selection
        while True:
            try:
                choice = input(f"\nSelect subnet (1-{len(subnets)}): ").strip()
                subnet_index = int(choice) - 1
                if 0 <= subnet_index < len(subnets):
                    selected_subnet = subnets[subnet_index]
                    break
                else:
                    print(f"Please enter a number between 1 and {len(subnets)}")
            except ValueError:
                print("Please enter a valid number")
        
        subnet_name = selected_subnet.get("name", "Unnamed")
        subnet_id = selected_subnet.get("extId")
        print(f"\nSelected subnet: {subnet_name}")
        
        # Step 2: Find VMs on subnet
        vms_on_subnet = self.get_vms_on_subnet_v3(subnet_id)
        if not vms_on_subnet:
            print(f"No VMs found connected to subnet '{subnet_name}'")
            return
        
        # Display VMs
        print(f"\nVMs connected to '{subnet_name}':")
        print("-" * 60)
        for i, vm in enumerate(vms_on_subnet):
            vm_name = vm.get("spec", {}).get("name", "Unnamed")
            vm_uuid = vm.get("metadata", {}).get("uuid", "N/A")
            print(f"{i+1:3d}. {vm_name} ({vm_uuid})")
        
        # Step 3: Get categories
        category_keys = self.get_ui_visible_categories()
        if not category_keys:
            print("No categories found!")
            return
        
        # Display category keys
        print(f"\nAvailable Category Keys:")
        print("-" * 40)
        for i, key in enumerate(category_keys):
            print(f"{i+1:3d}. {key}")
        
        # Get category selection
        while True:
            try:
                choice = input(f"\nSelect category key (1-{len(category_keys)}): ").strip()
                cat_index = int(choice) - 1
                if 0 <= cat_index < len(category_keys):
                    selected_category_key = category_keys[cat_index]
                    break
                else:
                    print(f"Please enter a number between 1 and {len(category_keys)}")
            except ValueError:
                print("Please enter a valid number")
        
        # Step 4: Get existing values and let user choose
        existing_values = self.get_existing_values_for_key(selected_category_key)
        
        category_value = None
        
        if existing_values:
            print(f"\nExisting values for '{selected_category_key}':")
            print("-" * 40)
            for i, value in enumerate(existing_values):
                print(f"{i+1:3d}. {value}")
            
            print(f"{len(existing_values)+1:3d}. [Enter new value]")
            
            # Get value selection
            while True:
                try:
                    choice = input(f"\nSelect value (1-{len(existing_values)+1}): ").strip()
                    value_index = int(choice) - 1
                    
                    if 0 <= value_index < len(existing_values):
                        category_value = existing_values[value_index]
                        break
                    elif value_index == len(existing_values):
                        category_value = input(f"\nEnter new value for category '{selected_category_key}': ").strip()
                        if category_value:
                            break
                        else:
                            print("Value cannot be empty!")
                    else:
                        print(f"Please enter a number between 1 and {len(existing_values)+1}")
                except ValueError:
                    print("Please enter a valid number")
        else:
            print(f"\nNo existing values found for '{selected_category_key}'")
            category_value = input(f"Enter value for category '{selected_category_key}': ").strip()
            if not category_value:
                print("Category value cannot be empty!")
                return
        
        # Step 5: Confirm and assign
        print(f"\nReady to assign:")
        print(f"  Category: {selected_category_key}:{category_value}")
        print(f"  To {len(vms_on_subnet)} VMs on subnet: {subnet_name}")
        
        confirm = input("\nProceed? (y/n): ").strip().lower()
        if confirm not in ['y', 'yes']:
            print("Assignment cancelled")
            return
        
        # Step 6: Perform assignments
        print(f"\nAssigning category to {len(vms_on_subnet)} VMs...")
        success_count = 0
        
        for vm in vms_on_subnet:
            vm_name = vm.get("spec", {}).get("name", "Unnamed")
            vm_uuid = vm.get("metadata", {}).get("uuid")
            print(f"  Assigning to {vm_name}...")
            
            if self.assign_category_to_vm_v3(vm_uuid, selected_category_key, category_value):
                success_count += 1
                print(f"    ✓ Success")
            else:
                print(f"    ✗ Failed")
        
        print(f"\nAssignment complete!")
        print(f"  Successfully assigned: {success_count}/{len(vms_on_subnet)} VMs")
        print(f"  Category: {selected_category_key}:{category_value}")
        print(f"\nPlease check Prism Central UI to verify the assignments.")

def get_credentials():
    """Prompt user for connection details"""
    print("VM Category Assigner - Final Version")
    print("=" * 40)
    
    ip = input("Prism Central IP: ").strip()
    username = input("Username: ").strip()
    password = getpass.getpass("Password: ")
    return ip, username, password

def main():
    if len(sys.argv) == 4:
        ip = sys.argv[1]
        username = sys.argv[2]
        password = sys.argv[3]
    elif len(sys.argv) == 1:
        ip, username, password = get_credentials()
    else:
        print("Usage: python vm_category_assigner_final.py [<ip> <username> <password>]")
        sys.exit(1)
    
    try:
        client = PrismCentralClient(ip, username, password)
        assigner = VMNetworkCategoryAssigner(client)
        assigner.run_interactive_assignment()
        
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user")
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
