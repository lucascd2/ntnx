#!/usr/bin/env python3
"""
Interactive script to list IAM roles from Nutanix Prism Central and display role permissions.
Enhanced version with role creation functionality.
Based on Nutanix IAM v4.1.b2 API specification.
"""

import requests
import json
import getpass
import sys
import re
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
        """List all available operations with pagination"""
        # Ensure limit doesn't exceed API maximum
        if limit > 100:
            limit = 100
        endpoint = "/iam/v4.1.b2/authz/operations"
        params = {"$limit": limit, "$page": page}
        return self._make_request("GET", endpoint, params=params)

    def get_operation_details(self, operations_cache, operation_ids):
        """Get details for specific operations"""
        if not operations_cache:
            print("Loading operations cache...")
            self._load_all_operations(operations_cache)
        
        return {op_id: operations_cache.get(op_id, {'displayName': 'Unknown Operation', 'description': 'Operation not found'}) 
                for op_id in operation_ids}

    def _load_all_operations(self, operations_cache):
        """Load all operations using pagination"""
        page = 0
        limit = 100
        total_loaded = 0
        
        while True:
            print(f"Loading operations page {page + 1}...")
            ops_response = self.list_operations(limit=limit, page=page)
            
            if not ops_response or 'data' not in ops_response:
                if page == 0:
                    print("Error: No operations data received!")
                break
            
            operations_data = ops_response['data']
            if not operations_data:
                break
            
            for op in operations_data:
                operations_cache[op['extId']] = op
            
            total_loaded += len(operations_data)
            print(f"Loaded {len(operations_data)} operations (total: {total_loaded})")
            
            # Check if we got fewer results than requested (last page)
            if len(operations_data) < limit:
                break
                
            page += 1
        
        print(f"Operations cache loaded: {len(operations_cache)} total operations")

    def create_role(self, role_name, description, operation_ids):
        """Create a new IAM role"""
        endpoint = "/iam/v4.1.b2/authz/roles"
        
        # Validate role name according to API pattern
        if not re.match(r"^[^<>;'()&+%\/\\`]*$", role_name):
            raise ValueError("Role name contains invalid characters. Avoid: < > ; ' ( ) & + % / \\ `")
        
        if len(role_name) < 1 or len(role_name) > 255:
            raise ValueError("Role name must be between 1 and 255 characters")
            
        if description and len(description) > 1000:
            raise ValueError("Description must be 1000 characters or less")
            
        if not operation_ids or len(operation_ids) < 1:
            raise ValueError("At least one operation must be selected")
            
        if len(operation_ids) > 2000:
            raise ValueError("Maximum 2000 operations allowed per role")

        role_data = {
            "displayName": role_name,
            "operations": operation_ids
        }
        
        if description:
            role_data["description"] = description
        
        return self._make_request("POST", endpoint, data=role_data)
    def get_view_only_operations(self, operations_cache):
        """Get all view-only operations based on operation names"""
        if not operations_cache:
            self._load_all_operations(operations_cache)
        
        view_only_patterns = [
            r'.*[Vv]iew.*',      # View operations
            r'.*[Gg]et.*',       # Get operations  
            r'.*[Ll]ist.*',      # List operations
            r'.*[Rr]ead.*',      # Read operations
            r'.*[Ss]how.*',      # Show operations
            r'.*[Dd]isplay.*',   # Display operations
            r'.*[Ff]etch.*',     # Fetch operations
            r'.*[Qq]uery.*',     # Query operations
            r'.*[Ss]earch.*',    # Search operations
            r'.*[Bb]rowse.*',    # Browse operations
            r'.*[Ii]nspect.*',   # Inspect operations
        ]
        
        view_only_ops = []
        for op_id, op_details in operations_cache.items():
            op_name = op_details.get('displayName', '')
            op_desc = op_details.get('description', '')
            
            # Check if operation name matches view-only patterns
            for pattern in view_only_patterns:
                if re.match(pattern, op_name, re.IGNORECASE):
                    view_only_ops.append(op_id)
                    break
            else:
                # Also check description for view-only keywords if name doesn't match
                view_keywords = ['view', 'get', 'list', 'read', 'show', 'display', 'fetch', 'query', 'search', 'browse', 'inspect']
                op_desc_lower = op_desc.lower()
                op_name_lower = op_name.lower()
                
                # Check if it's a read-only operation based on description
                if any(keyword in op_desc_lower for keyword in view_keywords):
                    # Exclude operations that seem to modify/create/delete
                    modify_keywords = ['create', 'update', 'delete', 'modify', 'add', 'remove', 'set', 'change', 'edit', 'write']
                    if not any(keyword in op_name_lower or keyword in op_desc_lower for keyword in modify_keywords):
                        view_only_ops.append(op_id)
        
        return view_only_ops

    def update_role_operations(self, role_ext_id, operation_ids):
        """Update a role's operations list"""
        endpoint = f"/iam/v4.1.b2/authz/roles/{role_ext_id}"
        
        # First get current role details
        current_role = self.get_role_details(role_ext_id)
        if not current_role or 'data' not in current_role:
            raise Exception("Could not retrieve current role details")
        
        role_data = current_role['data'].copy()
        
        # Update operations list
        role_data['operations'] = operation_ids
        
        # Remove read-only fields that shouldn't be in PUT request
        readonly_fields = ['extId', 'createdTime', 'lastUpdatedTime', 'createdBy', 'lastUpdatedBy', 
                          'accessibleClients', 'accessibleEntityTypes', 'accessibleClientsCount', 
                          'accessibleEntityTypesCount', 'assignedUsersCount', 'assignedUserGroupsCount',
                          'isSystemDefined', 'links']
        
        for field in readonly_fields:
            role_data.pop(field, None)
        
        return self._make_request("PUT", endpoint, data=role_data)

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

def print_operations_table(operations, show_indices=True):
    """Print operations in a formatted table"""
    if show_indices:
        print(f"\n{'#':<4} {'Operation Name':<50} {'Entity Type':<20} {'Client':<15}")
        print("-" * 89)
        
        for i, op in enumerate(operations, 1):
            name = op.get('displayName', 'N/A')[:49]
            entity_type = op.get('entityType', 'N/A')[:19]
            client = op.get('clientName', 'N/A')[:14]
            print(f"{i:<4} {name:<50} {entity_type:<20} {client:<15}")
    else:
        print(f"\n{'Operation Name':<50} {'Entity Type':<20} {'Client':<15}")
        print("-" * 85)
        
        for op in operations:
            name = op.get('displayName', 'N/A')[:49]
            entity_type = op.get('entityType', 'N/A')[:19]
            client = op.get('clientName', 'N/A')[:14]
            print(f"{name:<50} {entity_type:<20} {client:<15}")

def select_operations(operations):
    """Interactive operation selection for role creation"""
    selected_operations = []
    available_operations = operations.copy()
    
    while True:
        print(f"\n{'='*60}")
        print(f"Operation Selection ({len(selected_operations)} selected)")
        print(f"{'='*60}")
        
        if selected_operations:
            print("\nCurrently selected operations:")
            selected_ops_details = [op for op in operations if op['extId'] in selected_operations]
            print_operations_table(selected_ops_details, show_indices=False)
        
        print(f"\nAvailable operations ({len(available_operations)}):")
        print_operations_table(available_operations)
        
        print(f"\nOptions:")
        print("• Enter numbers (1-{}) to select operations (e.g., '1,3,5' or '1-10')".format(len(available_operations)))
        print("• Enter 's' to search/filter operations")
        print("• Enter 'c' to clear all selections")
        print("• Enter 'd' to finish selection")
        print("• Enter 'q' to cancel role creation")
        
        choice = input("\nYour choice: ").strip().lower()
        
        if choice == 'q':
            return None
        elif choice == 'd':
            if selected_operations:
                return selected_operations
            else:
                print("No operations selected. Please select at least one operation.")
                continue
        elif choice == 'c':
            selected_operations = []
            available_operations = operations.copy()
            continue
        elif choice == 's':
            # Search functionality
            search_term = input("Enter search term (operation name or entity type): ").strip()
            if search_term:
                filtered_ops = [op for op in operations 
                              if search_term.lower() in op.get('displayName', '').lower() 
                              or search_term.lower() in op.get('entityType', '').lower()]
                if filtered_ops:
                    available_operations = filtered_ops
                    print(f"Found {len(filtered_ops)} operations matching '{search_term}'")
                else:
                    print(f"No operations found matching '{search_term}'")
            continue
        else:
            # Parse selection
            try:
                selected_indices = parse_selection(choice, len(available_operations))
                for idx in selected_indices:
                    op_ext_id = available_operations[idx]['extId']
                    if op_ext_id not in selected_operations:
                        selected_operations.append(op_ext_id)
                
                print(f"Selected {len(selected_indices)} operation(s)")
                
            except ValueError as e:
                print(f"Invalid selection: {e}")
                continue

def parse_selection(selection, max_num):
    """Parse user selection (e.g., '1,3,5' or '1-10')"""
    indices = []
    parts = selection.split(',')
    
    for part in parts:
        part = part.strip()
        if '-' in part:
            # Range selection
            try:
                start, end = map(int, part.split('-'))
                if start < 1 or end > max_num or start > end:
                    raise ValueError(f"Range {start}-{end} is invalid")
                indices.extend(range(start-1, end))  # Convert to 0-based
            except ValueError:
                raise ValueError(f"Invalid range format: {part}")
        else:
            # Single selection
            try:
                num = int(part)
                if num < 1 or num > max_num:
                    raise ValueError(f"Number {num} is out of range (1-{max_num})")
                indices.append(num-1)  # Convert to 0-based
            except ValueError:
                raise ValueError(f"Invalid number: {part}")
    
    return list(set(indices))  # Remove duplicates

def create_new_role(pc_iam, operations_cache):
    """Interactive role creation wizard"""
    print(f"\n{'='*60}")
    print("Create New IAM Role")
    print(f"{'='*60}")
    
    # Get role name
    while True:
        role_name = input("Enter role name: ").strip()
        if not role_name:
            print("Role name is required.")
            continue
        
        if not re.match(r"^[^<>;'()&+%\/\\`]*$", role_name):
            print("Invalid characters in role name. Avoid: < > ; ' ( ) & + % / \\ `")
            continue
            
        if len(role_name) > 255:
            print("Role name must be 255 characters or less.")
            continue
            
        break
    
    # Get description (optional)
    description = input("Enter role description (optional): ").strip()
    if len(description) > 1000:
        print("Description truncated to 1000 characters.")
        description = description[:1000]
    
    # Load operations if not cached
    if not operations_cache:
        print("\nLoading available operations...")
        try:
            pc_iam._load_all_operations(operations_cache)
            if not operations_cache:
                print("Error: Could not load operations.")
                return False
        except Exception as e:
            print(f"Error: Could not load operations: {e}")
            return False
    
    operations_list = list(operations_cache.values())
    
    # Show options for role creation
    print(f"\n{'='*60}")
    print("Role Creation Options")
    print(f"{'='*60}")
    print(f"Role Name: {role_name}")
    print(f"Description: {description or 'None'}")
    print(f"Available Operations: {len(operations_list)}")
    
    print("\nHow would you like to create this role?")
    print("1. Select specific operations manually")
    print("2. Create view-only role (auto-select all view-only operations)")
    print("3. Create custom role with view-only operations (select specific + add view-only)")
    print("4. Cancel role creation")
    
    while True:
        choice = input("\nEnter your choice (1-4): ").strip()
        
        if choice == '4':
            print("Role creation cancelled.")
            return False
        elif choice == '1':
            # Manual selection only
            print(f"\nFound {len(operations_list)} available operations.")
            selected_operation_ids = select_operations(operations_list)
            if not selected_operation_ids:
                print("Role creation cancelled.")
                return False
            final_operations = selected_operation_ids
            break
        elif choice == '2':
            # View-only role
            print("\nCreating view-only role...")
            print("Identifying view-only operations...")
            view_only_ops = pc_iam.get_view_only_operations(operations_cache)
            if not view_only_ops:
                print("No view-only operations found.")
                continue
            print(f"Found {len(view_only_ops)} view-only operations")
            
            # Show sample operations
            print("\nSample view-only operations that will be included:")
            for i, op_id in enumerate(view_only_ops[:5]):
                op_details = operations_cache.get(op_id, {})
                op_name = op_details.get('displayName', 'N/A')
                print(f"  • {op_name}")
            if len(view_only_ops) > 5:
                print(f"  ... and {len(view_only_ops) - 5} more")
                
            confirm = input(f"\nCreate role with {len(view_only_ops)} view-only operations? (y/N): ").strip().lower()
            if confirm == 'y':
                final_operations = view_only_ops
                break
            else:
                continue
        elif choice == '3':
            # Custom + view-only
            print(f"\nFound {len(operations_list)} available operations.")
            selected_operation_ids = select_operations(operations_list)
            if not selected_operation_ids:
                print("Role creation cancelled.")
                return False
            
            print("\nAdding view-only operations...")
            view_only_ops = pc_iam.get_view_only_operations(operations_cache)
            new_view_ops = [op for op in view_only_ops if op not in selected_operation_ids]
            
            print(f"Selected operations: {len(selected_operation_ids)}")
            print(f"Additional view-only operations: {len(new_view_ops)}")
            print(f"Total operations: {len(selected_operation_ids) + len(new_view_ops)}")
            
            final_operations = selected_operation_ids + new_view_ops
            break
        else:
            print("Invalid choice. Please enter 1, 2, 3, or 4.")
            continue
    

    
    # Final confirmation
    print(f"\n{'='*60}")
    print("Role Creation Summary")
    print(f"{'='*60}")
    print(f"Name: {role_name}")
    print(f"Description: {description or 'None'}")
    print(f"Total Operations: {len(final_operations)}")
    
    confirm = input("\nCreate this role? (y/N): ").strip().lower()
    if confirm != 'y':
        print("Role creation cancelled.")
        return False
    
    # Create the role
    try:
        print("\nCreating role...")
        result = pc_iam.create_role(role_name, description, final_operations)
        
        if result and 'data' in result:
            created_role = result['data']
            print(f"✓ Role '{created_role.get('displayName')}' created successfully!")
            print(f"  Role ID: {created_role.get('extId')}")
            return True
        else:
            print("Error: Role creation failed.")
            return False
            
    except ValueError as e:
        print(f"Validation error: {e}")
        return False
    except Exception as e:
        print(f"Error creating role: {e}")
        return False


def add_view_only_to_existing_role(pc_iam, operations_cache, selected_role):
    """Add view-only operations to an existing role"""
    print(f"\n{'='*60}")
    print(f"Add View-Only Operations to: {selected_role.get('displayName', 'N/A')}")
    print(f"{'='*60}")
    
    # Check if role is system-defined
    if selected_role.get('isSystemDefined', False):
        print("Cannot modify system-defined roles.")
        return False
    
    # Get current role details
    role_ext_id = selected_role['extId']
    role_details = pc_iam.get_role_details(role_ext_id)
    if not role_details or 'data' not in role_details:
        print("Error: Could not retrieve role details.")
        return False
    
    role_data = role_details['data']
    current_operations = set(role_data.get('operations', []))
    
    print(f"Current role has {len(current_operations)} operations")
    
    # Get view-only operations
    print("\nIdentifying view-only operations...")
    view_only_ops = pc_iam.get_view_only_operations(operations_cache)
    view_only_set = set(view_only_ops)
    
    # Find view-only operations not already in the role
    new_view_ops = view_only_set - current_operations
    
    print(f"Found {len(view_only_ops)} total view-only operations")
    print(f"Role already has {len(view_only_set & current_operations)} view-only operations")
    print(f"Can add {len(new_view_ops)} additional view-only operations")
    
    if not new_view_ops:
        print("\nRole already has all available view-only operations.")
        return True
    
    # Show some examples of what will be added
    if len(new_view_ops) > 0:
        print("\nSample view-only operations to be added:")
        sample_ops = list(new_view_ops)[:5]
        for op_id in sample_ops:
            op_details = operations_cache.get(op_id, {})
            op_name = op_details.get('displayName', 'N/A')
            print(f"  • {op_name}")
        if len(new_view_ops) > 5:
            print(f"  ... and {len(new_view_ops) - 5} more")
    
    # Confirm addition
    confirm = input(f"\nAdd {len(new_view_ops)} view-only operations to this role? (y/N): ").strip().lower()
    if confirm != 'y':
        print("Operation cancelled.")
        return False
    
    # Update role with new operations
    try:
        print("\nUpdating role...")
        updated_operations = list(current_operations | new_view_ops)
        result = pc_iam.update_role_operations(role_ext_id, updated_operations)
        
        if result and 'data' in result:
            print(f"✓ Role updated successfully!")
            print(f"  Total operations: {len(updated_operations)}")
            print(f"  Added view-only operations: {len(new_view_ops)}")
            return True
        else:
            print("Error: Failed to update role.")
            return False
            
    except Exception as e:
        print(f"Error updating role: {e}")
        return False

def get_user_input():
    """Get user credentials and Prism Central IP"""
    print("Nutanix Prism Central IAM Roles Manager")
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
            print("Nutanix Prism Central IAM Roles Manager")
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
            print("• Enter 'c' to create a new role")
            print("• Enter 'r' to refresh the role list")
            print("• Enter 'q' to quit")
            
            choice = input("\nYour choice: ").strip().lower()
            
            if choice == 'q':
                print("Goodbye!")
                break
            elif choice == 'r':
                continue
            elif choice == 'c':
                create_new_role(pc_iam, operations_cache)
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
                        
                        # Always show option, but handle system roles appropriately
                        is_system_role = role_data.get('isSystemDefined', False)
                        if is_system_role:
                            print("\n[System-defined role - cannot be modified]")
                            add_view_choice = input("\nWould you like to add view-only operations to this role? (y/N): ").strip().lower()
                            if add_view_choice == 'y':
                                print("Cannot modify system-defined roles.")
                        else:
                            add_view_choice = input("\nWould you like to add view-only operations to this role? (y/N): ").strip().lower()
                            if add_view_choice == 'y':
                                add_view_only_to_existing_role(pc_iam, operations_cache, selected_role)
                        
                        input("\nPress Enter to continue...")
                        
                    else:
                        print("Invalid selection. Please enter a valid number.")
                except ValueError:
                    print("Invalid input. Please enter a number, 'c', 'r', or 'q'.")
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
