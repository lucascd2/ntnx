#!/usr/bin/env python3
"""
Nutanix Prism Central API Client for Prometheus Exporter
"""

import logging
import requests
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from urllib3.exceptions import InsecureRequestWarning
import urllib3

# Suppress InsecureRequestWarning if TLS verification is disabled
urllib3.disable_warnings(InsecureRequestWarning)

logger = logging.getLogger(__name__)


class NutanixAPIException(Exception):
    """Custom exception for Nutanix API errors"""
    pass


class NutanixClient:
    """Client for interacting with Nutanix Prism Central v4.2 APIs"""
    
    def __init__(self, base_url: str, username: str, password: str, 
                 verify_ssl: bool = True, timeout: int = 30):
        """
        Initialize Nutanix API client
        
        Args:
            base_url: Prism Central base URL (e.g., https://prism-central:9440)
            username: Authentication username
            password: Authentication password
            verify_ssl: Whether to verify SSL certificates
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip('/')
        self.api_base = f"{self.base_url}/api"
        self.session = requests.Session()
        self.session.auth = (username, password)
        self.session.verify = verify_ssl
        self.timeout = timeout
        
        # Set common headers
        self.session.headers.update({
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        })
        
        logger.info(f"Initialized Nutanix client for {base_url}")
    
    def _make_request(self, method: str, endpoint: str, params: Dict = None, 
                      data: Dict = None, max_retries: int = 3) -> Dict:
        """
        Make HTTP request with retry logic
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (without /api prefix)
            params: Query parameters
            data: Request body data
            max_retries: Maximum number of retry attempts
            
        Returns:
            Response data as dictionary
            
        Raises:
            NutanixAPIException: On API errors or connection issues
        """
        url = f"{self.api_base}{endpoint}"
        
        for attempt in range(max_retries + 1):
            try:
                logger.debug(f"Making {method} request to {endpoint} (attempt {attempt + 1})")
                
                response = self.session.request(
                    method=method,
                    url=url,
                    params=params,
                    json=data,
                    timeout=self.timeout
                )
                
                # Handle HTTP errors
                if response.status_code == 401:
                    raise NutanixAPIException("Authentication failed - check credentials")
                elif response.status_code == 403:
                    raise NutanixAPIException("Access forbidden - insufficient permissions")
                elif response.status_code == 404:
                    raise NutanixAPIException(f"Endpoint not found: {endpoint}")
                elif response.status_code >= 400:
                    error_msg = f"HTTP {response.status_code}: {response.text}"
                    raise NutanixAPIException(error_msg)
                
                response.raise_for_status()
                
                # Parse JSON response
                try:
                    return response.json()
                except ValueError as e:
                    raise NutanixAPIException(f"Invalid JSON response: {e}")
                    
            except requests.exceptions.ConnectTimeout:
                if attempt < max_retries:
                    wait_time = 2 ** attempt
                    logger.warning(f"Connection timeout, retrying in {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                else:
                    raise NutanixAPIException("Connection timeout after retries")
                    
            except requests.exceptions.ConnectionError as e:
                if attempt < max_retries:
                    wait_time = 2 ** attempt
                    logger.warning(f"Connection error: {e}, retrying in {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                else:
                    raise NutanixAPIException(f"Connection error: {e}")
                    
            except requests.exceptions.RequestException as e:
                raise NutanixAPIException(f"Request failed: {e}")
    
    def test_connection(self) -> bool:
        """
        Test connection to Prism Central
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            # Try to get cluster information as a connection test
            self._make_request('GET', '/clustermgmt/v4.2/config/clusters', 
                             params={'$limit': 1})
            logger.info("Connection test successful")
            return True
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False
    
    def get_vm_stats(self, start_time: datetime, end_time: datetime, 
                     vm_type: str = 'ahv', limit: int = 500) -> List[Dict]:
        """
        Get VM statistics for a time range with proper pagination
        
        Args:
            start_time: Start time for metrics
            end_time: End time for metrics
            vm_type: VM type ('ahv' or 'esxi')
            limit: Maximum number of VMs to return per page (max 100)
            
        Returns:
            List of VM statistics
        """
        if vm_type not in ['ahv', 'esxi']:
            raise ValueError("vm_type must be 'ahv' or 'esxi'")
        
        # Ensure limit doesn't exceed API maximum
        page_limit = min(limit, 100)
        endpoint = f'/vmm/v4.2/{vm_type}/stats/vms'
        
        all_vm_stats = []
        offset = 0
        
        while True:
            params = {
                '$startTime': start_time.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                '$endTime': end_time.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                '$limit': page_limit,
                '$offset': offset,
                '$statType': 'AVG',
                '$samplingInterval': 300,  # 5 minute intervals to reduce data
                '$select': 'stats'  # Required parameter - select all stats
            }
            
            try:
                response = self._make_request('GET', endpoint, params=params)
                page_data = response.get('data', [])
                metadata = response.get('metadata', {})
                total_available = metadata.get('totalAvailableResults', 0)
                
                logger.debug(f"VM stats page: offset={offset}, got={len(page_data)}, total_so_far={len(all_vm_stats)}, total_available={total_available}")
                
                if not page_data:
                    logger.info(f"No more VM stats data at offset {offset}")
                    break
                
                # Debug: Check if pc157-1 is in this page
                pc157_1_id = '889dfc57-8f7d-4fa1-9e85-abcd75e6a2a2'
                for vm in page_data:
                    if vm.get('extId') == pc157_1_id:
                        logger.info(f"FOUND pc157-1 in VM stats at offset {offset}!")
                
                all_vm_stats.extend(page_data)
                
                # Check if we have more data - rely on actual page size rather than total_available
                if len(page_data) < page_limit:
                    logger.info(f"VM stats pagination complete: collected={len(all_vm_stats)}, total_available={total_available}, page_size={len(page_data)}")
                    break
                
                # Safety check - don't collect more than reasonable limit
                if len(all_vm_stats) >= 2000:
                    logger.warning(f"VM stats collection stopped at safety limit: collected={len(all_vm_stats)}")
                    break
                
                offset += page_limit
                
                # Respect API rate limits - add small delay between requests
                time.sleep(0.1)
                
            except NutanixAPIException as e:
                logger.error(f"Failed to get VM stats (offset {offset}): {e}")
                break
        
        logger.info(f"Retrieved {len(all_vm_stats)} {vm_type} VM stats records")
        return all_vm_stats
    
    def get_clusters(self, limit: int = 50) -> List[Dict]:
        """
        Get cluster information
        
        Args:
            limit: Maximum number of clusters to return
            
        Returns:
            List of cluster data
        """
        endpoint = '/clustermgmt/v4.2/config/clusters'
        params = {'$limit': min(limit, 50)}
        
        try:
            response = self._make_request('GET', endpoint, params=params)
            return response.get('data', [])
        except NutanixAPIException as e:
            logger.error(f"Failed to get clusters: {e}")
            return []
    
    def get_hosts(self, cluster_id: str = None, limit: int = 100) -> List[Dict]:
        """
        Get host information
        
        Args:
            cluster_id: Optional cluster ID to filter hosts
            limit: Maximum number of hosts to return
            
        Returns:
            List of host data
        """
        endpoint = '/clustermgmt/v4.2/config/hosts'
        params = {'$limit': min(limit, 50)}
        
        if cluster_id:
            #params['$filter'] = f"clusterReference/extId eq '{cluster_id}'"  # Disabled due to API compatibility
            pass  # No cluster filtering applied
        
        try:
            response = self._make_request('GET', endpoint, params=params)
            return response.get('data', [])
        except NutanixAPIException as e:
            logger.error(f"Failed to get hosts: {e}")
            return []
    
    def get_alerts(self, limit: int = 100, severity: str = None) -> List[Dict]:
        """
        Get alerts from monitoring API
        
        Args:
            limit: Maximum number of alerts to return
            severity: Optional severity filter (INFO, WARNING, CRITICAL)
            
        Returns:
            List of alert data
        """
        endpoint = '/monitoring/v4.2/serviceability/alerts'
        params = {'$limit': min(limit, 50)}
        
        if severity:
            params['$filter'] = f"severity eq '{severity}'"
        
        try:
            response = self._make_request('GET', endpoint, params=params)
            return response.get('data', [])
        except NutanixAPIException as e:
            logger.error(f"Failed to get alerts: {e}")
            return []
    
    def get_storage_containers(self, limit: int = 100) -> List[Dict]:
        """
        Get storage container information
        
        Args:
            limit: Maximum number of containers to return
            
        Returns:
            List of storage container data
        """
        endpoint = '/clustermgmt/v4.2/config/storage-containers'
        params = {'$limit': min(limit, 50)}
        
        try:
            response = self._make_request('GET', endpoint, params=params)
            return response.get('data', [])
        except NutanixAPIException as e:
            logger.error(f"Failed to get storage containers: {e}")
            return []
    def get_vms(self, vm_type: str = 'ahv', limit: int = 500) -> List[Dict]:
        """
        Get VM configuration information with pagination.
        
        Args:
            vm_type: VM type ('ahv' or 'esxi')
            limit: Maximum number of VMs to return
            
        Returns:
            List of VM configuration data
        """
        if vm_type not in ['ahv', 'esxi']:
            raise ValueError("vm_type must be 'ahv' or 'esxi'")
        
        endpoint = f'/vmm/v4.2/{vm_type}/config/vms'
        page_limit = 50  # Reduced from 100 to avoid PLAT-10006 on large VM config list queries
        all_vms = []
        offset = 0
        
        while len(all_vms) < limit:
            current_limit = min(page_limit, limit - len(all_vms))
            params = {
                '$limit': current_limit,
                '$offset': offset,
            }
            
            try:
                response = self._make_request('GET', endpoint, params=params)
                page_data = response.get('data', [])
                
                if not page_data:
                    break
                
                all_vms.extend(page_data)
                
                if len(page_data) < current_limit:
                    break
                
                offset += current_limit
                time.sleep(0.05)
                
            except NutanixAPIException as e:
                logger.error(f"Failed to get VMs for {vm_type} (offset {offset}): {e}")
                break
        
        return all_vms
    
    def get_disks(self, limit: int = 100) -> List[Dict]:
        """
        Get disk information
        
        Args:
            limit: Maximum number of disks to return
            
        Returns:
            List of disk data
        """
        endpoint = '/clustermgmt/v4.2/config/disks'
        params = {'$limit': min(limit, 50)}
        
        try:
            response = self._make_request('GET', endpoint, params=params)
            return response.get('data', [])
        except NutanixAPIException as e:
            logger.error(f"Failed to get disks: {e}")
            return []
    
    def get_cluster_stats(self, cluster_id: str, start_time: datetime, end_time: datetime) -> Dict:
        """
        Get cluster statistics (if available)
        
        Args:
            cluster_id: Cluster ID
            start_time: Start time for stats
            end_time: End time for stats
            
        Returns:
            Cluster stats data
        """
        # Note: This endpoint might not exist in v4.2, but we'll try
        endpoint = f'/clustermgmt/v4.2/stats/clusters/{cluster_id}'
        params = {
            '$startTime': start_time.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            '$endTime': end_time.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        }
        
        try:
            response = self._make_request('GET', endpoint, params=params)
            return response.get('data', {})
        except NutanixAPIException as e:
            logger.debug(f"Cluster stats not available: {e}")
            return {}

    def get_cluster_stats_detailed(self, cluster_id: str, start_time: datetime, end_time: datetime) -> Dict:
        """
        Get detailed cluster statistics including I/O and storage metrics
        
        Args:
            cluster_id: Cluster ID
            start_time: Start time for stats
            end_time: End time for stats
            
        Returns:
            Detailed cluster stats data
        """
        endpoint = f'/clustermgmt/v4.2/stats/clusters/{cluster_id}'
        params = {
            '$startTime': start_time.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            '$endTime': end_time.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            '$statType': 'AVG',
            '$samplingInterval': 300,  # 5 minutes
        }
        
        try:
            response = self._make_request('GET', endpoint, params=params)
            return response.get('data', {})
        except NutanixAPIException as e:
            logger.debug(f"Detailed cluster stats not available for {cluster_id}: {e}")
            return {}
    

    def get_host_stats(self, cluster_id: str, host_id: str, start_time: datetime, end_time: datetime) -> Dict:
        """
        Get host statistics including storage metrics
        
        Args:
            cluster_id: Cluster ID
            host_id: Host ID
            start_time: Start time for stats
            end_time: End time for stats
            
        Returns:
            Host stats data
        """
        endpoint = f'/clustermgmt/v4.2/stats/clusters/{cluster_id}/hosts/{host_id}'
        params = {
            '$startTime': start_time.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            '$endTime': end_time.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            '$statType': 'AVG',
            '$samplingInterval': 300,  # 5 minutes
        }
        
        try:
            response = self._make_request('GET', endpoint, params=params)
            return response.get('data', {})
        except NutanixAPIException as e:
            logger.debug(f"Host stats not available for host {host_id}: {e}")
            return {}
    def get_vm_recovery_points(self, limit: int = 1000) -> List[Dict]:
        """
        Get VM recovery points (snapshots) with pagination
        
        Args:
            limit: Maximum number of recovery points to return (total across all pages)
            
        Returns:
            List of recovery point data
        """
        endpoint = '/vmm/v4.2/ahv/config/vm-recovery-points'
        page_limit = 100  # API maximum per page
        all_recovery_points = []
        offset = 0
        
        while len(all_recovery_points) < limit:
            current_limit = min(page_limit, limit - len(all_recovery_points))
            params = {
                '$limit': current_limit,
                '$offset': offset
            }
            
            try:
                response = self._make_request('GET', endpoint, params=params)
                page_data = response.get('data', [])
                
                if not page_data:
                    break
                
                all_recovery_points.extend(page_data)
                
                # Check if we have more data
                if len(page_data) < current_limit:
                    break
                
                offset += current_limit
                time.sleep(0.05)  # Small delay to respect rate limits
                
            except NutanixAPIException as e:
                logger.error(f"Failed to get VM recovery points (offset {offset}): {e}")
                break
        
        logger.info(f"Retrieved {len(all_recovery_points)} VM recovery points")
        return all_recovery_points
    
    def get_cluster_storage_summary(self, cluster_id: str) -> Dict:
        """
        Get cluster storage summary (calculated from storage containers)
        
        Args:
            cluster_id: Cluster ID
            
        Returns:
            Storage summary data
        """
        try:
            containers = self.get_storage_containers()
            
            total_capacity = 0
            total_used = 0
            
            for container in containers:
                container_cluster = container.get('clusterReference', {}).get('extId')
                if container_cluster == cluster_id:
                    capacity = container.get('config', {}).get('maxCapacityBytes', 0)
                    usage = container.get('stats', {}).get('usageBytes', 0)
                    
                    total_capacity += capacity
                    total_used += usage
            
            return {
                'totalCapacityBytes': total_capacity,
                'totalUsedBytes': total_used,
                'totalFreeBytes': total_capacity - total_used,
                'usagePercentage': (total_used / total_capacity * 100) if total_capacity > 0 else 0
            }
        except Exception as e:
            logger.error(f"Failed to calculate storage summary for cluster {cluster_id}: {e}")
            return {}

    def get_vm_configs(self, vm_type: str = 'ahv', limit: int = 5000) -> List[Dict]:
        """
        Get VM configurations with names and metadata
        
        Args:
            vm_type: VM type ('ahv' or 'esxi')
            limit: Maximum number of VMs to return (total across all pages)
            
        Returns:
            List of VM configuration data including names
        """
        if vm_type not in ['ahv', 'esxi']:
            raise ValueError("vm_type must be 'ahv' or 'esxi'")
        
        endpoint = f'/vmm/v4.2/{vm_type}/config/vms'
        page_limit = 50  # Reduced from 100 to avoid PLAT-10006 on large VM config list queries
        all_vm_configs = []
        offset = 0
        
        while len(all_vm_configs) < limit:
            current_limit = min(page_limit, limit - len(all_vm_configs))
            params = {
                '$limit': current_limit,
                '$offset': offset
            }
            
            try:
                response = self._make_request('GET', endpoint, params=params)
                page_data = response.get('data', [])
                
                if not page_data:
                    break
                
                all_vm_configs.extend(page_data)
                
                # Check if we have more data
                if len(page_data) < current_limit:
                    break
                
                offset += current_limit
                time.sleep(0.05)  # Small delay to respect rate limits
                
            except NutanixAPIException as e:
                logger.error(f"Failed to get VM configs for {vm_type} (offset {offset}): {e}")
                break
        
        logger.info(f"Retrieved {len(all_vm_configs)} {vm_type} VM config records")
        return all_vm_configs

    def get_all_vms_with_names(self, vm_type: str = 'ahv') -> Dict[str, str]:
        """Get VM names by fetching from each cluster separately with pagination.
        
        This works around large unfiltered list issues by fetching VMs per cluster
        in smaller pages.
        """
        try:
            vm_map = {}
            page_limit = 50
            
            # Get all clusters first
            clusters = self.get_clusters(limit=50)
            logger.info(f"Found {len(clusters)} clusters for {vm_type} VM name mapping")
            
            if not clusters:
                # Fall back to non-filtered approach if no clusters found
                logger.warning("No clusters found, trying unfiltered VM fetch")
                return self._get_vms_unfiltered(vm_type)
            
            # Fetch VMs from each cluster with pagination
            for cluster in clusters:
                cluster_id = cluster.get('extId')
                cluster_name = cluster.get('name', 'unknown')
                
                if not cluster_id:
                    continue
                cluster_vm_count = 0
                offset = 0
                previous_page_ids = set()  # Track IDs from previous page to detect duplicates
                
                try:
                    while True:
                        params = {
                            '$limit': page_limit,  # Reduced from 100 to avoid PLAT-10006 on large per-cluster VM list queries
                            '$offset': offset,
                            '$filter': f"cluster/extId eq '{cluster_id}'",
                            '$select': 'name,extId,cluster'
                        }
                        
                        response = self._make_request('GET', f'/vmm/v4.2/{vm_type}/config/vms', params=params)
                        vms = response.get('data', [])
                        
                        if not vms:
                            break
                        
                        
                        # Check for duplicate page (pagination loop detection)
                        current_page_ids = {vm.get('extId') for vm in vms if vm.get('extId')}
                        if offset > 0 and current_page_ids == previous_page_ids:
                            logger.warning(f"Cluster {cluster_name}: detected duplicate page at offset {offset}, breaking pagination loop")
                            break
                        
                        previous_page_ids = current_page_ids
                        cluster_vm_count += len(vms)
                        
                        for vm in vms:
                            vm_id = vm.get('extId')
                            vm_name = vm.get('name', 'unknown')
                            if vm_id:
                                vm_map[vm_id] = vm_name
                        
                        if len(vms) < page_limit:
                            break
                        
                        offset += page_limit
                        time.sleep(0.05)
                    
                    logger.info(f"Cluster {cluster_name}: got {cluster_vm_count} {vm_type} VMs")
                    
                except Exception as e:
                    logger.warning(f"Failed to fetch VMs from cluster {cluster_name}: {e}")
                    continue
            
            logger.info(f"Successfully mapped {len(vm_map)} {vm_type} VM names across all clusters")
            return vm_map
            
        except Exception as e:
            logger.error(f"Error getting VM names: {e}")
            return {}

    def _get_vms_unfiltered(self, vm_type: str) -> Dict[str, str]:
        """Fallback: Get VMs without cluster filtering (original pagination approach)"""
        try:
            vm_map = {}
            page_num = 0
            limit = 50
            max_pages = 100
            use_offset = False
            
            logger.info(f"Starting unfiltered VM name mapping for {vm_type}")
            
            while page_num < max_pages:
                if use_offset:
                    params = {
                        '$offset': page_num * limit,
                        '$limit': limit,
                        '$select': 'name,extId'
                    }
                else:
                    params = {
                        '$page': page_num,
                        '$limit': limit,
                        '$select': 'name,extId'
                    }
                
                try:
                    response = self._make_request('GET', f'/vmm/v4.2/{vm_type}/config/vms', params=params)
                    vms = response.get('data', [])
                    metadata = response.get('metadata', {})
                    total_available = metadata.get('totalAvailableResults', 0)
                    
                    if not vms:
                        break
                    
                    pagination_method = "offset" if use_offset else "$page"
                    logger.info(f"Page {page_num} [{pagination_method}]: got {len(vms)} VMs")
                    
                    for vm in vms:
                        vm_id = vm.get('extId')
                        vm_name = vm.get('name', 'unknown')
                        if vm_id:
                            vm_map[vm_id] = vm_name
                    
                    if len(vms) < limit:
                        break
                    
                    if total_available > 0 and len(vm_map) >= total_available:
                        break
                    
                    page_num += 1
                    
                except Exception as e:
                    error_str = str(e)
                    if 'HTTP 500' in error_str and page_num == 1 and not use_offset:
                        logger.warning(f"$page pagination failed, switching to $offset")
                        use_offset = True
                        continue
                    else:
                        logger.error(f"Error fetching VM names page {page_num}: {e}")
                        page_num += 1
                        if page_num >= max_pages:
                            break
                        continue
            
            logger.info(f"Unfiltered fetch: mapped {len(vm_map)} {vm_type} VM names")
            return vm_map
            
        except Exception as e:
            logger.error(f"Error in unfiltered fetch: {e}")
            return {}

    def get_individual_vm_stats(self, vm_id, start_time, end_time):
        """Get stats for a specific VM by ID using individual endpoint"""
        import requests
        from requests.auth import HTTPBasicAuth
        import urllib3
        
        try:
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            
            url = f"{self.base_url}/api/vmm/v4.2/ahv/stats/vms/{vm_id}"
            
            session = requests.Session()
            session.auth = HTTPBasicAuth(self.session.auth[0], self.session.auth[1])
            session.verify = False
            
            params = {
                '$select': 'stats',
                '$startTime': start_time.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                '$endTime': end_time.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                '$statType': 'AVG',
                '$samplingInterval': 300
            }
            
            response = session.get(url, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                vm_data = data.get('data', {})
                # Individual API returns a single VM object, wrap it in a list for consistent processing
                if vm_data:
                    return [vm_data]  # Wrap in list
                return []
            else:
                return []
                
        except Exception as e:
            return []


    def get_vm_name_by_id(self, vm_id: str, vm_type: str = 'ahv') -> str:
        """Lookup a single VM name by ID - fallback for VMs not in bulk API
        
        Args:
            vm_id: VM UUID
            vm_type: 'ahv' or 'esxi'
            
        Returns:
            VM name or 'unknown' if not found
        """
        try:
            endpoint = f'/vmm/v4.2/{vm_type}/config/vms/{vm_id}'
            params = {'$select': 'name,extId'}
            response = self._make_request('GET', endpoint, params=params)
            vm_data = response.get('data', {})
            return vm_data.get('name', 'unknown')
        except Exception as e:
            logger.debug(f"Could not fetch name for VM {vm_id}: {e}")
            return 'unknown'
