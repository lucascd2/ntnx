#!/usr/bin/env python3
"""
Interactive Nutanix Prism Central VM Listing Tool

This script provides an interactive interface to list VMs from Nutanix Prism Central
using the VMM v4.1 API with automatic fallback to older versions.

Based on:
- swagger-vmm-v4.1-all.yaml 
- swagger-clustermgmt-v4.1-all.yaml

Author: Assistant
Date: 2025-08-28
"""

import requests
import json
import csv
import base64
import getpass
import sys
import time
import urllib3
from urllib3.exceptions import InsecureRequestWarning
from typing import Dict, List, Optional, Tuple
import ssl

# Suppress SSL warnings for self-signed certificates
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class Colors:
    """ANSI color codes for terminal output"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    END = '\033[0m'

class NutanixVMClient:
    """Interactive client for Nutanix Prism Central VM operations"""
    
    def __init__(self):
        self.session = None
        self.base_url = None
        self.pc_ip = None
        self.username = None
        self.working_api_version = None
        self.api_endpoints = {
            'v4.1': '/vmm/v4.1/ahv/config/vms',
            'v4.0': '/vmm/v4.0/ahv/config/vms', 
            'v3.1': '/api/nutanix/v3/vms/list',
            'v3.0': '/api/nutanix/v3/vms',
            'v2.0': '/api/nutanix/v2.0/vms'
        }
        
    def print_header(self):
        """Print application header"""
        print(f"\n{Colors.CYAN}{'='*60}")
        print(f"  🖥️  Nutanix Prism Central VM Listing Tool")
        print(f"{'='*60}{Colors.END}\n")
        
    def get_credentials(self) -> Tuple[str, str, str]:
        """Interactive credential collection"""
        print(f"{Colors.BOLD}📡 Connection Setup{Colors.END}")
        print(f"{Colors.YELLOW}Please provide your Prism Central connection details:{Colors.END}\n")
        
        # Get Prism Central IP
        while True:
            pc_ip = input(f"{Colors.CYAN}Prism Central IP/FQDN: {Colors.END}").strip()
            if pc_ip:
                break
            print(f"{Colors.RED}❌ IP address is required{Colors.END}")
        
        # Get username
        while True:
            username = input(f"{Colors.CYAN}Username: {Colors.END}").strip()
            if username:
                break
            print(f"{Colors.RED}❌ Username is required{Colors.END}")
        
        # Get password securely
        while True:
            password = getpass.getpass(f"{Colors.CYAN}Password: {Colors.END}")
            if password:
                break
            print(f"{Colors.RED}❌ Password is required{Colors.END}")
            
        return pc_ip, username, password
    
    def setup_connection(self, pc_ip: str, username: str, password: str):
        """Setup HTTP session with SSL and authentication"""
        self.pc_ip = pc_ip
        self.username = username
        self.base_url = f"https://{pc_ip}:9440"
        
        # Create session with SSL handling
        self.session = requests.Session()
        self.session.verify = False
        
        # Enhanced SSL context for self-signed certificates
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        # Setup authentication
        auth_string = f"{username}:{password}"
        auth_bytes = base64.b64encode(auth_string.encode('utf-8'))
        self.session.headers.update({
            'Authorization': f'Basic {auth_bytes.decode("utf-8")}',
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'User-Agent': 'Nutanix-VM-List-Tool/1.0'
        })
        
    def test_api_endpoint(self, version: str, endpoint: str) -> Tuple[bool, Optional[Dict]]:
        """Test a specific API endpoint"""
        url = f"{self.base_url}{endpoint}"
        
        try:
            if version.startswith('v3'):
                # v3 API uses POST with JSON body
                response = self.session.post(url, json={"kind": "vm"}, timeout=15)
            else:
                # v4 APIs use GET with query parameters
                response = self.session.get(url, params={"$page": 0, "$limit": 1}, timeout=15)
            
            if response.status_code == 200:
                return True, response.json()
            elif response.status_code == 401:
                print(f"{Colors.RED}❌ Authentication failed for {version}{Colors.END}")
                return False, {"error": "authentication_failed"}
            elif response.status_code == 404:
                return False, {"error": "not_found"}
            else:
                return False, {"error": f"HTTP {response.status_code}"}
                
        except requests.exceptions.RequestException as e:
            return False, {"error": f"Connection error: {e}"}
    
    def discover_api_version(self) -> str:
        """Discover which API version is available"""
        print(f"\n{Colors.BOLD}🔍 Discovering API version...{Colors.END}")
        
        for version, endpoint in self.api_endpoints.items():
            print(f"  Testing {version} API...", end=" ")
            success, result = self.test_api_endpoint(version, endpoint)
            
            if success:
                print(f"{Colors.GREEN}✅ Available{Colors.END}")
                self.working_api_version = version
                return version
            elif result and result.get('error') == 'authentication_failed':
                print(f"{Colors.RED}❌ Auth failed{Colors.END}")
                return "auth_failed"
            else:
                print(f"{Colors.YELLOW}❌ Not available{Colors.END}")
        
        return "none_found"
    
    def get_vms_v4(self, page: int = 0, limit: int = 50, power_filter: str = None) -> Dict:
        """Get VMs using v4.x API (VMM)"""
        endpoint = self.api_endpoints[self.working_api_version]
        url = f"{self.base_url}{endpoint}"
        
        params = {
            '$page': page,
            '$limit': limit
        }
        
        if power_filter and power_filter != 'all':
            params['$filter'] = f"powerState eq '{power_filter.upper()}'"
        
        response = self.session.get(url, params=params)
        response.raise_for_status()
        return response.json()
    
    def get_vms_v3(self, offset: int = 0, length: int = 50, power_filter: str = None) -> Dict:
        """Get VMs using v3.x API"""
        endpoint = self.api_endpoints[self.working_api_version] 
        url = f"{self.base_url}{endpoint}"
        
        body = {
            "kind": "vm",
            "length": length,
            "offset": offset
        }
        
        if power_filter and power_filter != 'all':
            body["filter"] = f"power_state=={power_filter.lower()}"
        
        response = self.session.post(url, json=body)
        response.raise_for_status()
        
        # Convert v3 response to v4-like format for consistency
        v3_data = response.json()
        return {
            'data': v3_data.get('entities', []),
            'metadata': {
                'totalAvailableResults': v3_data.get('metadata', {}).get('total_matches', len(v3_data.get('entities', [])))
            }
        }
    
    def get_vms_v2(self, offset: int = 0, length: int = 50) -> Dict:
        """Get VMs using v2.0 API"""
        endpoint = self.api_endpoints[self.working_api_version]
        url = f"{self.base_url}{endpoint}"
        
        params = {
            'length': length,
            'offset': offset
        }
        
        response = self.session.get(url, params=params)
        response.raise_for_status()
        
        # Convert v2 response to v4-like format
        v2_data = response.json()
        return {
            'data': v2_data.get('entities', []),
            'metadata': {
                'totalAvailableResults': v2_data.get('metadata', {}).get('total_entities', len(v2_data.get('entities', [])))
            }
        }
    
    def get_vms(self, page: int = 0, limit: int = 50, power_filter: str = None) -> Dict:
        """Get VMs using the detected API version"""
        if self.working_api_version.startswith('v4'):
            return self.get_vms_v4(page, limit, power_filter)
        elif self.working_api_version.startswith('v3'):
            return self.get_vms_v3(page * limit, limit, power_filter)
        elif self.working_api_version.startswith('v2'):
            return self.get_vms_v2(page * limit, limit)
        else:
            raise Exception("No supported API version available")
    
    def format_vm_info(self, vm: Dict, api_version: str) -> Dict:
        """Format VM information consistently across API versions"""
        if api_version.startswith('v4'):
            return {
                'name': vm.get('name', 'N/A'),
                'uuid': vm.get('extId', 'N/A'),
                'power_state': vm.get('powerState', 'N/A'),
                'cpu_sockets': vm.get('numSockets', 1),
                'cpu_cores_per_socket': vm.get('numCoresPerSocket', 1),
                'memory_gb': round(vm.get('memorySizeBytes', 0) / (1024**3), 2),
                'cluster': vm.get('cluster', {}).get('name', 'N/A'),
                'host': vm.get('host', {}).get('name', 'N/A')
            }
        elif api_version.startswith('v3'):
            return {
                'name': vm.get('spec', {}).get('name', vm.get('name', 'N/A')),
                'uuid': vm.get('metadata', {}).get('uuid', 'N/A'),
                'power_state': vm.get('spec', {}).get('resources', {}).get('power_state', 'N/A'),
                'cpu_sockets': vm.get('spec', {}).get('resources', {}).get('num_sockets', 1),
                'cpu_cores_per_socket': vm.get('spec', {}).get('resources', {}).get('num_vcpus_per_socket', 1),
                'memory_gb': round(vm.get('spec', {}).get('resources', {}).get('memory_size_mib', 0) / 1024, 2),
                'cluster': vm.get('spec', {}).get('cluster_reference', {}).get('name', 'N/A'),
                'host': 'N/A'
            }
        elif api_version.startswith('v2'):
            return {
                'name': vm.get('name', 'N/A'),
                'uuid': vm.get('uuid', 'N/A'),
                'power_state': vm.get('power_state', 'N/A'),
                'cpu_sockets': vm.get('num_cores_per_vcpu', 1),
                'cpu_cores_per_socket': vm.get('num_vcpus', 1),
                'memory_gb': round(vm.get('memory_mb', 0) / 1024, 2),
                'cluster': 'N/A',
                'host': vm.get('host_name', 'N/A')
            }
        else:
            return vm
    
    def print_vm_table(self, vms: List[Dict], api_version: str):
        """Print VMs in a formatted table"""
        if not vms:
            print(f"{Colors.YELLOW}No VMs found{Colors.END}")
            return
        
        print(f"\n{Colors.BOLD}📋 Virtual Machines (using {api_version} API):{Colors.END}")
        print(f"{Colors.CYAN}{'='*120}{Colors.END}")
        
        # Header
        header = f"{'Name':<25} {'UUID':<38} {'Power':<8} {'CPU':<8} {'Memory':<10} {'Cluster':<15} {'Host':<15}"
        print(f"{Colors.BOLD}{header}{Colors.END}")
        print(f"{Colors.CYAN}{'-'*120}{Colors.END}")
        
        # VM rows
        for vm_data in vms:
            vm = self.format_vm_info(vm_data, api_version)
            
            # Color code power state
            power_color = Colors.GREEN if vm['power_state'].upper() == 'ON' else Colors.RED
            
            # Format vCPU count
            vcpu_count = vm['cpu_sockets'] * vm['cpu_cores_per_socket']
            
            row = f"{vm['name'][:24]:<25} {vm['uuid'][:37]:<38} {power_color}{vm['power_state']:<8}{Colors.END} {vcpu_count:<8} {vm['memory_gb']:<10} {vm['cluster'][:14]:<15} {vm['host'][:14]:<15}"
            print(row)
        
        print(f"{Colors.CYAN}{'='*120}{Colors.END}")
    
    def interactive_vm_listing(self):
        """Main interactive VM listing workflow"""
        try:
            while True:
                print(f"\n{Colors.BOLD}🎛️  VM Listing Options:{Colors.END}")
                print(f"1. {Colors.GREEN}List all VMs{Colors.END}")
                print(f"2. {Colors.GREEN}List powered ON VMs{Colors.END}")  
                print(f"3. {Colors.GREEN}List powered OFF VMs{Colors.END}")
                print(f"4. {Colors.YELLOW}Change connection{Colors.END}")
                print(f"5. {Colors.RED}Exit{Colors.END}")
                
                choice = input(f"\n{Colors.CYAN}Select option (1-5): {Colors.END}").strip()
                
                if choice == '1':
                    self.list_vms('all')
                elif choice == '2':
                    self.list_vms('on')
                elif choice == '3':
                    self.list_vms('off')
                elif choice == '4':
                    return False  # Signal to reconnect
                elif choice == '5':
                    print(f"\n{Colors.GREEN}👋 Goodbye!{Colors.END}")
                    return True  # Signal to exit
                else:
                    print(f"{Colors.RED}❌ Invalid option. Please choose 1-5.{Colors.END}")
                    
        except KeyboardInterrupt:
            print(f"\n\n{Colors.YELLOW}⚠️  Operation cancelled by user{Colors.END}")
            return True
    
    def list_vms(self, power_filter: str = 'all'):
        """List VMs with optional power state filtering"""
        try:
            print(f"\n{Colors.BOLD}🔄 Fetching VMs...{Colors.END}")
            
            all_vms = []
            page = 0
            page_size = 100
            
            while True:
                response = self.get_vms(page=page, limit=page_size, power_filter=power_filter)
                vms = response.get('data', [])
                
                if not vms:
                    break
                
                all_vms.extend(vms)
                
                # Check if we have more pages
                metadata = response.get('metadata', {})
                total_available = metadata.get('totalAvailableResults', 0)
                
                if len(all_vms) >= total_available or len(vms) < page_size:
                    break
                    
                page += 1
                print(f"  📄 Fetched page {page}, total VMs so far: {len(all_vms)}")
                
                # Rate limiting courtesy
                time.sleep(0.1)
            
            filter_text = f" ({power_filter.upper()})" if power_filter != 'all' else ""
            print(f"{Colors.GREEN}✅ Found {len(all_vms)} VMs{filter_text}{Colors.END}")
            
            if all_vms:
                self.print_vm_table(all_vms, self.working_api_version)
                
                # Option to export data
                if len(all_vms) > 0:
                    self.handle_export_options(all_vms)
            else:
                print(f"{Colors.YELLOW}No VMs found matching the criteria{Colors.END}")
                
        except Exception as e:
            print(f"{Colors.RED}❌ Error fetching VMs: {e}{Colors.END}")
    
    def handle_export_options(self, vms: List[Dict]):
        """Handle export options for VM data"""
        print(f"\n{Colors.BOLD}💾 Export Options:{Colors.END}")
        print(f"1. {Colors.GREEN}Export to JSON{Colors.END}")
        print(f"2. {Colors.GREEN}Export to CSV{Colors.END}")
        print(f"3. {Colors.YELLOW}Skip export{Colors.END}")
        
        export_choice = input(f"\n{Colors.CYAN}Select export format (1-3): {Colors.END}").strip()
        
        if export_choice == '1':
            self.export_to_json(vms)
        elif export_choice == '2':
            self.export_to_csv(vms)
        elif export_choice == '3':
            print(f"{Colors.YELLOW}Export skipped{Colors.END}")
        else:
            print(f"{Colors.RED}❌ Invalid option. Export skipped.{Colors.END}")
    
    def export_to_json(self, vms: List[Dict]):
        """Export VM data to JSON file"""
        try:
            filename = f"nutanix_vms_{int(time.time())}.json"
            formatted_vms = [self.format_vm_info(vm, self.working_api_version) for vm in vms]
            
            with open(filename, 'w') as f:
                json.dump({
                    'export_info': {
                        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                        'prism_central': self.pc_ip,
                        'api_version': self.working_api_version,
                        'total_vms': len(vms)
                    },
                    'vms': formatted_vms
                }, f, indent=2)
            
            print(f"{Colors.GREEN}✅ Exported {len(vms)} VMs to {filename}{Colors.END}")
            
        except Exception as e:
            print(f"{Colors.RED}❌ JSON export failed: {e}{Colors.END}")
    
    def export_to_csv(self, vms: List[Dict]):
        """Export VM data to CSV file"""
        try:
            filename = f"nutanix_vms_{int(time.time())}.csv"
            formatted_vms = [self.format_vm_info(vm, self.working_api_version) for vm in vms]
            
            # CSV headers
            headers = ['Name', 'UUID', 'Power State', 'CPU Sockets', 'CPU Cores/Socket', 'Total vCPUs', 'Memory (GB)', 'Cluster', 'Host']
            
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                
                # Write metadata as comments (CSV doesn't have standard metadata)
                writer.writerow([f"# Exported from Prism Central: {self.pc_ip}"])
                writer.writerow([f"# Export timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}"])
                writer.writerow([f"# API version used: {self.working_api_version}"])
                writer.writerow([f"# Total VMs: {len(vms)}"])
                writer.writerow([])  # Empty row for separation
                
                # Write headers
                writer.writerow(headers)
                
                # Write VM data
                for vm in formatted_vms:
                    total_vcpus = vm['cpu_sockets'] * vm['cpu_cores_per_socket']
                    writer.writerow([
                        vm['name'],
                        vm['uuid'],
                        vm['power_state'],
                        vm['cpu_sockets'],
                        vm['cpu_cores_per_socket'],
                        total_vcpus,
                        vm['memory_gb'],
                        vm['cluster'],
                        vm['host']
                    ])
            
            print(f"{Colors.GREEN}✅ Exported {len(vms)} VMs to {filename}{Colors.END}")
            
        except Exception as e:
            print(f"{Colors.RED}❌ CSV export failed: {e}{Colors.END}")

def main():
    """Main application entry point"""
    client = NutanixVMClient()
    
    while True:
        client.print_header()
        
        # Get credentials
        pc_ip, username, password = client.get_credentials()
        
        # Setup connection
        print(f"\n{Colors.BOLD}🔗 Connecting to Prism Central...{Colors.END}")
        client.setup_connection(pc_ip, username, password)
        
        # Discover API version
        api_result = client.discover_api_version()
        
        if api_result == "auth_failed":
            print(f"\n{Colors.RED}❌ Authentication failed. Please check your credentials.{Colors.END}")
            retry = input(f"{Colors.CYAN}Try again? (Y/n): {Colors.END}").strip().lower()
            if retry in ['n', 'no']:
                break
            continue
        elif api_result == "none_found":
            print(f"\n{Colors.RED}❌ No compatible API endpoints found.{Colors.END}")
            print(f"{Colors.YELLOW}This may indicate VMM service is not available or PC version is unsupported.{Colors.END}")
            retry = input(f"{Colors.CYAN}Try different connection? (Y/n): {Colors.END}").strip().lower()
            if retry in ['n', 'no']:
                break
            continue
        
        print(f"{Colors.GREEN}✅ Successfully connected using {api_result} API{Colors.END}")
        
        # Start interactive session
        should_exit = client.interactive_vm_listing()
        if should_exit:
            break

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}👋 Application terminated by user{Colors.END}")
        sys.exit(0)
    except Exception as e:
        print(f"\n{Colors.RED}❌ Unexpected error: {e}{Colors.END}")
        sys.exit(1)
