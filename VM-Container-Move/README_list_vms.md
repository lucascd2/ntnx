# Nutanix Prism Central VM List Script

This Python script lists all Virtual Machines from Nutanix Prism Central using the VMM REST API. It automatically tries v4.1 first and falls back to v4.0 for backward compatibility. It supports pagination for large environments and handles API rate limiting appropriately.

## Features

- **Automatic API Version Detection**: Tries v4.1 first, automatically falls back to v4.0 for backward compatibility
- **Command-line Interface**: Accept PC IP, username, and password via command-line arguments or interactive prompts
- **Pagination Support**: Automatically handles pagination for large VM environments
- **Rate Limiting**: Proper handling of API rate limits with retry logic
- **Multiple Output Formats**: Table, JSON, and CSV output formats
- **Filtering & Selection**: Support for OData filtering and field selection
- **SSL Verification**: Option to disable SSL verification for self-signed certificates
- **Comprehensive Logging**: Detailed logging with optional verbose mode

## Requirements

- Python 3.6+
- `requests` library
- `urllib3` library

## Installation

Install required dependencies:

```bash
pip install requests urllib3
```

## Usage

### Basic Usage

```bash
# Interactive mode - prompts for credentials
./list_vms.py

# Command-line with credentials
./list_vms.py --pc-ip 192.168.1.100 --username admin

# Full command-line specification
./list_vms.py --pc-ip pc.example.com --username admin --password mypassword
```

### Advanced Usage

```bash
# List only powered-on VMs
./list_vms.py --pc-ip 192.168.1.100 --username admin --filter "powerState eq 'ON'"

# Output in JSON format
./list_vms.py --pc-ip 192.168.1.100 --username admin --format json

# CSV output with specific fields
./list_vms.py --pc-ip 192.168.1.100 --username admin --format csv --select name,extId,powerState,memorySizeBytes

# Save output to file
./list_vms.py --pc-ip 192.168.1.100 --username admin --output vms.csv --format csv

# Order results by memory size (descending)
./list_vms.py --pc-ip 192.168.1.100 --username admin --orderby "memorySizeBytes desc"

# Enable verbose logging
./list_vms.py --pc-ip 192.168.1.100 --username admin --verbose
```

## Command-Line Options

| Option | Description |
|--------|-------------|
| `--pc-ip` | Prism Central IP address or FQDN |
| `--username` | Username for authentication |
| `--password` | Password for authentication (not recommended for security) |
| `--format` | Output format: `table` (default), `json`, or `csv` |
| `--limit` | Number of VMs to fetch per API call (1-100, default: 100) |
| `--filter` | OData filter expression |
| `--select` | Comma-separated list of fields to select |
| `--orderby` | Field to order results by |
| `--verify-ssl` | Verify SSL certificates (default: False) |
| `--output`, `-o` | Output file path (default: stdout) |
| `--verbose`, `-v` | Enable verbose logging |

## API Specifications

This script is based on the Nutanix VMM API specifications and supports both v4.1 and v4.0:

- **Primary Endpoint**: `GET /vmm/v4.1/ahv/config/vms`
- **Fallback Endpoint**: `GET /vmm/v4.0/ahv/config/vms` (if v4.1 returns HTTP 404)
- **Authentication**: HTTP Basic Authentication
- **Pagination**: Uses `$page` and `$limit` parameters
- **Filtering**: Supports OData v4.01 filter expressions
- **Rate Limiting**: Handles HTTP 429 responses with appropriate backoff
- **Version Detection**: Automatically detects and caches the working API version

## Backward Compatibility

The script automatically provides backward compatibility with older Prism Central versions:

1. **Primary**: Attempts to use VMM v4.1 API (`/vmm/v4.1/ahv/config/vms`)
2. **Fallback**: If v4.1 returns HTTP 404 (endpoint not found), automatically falls back to VMM v4.0 API (`/vmm/v4.0/ahv/config/vms`)
3. **Caching**: Once a working version is found, it's cached to avoid repeated version detection
4. **Logging**: The script logs which API version is being used for transparency

### Supported Prism Central Versions

- **VMM v4.1**: Latest API version with full feature support
- **VMM v4.0**: Legacy API version for older Prism Central installations

**Note**: The fallback only occurs for HTTP 404 errors (endpoint not found). Other errors like authentication failures (401/403) or network issues will not trigger a fallback, as these indicate configuration rather than version compatibility issues.

### Key VM Fields

The script extracts and displays the following key VM information:

- `name`: VM name
- `extId`: VM external identifier (UUID)
- `powerState`: Current power state (ON, OFF, etc.)
- `memorySizeBytes`: Memory allocation in bytes
- `numSockets`: Number of CPU sockets
- `numCoresPerSocket`: Number of cores per socket
- `numThreadsPerCore`: Number of threads per core
- `cluster.extId`: Cluster external identifier
- `host.extId`: Host external identifier

### Filter Examples

```bash
# VMs with specific power state
--filter "powerState eq 'ON'"

# VMs with memory greater than 4GB
--filter "memorySizeBytes gt 4294967296"

# VMs with names starting with 'web'
--filter "startswith(name, 'web')"

# VMs on a specific cluster
--filter "cluster/extId eq '12345678-1234-1234-1234-123456789012'"

# VMs with more than 4 vCPUs
--filter "numSockets mul numCoresPerSocket mul numThreadsPerCore gt 4"
```

## Rate Limiting

The Nutanix API implements rate limiting to protect the system. This script handles rate limiting by:

1. Detecting HTTP 429 responses
2. Reading the `Retry-After` header (defaults to 60 seconds if not present)
3. Waiting the specified time before retrying
4. Implementing exponential backoff for other failures

## Security Considerations

- **SSL Verification**: By default, SSL verification is disabled for self-signed certificates. Use `--verify-ssl` if your Prism Central has a valid SSL certificate.
- **Password Security**: Avoid using the `--password` option in scripts or command history. Instead, allow the script to prompt for the password interactively.
- **Credentials Storage**: Never store credentials in plain text files or version control.

## Error Handling

The script includes comprehensive error handling for:

- Network connectivity issues
- Authentication failures
- API rate limiting
- Invalid filter expressions
- JSON parsing errors
- File I/O errors

## Output Examples

### Table Format (Default)
```
VM Name                        VM ID        Power    Memory   vCPUs
----------------------------------------------------------------
web-server-01                  12345678...  ON         4.00      2
database-primary              87654321...  ON        16.00      4
test-vm                       abcdef12...  OFF        2.00      1
```

### JSON Format
```json
[
  {
    "name": "web-server-01",
    "extId": "12345678-1234-1234-1234-123456789012",
    "powerState": "ON",
    "memorySizeBytes": 4294967296,
    "numSockets": 1,
    "numCoresPerSocket": 2,
    "numThreadsPerCore": 1
  }
]
```

### CSV Format
```csv
Name,ExtId,PowerState,MemoryGB,vCPUs,ClusterID,HostID
web-server-01,12345678-1234-1234-1234-123456789012,ON,4.00,2,cluster-id,host-id
database-primary,87654321-1234-1234-1234-123456789012,ON,16.00,4,cluster-id,host-id
```

## Troubleshooting

### Common Issues

1. **SSL Certificate Errors**: Use `--verify-ssl=false` (default) for self-signed certificates
2. **Authentication Failures**: Verify username and password are correct
3. **Network Timeout**: Check network connectivity to Prism Central
4. **Rate Limiting**: The script handles this automatically, but may take longer for large environments
5. **Invalid Filter**: Ensure OData filter syntax is correct

### Debug Mode

Enable verbose logging to troubleshoot issues:

```bash
./list_vms.py --pc-ip 192.168.1.100 --username admin --verbose
```

This will show detailed information about API requests, responses, and pagination progress.
