#!/usr/bin/env python3
"""
Nutanix Move Migration Plan Creator

This script creates migration plans using the Nutanix Move API.
It supports:
- vCenter or Prism Central as source
- Prism Central as target
- CSV file for VM credentials mapping
- Interactive prompts for missing parameters
"""

import csv
import json
import requests
import sys
import argparse
import getpass
import os
from urllib.parse import urljoin
from typing import Dict, List, Optional, Any
import urllib3

# Disable SSL warnings for self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class MoveAPIClient:
    """Client for interacting with Nutanix Move API"""
    
    def __init__(self, move_server: str, username: str, password: str, verify_ssl: bool = False):
        self.base_url = f"https://{move_server}:9440"
        self.session = requests.Session()
        self.session.verify = verify_ssl
        self.auth_token = None
        
        # Authenticate
        self.login(username, password)
    
    def login(self, username: str, password: str) -> None:
        """Authenticate with Move API and obtain JWT token"""
        login_data = {
            "username": username,
            "password": password
        }
        
        # The API spec references login but the exact endpoint may vary
        # Common patterns for Move API login
        login_endpoints = [
            "/move/v2/users/login",
            "/move/v2/login", 
            "/move/v2/auth/login"
        ]
        
        for endpoint in login_endpoints:
            try:
                response = self.session.post(
                    urljoin(self.base_url, endpoint),
                    json=login_data,
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code == 200:
                    result = response.json()
                    # Extract token from response - format may vary
                    if "Status" in result and "token" in result["Status"]:
                        self.auth_token = result["Status"]["token"]
                    elif "token" in result:
                        self.auth_token = result["token"]
                    elif "access_token" in result:
                        self.auth_token = result["access_token"]
                    
                    if self.auth_token:
                        self.session.headers.update({
                            "Authorization": f"Bearer {self.auth_token}"
                        })
                        print(f"Successfully authenticated with Move API")
                        return
                        
            except requests.exceptions.RequestException as e:
                continue
        
        raise Exception("Failed to authenticate with Move API. Please check credentials and server address.")
    
    def create_provider(self, name: str, provider_type: str, **kwargs) -> str:
        """Create a provider (source or target)
        
        Args:
            name: Provider name
            provider_type: 'VCENTER' or 'AOS' (Prism Central)
            **kwargs: Additional provider-specific parameters
        
        Returns:
            Provider UUID
        """
        if provider_type.upper() == "VCENTER":
            provider_data = {
                "Spec": {
                    "Name": name,
                    "Type": "VCENTER",
                    "VCenterAccessInfo": {
                        "IPorFQDN": kwargs.get("ip_or_fqdn"),
                        "Username": kwargs.get("username"),
                        "Password": kwargs.get("password"),
                        "Port": kwargs.get("port", 443)
                    }
                }
            }
        elif provider_type.upper() == "AOS":
            provider_data = {
                "Spec": {
                    "Name": name,
                    "Type": "AOS",
                    "AOSAccessInfo": {
                        "IPorFQDN": kwargs.get("ip_or_fqdn"),
                        "Username": kwargs.get("username"),
                        "Password": kwargs.get("password"),
                        "Port": kwargs.get("port", 9440)
                    }
                }
            }
        else:
            raise ValueError(f"Unsupported provider type: {provider_type}")
        
        response = self.session.post(
            urljoin(self.base_url, "/move/v2/providers"),
            json=provider_data,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code in [200, 201]:
            result = response.json()
            provider_uuid = result.get("MetaData", {}).get("UUID")
            print(f"Created provider '{name}' with UUID: {provider_uuid}")
            return provider_uuid
        else:
            raise Exception(f"Failed to create provider: {response.status_code} - {response.text}")
    
    def get_provider_inventory(self, provider_uuid: str) -> Dict:
        """Get provider inventory (VMs, networks, etc.)"""
        response = self.session.get(
            urljoin(self.base_url, f"/move/v2/providers/{provider_uuid}")
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Failed to get provider inventory: {response.status_code} - {response.text}")
    
    def create_migration_plan(self, plan_name: str, source_provider_uuid: str, 
                            target_provider_uuid: str, network_mappings: List[Dict],
                            vm_list: List[str], vm_credentials: Dict[str, Dict]) -> str:
        """Create a migration plan
        
        Args:
            plan_name: Name of the migration plan
            source_provider_uuid: Source provider UUID
            target_provider_uuid: Target provider UUID  
            network_mappings: List of network mapping dictionaries
            vm_list: List of VM names to migrate
            vm_credentials: Dictionary mapping VM names to credentials
            
        Returns:
            Migration plan UUID
        """
        
        # Build workload list with credentials
        workloads = []
        for vm_name in vm_list:
            workload = {
                "Name": vm_name,
                "Type": "VM"
            }
            
            # Add credentials if available
            if vm_name in vm_credentials:
                creds = vm_credentials[vm_name]
                workload["Credentials"] = {
                    "Username": creds["username"],
                    "Password": creds["password"]
                }
            
            workloads.append(workload)
        
        plan_data = {
            "Spec": {
                "Name": plan_name,
                "SourceProviderUUID": source_provider_uuid,
                "TargetProviderUUID": target_provider_uuid,
                "NetworkMappings": network_mappings,
                "ScheduleSettings": {
                    "AutomaticPrepare": False,
                    "AutomaticCutover": False
                },
                "Workloads": workloads
            }
        }
        
        response = self.session.post(
            urljoin(self.base_url, "/move/v2/plans"),
            json=plan_data,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code in [200, 201]:
            result = response.json()
            plan_uuid = result.get("MetaData", {}).get("UUID")
            print(f"Created migration plan '{plan_name}' with UUID: {plan_uuid}")
            return plan_uuid
        else:
            raise Exception(f"Failed to create migration plan: {response.status_code} - {response.text}")
    
    def get_plan_status(self, plan_uuid: str) -> Dict:
        """Get migration plan status"""
        response = self.session.get(
            urljoin(self.base_url, f"/move/v2/plans/{plan_uuid}")
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Failed to get plan status: {response.status_code} - {response.text}")


def read_vm_credentials(csv_file: str) -> Dict[str, Dict]:
    """Read VM credentials from CSV file
    
    Args:
        csv_file: Path to CSV file with format: Server Name, Username, Password
        
    Returns:
        Dictionary mapping server names to credentials
    """
    credentials = {}
    
    try:
        with open(csv_file, 'r', newline='', encoding='utf-8') as file:
            reader = csv.reader(file)
            
            # Skip header if present
            first_row = next(reader, None)
            if first_row and not (first_row[0].lower().startswith('server') or 
                                first_row[0].lower().startswith('vm')):
                # First row is data, not header
                if len(first_row) >= 3:
                    credentials[first_row[0].strip()] = {
                        'username': first_row[1].strip(),
                        'password': first_row[2].strip()
                    }
            
            # Process remaining rows
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
        
        print(f"Loaded credentials for {len(credentials)} servers from {csv_file}")
        return credentials
        
    except FileNotFoundError:
        print(f"Error: CSV file '{csv_file}' not found")
        sys.exit(1)
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        sys.exit(1)


def prompt_for_input(prompt: str, default: str = None, password: bool = False, required: bool = True) -> str:
    """Prompt user for input with optional default value
    
    Args:
        prompt: The prompt message
        default: Default value if user presses enter
        password: Whether to hide input (for passwords)
        required: Whether the input is required
        
    Returns:
        User input string
    """
    if default:
        display_prompt = f"{prompt} [{default}]: "
    else:
        display_prompt = f"{prompt}: "
    
    while True:
        if password:
            value = getpass.getpass(display_prompt)
        else:
            value = input(display_prompt)
        
        # Use default if no value entered
        if not value and default:
            value = default
        
        # Check if required
        if required and not value:
            print("This field is required. Please enter a value.")
            continue
        
        return value


def prompt_for_list(prompt: str, required: bool = True) -> List[str]:
    """Prompt user for a list of values
    
    Args:
        prompt: The prompt message
        required: Whether at least one item is required
        
    Returns:
        List of strings
    """
    print(f"{prompt}")
    print("Enter items one per line. Press Enter twice to finish:")
    
    items = []
    while True:
        item = input(f"  Item {len(items) + 1}: ").strip()
        if not item:
            if items or not required:
                break
            else:
                print("At least one item is required.")
                continue
        items.append(item)
    
    return items


def get_user_inputs(args) -> dict:
    """Get user inputs either from args or by prompting
    
    Args:
        args: Parsed command line arguments
        
    Returns:
        Dictionary with all required parameters
    """
    inputs = {}
    
    print("\n=== Nutanix Move Migration Plan Creator ===\n")
    
    # Move server details
    print("Move Server Configuration:")
    inputs['move_server'] = args.move_server or prompt_for_input("Move server IP/FQDN")
    inputs['move_username'] = args.move_username or prompt_for_input("Move username")
    inputs['move_password'] = args.move_password or prompt_for_input("Move password", password=True)
    
    # Source provider details
    print("\nSource Provider Configuration:")
    if args.source_type:
        inputs['source_type'] = args.source_type
    else:
        while True:
            source_type = prompt_for_input("Source type (vcenter/prism)").lower()
            if source_type in ['vcenter', 'prism']:
                inputs['source_type'] = source_type
                break
            print("Please enter 'vcenter' or 'prism'")
    
    inputs['source_server'] = args.source_server or prompt_for_input("Source server IP/FQDN")
    inputs['source_username'] = args.source_username or prompt_for_input("Source server username")
    inputs['source_password'] = args.source_password or prompt_for_input("Source server password", password=True)
    
    # Target provider details
    print("\nTarget Provider Configuration (Prism Central):")
    inputs['target_server'] = args.target_server or prompt_for_input("Target Prism Central IP/FQDN")
    inputs['target_username'] = args.target_username or prompt_for_input("Target Prism Central username")
    inputs['target_password'] = args.target_password or prompt_for_input("Target Prism Central password", password=True)
    
    # Migration plan details
    print("\nMigration Plan Configuration:")
    inputs['plan_name'] = args.plan_name or prompt_for_input("Migration plan name")
    
    # VM list
    if args.vm_list:
        inputs['vm_list'] = args.vm_list
    else:
        inputs['vm_list'] = prompt_for_list("VMs to migrate")
    
    # VM credentials CSV
    if args.vm_credentials_csv:
        inputs['vm_credentials_csv'] = args.vm_credentials_csv
    else:
        while True:
            csv_file = prompt_for_input("VM credentials CSV file path")
            if os.path.exists(csv_file):
                inputs['vm_credentials_csv'] = csv_file
                break
            else:
                print(f"File '{csv_file}' not found. Please enter a valid path.")
    
    # Optional network mappings
    print("\nNetwork Mappings (Optional):")
    if args.source_networks and args.target_networks:
        inputs['source_networks'] = args.source_networks
        inputs['target_networks'] = args.target_networks
    else:
        add_networks = prompt_for_input("Configure network mappings? (y/n)", "n", required=False).lower()
        if add_networks.startswith('y'):
            inputs['source_networks'] = prompt_for_list("Source networks", required=False)
            if inputs['source_networks']:
                inputs['target_networks'] = prompt_for_list("Target networks", required=False)
        else:
            inputs['source_networks'] = []
            inputs['target_networks'] = []
    
    # SSL verification
    inputs['verify_ssl'] = args.verify_ssl
    
    return inputs


def main():
    parser = argparse.ArgumentParser(
        description="Create Nutanix Move migration plans",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive mode (prompts for all inputs)
  python3 nutanix_move_migration.py
  
  # Partial command line args (prompts for missing)
  python3 nutanix_move_migration.py --move-server 10.1.1.100 --source-type vcenter
  
  # Full command line mode
  python3 nutanix_move_migration.py --move-server 10.1.1.100 --move-username admin \\
    --move-password pass123 --source-type vcenter --source-server 10.1.1.50 \\
    --source-username admin --source-password pass456 --target-server 10.1.1.200 \\
    --target-username admin --target-password pass789 --plan-name "My-Plan" \\
    --vm-list vm1 vm2 --vm-credentials-csv creds.csv
        """
    )
    
    # Make all arguments optional for interactive mode
    parser.add_argument("--move-server", help="Move server IP or FQDN")
    parser.add_argument("--move-username", help="Move username")
    parser.add_argument("--move-password", help="Move password")
    parser.add_argument("--source-type", choices=["vcenter", "prism"], help="Source provider type")
    parser.add_argument("--source-server", help="Source server IP or FQDN")
    parser.add_argument("--source-username", help="Source server username")
    parser.add_argument("--source-password", help="Source server password")
    parser.add_argument("--target-server", help="Target Prism Central IP or FQDN")
    parser.add_argument("--target-username", help="Target Prism Central username")
    parser.add_argument("--target-password", help="Target Prism Central password")
    parser.add_argument("--plan-name", help="Migration plan name")
    parser.add_argument("--vm-list", nargs="+", help="List of VMs to migrate")
    parser.add_argument("--vm-credentials-csv", help="CSV file with VM credentials (Server Name, Username, Password)")
    parser.add_argument("--source-networks", nargs="+", help="Source network names/IDs")
    parser.add_argument("--target-networks", nargs="+", help="Target network names/IDs")
    parser.add_argument("--verify-ssl", action="store_true", help="Verify SSL certificates")
    
    args = parser.parse_args()
    
    try:
        # Get all inputs (from args or prompts)
        inputs = get_user_inputs(args)
        
        # Read VM credentials
        print(f"\nReading VM credentials from {inputs['vm_credentials_csv']}...")
        vm_credentials = read_vm_credentials(inputs['vm_credentials_csv'])
        
        # Initialize Move API client
        print("\nConnecting to Move API...")
        move_client = MoveAPIClient(inputs['move_server'], inputs['move_username'], 
                                  inputs['move_password'], inputs['verify_ssl'])
        
        # Create source provider
        print(f"\nCreating source provider ({inputs['source_type']})...")
        source_provider_uuid = move_client.create_provider(
            name=f"Source-{inputs['source_type']}-{inputs['source_server']}",
            provider_type="VCENTER" if inputs['source_type'] == "vcenter" else "AOS",
            ip_or_fqdn=inputs['source_server'],
            username=inputs['source_username'],
            password=inputs['source_password']
        )
        
        # Create target provider (Prism Central)
        print("\nCreating target provider (Prism Central)...")
        target_provider_uuid = move_client.create_provider(
            name=f"Target-PC-{inputs['target_server']}",
            provider_type="AOS",
            ip_or_fqdn=inputs['target_server'],
            username=inputs['target_username'],
            password=inputs['target_password']
        )
        
        # Build network mappings if provided
        network_mappings = []
        if inputs['source_networks'] and inputs['target_networks']:
            if len(inputs['source_networks']) != len(inputs['target_networks']):
                print("Warning: Source and target network lists have different lengths")
            
            for i, source_net in enumerate(inputs['source_networks']):
                target_net = inputs['target_networks'][i] if i < len(inputs['target_networks']) else inputs['target_networks'][0]
                network_mappings.append({
                    "SourceNetworkID": source_net,
                    "TargetNetworkID": target_net
                })
                print(f"Network mapping: {source_net} -> {target_net}")
        
        # Create migration plan
        print(f"\nCreating migration plan '{inputs['plan_name']}'...")
        plan_uuid = move_client.create_migration_plan(
            plan_name=inputs['plan_name'],
            source_provider_uuid=source_provider_uuid,
            target_provider_uuid=target_provider_uuid,
            network_mappings=network_mappings,
            vm_list=inputs['vm_list'],
            vm_credentials=vm_credentials
        )
        
        # Success summary
        print("\n" + "="*60)
        print("MIGRATION PLAN CREATED SUCCESSFULLY!")
        print("="*60)
        print(f"Plan Name: {inputs['plan_name']}")
        print(f"Plan UUID: {plan_uuid}")
        print(f"Source Provider: {source_provider_uuid}")
        print(f"Target Provider: {target_provider_uuid}")
        print(f"VMs to migrate: {', '.join(inputs['vm_list'])}")
        print(f"Network mappings: {len(network_mappings)}")
        print("="*60)
        
        # Get initial plan status
        print("\nGetting initial plan status...")
        try:
            status = move_client.get_plan_status(plan_uuid)
            print(f"Plan Status: {status.get('Status', {}).get('State', 'Unknown')}")
        except Exception as e:
            print(f"Note: Could not retrieve plan status: {e}")
        
        print("\nNext steps:")
        print("1. Verify the migration plan in the Move UI")
        print("2. Prepare VMs for migration")
        print("3. Perform readiness checks")
        print("4. Start the migration when ready")
        
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
