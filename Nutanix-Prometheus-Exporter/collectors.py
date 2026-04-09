#!/usr/bin/env python3
"""
Prometheus metric collectors for Nutanix Prism Central
"""

import os
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
from prometheus_client import Gauge, Counter, Info, Histogram
from nutanix_client import NutanixClient, NutanixAPIException


class SystemVMDetector:
    """Detects system VMs excluded from bulk API"""
    def __init__(self):
        self.patterns = ["prism-central", "pc157-", "pcvm", "service-vm", "cvm-"]
    def is_system_vm(self, vm_id, vm_name=""):
        if vm_name:
            return any(p in vm_name.lower() for p in self.patterns)
        return vm_id == "889dfc57-8f7d-4fa1-9e85-abcd75e6a2a2"  # pc157-1

logger = logging.getLogger(__name__)


class BaseCollector:
    """Base class for metric collectors"""
    
    def __init__(self, client: NutanixClient):
        self.client = client
        
    def collect_metrics(self):
        """Collect and update metrics - to be implemented by subclasses"""
        raise NotImplementedError


class VMStatsCollector(BaseCollector):
    """Collector for VM statistics metrics"""
    
    def __init__(self, client: NutanixClient):
        super().__init__(client)
        self.system_vm_detector = SystemVMDetector()
        
        # CPU metrics
        self.vm_cpu_usage_ppm = Gauge(
            'nutanix_vm_cpu_usage_ppm',
            'VM CPU usage in parts per million',
            ['vm_id', 'vm_name', 'cluster', 'vm_type']
        )
        
        self.vm_cpu_ready_time_ppm = Gauge(
            'nutanix_vm_cpu_ready_time_ppm',
            'VM CPU ready time in parts per million',
            ['vm_id', 'vm_name', 'cluster', 'vm_type']
        )
        
        # Memory metrics
        self.vm_guest_memory_usage_ppm = Gauge(
            'nutanix_vm_guest_memory_usage_ppm',
            'VM guest memory usage as percentage in parts per million (1000000 = 100%)',
            ['vm_id', 'vm_name', 'cluster', 'vm_type']
        )
                # Memory usage metrics
        self.vm_memory_usage = Gauge(
            'nutanix_vm_memory_usage_bytes',
            'VM hypervisor memory usage in bytes',
            ['vm_id', 'vm_name', 'cluster', 'vm_type']
        )
        
        
        # Disk I/O metrics
        self.vm_controller_io_latency_micros = Gauge(
            'nutanix_vm_controller_avg_io_latency_micros',
            'VM controller average I/O latency in microseconds',
            ['vm_id', 'vm_name', 'cluster', 'vm_type']
        )
        
        self.vm_controller_read_io_latency_micros = Gauge(
            'nutanix_vm_controller_avg_read_io_latency_micros',
            'VM controller average read I/O latency in microseconds',
            ['vm_id', 'vm_name', 'cluster', 'vm_type']
        )
        
        self.vm_controller_write_io_latency_micros = Gauge(
            'nutanix_vm_controller_avg_write_io_latency_micros',
            'VM controller average write I/O latency in microseconds',
            ['vm_id', 'vm_name', 'cluster', 'vm_type']
        )
        
        self.vm_controller_iops = Gauge(
            'nutanix_vm_controller_iops',
            'VM controller I/O operations per second',
            ['vm_id', 'vm_name', 'cluster', 'vm_type']
        )
        
        self.vm_controller_read_iops = Gauge(
            'nutanix_vm_controller_read_iops',
            'VM controller read I/O operations per second',
            ['vm_id', 'vm_name', 'cluster', 'vm_type']
        )
        
        self.vm_controller_write_iops = Gauge(
            'nutanix_vm_controller_write_iops',
            'VM controller write I/O operations per second',
            ['vm_id', 'vm_name', 'cluster', 'vm_type']
        )
        
        self.vm_controller_io_bandwidth_kbps = Gauge(
            'nutanix_vm_controller_io_bandwidth_kbps',
            'VM controller I/O bandwidth in kilobytes per second',
            ['vm_id', 'vm_name', 'cluster', 'vm_type']
        )
        
        # Storage metrics
        self.vm_controller_user_bytes = Gauge(
            'nutanix_vm_controller_user_bytes',
            'VM controller user bytes',
            ['vm_id', 'vm_name', 'cluster', 'vm_type']
        )
        
        # GPU metrics (if available)
        self.vm_gpu_usage_ppm = Gauge(
            'nutanix_vm_gpu_usage_ppm',
            'VM GPU usage in parts per million',
            ['vm_id', 'vm_name', 'cluster', 'vm_type']
        )
        
        # Disk/Storage metrics
        self.vm_disk_capacity_bytes = Gauge(
            'nutanix_vm_disk_capacity_bytes',
            'VM total disk capacity in bytes',
            ['vm_id', 'vm_name', 'cluster', 'vm_type']
        )
        
        self.vm_disk_usage_bytes = Gauge(
            'nutanix_vm_disk_usage_bytes',
            'VM disk usage in bytes',
            ['vm_id', 'vm_name', 'cluster', 'vm_type']
        )
        
        self.vm_storage_tier_ssd_usage_bytes = Gauge(
            'nutanix_vm_storage_tier_ssd_usage_bytes',
            'VM SSD storage tier usage in bytes',
            ['vm_id', 'vm_name', 'cluster', 'vm_type']
        )
        
        # Network metrics
        self.vm_network_received_bytes = Gauge(
            'nutanix_vm_network_received_bytes',
            'VM total bytes received over the network',
            ['vm_id', 'vm_name', 'cluster', 'vm_type']
        )
        
        self.vm_network_transmitted_bytes = Gauge(
            'nutanix_vm_network_transmitted_bytes',
            'VM total bytes transmitted over the network',
            ['vm_id', 'vm_name', 'cluster', 'vm_type']
        )
        
        self.vm_network_dropped_received_packets = Gauge(
            'nutanix_vm_network_dropped_received_packets',
            'VM number of dropped inbound packets',
            ['vm_id', 'vm_name', 'cluster', 'vm_type']
        )
        
        self.vm_network_dropped_transmitted_packets = Gauge(
            'nutanix_vm_network_dropped_transmitted_packets',
            'VM number of dropped outbound packets',
            ['vm_id', 'vm_name', 'cluster', 'vm_type']
        )
        
        logger.info("Initialized VM stats collector")
    
    def collect_metrics(self):
        """Base collect_metrics method called by main exporter"""
        self._collect_vm_metrics(['ahv', 'esxi'])
    
    def _collect_vm_metrics(self, vm_types: List[str] = ['ahv', 'esxi']):
        """
        Collect VM statistics metrics
        
        Args:
            vm_types: List of VM types to collect stats for
        """
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(minutes=15)  # Last 15 minutes
        
        # Track processed VMs to avoid duplicates across vm_types
        processed_vm_ids = set()

        for vm_type in vm_types:
            try:
                logger.info(f"Getting comprehensive VM name mapping for {vm_type}")
                vm_name_map = self.client.get_all_vms_with_names(vm_type)
                vm_cluster_map = {}  # Will be populated if needed
                pc157_stats = None  # Reset for each vm_type iteration
                
                logger.info(f"Created comprehensive name mapping for {len(vm_name_map)} {vm_type} VMs")
                
                # Debug: Log first few mappings and first few stats VM IDs
                if vm_name_map:
                    first_few_configs = list(vm_name_map.items())[:3]
                    logger.info(f"DEBUG - Sample VM config mappings: {first_few_configs}")
                
                logger.debug(f"Collecting VM stats for {vm_type}")
                vm_stats = self.client.get_vm_stats(start_time, end_time, vm_type, 500)
                
                # Debug: Log first few VM stat IDs
                if vm_stats:
                    first_few_stats = [vm.get('extId', 'no-id') for vm in vm_stats[:3]]
                    logger.info(f"DEBUG - Sample VM stats IDs: {first_few_stats}")
                
                vms_processed = 0
                vms_with_stats = 0
                
                for vm_data in vm_stats:
                    if not isinstance(vm_data, dict):
                        logger.warning(f"Skipping invalid VM data: {type(vm_data)}")
                        continue

                    vm_id = vm_data.get('extId', 'unknown')
                    vms_processed += 1
                    # Skip if we've already processed this VM in a previous vm_type iteration
                    if vm_id in processed_vm_ids:
                        logger.debug(f"Skipping duplicate VM {vm_id} for vm_type {vm_type}")
                        continue
                    processed_vm_ids.add(vm_id)

                    
                    # Check specifically for pc157-1
                    if vm_id == '889dfc57-8f7d-4fa1-9e85-abcd75e6a2a2':
                        logger.info(f"FOUND pc157-1 in VM stats! Processing...")
                    
                    # Use mapped name from config, fallback to 'unknown'
                    # Try bulk map first, then individual lookup as fallback
                    vm_name = vm_name_map.get(vm_id)
                    if vm_name is None:
                        # VM not in bulk API - try individual lookup (with caching)
                        if not hasattr(self, '_vm_name_cache'):
                            self._vm_name_cache = {}
                        
                        if vm_id not in self._vm_name_cache:
                            # Try current vm_type first, then alternate type (cross-type VMs)
                            vm_name = self.client.get_vm_name_by_id(vm_id, vm_type)
                            if vm_name == 'unknown':
                                # Try alternate type (ahv<->esxi)
                                alt_type = 'esxi' if vm_type == 'ahv' else 'ahv'
                                vm_name = self.client.get_vm_name_by_id(vm_id, alt_type)
                                if vm_name != 'unknown':
                                    logger.debug(f"VM {vm_id} found as {alt_type} type: {vm_name}")
                            self._vm_name_cache[vm_id] = vm_name
                            logger.debug(f"Fetched name for {vm_id}: {vm_name}")
                        else:
                            vm_name = self._vm_name_cache[vm_id]
                    cluster = vm_cluster_map.get(vm_id, 'unknown')
                    
                    # Debug first few mappings
                    if vm_data == vm_stats[0]:
                        logger.info(f"DEBUG - First VM: ID={vm_id}, mapped_name={vm_name}, cluster={cluster}")
                    
                    # Get the latest stats
                    stats_list = vm_data.get('stats', [])
                    if not stats_list:
                        # Debug: Check if this is pc157-1
                        if vm_id == '889dfc57-8f7d-4fa1-9e85-abcd75e6a2a2':
                            logger.info(f"pc157-1 found in VM stats but has NO stats data - skipping")
                        continue
                    
                    # Use the most recent stats entry
                    latest_stats = stats_list[-1]
                    labels = [vm_id, vm_name, cluster, vm_type]
                    
                    vms_with_stats += 1
                    
                    # CPU metrics
                    if 'hypervisorCpuUsagePpm' in latest_stats:
                        self.vm_cpu_usage_ppm.labels(*labels).set(
                            latest_stats['hypervisorCpuUsagePpm']
                        )
                    
                    if 'hypervisorCpuReadyTimePpm' in latest_stats:
                        self.vm_cpu_ready_time_ppm.labels(*labels).set(
                            latest_stats['hypervisorCpuReadyTimePpm']
                        )
                    
                    # Memory metrics
                    if 'guestMemoryUsagePpm' in latest_stats:
                        self.vm_guest_memory_usage_ppm.labels(*labels).set(
                            latest_stats['guestMemoryUsagePpm']
                        )
                    
                    # I/O latency metrics
                    if 'controllerAvgIoLatencyMicros' in latest_stats:
                        self.vm_controller_io_latency_micros.labels(*labels).set(
                            latest_stats['controllerAvgIoLatencyMicros']
                        )
                    
                    if 'controllerAvgReadIoLatencyMicros' in latest_stats:
                        self.vm_controller_read_io_latency_micros.labels(*labels).set(
                            latest_stats['controllerAvgReadIoLatencyMicros']
                        )
                    
                    if 'controllerAvgWriteIoLatencyMicros' in latest_stats:
                        self.vm_controller_write_io_latency_micros.labels(*labels).set(
                            latest_stats['controllerAvgWriteIoLatencyMicros']
                        )
                    
                    # IOPS metrics
                    if 'controllerNumIops' in latest_stats:
                        self.vm_controller_iops.labels(*labels).set(
                            latest_stats['controllerNumIops']
                        )
                    
                    if 'controllerNumReadIops' in latest_stats:
                        self.vm_controller_read_iops.labels(*labels).set(
                            latest_stats['controllerNumReadIops']
                        )
                    
                    if 'controllerNumWriteIops' in latest_stats:
                        self.vm_controller_write_iops.labels(*labels).set(
                            latest_stats['controllerNumWriteIops']
                        )
                    
                    # Bandwidth metrics
                    if 'controllerIoBandwidthKbps' in latest_stats:
                        self.vm_controller_io_bandwidth_kbps.labels(*labels).set(
                            latest_stats['controllerIoBandwidthKbps']
                        )
                    
                    # Disk/Storage metrics
                    if 'diskCapacityBytes' in latest_stats:
                        disk_capacity = latest_stats['diskCapacityBytes']
                        self.vm_disk_capacity_bytes.labels(*labels).set(disk_capacity)
                        
                        # Calculate disk usage from diskUsagePpm
                        if 'diskUsagePpm' in latest_stats:
                            disk_usage_ppm = latest_stats['diskUsagePpm']
                            # diskUsagePpm is parts per million, convert to bytes
                            disk_usage = (disk_usage_ppm / 1000000.0) * disk_capacity
                            self.vm_disk_usage_bytes.labels(*labels).set(disk_usage)
                    
                    # SSD tier storage
                    if 'controllerStorageTierSsdUsageBytes' in latest_stats:
                        self.vm_storage_tier_ssd_usage_bytes.labels(*labels).set(
                            latest_stats['controllerStorageTierSsdUsageBytes']
                        )
                    
                    # Network metrics
                    if 'hypervisorNumReceivedBytes' in latest_stats:
                        self.vm_network_received_bytes.labels(*labels).set(
                            latest_stats['hypervisorNumReceivedBytes']
                        )
                    
                    if 'hypervisorNumTransmittedBytes' in latest_stats:
                        self.vm_network_transmitted_bytes.labels(*labels).set(
                            latest_stats['hypervisorNumTransmittedBytes']
                        )
                    
                    if 'hypervisorNumReceivePacketsDropped' in latest_stats:
                        self.vm_network_dropped_received_packets.labels(*labels).set(
                            latest_stats['hypervisorNumReceivePacketsDropped']
                        )
                    
                    if 'hypervisorNumTransmitPacketsDropped' in latest_stats:
                        self.vm_network_dropped_transmitted_packets.labels(*labels).set(
                            latest_stats['hypervisorNumTransmitPacketsDropped']
                        )
                    

                
                logger.info(f"Processed {vms_processed} {vm_type} VM records, {vms_with_stats} had stats data")
                
                # Fetch individual stats for VMs in config but not in bulk stats
                stats_vm_ids = set(vm_data.get('extId') for vm_data in vm_stats if isinstance(vm_data, dict))
                config_vm_ids = set(vm_name_map.keys())
                missing_vm_ids = config_vm_ids - stats_vm_ids
                
                if missing_vm_ids:
                    logger.info(f"Found {len(missing_vm_ids)} VMs in config but not in bulk stats, fetching individually...")
                    individual_fetched = 0
                    
                    for vm_id in list(missing_vm_ids)[:100]:  # Limit to 50 to avoid too many API calls
                        try:
                            vm_name = vm_name_map.get(vm_id, 'unknown')
                            individual_stats = self.client.get_individual_vm_stats(vm_id, start_time, end_time)
                            
                            if individual_stats and len(individual_stats) > 0:
                                # Process the individual stats
                                vm_data = individual_stats[0]
                                vm_data['extId'] = vm_id  # Ensure ID is set
                                
                                cluster = vm_cluster_map.get(vm_id, 'unknown')
                                labels = [vm_id, vm_name, cluster, vm_type]
                                
                                stats_list = vm_data.get('stats', [])
                                if stats_list:
                                    latest_stats = stats_list[-1]
                                    
                                    # CPU metrics
                                    if 'hypervisorCpuUsagePpm' in latest_stats:
                                        self.vm_cpu_usage_ppm.labels(*labels).set(latest_stats['hypervisorCpuUsagePpm'])
                                    if 'hypervisorCpuReadyTimePpm' in latest_stats:
                                        self.vm_cpu_ready_time_ppm.labels(*labels).set(latest_stats['hypervisorCpuReadyTimePpm'])
                                    
                                    # Memory metrics
                                    if 'guestMemoryUsagePpm' in latest_stats:
                                        self.vm_guest_memory_usage_ppm.labels(*labels).set(latest_stats['guestMemoryUsagePpm'])
                                    
                                    # Storage metrics
                                    if 'controllerAvgIoLatencyMicros' in latest_stats:
                                        self.vm_controller_io_latency_micros.labels(*labels).set(latest_stats['controllerAvgIoLatencyMicros'])
                                    if 'controllerAvgReadIoLatencyMicros' in latest_stats:
                                        self.vm_controller_read_io_latency_micros.labels(*labels).set(latest_stats['controllerAvgReadIoLatencyMicros'])
                                    if 'controllerAvgWriteIoLatencyMicros' in latest_stats:
                                        self.vm_controller_write_io_latency_micros.labels(*labels).set(latest_stats['controllerAvgWriteIoLatencyMicros'])
                                    if 'controllerNumIops' in latest_stats:
                                        self.vm_controller_iops.labels(*labels).set(latest_stats['controllerNumIops'])
                                    if 'controllerNumReadIops' in latest_stats:
                                        self.vm_controller_read_iops.labels(*labels).set(latest_stats['controllerNumReadIops'])
                                    if 'controllerNumWriteIops' in latest_stats:
                                        self.vm_controller_write_iops.labels(*labels).set(latest_stats['controllerNumWriteIops'])
                                    if 'controllerIoBandwidthKbps' in latest_stats:
                                        self.vm_controller_io_bandwidth_kbps.labels(*labels).set(latest_stats['controllerIoBandwidthKbps'])
                                    
                                    individual_fetched += 1
                                    logger.debug(f"Fetched individual stats for {vm_name} ({vm_id})")
                        except Exception as e:
                            logger.debug(f"Could not fetch individual stats for {vm_id}: {e}")
                            continue
                    
                    logger.info(f"Successfully fetched individual stats for {individual_fetched}/{len(missing_vm_ids)} missing VMs")

                logger.info(f"Collected metrics for {vms_with_stats} {vm_type} VMs (including individual lookups)")
                
            except Exception as e:
                logger.error(f"Error collecting VM stats for {vm_type}: {e}")

class ClusterCollector(BaseCollector):
    """Collector for cluster health and infrastructure metrics"""
    
    def __init__(self, client: NutanixClient):
        super().__init__(client)
        self.system_vm_detector = SystemVMDetector()
        
        # Cluster info
        self.cluster_info = Info(
            'nutanix_cluster_info',
            'Cluster information',
            ['cluster_id', 'cluster_name', 'version']
        )
        
        # Cluster node metrics
        self.cluster_nodes_total = Gauge(
            'nutanix_cluster_nodes_total',
            'Total number of nodes in cluster',
            ['cluster_id', 'cluster_name']
        )
        
        self.cluster_nodes_healthy = Gauge(
            'nutanix_cluster_nodes_healthy',
            'Number of healthy nodes in cluster',
            ['cluster_id', 'cluster_name']
        )
        
        # Host metrics
        self.host_cpu_capacity_hz = Gauge(
            'nutanix_host_cpu_capacity_hz',
            'Host CPU capacity in Hz',
            ['host_id', 'host_name', 'cluster_id', 'cluster_name']
        )
        
        self.host_memory_capacity_bytes = Gauge(
            'nutanix_host_memory_capacity_bytes',
            'Host memory capacity in bytes',
            ['host_id', 'host_name', 'cluster_id', 'cluster_name']
        )
        
        # Storage container metrics
        self.storage_container_capacity_bytes = Gauge(
            'nutanix_storage_container_capacity_bytes',
            'Storage container capacity in bytes',
            ['container_id', 'container_name', 'cluster_id']
        )
        
        self.storage_container_usage_bytes = Gauge(
            'nutanix_storage_container_usage_bytes',
            'Storage container usage in bytes',
            ['container_id', 'container_name', 'cluster_id']
        )
        
        # Cluster storage metrics
        self.cluster_storage_usage_bytes = Gauge(
            'nutanix_cluster_storage_usage_bytes',
            'Cluster storage usage in bytes (logical)',
            ['cluster_id', 'cluster_name']
        )
        
        self.cluster_storage_capacity_bytes = Gauge(
            'nutanix_cluster_storage_capacity_bytes',
            'Cluster storage capacity in bytes (total)',
            ['cluster_id', 'cluster_name']
        )
        
        self.cluster_storage_free_bytes = Gauge(
            'nutanix_cluster_storage_free_bytes',
            'Cluster free physical storage in bytes',
            ['cluster_id', 'cluster_name']
        )
        
        self.cluster_storage_logical_usage_bytes = Gauge(
            'nutanix_cluster_storage_logical_usage_bytes',
            'Cluster logical storage usage in bytes',
            ['cluster_id', 'cluster_name']
        )
        
        self.cluster_snapshot_capacity_bytes = Gauge(
            'nutanix_cluster_snapshot_capacity_bytes',
            'Cluster snapshot capacity in bytes',
            ['cluster_id', 'cluster_name']
        )
        
        self.cluster_recycle_bin_usage_bytes = Gauge(
            'nutanix_cluster_recycle_bin_usage_bytes',
            'Cluster recycle bin usage in bytes',
            ['cluster_id', 'cluster_name']
        )
        
        self.cluster_storage_savings_bytes = Gauge(
            'nutanix_cluster_storage_savings_bytes',
            'Cluster storage savings from dedup/compression in bytes',
            ['cluster_id', 'cluster_name']
        )
        
        self.cluster_storage_savings_ratio = Gauge(
            'nutanix_cluster_storage_savings_ratio',
            'Cluster storage savings ratio',
            ['cluster_id', 'cluster_name']
        )
        
        logger.info("Initialized cluster collector")
    
    def collect_metrics(self):
        """Collect cluster and infrastructure metrics"""
        try:
            # Collect cluster information
            clusters = self.client.get_clusters()
            
            for cluster in clusters:
                cluster_id = cluster.get('extId', 'unknown')
                cluster_name = cluster.get('name', 'unknown')
                cluster_version = cluster.get('config', {}).get('softwareVersion', 'unknown')
                
                # Set cluster info
                self.cluster_info.labels(
                    cluster_id=cluster_id,
                    cluster_name=cluster_name,
                    version=cluster_version
                ).info({
                    'hypervisor_type': cluster.get('config', {}).get('hypervisorType', 'unknown'),
                    'timezone': cluster.get('config', {}).get('timezone', 'unknown')
                })
                
                # Get hosts for this cluster
                hosts = self.client.get_hosts(cluster_id)
                
                total_nodes = len(hosts)
                healthy_nodes = sum(1 for host in hosts 
                                  if host.get('status', {}).get('state') == 'NORMAL')
                
                self.cluster_nodes_total.labels(cluster_id, cluster_name).set(total_nodes)
                self.cluster_nodes_healthy.labels(cluster_id, cluster_name).set(healthy_nodes)
                
                # Collect host metrics
                for host in hosts:
                    host_id = host.get('extId', 'unknown')
                    host_name = host.get('name', 'unknown')
                    
                    # CPU capacity
                    cpu_capacity = host.get('config', {}).get('cpuCapacityHz')
                    if cpu_capacity:
                        self.host_cpu_capacity_hz.labels(
                            host_id, host_name, cluster_id, cluster_name
                        ).set(cpu_capacity)
                    
                    # Memory capacity
                    memory_capacity = host.get('config', {}).get('memoryCapacityBytes')
                    if memory_capacity:
                        self.host_memory_capacity_bytes.labels(
                            host_id, host_name, cluster_id, cluster_name
                        ).set(memory_capacity)
            
            logger.info(f"Collected metrics for {len(clusters)} clusters")
            
            # Collect storage container metrics
            containers = self.client.get_storage_containers()
            
            for container in containers:
                container_id = container.get('extId', 'unknown')
                container_name = container.get('name', 'unknown')
                cluster_ref = container.get('clusterReference', {})
                cluster_id = cluster_ref.get('extId', 'unknown')
                
                # Storage capacity and usage
                capacity = container.get('config', {}).get('maxCapacityBytes')
                usage = container.get('stats', {}).get('usageBytes')
                
                if capacity:
                    self.storage_container_capacity_bytes.labels(
                        container_id, container_name, cluster_id
                    ).set(capacity)
                
                if usage:
                    self.storage_container_usage_bytes.labels(
                        container_id, container_name, cluster_id
                    ).set(usage)
            
            logger.info(f"Collected metrics for {len(containers)} storage containers")
            
            # Collect cluster storage stats
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(minutes=15)
            
            for cluster in clusters:
                cluster_id = cluster.get('extId', 'unknown')
                cluster_name = cluster.get('name', 'unknown')
                
                try:
                    stats = self.client.get_cluster_stats_detailed(cluster_id, start_time, end_time)
                    
                    if stats:
                        # Helper function to get latest value from TimeValuePair array
                        def get_latest(data_array):
                            if data_array and len(data_array) > 0:
                                latest_item = data_array[-1]
                                if isinstance(latest_item, dict):
                                    return latest_item.get('value')
                            return None
                        
                        # Storage usage (logical)
                        storage_usage = get_latest(stats.get('storageUsageBytes', []))
                        if storage_usage is not None:
                            self.cluster_storage_usage_bytes.labels(cluster_id, cluster_name).set(storage_usage)
                        
                        # Storage capacity (total)
                        storage_capacity = get_latest(stats.get('storageCapacityBytes', []))
                        if storage_capacity is not None:
                            self.cluster_storage_capacity_bytes.labels(cluster_id, cluster_name).set(storage_capacity)
                        
                        # Free physical storage
                        free_storage = get_latest(stats.get('freePhysicalStorageBytes', []))
                        if free_storage is not None:
                            self.cluster_storage_free_bytes.labels(cluster_id, cluster_name).set(free_storage)
                        
                        # Logical storage usage
                        logical_usage = get_latest(stats.get('logicalStorageUsageBytes', []))
                        if logical_usage is not None:
                            self.cluster_storage_logical_usage_bytes.labels(cluster_id, cluster_name).set(logical_usage)
                        
                        # Snapshot capacity
                        snapshot_capacity = get_latest(stats.get('snapshotCapacityBytes', []))
                        if snapshot_capacity is not None:
                            self.cluster_snapshot_capacity_bytes.labels(cluster_id, cluster_name).set(snapshot_capacity)
                        
                        # Recycle bin usage
                        recycle_bin = get_latest(stats.get('recycleBinUsageBytes', []))
                        if recycle_bin is not None:
                            self.cluster_recycle_bin_usage_bytes.labels(cluster_id, cluster_name).set(recycle_bin)
                        
                        # Storage savings from dedup/compression
                        savings_bytes = get_latest(stats.get('overallSavingsBytes', []))
                        if savings_bytes is not None:
                            self.cluster_storage_savings_bytes.labels(cluster_id, cluster_name).set(savings_bytes)
                        
                        # Storage savings ratio
                        savings_ratio = get_latest(stats.get('overallSavingsRatio', []))
                        if savings_ratio is not None:
                            self.cluster_storage_savings_ratio.labels(cluster_id, cluster_name).set(savings_ratio)
                        
                except Exception as e:
                    logger.debug(f"Failed to collect storage stats for cluster {cluster_name}: {e}")
            
            
        except Exception as e:
            logger.error(f"Failed to collect cluster metrics: {e}")


class AlertCollector(BaseCollector):
    """Collector for alert metrics"""
    
    def __init__(self, client: NutanixClient):
        super().__init__(client)
        self.system_vm_detector = SystemVMDetector()
        
        self.alerts_total = Gauge(
            'nutanix_alerts_total',
            'Total number of alerts by severity',
            ['severity', 'cluster_id']
        )
        
        self.alert_info = Info(
            'nutanix_alert_info',
            'Alert information',
            ['alert_id', 'severity', 'cluster_id']
        )
        
        logger.info("Initialized alert collector")
    
    def collect_metrics(self):
        """Collect alert metrics"""
        try:
            # Reset all severity counters
            severity_counts = {'INFO': 0, 'WARNING': 0, 'CRITICAL': 0}
            
            # Get all alerts
            alerts = self.client.get_alerts()
            
            for alert in alerts:
                alert_id = alert.get('extId', 'unknown')
                severity = alert.get('severity', 'UNKNOWN')
                cluster_ref = alert.get('clusterReference', {})
                cluster_id = cluster_ref.get('extId', 'unknown')
                
                # Count alerts by severity
                if severity in severity_counts:
                    severity_counts[severity] += 1
                
                # Set alert info
                self.alert_info.labels(
                    alert_id=alert_id,
                    severity=severity,
                    cluster_id=cluster_id
                ).info({
                    'title': alert.get('title', 'unknown'),
                    'message': alert.get('message', 'unknown'),
                    'created_time': alert.get('createdTime', 'unknown')
                })
            
            # Set severity totals
            for severity, count in severity_counts.items():
                self.alerts_total.labels(severity=severity, cluster_id='all').set(count)
            
            logger.info(f"Collected {len(alerts)} alerts")
            
        except Exception as e:
            logger.error(f"Failed to collect alert metrics: {e}")

class InfrastructureCollector(BaseCollector):
    """Collector for comprehensive infrastructure metrics"""
    
    def __init__(self, client: NutanixClient):
        super().__init__(client)
        self.system_vm_detector = SystemVMDetector()
        
        # VM configuration metrics (counts, states, etc.)
        self.vm_total = Gauge(
            'nutanix_vms_total',
            'Total number of VMs by type and state',
            ['vm_type', 'power_state', 'cluster']
        )
        
        self.vm_vcpu_total = Gauge(
            'nutanix_vm_vcpu_total', 
            'Total vCPUs configured for VM',
            ['vm_id', 'vm_name', 'vm_type', 'cluster']
        )
        
        self.vm_memory_bytes = Gauge(
            'nutanix_vm_memory_bytes',
            'Memory configured for VM in bytes',
            ['vm_id', 'vm_name', 'vm_type', 'cluster']
        )
        
        # Disk metrics
        self.disk_total = Gauge(
            'nutanix_disks_total',
            'Total number of disks by status',
            ['disk_status', 'disk_tier', 'cluster_id']
        )
        
        self.disk_capacity_bytes = Gauge(
            'nutanix_disk_capacity_bytes',
            'Disk capacity in bytes',
            ['disk_id', 'disk_status', 'disk_tier', 'host_id', 'cluster_id']
        )
        
        # Additional cluster metrics
        self.cluster_cpu_capacity_hz = Gauge(
            'nutanix_cluster_cpu_capacity_hz',
            'Total cluster CPU capacity in Hz',
            ['cluster_id', 'cluster_name']
        )
        
        self.cluster_memory_capacity_bytes = Gauge(
            'nutanix_cluster_memory_capacity_bytes', 
            'Total cluster memory capacity in bytes',
            ['cluster_id', 'cluster_name']
        )
        
        
        logger.info("Initialized infrastructure collector")
    
    def collect_metrics(self):
        """Collect comprehensive infrastructure metrics"""
        try:
            # Collect VM configuration data
            self._collect_vm_configs()
            
            # Collect disk information
            self._collect_disk_info()
            
            # Collect enhanced cluster info
            self._collect_cluster_resources()
            
        except Exception as e:
            logger.error(f"Failed to collect infrastructure metrics: {e}")
    
    def _collect_vm_configs(self):
        """Collect VM configuration information"""
        for vm_type in ['ahv', 'esxi']:
            try:
                vms = self.client.get_vms(vm_type, limit=100)
                
                # Count VMs by state and cluster
                vm_counts = {}
                
                for vm in vms:
                    # Handle cluster field - can be string or dict reference
                    cluster_ref = vm.get('cluster', 'unknown')
                    if isinstance(cluster_ref, dict):
                        cluster = cluster_ref.get('extId', 'unknown')
                    else:
                        cluster = cluster_ref if cluster_ref else 'unknown'
                    power_state = vm.get('powerState', 'unknown')
                    
                    key = (vm_type, power_state, cluster)
                    vm_counts[key] = vm_counts.get(key, 0) + 1
                    
                    # Individual VM metrics
                    vm_id = vm.get('extId', 'unknown')
                    vm_name = vm.get('name', 'unknown')
                    
                    # vCPU count
                    num_sockets = vm.get('numSockets', 0)
                    num_cores_per_socket = vm.get('numCoresPerSocket', 0) 
                    total_vcpus = num_sockets * num_cores_per_socket
                    
                    if total_vcpus > 0:
                        self.vm_vcpu_total.labels(vm_id, vm_name, vm_type, cluster).set(total_vcpus)
                    
                    # Memory size
                    memory_bytes = vm.get('memorySizeBytes', 0)
                    if memory_bytes > 0:
                        self.vm_memory_bytes.labels(vm_id, vm_name, vm_type, cluster).set(memory_bytes)
                
                # Set VM count metrics
                for (vm_type, power_state, cluster), count in vm_counts.items():
                    self.vm_total.labels(vm_type, power_state, cluster).set(count)
                
                logger.info(f"Collected config for {len(vms)} {vm_type} VMs")
                
            except Exception as e:
                logger.error(f"Failed to collect VM configs for {vm_type}: {e}")
    
    def _collect_disk_info(self):
        """Collect disk information"""
        try:
            disks = self.client.get_disks(limit=100)
            
            disk_counts = {}
            
            for disk in disks:
                disk_id = disk.get('extId', 'unknown')
                disk_status = disk.get('status', 'unknown')
                disk_tier = disk.get('storageClassification', 'unknown')
                host_id = disk.get('hostReference', {}).get('extId', 'unknown')
                cluster_id = disk.get('clusterReference', {}).get('extId', 'unknown')
                
                # Count disks by status and tier
                key = (disk_status, disk_tier, cluster_id)
                disk_counts[key] = disk_counts.get(key, 0) + 1
                
                # Individual disk capacity
                capacity_bytes = disk.get('capacityBytes', 0)
                if capacity_bytes > 0:
                    self.disk_capacity_bytes.labels(
                        disk_id, disk_status, disk_tier, host_id, cluster_id
                    ).set(capacity_bytes)
            
            # Set disk count metrics
            for (disk_status, disk_tier, cluster_id), count in disk_counts.items():
                self.disk_total.labels(disk_status, disk_tier, cluster_id).set(count)
            
            logger.info(f"Collected info for {len(disks)} disks")
            
        except Exception as e:
            logger.error(f"Failed to collect disk info: {e}")
    
    def _collect_cluster_resources(self):
        """Collect enhanced cluster resource information"""
        try:
            clusters = self.client.get_clusters()
            
            for cluster in clusters:
                cluster_id = cluster.get('extId', 'unknown')
                cluster_name = cluster.get('name', 'unknown')
                
                # Get hosts for resource calculations
                hosts = self.client.get_hosts(cluster_id)
                
                total_cpu_hz = 0
                total_memory_bytes = 0
                
                for host in hosts:
                    cpu_capacity = host.get('config', {}).get('cpuCapacityHz', 0)
                    memory_capacity = host.get('config', {}).get('memoryCapacityBytes', 0)
                    
                    total_cpu_hz += cpu_capacity
                    total_memory_bytes += memory_capacity
                
                if total_cpu_hz > 0:
                    self.cluster_cpu_capacity_hz.labels(cluster_id, cluster_name).set(total_cpu_hz)
                
                if total_memory_bytes > 0:
                    self.cluster_memory_capacity_bytes.labels(cluster_id, cluster_name).set(total_memory_bytes)
                
                # Storage capacity from containers
                containers = self.client.get_storage_containers()
                total_storage_bytes = 0
                
                for container in containers:
                    container_cluster = container.get('clusterReference', {}).get('extId')
                    if container_cluster == cluster_id:
                        capacity = container.get('config', {}).get('maxCapacityBytes', 0)
                        total_storage_bytes += capacity
                
                if total_storage_bytes > 0:
                    self.cluster_storage_capacity_bytes.labels(cluster_id, cluster_name).set(total_storage_bytes)
            
            logger.info(f"Collected enhanced metrics for {len(clusters)} clusters")
            
        except Exception as e:
            logger.error(f"Failed to collect cluster resources: {e}")

def get_latest_value(time_series):
    """Extract the most recent value from a list of TimeValuePair objects"""
    if not time_series or not isinstance(time_series, list):
        return 0
    # Time series is sorted oldest to newest, so take the last one
    if len(time_series) > 0:
        return time_series[-1].get('value', 0)
    return 0



class HostStorageCollector(BaseCollector):
    """Collector for per-host storage metrics"""
    
    def __init__(self, client: NutanixClient):
        super().__init__(client)
        
        # Host storage metrics
        self.host_storage_usage_bytes = Gauge(
            'nutanix_host_storage_usage_bytes',
            'Host storage usage in bytes',
            ['host_id', 'host_name', 'cluster_id', 'cluster_name']
        )
        
        self.host_storage_capacity_bytes = Gauge(
            'nutanix_host_storage_capacity_bytes',
            'Host storage capacity in bytes',
            ['host_id', 'host_name', 'cluster_id', 'cluster_name']
        )
        
        self.host_storage_free_bytes = Gauge(
            'nutanix_host_storage_free_bytes',
            'Host free physical storage in bytes',
            ['host_id', 'host_name', 'cluster_id', 'cluster_name']
        )
        
        self.host_storage_logical_usage_bytes = Gauge(
            'nutanix_host_storage_logical_usage_bytes',
            'Host logical storage usage in bytes',
            ['host_id', 'host_name', 'cluster_id', 'cluster_name']
        )
        
        logger.info("Initialized host storage collector")
    
    def collect_metrics(self):
        """Collect per-host storage metrics"""
        try:
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(minutes=15)
            
            # Get all clusters
            clusters = self.client.get_clusters()
            
            for cluster in clusters:
                cluster_id = cluster.get('extId', 'unknown')
                cluster_name = cluster.get('name', 'unknown')
                
                # Get hosts for this cluster
                hosts = self.client.get_hosts(cluster_id)
                
                for host in hosts:
                    host_id = host.get('extId', 'unknown')
                    host_name = host.get('name', 'unknown')
                    
                    try:
                        # Get host stats
                        stats = self.client.get_host_stats(cluster_id, host_id, start_time, end_time)
                        
                        if stats:
                            # Helper function to get latest value from TimeValuePair array
                            def get_latest(data_array):
                                if data_array and len(data_array) > 0:
                                    latest_item = data_array[-1]
                                    if isinstance(latest_item, dict):
                                        return latest_item.get('value')
                                return None
                            
                            labels = [host_id, host_name, cluster_id, cluster_name]
                            
                            # Storage usage
                            storage_usage = get_latest(stats.get('storageUsageBytes', []))
                            if storage_usage is not None:
                                self.host_storage_usage_bytes.labels(*labels).set(storage_usage)
                            
                            # Storage capacity
                            storage_capacity = get_latest(stats.get('storageCapacityBytes', []))
                            if storage_capacity is not None:
                                self.host_storage_capacity_bytes.labels(*labels).set(storage_capacity)
                            
                            # Free physical storage
                            free_storage = get_latest(stats.get('freePhysicalStorageBytes', []))
                            if free_storage is not None:
                                self.host_storage_free_bytes.labels(*labels).set(free_storage)
                            
                            # Logical storage usage
                            logical_usage = get_latest(stats.get('logicalStorageUsageBytes', []))
                            if logical_usage is not None:
                                self.host_storage_logical_usage_bytes.labels(*labels).set(logical_usage)
                        
                    except Exception as e:
                        logger.debug(f"Failed to collect storage stats for host {host_name}: {e}")
            
            logger.info(f"Collected host storage metrics for {sum(len(self.client.get_hosts(c.get('extId'))) for c in clusters)} hosts")
            
        except Exception as e:
            logger.error(f"Failed to collect host storage metrics: {e}")

class ClusterPerformanceCollector:
    """Collector for detailed cluster performance metrics including I/O, latency, and storage"""
    
    def __init__(self, client):
        self.client = client
        
        # Cluster I/O metrics
        self.cluster_read_iops = Gauge('nutanix_cluster_read_iops', 'Cluster read IOPS', ['cluster_name', 'cluster_id'])
        self.cluster_write_iops = Gauge('nutanix_cluster_write_iops', 'Cluster write IOPS', ['cluster_name', 'cluster_id'])
        self.cluster_read_bandwidth_bps = Gauge('nutanix_cluster_read_bandwidth_bytes_per_second', 'Cluster read bandwidth', ['cluster_name', 'cluster_id'])
        self.cluster_write_bandwidth_bps = Gauge('nutanix_cluster_write_bandwidth_bytes_per_second', 'Cluster write bandwidth', ['cluster_name', 'cluster_id'])
        
        # Cluster latency metrics
        self.cluster_avg_io_latency_us = Gauge('nutanix_cluster_avg_io_latency_microseconds', 'Cluster average I/O latency', ['cluster_name', 'cluster_id'])
        self.cluster_avg_read_latency_us = Gauge('nutanix_cluster_avg_read_latency_microseconds', 'Cluster average read latency', ['cluster_name', 'cluster_id'])
        self.cluster_avg_write_latency_us = Gauge('nutanix_cluster_avg_write_latency_microseconds', 'Cluster average write latency', ['cluster_name', 'cluster_id'])
        
        # Cluster storage metrics
        
        # Additional cluster metrics
        self.cluster_cpu_usage_ppm = Gauge('nutanix_cluster_cpu_usage_ppm', 'Cluster CPU usage in PPM', ['cluster_name', 'cluster_id'])
        self.cluster_memory_usage_ppm = Gauge('nutanix_cluster_memory_usage_ppm', 'Cluster memory usage in PPM', ['cluster_name', 'cluster_id'])
        

    def collect_metrics(self):
        """Collect cluster performance metrics"""
        logger.info("Collecting cluster performance metrics...")
        
        try:
            clusters = self.client.get_clusters()
            logger.info(f"Found {len(clusters)} clusters for performance collection")
            
            # Get time range for stats (last 15 minutes)
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(minutes=15)
            
            for cluster in clusters:
                cluster_id = cluster.get('extId', '')
                cluster_name = cluster.get('name', 'unknown')
                
                if not cluster_id:
                    continue
                
                logger.debug(f"Getting performance stats for cluster {cluster_name} ({cluster_id})")
                
                # Get detailed cluster stats
                stats = self.client.get_cluster_stats_detailed(cluster_id, start_time, end_time)
                logger.info(f"Got stats for {cluster_name}: {bool(stats)}, keys: {list(stats.keys())[:10] if stats else None}")
                
                if stats:
                    # Extract I/O metrics
                    self._process_io_metrics(stats, cluster_name, cluster_id)
                    
                    # Extract latency metrics
                    self._process_latency_metrics(stats, cluster_name, cluster_id)
                    
                    # Extract CPU and memory metrics
                    self._process_resource_metrics(stats, cluster_name, cluster_id)
                
                
        except Exception as e:
            logger.error(f"Error collecting cluster performance metrics: {e}")
    
    def _process_io_metrics(self, stats, cluster_name, cluster_id):
        """Process I/O related metrics"""
        try:
            # Read IOPS
            read_iops = get_latest_value(stats.get('controllerNumReadIops', []))
            if read_iops:
                self.cluster_read_iops.labels(cluster_name=cluster_name, cluster_id=cluster_id).set(read_iops)
            
            # Write IOPS
            write_iops = get_latest_value(stats.get('controllerNumWriteIops', []))
            if write_iops:
                self.cluster_write_iops.labels(cluster_name=cluster_name, cluster_id=cluster_id).set(write_iops)
            
            # Read bandwidth (convert KB/s to bytes/s)
            read_kbps = get_latest_value(stats.get('controllerReadIoBandwidthKbps', []))
            if read_kbps:
                self.cluster_read_bandwidth_bps.labels(cluster_name=cluster_name, cluster_id=cluster_id).set(read_kbps * 1024)
            
            # Write bandwidth (convert KB/s to bytes/s)
            write_kbps = get_latest_value(stats.get('controllerWriteIoBandwidthKbps', []))
            if write_kbps:
                self.cluster_write_bandwidth_bps.labels(cluster_name=cluster_name, cluster_id=cluster_id).set(write_kbps * 1024)
                
        except Exception as e:
            logger.error(f"Error processing I/O metrics for cluster {cluster_name}: {e}")
    
    def _process_latency_metrics(self, stats, cluster_name, cluster_id):
        """Process latency related metrics"""
        try:
            # Average I/O latency
            avg_latency = get_latest_value(stats.get('controllerAvgIoLatencyUsecs', []))
            if avg_latency:
                self.cluster_avg_io_latency_us.labels(cluster_name=cluster_name, cluster_id=cluster_id).set(avg_latency)
            
            # Read latency
            read_latency = get_latest_value(stats.get('controllerAvgReadIoLatencyUsecs', []))
            if read_latency:
                self.cluster_avg_read_latency_us.labels(cluster_name=cluster_name, cluster_id=cluster_id).set(read_latency)
            
            # Write latency
            write_latency = get_latest_value(stats.get('controllerAvgWriteIoLatencyUsecs', []))
            if write_latency:
                self.cluster_avg_write_latency_us.labels(cluster_name=cluster_name, cluster_id=cluster_id).set(write_latency)
                
        except Exception as e:
            logger.error(f"Error processing latency metrics for cluster {cluster_name}: {e}")
    
    def _process_resource_metrics(self, stats, cluster_name, cluster_id):
        """Process CPU and memory metrics"""
        try:
            # CPU usage
            cpu_usage = get_latest_value(stats.get('hypervisorCpuUsagePpm', []))
            if cpu_usage:
                self.cluster_cpu_usage_ppm.labels(cluster_name=cluster_name, cluster_id=cluster_id).set(cpu_usage)
            
            # Memory usage
            memory_usage = get_latest_value(stats.get('aggregateHypervisorMemoryUsagePpm', []))
            if memory_usage:
                self.cluster_memory_usage_ppm.labels(cluster_name=cluster_name, cluster_id=cluster_id).set(memory_usage)
                
        except Exception as e:
            logger.error(f"Error processing resource metrics for cluster {cluster_name}: {e}")
    

class VMSnapshotCollector:
    """Collector for VM snapshot/recovery point metrics"""
    
    def __init__(self, client):
        self.client = client
        
        # VM snapshot metrics
        self.vm_snapshots_total = Gauge('nutanix_vm_snapshots_total', 'Total number of VM snapshots', ['vm_name', 'vm_id'])
        self.vm_snapshot_size_bytes = Gauge('nutanix_vm_snapshot_size_bytes', 'VM snapshot size in bytes', ['vm_name', 'vm_id', 'snapshot_name'])
        self.cluster_snapshots_total = Gauge('nutanix_cluster_snapshots_total', 'Total snapshots per cluster', ['cluster_name', 'cluster_id'])
        
    def collect_metrics(self):
        """Collect VM snapshot metrics"""
        logger.info("Collecting VM snapshot metrics...")
        
        try:
            recovery_points = self.client.get_vm_recovery_points()
            
            vm_snapshot_counts = {}
            cluster_snapshot_counts = {}
            
            for rp in recovery_points:
                # Get VM information
                vm_ref = rp.get('vmReference', {})
                vm_id = vm_ref.get('extId', '')
                vm_name = rp.get('vmName', vm_id)
                
                # Get cluster information
                cluster_ref = rp.get('clusterReference', {})
                cluster_id = cluster_ref.get('extId', '')
                
                # Get snapshot information
                snapshot_name = rp.get('name', 'unknown')
                snapshot_size = rp.get('sizeInBytes', 0)
                
                # Count snapshots per VM
                vm_key = (vm_name, vm_id)
                vm_snapshot_counts[vm_key] = vm_snapshot_counts.get(vm_key, 0) + 1
                
                # Count snapshots per cluster
                if cluster_id:
                    cluster_snapshot_counts[cluster_id] = cluster_snapshot_counts.get(cluster_id, 0) + 1
                
                # Set individual snapshot size metric
                if snapshot_size > 0:
                    self.vm_snapshot_size_bytes.labels(
                        vm_name=vm_name,
                        vm_id=vm_id,
                        snapshot_name=snapshot_name
                    ).set(snapshot_size)
            
            # Set VM snapshot count metrics
            for (vm_name, vm_id), count in vm_snapshot_counts.items():
                self.vm_snapshots_total.labels(vm_name=vm_name, vm_id=vm_id).set(count)
            
            # Set cluster snapshot count metrics
            clusters = self.client.get_clusters()
            cluster_names = {c.get('extId'): c.get('name', 'unknown') for c in clusters}
            
            for cluster_id, count in cluster_snapshot_counts.items():
                cluster_name = cluster_names.get(cluster_id, 'unknown')
                self.cluster_snapshots_total.labels(cluster_name=cluster_name, cluster_id=cluster_id).set(count)
            
            logger.info(f"Collected snapshot data for {len(vm_snapshot_counts)} VMs across {len(cluster_snapshot_counts)} clusters")
            
        except Exception as e:
            logger.error(f"Error collecting VM snapshot metrics: {e}")
