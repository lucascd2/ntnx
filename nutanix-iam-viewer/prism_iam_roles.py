#!/usr/bin/env python3
"""
Interactive script to list IAM roles from Nutanix Prism Central and display role permissions.
Based on Nutanix IAM v4.1.b2 API specification.
"""

import requests
import json
import getpass
import sys
from urllib3.exceptions import InsecureRequestWarning
from requests.auth import HTTPBasicAuth

# Disable SSL warnings for self-signed certificates
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

class PrismCentralIAM:
    def __init__(self, pc_ip, username, password, verify_ssl=False):
        self.pc_ip = pc_ip
        self.username = username
        self.password = password
        self.verify_ssl = verify_ssl
        self.base_url = f"https://{pc_ip}:9440/api"
        self.auth = HTTPBasicAuth(username, password)
        self.headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }

    def _make_request(self, method, endpoint, params=None, data=None):
        """Make HTTP request to Prism Central API"""
        url = f"{self.base_url}{endpoint}"
        try:
            response = requests.request(
                method=method,
                url=url,
                auth=self.auth,
                headers=self.headers,
                params=params,
                json=data,
                verify=self.verify_ssl,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error making request to {url}: {e}")
            return None
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON response: {e}")
            return None

    def list_roles(self, limit=50):
        """List all IAM roles"""
        endpoint = "/iam/v4.1.b2/authz/roles"
        params = {"$limit": limit}
        return self._make_request("GET", endpoint, params=params)

    def get_role_details(self, role_ext_id):
        """Get detailed information about a specific role"""
        endpoint = f"/iam/v4.1.b2/authz/roles/{role_ext_id}"
        return self._make_request("GET", endpoint)

    def list_operations(self, limit=100, page=0):
        """List all available operations with pagination support"""
        endpoint = "/iam/v4.1.b2/authz/operations"
        params = {"$limit": limit, "$page": page}
        return self._make_request("GET", endpoint, params=params)
        
    def get_all_operations(self):
        """Get all operations by paginating through results"""
        all_operations = {}
        page = 0
        limit = 100
        
        print("Loading all operations...")
        while True:
            ops_response = self.list_operations(limit=limit, page=page)
            if not ops_response or 'data' not in ops_response:
                if page == 0:
                    print("ERROR: No operations data received!")
                break
            
            operations_data = ops_response['data']
            if not operations_data:
                break
                
            print(f"Loaded page {page + 1}: {len(operations_data)} operations")
            for op in operations_data:
                all_operations[op['extId']] = op
            
            # Check if there are more pages
            metadata = ops_response.get('metadata', {})
            total_available = metadata.get('totalAvailableResults', 0)
            current_count = (page + 1) * limit
            
            if current_count >= total_available:
                break
                
            page += 1
        
        print(f"Total operations loaded: {len(all_operations)}")
        return all_operations

    def get_operation_details(self, operations_cache, operation_ids):
        """Get details for specific operations"""
        if not operations_cache:
            operations_cache.update(self.get_all_operations())
        
        if not operations_cache:
            print("WARNING: No operations found in cache!")
            return {}
        
        print(f"Looking up {len(operation_ids)} operation permissions...")
        
        # Show some sample operations for debugging
        if operation_ids:
            found_count = sum(1 for op_id in operation_ids if op_id in operations_cache)
            print(f"Found {found_count}/{len(operation_ids)} operations in cache")
            
            # Show first few missing operations
            missing_ops = [op_id for op_id in operation_ids if op_id not in operations_cache]
            if missing_ops:
                print(f"Missing operations (first 3): {missing_ops[:3]}")
        
        return {op_id: operations_cache.get(op_id, {'displayName': 'Unknown Operation', 'description': 'Operation not found'}) 
                for op_id in operation_ids}

def print_roles_table(roles):
    """Print roles in a formatted table"""
    print(f"\n{'#':<4} {'Role Name':<40} {'Description':<50} {'System':<8}")
    print("-" * 102)
    
    for i, role in enumerate(roles, 1):
        name = role.get('displayName', 'N/A')[:39]
        desc = role.get('description', 'No description')[:49]
        is_system = 'Yes' if role.get('isSystemDefined', False) else 'No'
        print(f"{i:<4} {name:<40} {desc:<50} {is_system:<8}")

def print_role_permissions(role_details, operations_details):
    """Print detailed role permissions"""
    print(f"\nRole: {role_details.get('displayName', 'N/A')}")
    print(f"Description: {role_details.get('description', 'No description')}")
    print(f"System Defined: {'Yes' if role_details.get('isSystemDefined', False) else 'No'}")
    print(f"External ID: {role_details.get('extId', 'N/A')}")
    
    operations = role_details.get('operations', [])
    if not operations:
        print("\nNo operations/permissions defined for this role.")
        return
    
    print(f"\nPermissions ({len(operations)} operations):")
    print("-" * 80)
    
    for op_id in operations:
        op_details = operations_details.get(op_id, {})
        op_name = op_details.get('displayName', 'Unknown Operation')
        op_desc = op_details.get('description', 'No description available')
        print(f"• {op_name}")
        if op_desc and op_desc != 'No description available':
            print(f"  {op_desc}")
        print()

def get_user_input():
    """Get user credentials and Prism Central IP"""
    print("Nutanix Prism Central IAM Roles Inspector")
    print("=" * 45)
    
    pc_ip = input("Enter Prism Central IP address: ").strip()
    if not pc_ip:
        print("Error: Prism Central IP is required")
        sys.exit(1)
    
    username = input("Enter username: ").strip()
    if not username:
        print("Error: Username is required")
        sys.exit(1)
    
    password = getpass.getpass("Enter password: ")
    if not password:
        print("Error: Password is required")
        sys.exit(1)
    
    return pc_ip, username, password

def main():
    try:
        # Get user input
        pc_ip, username, password = get_user_input()
        
        # Initialize Prism Central IAM client
        pc_iam = PrismCentralIAM(pc_ip, username, password)
        operations_cache = {}
        
        while True:
            print(f"\n{'='*60}")
            print("Nutanix Prism Central IAM Roles")
            print(f"{'='*60}")
            
            # List roles
            print("\nFetching IAM roles...")
            roles_response = pc_iam.list_roles(limit=100)
            
            if not roles_response or 'data' not in roles_response:
                print("Error: Could not retrieve roles. Please check your credentials and connection.")
                break
            
            roles = roles_response['data']
            if not roles:
                print("No roles found.")
                break
            
            # Display roles
            print_roles_table(roles)
            
            # Get user selection
            print(f"\nOptions:")
            print("• Enter a number (1-{}) to view role permissions".format(len(roles)))
            print("• Enter 'r' to refresh the role list")
            print("• Enter 'q' to quit")
            
            choice = input("\nYour choice: ").strip().lower()
            
            if choice == 'q':
                print("Goodbye!")
                break
            elif choice == 'r':
                continue
            else:
                try:
                    role_index = int(choice) - 1
                    if 0 <= role_index < len(roles):
                        selected_role = roles[role_index]
                        role_ext_id = selected_role['extId']
                        
                        print(f"\nFetching details for role: {selected_role.get('displayName', 'N/A')}...")
                        
                        # Get role details
                        role_details = pc_iam.get_role_details(role_ext_id)
                        if not role_details or 'data' not in role_details:
                            print("Error: Could not retrieve role details.")
                            continue
                        
                        role_data = role_details['data']
                        
                        # Get operation details
                        operations = role_data.get('operations', [])
                        operations_details = pc_iam.get_operation_details(operations_cache, operations)
                        
                        # Display role permissions
                        print_role_permissions(role_data, operations_details)
                        
                        input("\nPress Enter to continue...")
                        
                    else:
                        print("Invalid selection. Please enter a valid number.")
                except ValueError:
                    print("Invalid input. Please enter a number, 'r', or 'q'.")
                except KeyboardInterrupt:
                    print("\nOperation cancelled.")
                    continue
    
    except KeyboardInterrupt:
        print("\n\nScript interrupted by user. Goodbye!")
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
