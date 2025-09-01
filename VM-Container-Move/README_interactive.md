# Interactive Nutanix Prism Central VM Listing Tool

A user-friendly, interactive Python script to list and manage VMs from Nutanix Prism Central with automatic API version detection and fallback support.

## Features

### 🚀 **Core Features**
- **Interactive Interface**: User-friendly menu-driven experience
- **Multi-API Support**: Automatically detects and uses VMM v4.1, v4.0, v3.1, v3.0, or v2.0 APIs
- **Smart Fallback**: Tries newest API first, falls back to older versions automatically
- **SSL Friendly**: Handles self-signed certificates gracefully
- **Credential Security**: Secure password input (no echo to terminal)

### 📊 **VM Listing Options**
- **List All VMs**: Shows all virtual machines in the environment
- **Filter by Power State**: Show only powered ON or OFF VMs
- **Formatted Display**: Clean, color-coded table with key VM information
- **Export to JSON**: Save VM data to timestamped JSON files

### 🔧 **Technical Features**
- **Pagination Support**: Handles large VM inventories automatically
- **Rate Limiting**: Built-in delays to respect API limits
- **Error Handling**: Graceful handling of connection and authentication issues
- **Cross-Version Compatibility**: Works with different Nutanix software versions

## Requirements

```bash
# Python 3.6+ with required packages
pip install requests urllib3
```

## Quick Start

### Basic Usage
```bash
# Run the interactive script
python3 get_vms_interactive.py
```

### Example Session
```
============================================================
  🖥️  Nutanix Prism Central VM Listing Tool
============================================================

📡 Connection Setup
Please provide your Prism Central connection details:

Prism Central IP/FQDN: 192.168.1.100
Username: admin
Password: [hidden]

🔗 Connecting to Prism Central...

🔍 Discovering API version...
  Testing v4.1 API... ❌ Not available
  Testing v4.0 API... ❌ Not available  
  Testing v3.1 API... ✅ Available
✅ Successfully connected using v3.1 API

🎛️  VM Listing Options:
1. List all VMs
2. List powered ON VMs
3. List powered OFF VMs
4. Change connection
5. Exit

Select option (1-5): 1

🔄 Fetching VMs...
✅ Found 25 VMs

📋 Virtual Machines (using v3.1 API):
========================================================================================================================
Name                      UUID                                   Power    CPU      Memory     Cluster         Host           
------------------------------------------------------------------------------------------------------------------------
web-server-01            12345678-1234-1234-1234-123456789012   ON       4        8.0        cluster-01      host-01        
database-primary         87654321-1234-1234-1234-123456789012   ON       8        32.0       cluster-01      host-02        
test-vm                  abcdef12-1234-1234-1234-123456789012   OFF      2        4.0        cluster-02      host-03        
========================================================================================================================

💾 Export to JSON file? (y/N): y
✅ Exported 25 VMs to nutanix_vms_1693234567.json
```

## API Version Support

The script automatically tries APIs in this order:

| API Version | Endpoint | Notes |
|-------------|----------|-------|
| **v4.1** | `/vmm/v4.1/ahv/config/vms` | Latest VMM API (preferred) |
| **v4.0** | `/vmm/v4.0/ahv/config/vms` | VMM API fallback |
| **v3.1** | `/api/nutanix/v3/vms/list` | Standard v3 list endpoint |
| **v3.0** | `/api/nutanix/v3/vms` | Alternative v3 endpoint |
| **v2.0** | `/api/nutanix/v2.0/vms` | Legacy v2 API |

## VM Information Displayed

| Field | Description | Source |
|-------|-------------|---------|
| **Name** | VM display name | `name` field |
| **UUID** | Unique identifier | `extId`, `uuid`, or `metadata.uuid` |
| **Power** | Power state (ON/OFF/UNKNOWN) | `powerState` or `power_state` |
| **CPU** | Total vCPU count | `numSockets × numCoresPerSocket` |
| **Memory** | Memory in GB | `memorySizeBytes`, `memory_size_mib`, or `memory_mb` |
| **Cluster** | Associated cluster | `cluster.name` or `cluster_reference.name` |
| **Host** | Current host | `host.name` or `host_name` |

## JSON Export Format

```json
{
  "export_info": {
    "timestamp": "2025-08-28 12:01:31",
    "prism_central": "192.168.1.100",
    "api_version": "v3.1",
    "total_vms": 25
  },
  "vms": [
    {
      "name": "web-server-01",
      "uuid": "12345678-1234-1234-1234-123456789012", 
      "power_state": "ON",
      "cpu_sockets": 2,
      "cpu_cores_per_socket": 2,
      "memory_gb": 8.0,
      "cluster": "cluster-01",
      "host": "host-01"
    }
  ]
}
```

## Troubleshooting

### Connection Issues
```bash
# Test basic connectivity first
python3 troubleshoot.py --pc-ip YOUR_PC_IP --skip-auth-test

# Run diagnostic tests
python3 diagnose_api.py
```

### Authentication Failures
- **Check credentials**: Verify username and password are correct
- **Account permissions**: Ensure user has VM viewing permissions
- **Domain users**: Try `domain\username` or `username@domain.com` formats

### API Version Issues
- **No compatible APIs**: VMM service might not be installed/enabled
- **HTTP 412 errors**: Try connecting to individual PE clusters instead of PC
- **HTTP 422 errors**: API request format issues (handled automatically)

### Common Error Messages

| Error | Cause | Solution |
|-------|-------|----------|
| `Authentication failed` | Invalid credentials | Check username/password |
| `No compatible API endpoints found` | VMM not available | Check VMM service status |
| `Connection timeout` | Network issues | Verify IP/FQDN and firewall |
| `SSL certificate verify failed` | Certificate issues | Script handles this automatically |

## Advanced Usage

### Manual API Testing
```python
# Test specific API version
from get_vms_interactive import NutanixVMClient

client = NutanixVMClient()
client.setup_connection("192.168.1.100", "admin", "password")
success, data = client.test_api_endpoint("v3.1", "/api/nutanix/v3/vms/list")
```

### Custom Filtering
The script supports basic power state filtering through the UI. For advanced filtering, you can modify the API calls in the code.

### Large Environments
- **Pagination**: Automatic (handles 100+ VMs seamlessly)
- **Rate Limiting**: Built-in delays between API calls
- **Memory Efficient**: Processes VMs in batches

## Script Architecture

```
get_vms_interactive.py
├── NutanixVMClient Class
│   ├── Connection Management
│   ├── API Version Discovery  
│   ├── Multi-Version VM Retrieval
│   ├── Data Formatting & Display
│   └── JSON Export
├── Interactive Menu System
├── Color-Coded Output
└── Error Handling
```

## Files Created

| File | Purpose |
|------|---------|
| `get_vms_interactive.py` | Main interactive script |
| `nutanix_vms_*.json` | Exported VM data (timestamped) |

## Security Notes

- **No credential storage**: Passwords are never saved or logged
- **SSL handling**: Self-signed certificates are handled securely
- **Secure input**: Password input is hidden from terminal
- **No network logging**: API calls don't log sensitive data

## Contributing

The script is designed to be easily extensible:
- **Add new API versions**: Update `api_endpoints` dictionary
- **Add new filters**: Modify filtering logic in `get_vms_*` methods  
- **Custom output formats**: Extend `format_vm_info` and `print_vm_table` methods
- **Additional VM fields**: Update field mapping in format methods

## Version History

- **v1.0** (2025-08-28): Initial release with multi-API support and interactive interface

## Support

For issues with the script:
1. Run diagnostics: `python3 diagnose_api.py`
2. Check troubleshooting section above
3. Verify Prism Central version compatibility
4. Test with individual PE clusters if PC APIs fail
