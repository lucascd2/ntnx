#!/usr/bin/env python3
"""
Interactive script for Nutanix Prism Central IAM management - roles, users, and authorization policies.
Based on Nutanix IAM v4.1.b2 API specification. Supports role management, user search, and authorization policy viewing.
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

    def list_users(self, limit=100, page=0, username_filter=None):
        """List all users with optional username filtering"""
        if limit > 100:
            limit = 100
        endpoint = "/iam/v4.1.b2/authn/users"
        params = {"$limit": limit, "$page": page}
        
        # Add username filter if provided
        if username_filter:
            # Use OData filtering for username search
            params["$filter"] = f"startswith(username, '{username_filter}') or contains(username, '{username_filter}') or startswith(displayName, '{username_filter}') or contains(displayName, '{username_filter}')"
        
        return self._make_request("GET", endpoint, params=params)

    def get_user_details(self, user_ext_id):
        """Get detailed information about a specific user"""
        endpoint = f"/iam/v4.1.b2/authn/users/{user_ext_id}"
        return self._make_request("GET", endpoint)

    def list_authorization_policies(self, limit=100, page=0):
        """List all authorization policies"""
        if limit > 100:
            limit = 100
        endpoint = "/iam/v4.1.b2/authz/authorization-policies"
        params = {"$limit": limit, "$page": page}
        return self._make_request("GET", endpoint, params=params)

    def get_authorization_policy_details(self, policy_ext_id):
        """Get detailed information about a specific authorization policy"""
        endpoint = f"/iam/v4.1.b2/authz/authorization-policies/{policy_ext_id}"
        return self._make_request("GET", endpoint)

    def get_user_authorization_policies(self, user_ext_id, user_username):
        """Get all authorization policies that apply to a specific user"""
        user_policies = []
        page = 0
        limit = 100
        
        print(f"Searching for authorization policies for user: {user_username}")
        
        while True:
            policies_response = self.list_authorization_policies(limit=limit, page=page)
            if not policies_response or 'data' not in policies_response:
                break
            
            policies = policies_response['data']
            if not policies:
                break
            
            print(f"Checking page {page + 1} ({len(policies)} policies)...")
            
            for policy in policies:
                # Check if this policy applies to our user
                identities = policy.get('identities', [])
                for identity in identities:
                    identity_filter = identity.get('identityFilter', {})
                    
                    # Check various ways a user might be referenced in the policy
                    # This is a simplified check - the actual structure may vary
                    if self._user_matches_identity_filter(user_ext_id, user_username, identity_filter):
                        user_policies.append(policy)
                        break
            
            # Check if there are more pages
            if len(policies) < limit:
                break
            page += 1
        
        return user_policies

    def _user_matches_identity_filter(self, user_ext_id, user_username, identity_filter):
        """Check if a user matches an identity filter (simplified implementation)"""
        # This is a simplified implementation. In reality, identity filters can be complex
        # and may include group memberships, user attributes, etc.
        
        # Convert to string for checking
        filter_str = str(identity_filter).lower()
        user_ext_id_lower = user_ext_id.lower()
        user_username_lower = user_username.lower()
        
        # Check if user ID or username appears in the filter
        if user_ext_id_lower in filter_str or user_username_lower in filter_str:
            return True
        
        # Check for common identity filter patterns
        # Note: This is a basic implementation - actual filters may be more complex
        for key, value in identity_filter.items():
            if isinstance(value, str):
                if user_ext_id_lower in value.lower() or user_username_lower in value.lower():
                    return True
            elif isinstance(value, dict):
                # Recursive check for nested filters
                if self._user_matches_identity_filter(user_ext_id, user_username, value):
                    return True
        
        return False
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


def print_users_table(users):
    """Print users in a formatted table"""
    print(f"\n{'#':<4} {'Username':<25} {'Display Name':<30} {'Type':<15} {'Status':<10}")
    print("-" * 84)
    
    for i, user in enumerate(users, 1):
        username = user.get('username', 'N/A')[:24]
        display_name = user.get('displayName', 'N/A')[:29]
        user_type = user.get('userType', 'N/A')[:14]
        status = 'Active' if user.get('isActive', True) else 'Inactive'
        print(f"{i:<4} {username:<25} {display_name:<30} {user_type:<15} {status:<10}")

def print_authorization_policies_table(policies):
    """Print authorization policies in a formatted table"""
    print(f"\n{'#':<4} {'Policy Name':<40} {'Type':<20} {'Users':<8} {'System':<8}")
    print("-" * 80)
    
    for i, policy in enumerate(policies, 1):
        name = policy.get('displayName', 'N/A')[:39]
        policy_type = policy.get('authorizationPolicyType', 'N/A')[:19]
        users_count = policy.get('assignedUsersCount', 0)
        is_system = 'Yes' if policy.get('isSystemDefined', False) else 'No'
        print(f"{i:<4} {name:<40} {policy_type:<20} {users_count:<8} {is_system:<8}")

def print_policy_details(policy, role_details=None):
    """Print detailed authorization policy information"""
    print(f"\nPolicy: {policy.get('displayName', 'N/A')}")
    print(f"Description: {policy.get('description', 'No description')}")
    print(f"Type: {policy.get('authorizationPolicyType', 'N/A')}")
    print(f"System Defined: {'Yes' if policy.get('isSystemDefined', False) else 'No'}")
    print(f"External ID: {policy.get('extId', 'N/A')}")
    print(f"Assigned Users: {policy.get('assignedUsersCount', 0)}")
    print(f"Assigned User Groups: {policy.get('assignedUserGroupsCount', 0)}")
    
    # Show role information if available
    role = policy.get('role', {})
    if role:
        print(f"\nAssigned Role:")
        print(f"  Role Name: {role.get('displayName', 'N/A')}")
        if role_details:
            operations = role_details.get('operations', [])
            print(f"  Operations: {len(operations)} permissions")
    
    # Show entities
    entities = policy.get('entities', [])
    if entities:
        print(f"\nEntities ({len(entities)}):")
        for i, entity in enumerate(entities[:3]):  # Show first 3 entities
            entity_filter = entity.get('entityFilter', {})
            print(f"  • Entity {i+1}: {str(entity_filter)[:100]}")
        if len(entities) > 3:
            print(f"  ... and {len(entities) - 3} more entities")
    
    # Show identities (users/groups this policy applies to)
    identities = policy.get('identities', [])
    if identities:
        print(f"\nIdentities ({len(identities)}):")
        for i, identity in enumerate(identities[:3]):  # Show first 3 identities
            identity_filter = identity.get('identityFilter', {})
            print(f"  • Identity {i+1}: {str(identity_filter)[:100]}")
        if len(identities) > 3:
            print(f"  ... and {len(identities) - 3} more identities")

def search_and_display_user_policies(pc_iam, operations_cache):
    """Search for a user and display their authorization policies"""
    print(f"\n{'='*60}")
    print("User Authorization Policy Search")
    print(f"{'='*60}")
    
    # Get search term
    search_term = input("Enter username to search for: ").strip()
    if not search_term:
        print("Search term is required.")
        return
    
    # Search for users
    print(f"\nSearching for users matching '{search_term}'...")
    users_response = pc_iam.list_users(limit=100, username_filter=search_term)
    
    if not users_response or 'data' not in users_response:
        print("Error: Could not retrieve users.")
        return
    
    users = users_response['data']
    if not users:
        print(f"No users found matching '{search_term}'.")
        return
    
    # Display found users
    print(f"Found {len(users)} user(s):")
    print_users_table(users)
    
    # Let user select which user to analyze
    if len(users) == 1:
        selected_user = users[0]
        print(f"\nAnalyzing authorization policies for: {selected_user.get('username', 'N/A')}")
    else:
        try:
            choice = input(f"\nSelect user (1-{len(users)}): ").strip()
            user_index = int(choice) - 1
            if 0 <= user_index < len(users):
                selected_user = users[user_index]
            else:
                print("Invalid selection.")
                return
        except ValueError:
            print("Invalid input.")
            return
    
    # Get user details
    user_ext_id = selected_user['extId']
    user_username = selected_user.get('username', 'N/A')
    
    # Find authorization policies for this user
    print(f"\nSearching for authorization policies for user: {user_username}")
    user_policies = pc_iam.get_user_authorization_policies(user_ext_id, user_username)
    
    if not user_policies:
        print(f"No authorization policies found for user: {user_username}")
        return
    
    # Display policies
    print(f"\nFound {len(user_policies)} authorization policies for user: {user_username}")
    print_authorization_policies_table(user_policies)
    
    # Allow user to view policy details
    while True:
        print(f"\nOptions:")
        print(f"• Enter a number (1-{len(user_policies)}) to view policy details")
        print("• Enter 'q' to return to main menu")
        
        choice = input("\nYour choice: ").strip().lower()
        
        if choice == 'q':
            break
        
        try:
            policy_index = int(choice) - 1
            if 0 <= policy_index < len(user_policies):
                selected_policy = user_policies[policy_index]
                
                # Get detailed policy information
                policy_ext_id = selected_policy['extId']
                policy_details_response = pc_iam.get_authorization_policy_details(policy_ext_id)
                
                if policy_details_response and 'data' in policy_details_response:
                    policy_data = policy_details_response['data']
                    
                    # Get role details if available
                    role_details = None
                    role = policy_data.get('role', {})
                    if role and 'extId' in role:
                        role_response = pc_iam.get_role_details(role['extId'])
                        if role_response and 'data' in role_response:
                            role_details = role_response['data']
                    
                    print_policy_details(policy_data, role_details)
                else:
                    print("Error: Could not retrieve policy details.")
                
                input("\nPress Enter to continue...")
            else:
                print("Invalid selection.")
        except ValueError:
            print("Invalid input. Please enter a number or 'q'.")

def get_user_input():
    """Get user credentials and Prism Central IP"""
    print("Nutanix Prism Central IAM Manager")
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
            print("Nutanix Prism Central IAM Manager")
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
            print("• Enter 'u' to search users and view their authorization policies")
            print("• Enter 'r' to refresh the role list")
            print("• Enter 'q' to quit")
            
            choice = input("\nYour choice: ").strip().lower()
            
            if choice == 'q':
                print("Goodbye!")
                break
            elif choice == 'r':
                continue
            elif choice == 'u':
                search_and_display_user_policies(pc_iam, operations_cache)
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
                    print("Invalid input. Please enter a number, 'u', 'r', or 'q'.")
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
