#!/usr/bin/env python3
"""
Nutanix Prism Central VM List Script

This script lists all Virtual Machines from Nutanix Prism Central using the
VMM REST API. It tries v4.1 first and automatically falls back to v4.0 for
backward compatibility. It supports pagination for large environments and handles
API rate limiting appropriately.

Author: Generated from Nutanix VMM v4.1 Swagger specs
Date: 2025-08-28
API Reference: swagger-clustermgmt-v4.1-all.yaml and swagger-vmm-v4.1-all.yaml
Compatibility: VMM v4.1 and v4.0
"""

import argparse
import base64
import getpass
import json
import logging
import requests
import ssl
import sys
import time
from typing import Dict, List, Optional, Tuple
from urllib3.exceptions import InsecureRequestWarning
from urllib.parse import urljoin
import urllib3

# Suppress SSL warnings for self-signed certificates
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class NutanixAPIClient:
    """Client for Nutanix Prism Central API interactions."""
    
    def __init__(self, pc_ip: str, username: str, password: str, verify_ssl: bool = False):
        """
        Initialize the Nutanix API client.
        
        Args:
            pc_ip: Prism Central IP address or FQDN
            username: Username for authentication
            password: Password for authentication
            verify_ssl: Whether to verify SSL certificates (default: False)
        """
        self.base_url = f"https://{pc_ip}:9440/api"
        self.session = requests.Session()
        self.session.verify = verify_ssl
        
        # Enhanced SSL handling for self-signed certificates
        if not verify_ssl:
            # Disable SSL verification and warnings
            self.session.verify = False
            # Create an SSL context that doesn't verify certificates
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            # Mount HTTPAdapter with custom SSL context
            from requests.adapters import HTTPAdapter
            from urllib3.poolmanager import PoolManager
            from urllib3.util import ssl_
            
            class SSLContextHTTPAdapter(HTTPAdapter):
                def init_poolmanager(self, *args, **kwargs):
                    kwargs['ssl_context'] = ssl_context
                    return super().init_poolmanager(*args, **kwargs)
            
            self.session.mount('https://', SSLContextHTTPAdapter())
        
        # Set authentication
        auth_string = f"{username}:{password}"
        auth_bytes = base64.b64encode(auth_string.encode('utf-8'))
        self.session.headers.update({
            'Authorization': f'Basic {auth_bytes.decode("utf-8")}',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        })
        
        self.pc_ip = pc_ip
        # Preferred API versions (try v4.1 first, then v4.0, then v3.0)
        self._vmm_api_versions = ["v4.1", "v4.0", "v3.0"]
        # Also try legacy v2 API paths as fallback
        self._legacy_api_paths = [
            "/api/nutanix/v3/vms",  # v3 API
            "/api/nutanix/v2.0/vms",  # v2 API
            "/PrismGateway/services/rest/v2.0/vms"  # Very old v2 API
        ]
        # Cache the first version that succeeds to avoid repeated fallbacks
        self._working_vmm_version: Optional[str] = None
        ssl_status = "enabled" if verify_ssl else "disabled (ignoring self-signed certificates)"
        logger.info(f"Initialized API client for Prism Central: {pc_ip} (SSL verification: {ssl_status})")

    def _make_request(self, method: str, endpoint: str, params: Optional[Dict] = None, 
                     data: Optional[Dict] = None, retries: int = 3, backoff: float = 1.0) -> Dict:
        """
        Make an HTTP request with retry logic and rate limiting handling.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint
            params: Query parameters
            data: Request body data
            retries: Number of retry attempts
            backoff: Backoff factor for retries
            
        Returns:
            Dictionary containing the JSON response
            
        Raises:
            Exception: If the request fails after all retries
        """
        url = urljoin(self.base_url, endpoint)
        
        for attempt in range(retries + 1):
            try:
                response = self.session.request(
                    method=method,
                    url=url,
                    params=params,
                    json=data,
                    timeout=30
                )
                
                # Handle rate limiting (HTTP 429)
                if response.status_code == 429:
                    retry_after = int(response.headers.get('Retry-After', 60))
                    logger.warning(f"Rate limited. Waiting {retry_after} seconds before retry...")
                    time.sleep(retry_after)
                    continue
                
                # Handle other HTTP errors
                if not response.ok:
                    error_msg = f"HTTP {response.status_code}: {response.text}"
                    if attempt < retries:
                        logger.warning(f"Request failed (attempt {attempt + 1}/{retries + 1}): {error_msg}")
                        time.sleep(backoff * (2 ** attempt))
                        continue
                    else:
                        raise Exception(f"Request failed after {retries + 1} attempts: {error_msg}")
                
                return response.json()
                
            except requests.exceptions.RequestException as e:
                if attempt < retries:
                    logger.warning(f"Request exception (attempt {attempt + 1}/{retries + 1}): {e}")
                    time.sleep(backoff * (2 ** attempt))
                    continue
                else:
                    raise Exception(f"Request failed after {retries + 1} attempts: {e}")
        
        raise Exception("Unexpected error in request handling")

    def get_vms(self, page: int = 0, limit: int = 50, vm_filter: Optional[str] = None,
                select_fields: Optional[str] = None, orderby: Optional[str] = None) -> Dict:
        """
        Get Virtual Machines from Prism Central.
        
        Args:
            page: Page number (0-based)
            limit: Number of VMs per page (1-100, default: 50)
            vm_filter: OData filter expression
            select_fields: Comma-separated list of fields to select
            orderby: Field to order by
            
        Returns:
            Dictionary containing VM data and metadata
        """
        params = {
            '$page': page,
            '$limit': limit
        }
        
        if vm_filter:
            params['$filter'] = vm_filter
        if select_fields:
            params['$select'] = select_fields
        if orderby:
            params['$orderby'] = orderby
        
        logger.debug(f"Fetching VMs - Page: {page}, Limit: {limit}")
        
        # Determine order of versions to try (prefer previously working one)
        versions_to_try: List[str] = []
        if self._working_vmm_version:
            versions_to_try.append(self._working_vmm_version)
            versions_to_try.extend([v for v in self._vmm_api_versions if v != self._working_vmm_version])
        else:
            versions_to_try = list(self._vmm_api_versions)
        
        last_exception: Optional[Exception] = None
        
        # First try VMM API versions
        for version in versions_to_try:
            endpoint = f"/vmm/{version}/ahv/config/vms"
            url = urljoin(self.base_url, endpoint)
            logger.debug(f"Attempting VMM endpoint {endpoint}")
            
            # Retry logic per version, similar to _make_request
            retries = 3
            backoff = 1.0
            for attempt in range(retries + 1):
                try:
                    logger.debug(f"Making request to: {url}")
                    logger.debug(f"Request params: {params}")
                    response = self.session.get(url, params=params, timeout=30)
                    logger.debug(f"Response status: {response.status_code}")
                    
                    # Handle rate limiting
                    if response.status_code == 429:
                        retry_after = int(response.headers.get('Retry-After', 60))
                        logger.warning(f"Rate limited on {version}. Waiting {retry_after}s before retry...")
                        time.sleep(retry_after)
                        continue
                    
                    # Handle unsupported path/version: try next version without exhausting retries
                    if response.status_code in (404,):
                        logger.info(f"Endpoint not found for {version} (HTTP 404). Trying next available API version...")
                        break  # break retry loop and move to next version
                    
                    if not response.ok:
                        error_msg = f"HTTP {response.status_code}: {response.text}"
                        if attempt < retries:
                            logger.warning(f"Request failed on {version} (attempt {attempt + 1}/{retries + 1}): {error_msg}")
                            time.sleep(backoff * (2 ** attempt))
                            continue
                        else:
                            raise Exception(f"Request failed after {retries + 1} attempts on {version}: {error_msg}")
                    
                    # Success
                    if not self._working_vmm_version:
                        logger.info(f"Successfully connected using VMM API {version}")
                    self._working_vmm_version = version
                    return response.json()
                except requests.exceptions.RequestException as e:
                    last_exception = e
                    if attempt < retries:
                        logger.warning(f"Request exception on {version} (attempt {attempt + 1}/{retries + 1}): {e}")
                        time.sleep(backoff * (2 ** attempt))
                        continue
                    else:
                        # Do not fallback on network/auth errors unless it is clearly a 404 handled above
                        logger.error(f"Request failed after {retries + 1} attempts on {version}: {e}")
                        raise Exception(f"Request failed after {retries + 1} attempts on {version}: {e}")
        
        # If VMM API versions failed, try legacy API paths
        logger.info("VMM API endpoints not available. Trying legacy API paths...")
        
        for api_path in self._legacy_api_paths:
            url = f"https://{self.pc_ip}:9440{api_path}"
            logger.debug(f"Attempting legacy endpoint: {api_path}")
            
            # For v3 API, we need to use POST with a request body
            if "v3" in api_path:
                try:
                    # v3 API uses POST with request body for list operations
                    request_body = {
                        "kind": "vm"
                    }
                    
                    # Add pagination if not the first page
                    if limit and limit != 50:  # Only add if different from default
                        request_body["length"] = limit
                    if page > 0:
                        request_body["offset"] = page * limit
                    
                    # Add filter if provided (convert basic OData to v3 format)
                    if vm_filter:
                        # Basic conversion from OData to v3 filter format
                        if "eq" in vm_filter and "powerState" in vm_filter:
                            # Convert "powerState eq 'ON'" to v3 format
                            if "'ON'" in vm_filter:
                                request_body["filter"] = "power_state==on"
                            elif "'OFF'" in vm_filter:
                                request_body["filter"] = "power_state==off"
                    
                    logger.debug(f"v3 API request body: {request_body}")
                    response = self.session.post(url, json=request_body, timeout=30)
                    
                    if response.ok:
                        logger.info(f"Successfully connected using v3 API")
                        self._working_vmm_version = "v3.0"
                        # Convert v3 response format to v4 format for compatibility
                        v3_data = response.json()
                        converted_data = {
                            'data': v3_data.get('entities', []),
                            'metadata': {
                                'totalAvailableResults': v3_data.get('metadata', {}).get('total_matches', 0)
                            }
                        }
                        return converted_data
                    elif response.status_code == 404:
                        logger.debug(f"v3 API not found (HTTP 404)")
                        continue
                    else:
                        logger.warning(f"v3 API returned HTTP {response.status_code}: {response.text[:100]}")
                        continue
                        
                except Exception as e:
                    logger.debug(f"v3 API request failed: {e}")
                    continue
            else:
                # For v2 API, use GET
                try:
                    v2_params = {}
                    if limit:
                        v2_params['length'] = limit
                    if page:
                        v2_params['offset'] = page * limit
                    
                    response = self.session.get(url, params=v2_params, timeout=30)
                    
                    if response.ok:
                        logger.info(f"Successfully connected using legacy API {api_path}")
                        self._working_vmm_version = "v2.0"
                        # Convert v2 response format to v4 format for compatibility
                        v2_data = response.json()
                        converted_data = {
                            'data': v2_data.get('entities', []),
                            'metadata': {
                                'totalAvailableResults': v2_data.get('metadata', {}).get('total_entities', len(v2_data.get('entities', [])))
                            }
                        }
                        return converted_data
                    elif response.status_code == 404:
                        logger.debug(f"Legacy API {api_path} not found (HTTP 404)")
                        continue
                    else:
                        logger.warning(f"Legacy API {api_path} returned HTTP {response.status_code}: {response.text[:100]}")
                        continue
                        
                except Exception as e:
                    logger.debug(f"Legacy API {api_path} request failed: {e}")
                    continue
        
        # If we get here, all API versions and paths failed
        if last_exception:
            raise Exception(f"All API endpoints failed. Last error: {last_exception}")
        raise Exception("No working API endpoints found. This may indicate VMM service is not available or API structure has changed.")

    def list_all_vms(self, limit: int = 100, vm_filter: Optional[str] = None,
                     select_fields: Optional[str] = None, orderby: Optional[str] = None) -> List[Dict]:
        """
        List all Virtual Machines from Prism Central with automatic pagination.
        
        Args:
            limit: Number of VMs per page (1-100)
            vm_filter: OData filter expression
            select_fields: Comma-separated list of fields to select
            orderby: Field to order by
            
        Returns:
            List of VM dictionaries
        """
        all_vms = []
        page = 0
        
        logger.info("Starting VM enumeration...")
        
        while True:
            try:
                response = self.get_vms(
                    page=page,
                    limit=limit,
                    vm_filter=vm_filter,
                    select_fields=select_fields,
                    orderby=orderby
                )
                
                vms = response.get('data', [])
                if not vms:
                    logger.info(f"No more VMs found on page {page}. Enumeration complete.")
                    break
                
                all_vms.extend(vms)
                logger.info(f"Retrieved {len(vms)} VMs from page {page} (total: {len(all_vms)})")
                
                # Check if there are more pages
                metadata = response.get('metadata', {})
                total_available = metadata.get('totalAvailableResults')
                if total_available and len(all_vms) >= total_available:
                    logger.info(f"Retrieved all {total_available} VMs")
                    break
                
                # Check if we got fewer results than requested (last page)
                if len(vms) < limit:
                    logger.info(f"Last page reached (got {len(vms)} < {limit} requested)")
                    break
                
                page += 1
                
                # Small delay to be respectful to the API
                time.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Error retrieving VMs on page {page}: {e}")
                raise
        
        return all_vms

    def get_api_version(self) -> Optional[str]:
        """
        Get the working API version after successful VM enumeration.
        
        Returns:
            The API version string (e.g., "v4.1", "v4.0") or None if not determined yet
        """
        return self._working_vmm_version

    def test_connection(self) -> Dict[str, any]:
        """
        Test connectivity to Prism Central and determine available API versions.
        
        Returns:
            Dictionary with connection test results
        """
        results = {
            'reachable': False,
            'available_versions': [],
            'working_version': None,
            'errors': []
        }
        
        logger.info(f"Testing connection to Prism Central: {self.pc_ip}")
        
        for version in self._vmm_api_versions:
            endpoint = f"/vmm/{version}/ahv/config/vms"
            url = urljoin(self.base_url, endpoint)
            
            try:
                logger.debug(f"Testing endpoint: {endpoint}")
                response = self.session.get(
                    url, 
                    params={'$page': 0, '$limit': 1}, 
                    timeout=10
                )
                
                if response.status_code == 200:
                    results['available_versions'].append(version)
                    if not results['working_version']:
                        results['working_version'] = version
                    results['reachable'] = True
                    logger.info(f"✓ VMM API {version} is available")
                elif response.status_code == 404:
                    logger.info(f"✗ VMM API {version} not found (HTTP 404)")
                elif response.status_code in (401, 403):
                    logger.warning(f"✗ VMM API {version} - Authentication error (HTTP {response.status_code})")
                    results['errors'].append(f"Authentication failed for {version}")
                else:
                    logger.warning(f"✗ VMM API {version} - HTTP {response.status_code}: {response.text[:100]}")
                    results['errors'].append(f"HTTP {response.status_code} for {version}")
                    
            except Exception as e:
                logger.error(f"✗ VMM API {version} - Connection error: {e}")
                results['errors'].append(f"Connection error for {version}: {e}")
        
        return results


def format_vm_output(vm_data: Dict, format_type: str = 'table') -> str:
    """
    Format VM data for output.
    
    Args:
        vm_data: VM dictionary from API response
        format_type: Output format ('table', 'json', 'csv')
        
    Returns:
        Formatted string representation of VM data
    """
    if format_type == 'json':
        return json.dumps(vm_data, indent=2)
    elif format_type == 'csv':
        # Extract key fields for CSV format
        name = vm_data.get('name', 'N/A')
        ext_id = vm_data.get('extId', 'N/A')
        power_state = vm_data.get('powerState', 'N/A')
        memory_gb = vm_data.get('memorySizeBytes', 0) / (1024**3) if vm_data.get('memorySizeBytes') else 0
        num_vcpus = (vm_data.get('numSockets', 1) * 
                    vm_data.get('numCoresPerSocket', 1) * 
                    vm_data.get('numThreadsPerCore', 1))
        cluster_id = vm_data.get('cluster', {}).get('extId', 'N/A')
        host_id = vm_data.get('host', {}).get('extId', 'N/A')
        
        return f"{name},{ext_id},{power_state},{memory_gb:.2f},{num_vcpus},{cluster_id},{host_id}"
    else:  # table format
        name = vm_data.get('name', 'N/A')
        ext_id = vm_data.get('extId', 'N/A')[:8] + '...' if vm_data.get('extId') else 'N/A'
        power_state = vm_data.get('powerState', 'N/A')
        memory_gb = vm_data.get('memorySizeBytes', 0) / (1024**3) if vm_data.get('memorySizeBytes') else 0
        num_vcpus = (vm_data.get('numSockets', 1) * 
                    vm_data.get('numCoresPerSocket', 1) * 
                    vm_data.get('numThreadsPerCore', 1))
        
        return f"{name:<30} {ext_id:<12} {power_state:<8} {memory_gb:>8.2f} {num_vcpus:>6}"


def get_credentials_from_args(args) -> Tuple[str, str, str]:
    """
    Get Prism Central credentials from command line arguments or user input.
    
    Args:
        args: Parsed command line arguments
        
    Returns:
        Tuple of (pc_ip, username, password)
    """
    pc_ip = args.pc_ip
    username = args.username
    password = args.password
    
    # Prompt for missing credentials
    if not pc_ip:
        pc_ip = input("Enter Prism Central IP address or FQDN: ").strip()
        if not pc_ip:
            logger.error("Prism Central IP address is required")
            sys.exit(1)
    
    if not username:
        username = input("Enter username: ").strip()
        if not username:
            logger.error("Username is required")
            sys.exit(1)
    
    if not password:
        password = getpass.getpass("Enter password: ")
        if not password:
            logger.error("Password is required")
            sys.exit(1)
    
    return pc_ip, username, password


def main():
    """Main function to execute the VM listing script."""
    parser = argparse.ArgumentParser(
        description="List all Virtual Machines from Nutanix Prism Central",
        epilog="Example usage:\n"
               "  %(prog)s --pc-ip 192.168.1.100 --username admin\n"
               "  %(prog)s --pc-ip pc.example.com --username admin --format json\n"
               "  %(prog)s --filter \"powerState eq 'ON'\" --select name,extId,powerState",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument('--pc-ip', help='Prism Central IP address or FQDN')
    parser.add_argument('--username', help='Username for authentication')
    parser.add_argument('--password', help='Password for authentication (not recommended for security)')
    parser.add_argument('--format', choices=['table', 'json', 'csv'], default='table',
                       help='Output format (default: table)')
    parser.add_argument('--limit', type=int, default=100, choices=range(1, 101),
                       help='Number of VMs to fetch per API call (1-100, default: 100)')
    parser.add_argument('--filter', help='OData filter expression (e.g., "powerState eq \'ON\'")')
    parser.add_argument('--select', help='Comma-separated list of fields to select')
    parser.add_argument('--orderby', help='Field to order results by (e.g., "name", "memorySizeBytes desc")')
    parser.add_argument('--verify-ssl', action='store_true', default=False,
                       help='Verify SSL certificates (default: False)')
    parser.add_argument('--output', '-o', help='Output file path (default: stdout)')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')
    parser.add_argument('--test-connection', action='store_true', 
                       help='Test connection and API availability without listing VMs')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        # Get credentials
        pc_ip, username, password = get_credentials_from_args(args)
        
        # Initialize API client
        client = NutanixAPIClient(pc_ip, username, password, args.verify_ssl)
        
        # Test connection if requested
        if args.test_connection:
            logger.info("Testing connection to Prism Central...")
            test_results = client.test_connection()
            
            print("\nConnection Test Results:")
            print(f"  Reachable: {test_results['reachable']}")
            print(f"  Available API versions: {test_results['available_versions']}")
            print(f"  Working version: {test_results['working_version']}")
            
            if test_results['errors']:
                print("  Errors:")
                for error in test_results['errors']:
                    print(f"    - {error}")
            
            if test_results['reachable']:
                logger.info("Connection test passed!")
                sys.exit(0)
            else:
                logger.error("Connection test failed!")
                sys.exit(1)
        
        # List all VMs
        logger.info("Starting VM enumeration from Prism Central...")
        vms = client.list_all_vms(
            limit=args.limit,
            vm_filter=args.filter,
            select_fields=args.select,
            orderby=args.orderby
        )
        
        # Log the API version used
        api_version = client.get_api_version()
        if api_version:
            logger.info(f"Successfully retrieved {len(vms)} Virtual Machines using VMM API {api_version}")
        else:
            logger.info(f"Successfully retrieved {len(vms)} Virtual Machines")
        
        # Prepare output
        output_lines = []
        
        if args.format == 'table':
            # Table header
            header = f"{'VM Name':<30} {'VM ID':<12} {'Power':<8} {'Memory':<8} {'vCPUs':<6}"
            separator = "-" * len(header)
            output_lines.extend([header, separator])
        elif args.format == 'csv':
            # CSV header
            output_lines.append("Name,ExtId,PowerState,MemoryGB,vCPUs,ClusterID,HostID")
        
        # Format VM data
        for vm in vms:
            output_lines.append(format_vm_output(vm, args.format))
        
        # Output results
        output_text = "\n".join(output_lines)
        
        if args.output:
            with open(args.output, 'w') as f:
                f.write(output_text)
            logger.info(f"Results written to {args.output}")
        else:
            print(output_text)
        
        logger.info("VM listing completed successfully")
        
    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
