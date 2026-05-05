#!/usr/bin/env python3

import os
import time
import logging
import threading
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST, CollectorRegistry
from nutanix_client import NutanixClient
from collectors import VMStatsCollector, ClusterCollector, AlertCollector, InfrastructureCollector, HostStorageCollector, ClusterPerformanceCollector, VMSnapshotCollector

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class NutanixExporter:
    def __init__(self):
        self.prism_central_url = os.environ.get('PRISM_CENTRAL_URL', 'https://localhost:9440')
        self.username = os.environ.get('USERNAME', 'admin')
        self.password = os.environ.get('PASSWORD', 'nutanix/4u')
        self.port = int(os.environ.get('PORT', '8080'))
        self.scrape_interval = int(os.environ.get('SCRAPE_INTERVAL', '300'))
        self.verify_ssl = os.environ.get('TLS_VERIFY', 'true').lower() == 'true'
        
        # Initialize client
        self.client = NutanixClient(
            base_url=self.prism_central_url,
            username=self.username,
            password=self.password,
            verify_ssl=self.verify_ssl,
        )
        
        # Initialize collectors
        self.collectors = [
            VMStatsCollector(self.client),
            ClusterCollector(self.client),
            AlertCollector(self.client),
            InfrastructureCollector(self.client),
            HostStorageCollector(self.client),
            ClusterPerformanceCollector(self.client),
            VMSnapshotCollector(self.client)
        ]
        
        self.registry = CollectorRegistry()
        self.last_scrape_time = 0
        self.scrape_lock = threading.Lock()
        
        logger.info(f"Nutanix Prometheus Exporter initialized")
        logger.info(f"Prism Central URL: {self.prism_central_url}")
        logger.info(f"Port: {self.port}")
        logger.info(f"Scrape interval: {self.scrape_interval} seconds")
    
    def collect_all_metrics(self):
        """Collect metrics from all collectors"""
        with self.scrape_lock:
            current_time = time.time()
            if current_time - self.last_scrape_time < self.scrape_interval:
                logger.debug("Skipping scrape due to interval")
                return
            
            logger.info("Starting metrics collection...")
            start_time = time.time()
            
            for collector in self.collectors:
                try:
                    collector_name = collector.__class__.__name__
                    logger.debug(f"Collecting metrics from {collector_name}")
                    collector.collect_metrics()
                except Exception as e:
                    logger.error(f"Error in collector {collector.__class__.__name__}: {e}")
            
            self.last_scrape_time = current_time
            duration = time.time() - start_time
            logger.info(f"Metrics collection completed in {duration:.2f} seconds")

class MetricsHandler(BaseHTTPRequestHandler):
    def __init__(self, exporter):
        self.exporter = exporter
    
    def __call__(self, *args):
        super().__init__(*args)
    
    def do_GET(self):
        if self.path == '/metrics':
            try:
                self.exporter.collect_all_metrics()
                
                # Generate Prometheus metrics
                output = generate_latest()
                
                self.send_response(200)
                self.send_header('Content-Type', CONTENT_TYPE_LATEST)
                self.send_header('Content-Length', str(len(output)))
                self.end_headers()
                self.wfile.write(output)
                
                logger.debug(f"Served metrics request from {self.client_address[0]}")
                
            except (ConnectionResetError, BrokenPipeError) as e:
                # Client disconnected - data may have been sent successfully
                # This is common with Prometheus scrapes and not necessarily an error
                logger.debug(f"Connection closed by client: {e}")
            except Exception as e:
                logger.error(f"Error generating metrics: {e}")
                try:
                    self.send_error(500, f"Error generating metrics: {e}")
                except (ConnectionResetError, BrokenPipeError):
                    pass  # Can't send error, connection already closed
        
        elif self.path == '/health':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"status": "healthy"}')
        
        else:
            self.send_error(404, "Not Found")
    
    def log_message(self, format, *args):
        # Suppress default HTTP logging
        pass

def main():
    try:
        exporter = NutanixExporter()
        
        # Test connection
        logger.info("Testing connection to Prism Central...")
        clusters = exporter.client.get_clusters()
        logger.info(f"Successfully connected. Found {len(clusters)} clusters.")
        
        # Start HTTP server
        handler = lambda *args: MetricsHandler(exporter)(*args)
        httpd = ThreadingHTTPServer(('0.0.0.0', exporter.port), handler)
        
        logger.info(f"Starting HTTP server on port {exporter.port}")
        logger.info("Available endpoints:")
        logger.info("  /metrics - Prometheus metrics")
        logger.info("  /health  - Health check")
        
        httpd.serve_forever()
        
    except KeyboardInterrupt:
        logger.info("Received interrupt signal, shutting down...")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        raise

if __name__ == '__main__':
    main()
