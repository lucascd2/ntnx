#!/bin/bash

# Example usage script for list_vms.py
# This script demonstrates various ways to use the VM listing script

# Make sure the script is executable
chmod +x list_vms.py

echo "=== Nutanix Prism Central VM List Script - Usage Examples ==="
echo

# Example 1: Interactive mode
echo "Example 1: Interactive mode (will prompt for credentials)"
echo "Command: ./list_vms.py"
echo

# Example 2: Basic usage with command line parameters
echo "Example 2: Basic usage with PC IP and username"
echo "Command: ./list_vms.py --pc-ip 192.168.1.100 --username admin"
echo

# Example 3: JSON output format
echo "Example 3: JSON output format"
echo "Command: ./list_vms.py --pc-ip pc.example.com --username admin --format json"
echo

# Example 4: CSV output saved to file
echo "Example 4: CSV output saved to file"
echo "Command: ./list_vms.py --pc-ip 192.168.1.100 --username admin --format csv --output vms.csv"
echo

# Example 5: Filter for powered-on VMs only
echo "Example 5: Filter for powered-on VMs only"
echo "Command: ./list_vms.py --pc-ip 192.168.1.100 --username admin --filter \"powerState eq 'ON'\""
echo

# Example 6: Select specific fields
echo "Example 6: Select specific fields"
echo "Command: ./list_vms.py --pc-ip 192.168.1.100 --username admin --select name,extId,powerState,memorySizeBytes"
echo

# Example 7: Order by memory size (descending)
echo "Example 7: Order by memory size (descending)"
echo "Command: ./list_vms.py --pc-ip 192.168.1.100 --username admin --orderby \"memorySizeBytes desc\""
echo

# Example 8: Complex filter with multiple conditions
echo "Example 8: Complex filter - VMs with more than 8GB memory and powered on"
echo "Command: ./list_vms.py --pc-ip 192.168.1.100 --username admin --filter \"memorySizeBytes gt 8589934592 and powerState eq 'ON'\""
echo

# Example 9: Verbose logging enabled
echo "Example 9: Verbose logging for troubleshooting"
echo "Command: ./list_vms.py --pc-ip 192.168.1.100 --username admin --verbose"
echo

# Example 10: Get VMs from a specific cluster
echo "Example 10: Get VMs from a specific cluster"
echo "Command: ./list_vms.py --pc-ip 192.168.1.100 --username admin --filter \"cluster/extId eq '12345678-1234-1234-1234-123456789012'\""
echo

echo "=== Additional Filtering Examples ==="
echo

echo "Filter by VM name pattern:"
echo "./list_vms.py --pc-ip PC_IP --username USER --filter \"startswith(name, 'web')\""
echo

echo "Filter by minimum vCPU count:"
echo "./list_vms.py --pc-ip PC_IP --username USER --filter \"numSockets mul numCoresPerSocket mul numThreadsPerCore ge 4\""
echo

echo "Filter VMs created after a specific date:"
echo "./list_vms.py --pc-ip PC_IP --username USER --filter \"createTime gt 2024-01-01T00:00:00Z\""
echo

echo "Combine multiple filters:"
echo "./list_vms.py --pc-ip PC_IP --username USER --filter \"powerState eq 'ON' and memorySizeBytes gt 4294967296\""
echo

echo "=== Tips ==="
echo "- The script automatically tries VMM v4.1 first, falls back to v4.0 if needed"
echo "- For security, avoid using --password on command line"
echo "- Use --verify-ssl if your PC has valid SSL certificates"
echo "- Use --verbose for troubleshooting connection issues"
echo "- The script handles pagination automatically for large environments"
echo "- API rate limiting is handled automatically with proper backoff"
echo

echo "For more information, run: ./list_vms.py --help"
