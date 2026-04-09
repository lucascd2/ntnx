# Nutanix Prism Central Prometheus Exporter

A production-ready Python-based Prometheus exporter for Nutanix Prism Central v4.2 APIs. Collects comprehensive metrics from AHV and ESXi environments including VM statistics, cluster health, storage, and alerts.

---

## Features

- **40+ VM Metrics per VM**: CPU, memory, guest memory, storage I/O, network, controller statistics
- **Cluster Health**: Performance metrics, resource utilization, health status
- **Storage Metrics**: Container capacity, usage, and performance (26+ containers)
- **Alert Monitoring**: Active alerts from Nutanix monitoring system (100+ alerts)
- **Infrastructure**: Host-level metrics and configuration data
- **Automatic System VM Detection**: Detects and monitors system VMs (Prism Central VMs, CVMs)
- **Multi-Platform**: Supports both AHV and ESXi hypervisors
- **Advanced Features**:
  - Hybrid collection with individual VM fallback for system VMs
  - Automatic VM name mapping with pagination (supports 10,000+ VMs)
  - Configurable sampling intervals and collection parameters

---

## System Requirements & Dependencies

### Ubuntu/Debian System Packages

Install required system packages before deploying the exporter:

```bash
# Update package list
sudo apt update

# Install Docker
sudo apt install -y docker.io

# Start and enable Docker
sudo systemctl start docker
sudo systemctl enable docker

# Add current user to docker group (optional - allows running docker without sudo)
sudo usermod -aG docker $USER
# Note: Log out and back in for group changes to take effect

# Verify Docker installation
docker --version

# Install additional utilities (optional but recommended)
sudo apt install -y curl wget git nano
```

### Install Prometheus (Optional - for local testing)

If you want to run Prometheus locally on the same machine:

```bash
# Download Prometheus
cd /tmp
wget https://github.com/prometheus/prometheus/releases/download/v2.45.0/prometheus-2.45.0.linux-amd64.tar.gz

# Extract
tar xvfz prometheus-2.45.0.linux-amd64.tar.gz

# Move to /opt
sudo mv prometheus-2.45.0.linux-amd64 /opt/prometheus

# Create Prometheus user
sudo useradd --no-create-home --shell /bin/false prometheus

# Create directories
sudo mkdir -p /etc/prometheus /var/lib/prometheus

# Set ownership
sudo chown -R prometheus:prometheus /opt/prometheus /etc/prometheus /var/lib/prometheus

# Create systemd service
sudo cat > /etc/systemd/system/prometheus.service << 'EOF'
[Unit]
Description=Prometheus
Wants=network-online.target
After=network-online.target

[Service]
User=prometheus
Group=prometheus
Type=simple
ExecStart=/opt/prometheus/prometheus   --config.file=/etc/prometheus/prometheus.yml   --storage.tsdb.path=/var/lib/prometheus/

[Install]
WantedBy=multi-user.target
EOF

# Create basic config
sudo cat > /etc/prometheus/prometheus.yml << 'EOF'
global:
  scrape_interval: 60s
  scrape_timeout: 30s

scrape_configs:
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  - job_name: 'nutanix-exporter'
    static_configs:
      - targets: ['localhost:8080']
EOF

# Set permissions
sudo chown prometheus:prometheus /etc/prometheus/prometheus.yml

# Start Prometheus
sudo systemctl daemon-reload
sudo systemctl start prometheus
sudo systemctl enable prometheus

# Check status
sudo systemctl status prometheus

# Access Prometheus at http://localhost:9090
```

### Install Grafana (Optional - for visualization)

If you want to run Grafana locally:

```bash
# Add Grafana GPG key
sudo apt-get install -y software-properties-common
wget -q -O - https://packages.grafana.com/gpg.key | sudo apt-key add -

# Add Grafana repository
echo "deb https://packages.grafana.com/oss/deb stable main" | sudo tee /etc/apt/sources.list.d/grafana.list

# Update and install
sudo apt update
sudo apt install -y grafana

# Start Grafana
sudo systemctl start grafana-server
sudo systemctl enable grafana-server

# Check status
sudo systemctl status grafana-server

# Access Grafana at http://localhost:3000
# Default credentials: admin/admin
```

### Python Dependencies (For Development Only)

**Note**: You do NOT need Python installed on the host system when using Docker. The Docker container includes all Python dependencies.

If you want to develop or test without Docker:

```bash
# Install Python 3.11+
sudo apt install -y python3 python3-pip python3-venv

# Verify installation
python3 --version

# Create virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run exporter (without Docker)
python3 nutanix_exporter.py
```

---

## Quick Start

### Prerequisites

- **Docker** installed on Linux system
- **Nutanix Prism Central** v4.2 or later
- Network access to Prism Central API (port 9440)
- Valid Prism Central credentials with read access

### Installation (5 Minutes)

```bash
# 1. Create directory
mkdir -p /home/nutanix/prometheus
cd /home/nutanix/prometheus

# 2. Download/copy exporter files
# (Copy all files from repository to this directory)

# 3. Configure credentials
cat > .env << 'ENVFILE'
# Prism Central Connection (REQUIRED)
PRISM_CENTRAL_URL=https://10.42.157.19:9440
PRISM_USERNAME=your-username@domain.local
PRISM_PASSWORD=your-password

# TLS Settings
TLS_VERIFY=false

# VM Types to Monitor (comma-separated)
VM_TYPES=ahv,esxi

# Optional: Metrics Collection Settings
METRICS_PORT=8080
COLLECTION_INTERVAL=60
REQUEST_TIMEOUT=30
LOG_LEVEL=INFO
ENVFILE

# 4. Edit .env with your actual credentials
nano .env

# 5. Build Docker image
sudo docker build -t nutanix-prometheus-exporter:latest .

# 6. Run container
sudo docker run -d \
  --name nutanix-exporter \
  --env-file .env \
  -p 8080:8080 \
  --restart unless-stopped \
  nutanix-prometheus-exporter:latest

# 7. Verify it's running
sudo docker logs -f nutanix-exporter
curl http://localhost:8080/metrics | grep nutanix_vm_cpu
```

**Done!** Metrics available at `http://localhost:8080/metrics`

---

## Configuration Reference

### Environment Variables (.env file)

#### Required Configuration

| Variable | Description | Example |
|----------|-------------|---------|
| `PRISM_CENTRAL_URL` | Full URL to Prism Central | `https://10.42.157.19:9440` |
| `PRISM_USERNAME` | Username with API access | `admin@domain.local` |
| `PRISM_PASSWORD` | Password for authentication | `SecurePassword123!` |

#### Optional Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `TLS_VERIFY` | `true` | Verify TLS certificates (`false` for self-signed) |
| `VM_TYPES` | `ahv` | VM types to collect: `ahv`, `esxi`, or `ahv,esxi` |
| `METRICS_PORT` | `8080` | Port to expose metrics endpoint |
| `COLLECTION_INTERVAL` | `60` | Metrics collection interval (seconds) |
| `REQUEST_TIMEOUT` | `30` | API request timeout (seconds) |
| `LOG_LEVEL` | `INFO` | Logging level: `DEBUG`, `INFO`, `WARNING`, `ERROR` |

#### Advanced Configuration (System VM Detection)

| Variable | Default | Description |
|----------|---------|-------------|
| `METRICS_SYSTEM_VM_PATTERNS` | `pc157-,prism-central,pcvm` | Comma-separated VM name patterns |
| `METRICS_SYSTEM_VM_IDS` | - | Comma-separated explicit VM IDs |

---

## Docker Management

### Build Image

```bash
# Standard build
sudo docker build -t nutanix-prometheus-exporter:latest .

# Build with no cache (clean build)
sudo docker build --no-cache -t nutanix-prometheus-exporter:latest .
```

### Run Container

```bash
# Basic run
sudo docker run -d \
  --name nutanix-exporter \
  --env-file .env \
  -p 8080:8080 \
  --restart unless-stopped \
  nutanix-prometheus-exporter:latest

# With custom port
sudo docker run -d \
  --name nutanix-exporter \
  --env-file .env \
  -p 9090:8080 \
  --restart unless-stopped \
  nutanix-prometheus-exporter:latest
```

### Container Operations

```bash
# View logs
sudo docker logs nutanix-exporter

# Follow logs (live)
sudo docker logs -f nutanix-exporter

# View last 100 lines
sudo docker logs --tail=100 nutanix-exporter

# Check container status
sudo docker ps | grep nutanix-exporter

# Restart container
sudo docker restart nutanix-exporter

# Stop container
sudo docker stop nutanix-exporter

# Remove container
sudo docker rm nutanix-exporter

# Stop and remove
sudo docker stop nutanix-exporter && sudo docker rm nutanix-exporter
```

### Update Configuration

```bash
# 1. Edit .env file
nano .env

# 2. Restart container to apply changes
sudo docker restart nutanix-exporter
```

### Update Code/Rebuild

```bash
# 1. Stop and remove old container
sudo docker stop nutanix-exporter
sudo docker rm nutanix-exporter

# 2. Rebuild image
sudo docker build -t nutanix-prometheus-exporter:latest .

# 3. Start new container
sudo docker run -d \
  --name nutanix-exporter \
  --env-file .env \
  -p 8080:8080 \
  --restart unless-stopped \
  nutanix-prometheus-exporter:latest
```

---

## Metrics Collected

### VM Metrics (40+ metrics per VM)

**CPU & Performance**:
- `nutanix_vm_cpu_usage_ppm` - CPU usage in parts per million (1,000,000 = 100%)
- `nutanix_vm_cpu_ready_time_ppm` - CPU ready time (waiting for CPU)
- `nutanix_vm_memory_usage_ppm` - Hypervisor memory usage
- `nutanix_vm_guest_memory_usage_ppm` - Guest OS memory usage (1,000,000 = 100%)

**Storage I/O**:
- `nutanix_vm_controller_avg_io_latency_micros` - Average I/O latency (microseconds)
- `nutanix_vm_controller_avg_read_io_latency_micros` - Read latency
- `nutanix_vm_controller_avg_write_io_latency_micros` - Write latency
- `nutanix_vm_controller_num_iops` - Total IOPS
- `nutanix_vm_controller_num_read_iops` - Read IOPS
- `nutanix_vm_controller_num_write_iops` - Write IOPS
- `nutanix_vm_controller_io_bandwidth_kbps` - I/O bandwidth (KB/s)

**Network**:
- `nutanix_vm_hypervisor_num_received_bytes` - Bytes received
- `nutanix_vm_hypervisor_num_transmitted_bytes` - Bytes transmitted

**Labels**: `vm_id`, `vm_name`, `cluster`, `vm_type` (ahv/esxi)

### Cluster Metrics

- `nutanix_cluster_cpu_capacity_hz` - Total CPU capacity
- `nutanix_cluster_memory_capacity_bytes` - Total memory
- `nutanix_cluster_storage_capacity_bytes` - Total storage
- `nutanix_cluster_iops` - Cluster-wide IOPS

**Labels**: `cluster_name`, `cluster_id`

### Storage Metrics

- `nutanix_storage_capacity_bytes` - Total container capacity
- `nutanix_storage_free_bytes` - Free space
- `nutanix_storage_usage_bytes` - Used space

**Labels**: `container_name`, `container_id`, `cluster`

### Alert Metrics

- `nutanix_alert_active` - Active alerts by severity

**Labels**: `alert_id`, `severity`, `title`, `cluster`

### Exporter Health Metrics

- `nutanix_exporter_collection_success` - Collection success (1=success, 0=failure)
- `nutanix_exporter_collection_duration_seconds` - Collection time
- `nutanix_exporter_last_collection_timestamp` - Last collection timestamp

---

## Prometheus Integration

### Add Scrape Target

Edit your Prometheus configuration (`prometheus.yml`):

```yaml
scrape_configs:
  - job_name: 'nutanix-exporter'
    scrape_interval: 60s
    scrape_timeout: 30s
    static_configs:
      - targets: ['localhost:8080']  # Or IP:port of exporter host
        labels:
          environment: 'production'
          datacenter: 'dc1'
```

### Reload Prometheus

```bash
# If using systemd
sudo systemctl reload prometheus

# If using Docker
docker kill -s HUP prometheus

# Or restart
docker restart prometheus
```

---

## Grafana Integration

### Add Prometheus Data Source

1. **Login to Grafana** (default: admin/admin)
2. Go to **Configuration** → **Data Sources**
3. Click **Add data source**
4. Select **Prometheus**
5. Set URL: `http://localhost:9090` (or your Prometheus URL)
6. Click **Save & Test**

### Example Queries

**VM CPU Usage (as percentage)**:
```promql
nutanix_vm_cpu_usage_ppm / 10000
```

**VM Memory Usage (as percentage)**:
```promql
nutanix_vm_guest_memory_usage_ppm / 10000
```

**Top 10 VMs by CPU**:
```promql
topk(10, nutanix_vm_cpu_usage_ppm)
```

**Top 10 VMs by Memory**:
```promql
topk(10, nutanix_vm_guest_memory_usage_ppm)
```

**VM I/O Latency**:
```promql
nutanix_vm_controller_avg_io_latency_micros
```

**Cluster Storage Usage Percentage**:
```promql
(nutanix_storage_usage_bytes / nutanix_storage_capacity_bytes) * 100
```

**Active Alerts by Severity**:
```promql
sum by (severity) (nutanix_alert_active)
```

### Filter by VM Name

```promql
nutanix_vm_cpu_usage_ppm{vm_name="your-vm-name"}
nutanix_vm_guest_memory_usage_ppm{vm_name=~"pc157.*"}
```

---

## Troubleshooting

### Container Not Starting

**Check logs**:
```bash
sudo docker logs nutanix-exporter
```

**Common issues**:
- Invalid credentials in `.env` → Check USERNAME/PASSWORD
- Network connectivity → Verify Prism Central is accessible: `curl -k https://your-pc:9440`
- Port already in use → Change port: `-p 9090:8080`

### No Metrics Appearing

**Verify exporter is running**:
```bash
sudo docker ps | grep nutanix-exporter
curl http://localhost:8080/metrics
```

**Check for errors**:
```bash
sudo docker logs nutanix-exporter | grep -i error
```

**Test API connectivity**:
```bash
sudo docker exec -it nutanix-exporter curl -k https://your-prism-central:9440/api/vmm/v4.2/ahv/config/vms
```

### VMs Showing as "unknown"

This indicates VM name mapping issues. Check logs:
```bash
sudo docker logs nutanix-exporter | grep "mapped.*VM names"
# Should see: "Successfully mapped 130 ahv VM names"
```

If mapping is incomplete:
1. Check pagination logs for errors
2. Verify API permissions
3. Check `LOG_LEVEL=DEBUG` in `.env` for detailed info

### Missing Specific VMs (System VMs)

System VMs (like Prism Central) may need individual lookup. Check logs:
```bash
sudo docker logs nutanix-exporter | grep "system VM"
```

Add explicit system VM IDs to `.env`:
```bash
METRICS_SYSTEM_VM_IDS=889dfc57-8f7d-4fa1-9e85-abcd75e6a2a2
```

### High Memory Usage

**Reduce collection frequency**:
```bash
# In .env
COLLECTION_INTERVAL=120  # 2 minutes instead of 1
```

**Limit VM types**:
```bash
# In .env
VM_TYPES=ahv  # Only AHV, not ESXi
```

### SSL/TLS Errors

**For self-signed certificates**:
```bash
# In .env
TLS_VERIFY=false
```

---

## File Structure

```
/home/nutanix/prometheus/
├── Dockerfile              # Container image definition
├── .env                    # Configuration (DO NOT COMMIT)
├── .env.example            # Example configuration
├── requirements.txt        # Python dependencies
├── nutanix_exporter.py     # Main application
├── nutanix_client.py       # Nutanix API client
├── collectors.py           # Prometheus metric collectors
├── prometheus.yml          # Example Prometheus config
├── README.md               # This file
└── swagger-*.yml           # Nutanix API specifications
```

---

## Security Best Practices

### 1. Protect Credentials

```bash
# Restrict .env file permissions
chmod 600 .env

# Never commit .env to git
echo ".env" >> .gitignore
```

### 2. Use Read-Only Account

Create a dedicated Prism Central user with **read-only** permissions for the exporter.

### 3. Enable TLS Verification

```bash
# In production with valid certificates
TLS_VERIFY=true
```

### 4. Network Security

- Restrict port 8080 access using firewall rules
- Use reverse proxy (nginx) with authentication
- Deploy in isolated network segment

### 5. Container Security

```bash
# Run as non-root user (already configured in Dockerfile)
# Regular security updates
sudo docker pull python:3.11-slim
sudo docker build -t nutanix-prometheus-exporter:latest .
```

---

## Performance Tuning

### For Large Environments (2000+ VMs)

```bash
# In .env
COLLECTION_INTERVAL=120     # Increase to 2 minutes
REQUEST_TIMEOUT=60          # Increase timeout
```

**Resource limits**:
```bash
sudo docker run -d \
  --name nutanix-exporter \
  --env-file .env \
  -p 8080:8080 \
  --memory="1g" \
  --cpus="1.0" \
  --restart unless-stopped \
  nutanix-prometheus-exporter:latest
```

### For Small Environments (<500 VMs)

```bash
# In .env
COLLECTION_INTERVAL=30      # More frequent updates
```

---

## Monitoring the Exporter

### Check Exporter Health

```bash
# Check success metric
curl -s http://localhost:8080/metrics | grep nutanix_exporter_collection_success

# Check collection duration
curl -s http://localhost:8080/metrics | grep nutanix_exporter_collection_duration_seconds

# Check last collection time
curl -s http://localhost:8080/metrics | grep nutanix_exporter_last_collection_timestamp
```

### Alert on Exporter Failures

Add to Prometheus `alerts.yml`:
```yaml
groups:
  - name: nutanix_exporter
    rules:
      - alert: NutanixExporterDown
        expr: nutanix_exporter_collection_success == 0
        for: 5m
        annotations:
          summary: "Nutanix exporter failing to collect metrics"
          
      - alert: NutanixExporterSlow
        expr: nutanix_exporter_collection_duration_seconds > 60
        for: 10m
        annotations:
          summary: "Nutanix exporter collection taking too long"
```

---

## Advanced Features

### Automatic System VM Detection

The exporter automatically detects system VMs (Prism Central VMs, CVMs) that may not appear in bulk API responses.

**Default patterns**:
- `prism-central`
- `pc157-`
- `pcvm`
- `service-vm`
- `cvm-`

**Customize patterns**:
```bash
# In .env
METRICS_SYSTEM_VM_PATTERNS=my-system-vm-,custom-prefix-
```

### Hybrid Collection Strategy

- **Bulk API**: Fast collection for most VMs
- **Individual API**: Fallback for system VMs not in bulk response
- **Automatic**: No configuration needed

---

## Version Information

- **Exporter Version**: 1.1.0
- **API Version**: Nutanix v4.2
- **Python**: 3.11+
- **Prometheus Client**: Latest

---

## Changelog

### v1.1.0 (2026-02-17)
- ✅ Fixed VM name mapping pagination (`$page` instead of `$offset`)
- ✅ Added automatic system VM detection
- ✅ Improved logging with pagination details
- ✅ Support for up to 10,000 VMs
- ✅ Better error handling and debugging

### v1.0.0 (2026-02-16)
- Initial production release
- Support for AHV and ESXi VMs
- 40+ VM metrics per VM
- Cluster, host, storage, and alert metrics
- Hybrid collection with individual VM fallback
- Docker containerization

---

## Support

### Reporting Issues

When reporting issues, include:
1. **Exporter logs**: `sudo docker logs nutanix-exporter > exporter.log`
2. **Nutanix Prism Central version**
3. **Environment details**: Number of VMs, clusters
4. **Steps to reproduce**

### Debug Mode

```bash
# In .env
LOG_LEVEL=DEBUG

# Restart and check logs
sudo docker restart nutanix-exporter
sudo docker logs -f nutanix-exporter
```

---

## Additional Documentation

- `EFFICIENCY_ANALYSIS.md` - Performance optimization opportunities
- `SYSTEM_VM_DETECTION_CHANGELOG.md` - System VM detection details
- `VM_NAME_MAPPING_FIX.md` - Pagination fix documentation
- `KUBERNETES_DEPLOYMENT_GUIDE.md` - Deploy on Nutanix NKP
- `GITHUB_REGISTRY_GUIDE.md` - Using GitHub Container Registry

---

## Quick Reference Commands

```bash
# Build
sudo docker build -t nutanix-prometheus-exporter:latest .

# Run
sudo docker run -d --name nutanix-exporter --env-file .env -p 8080:8080 --restart unless-stopped nutanix-prometheus-exporter:latest

# Logs
sudo docker logs -f nutanix-exporter

# Restart
sudo docker restart nutanix-exporter

# Stop & Remove
sudo docker stop nutanix-exporter && sudo docker rm nutanix-exporter

# Test metrics
curl http://localhost:8080/metrics | grep nutanix_vm_cpu

# Check specific VM
curl -s http://localhost:8080/metrics | grep 'vm_name="your-vm-name"'
```

---

**Status**: Production Ready  
**Tested With**: Nutanix Prism Central v4.2, 130+ VMs  
**License**: See LICENSE file  

**Questions?** Check the troubleshooting section or review logs with `sudo docker logs nutanix-exporter`

