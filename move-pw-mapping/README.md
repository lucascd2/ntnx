# Nutanix Move Migration Plan Creator

This Python script creates migration plans using the Nutanix Move API. It supports migrating VMs from vCenter or Prism Central to a target Prism Central environment with **full interactive mode** for ease of use.

## Features

- **Interactive Mode**: Prompts for missing parameters when not provided via command line
- **Source Support**: vCenter or Prism Central
- **Target Support**: Prism Central
- **VM Credentials**: CSV file mapping for VM-specific credentials
- **Network Mappings**: Source-to-target network mapping
- **Flexible Usage**: Command line, interactive, or hybrid modes
- **Error Handling**: Comprehensive error handling and validation

## Prerequisites

1. Nutanix Move appliance deployed and configured
2. Python 3.6+ 
3. Required Python packages (install with `pip install -r requirements.txt`)

## Installation

```bash
pip install -r requirements.txt
chmod +x nutanix_move_migration.py
```

## Usage Modes

### 1. Interactive Mode (Recommended for beginners)
Run the script without arguments and it will prompt for all required information:

```bash
python3 nutanix_move_migration.py
```

The script will guide you through:
- Move server configuration
- Source provider setup (vCenter or Prism Central)
- Target Prism Central configuration
- Migration plan details
- VM selection and credentials
- Optional network mappings

### 2. Hybrid Mode
Provide some arguments and get prompted for the rest:

```bash
python3 nutanix_move_migration.py --move-server 10.1.1.100 --source-type vcenter
```

### 3. Full Command Line Mode
Provide all arguments for automated/scripted usage:

```bash
python3 nutanix_move_migration.py \
  --move-server 10.1.1.100 \
  --move-username admin \
  --move-password MovePassword123 \
  --source-type vcenter \
  --source-server 10.1.1.50 \
  --source-username administrator@vsphere.local \
  --source-password vCenterPass456 \
  --target-server 10.1.1.200 \
  --target-username admin \
  --target-password PrismPass789 \
  --plan-name "Production-Migration-Plan" \
  --vm-list web-server-01 db-server-02 app-server-03 \
  --vm-credentials-csv vm_credentials.csv \
  --source-networks "VM Network" "Production LAN" \
  --target-networks "vlan-100" "vlan-200"
```

## CSV File Format

The VM credentials CSV file should follow this format:

```csv
Server Name,Username,Password
web-server-01,administrator,MyPassword123!
db-server-02,root,DbPass456@
app-server-03,admin,AppAdmin789#
```

- **Server Name**: Must match the VM name specified in the VM list
- **Username**: VM login username for Move agent installation
- **Password**: VM login password

## Interactive Prompts

When running in interactive mode, the script will prompt for:

### Move Server Configuration
- Move server IP/FQDN
- Move username  
- Move password (hidden input)

### Source Provider Configuration
- Source type (vcenter/prism)
- Source server IP/FQDN
- Source server username
- Source server password (hidden input)

### Target Provider Configuration
- Target Prism Central IP/FQDN
- Target Prism Central username
- Target Prism Central password (hidden input)

### Migration Plan Configuration
- Migration plan name
- List of VMs to migrate
- VM credentials CSV file path (with validation)

### Network Mappings (Optional)
- Option to configure network mappings
- Source networks (if enabled)
- Target networks (if enabled)

## Command Line Arguments

### Optional Arguments (All can be prompted for)
- `--move-server`: Move appliance IP or FQDN
- `--move-username`: Move appliance username
- `--move-password`: Move appliance password
- `--source-type`: Source type (`vcenter` or `prism`)
- `--source-server`: Source server IP or FQDN
- `--source-username`: Source server username
- `--source-password`: Source server password
- `--target-server`: Target Prism Central IP or FQDN
- `--target-username`: Target Prism Central username
- `--target-password`: Target Prism Central password
- `--plan-name`: Migration plan name
- `--vm-list`: List of VM names to migrate
- `--vm-credentials-csv`: Path to CSV file with VM credentials
- `--source-networks`: List of source network names/IDs
- `--target-networks`: List of target network names/IDs
- `--verify-ssl`: Verify SSL certificates (disabled by default)

## Output

The script will:
1. Authenticate with Move API
2. Create source and target providers
3. Create the migration plan with specified VMs
4. Display comprehensive success summary with UUIDs
5. Show initial plan status
6. Provide next steps guidance

## Example Interactive Session

```
=== Nutanix Move Migration Plan Creator ===

Move Server Configuration:
Move server IP/FQDN: 10.1.1.100
Move username: admin
Move password: [hidden]

Source Provider Configuration:
Source type (vcenter/prism): vcenter
Source server IP/FQDN: 10.1.1.50
Source server username: administrator@vsphere.local
Source server password: [hidden]

Target Provider Configuration (Prism Central):
Target Prism Central IP/FQDN: 10.1.1.200
Target Prism Central username: admin
Target Prism Central password: [hidden]

Migration Plan Configuration:
Migration plan name: Production-Migration-Jan2024
VMs to migrate
Enter items one per line. Press Enter twice to finish:
  Item 1: web-server-01
  Item 2: db-server-02
  Item 3: 

VM credentials CSV file path: vm_credentials.csv

Network Mappings (Optional):
Configure network mappings? (y/n) [n]: y
Source networks
Enter items one per line. Press Enter twice to finish:
  Item 1: VM Network
  Item 2: 

Target networks
Enter items one per line. Press Enter twice to finish:
  Item 1: vlan-100
  Item 2: 
```

## Error Handling

The script includes comprehensive error handling for:
- Authentication failures
- Network connectivity issues
- Invalid credentials
- Missing or invalid CSV files
- File path validation
- API response errors
- User input validation

## Security Features

- **Hidden Password Input**: All passwords are entered securely using `getpass`
- **SSL Warning Suppression**: Self-signed certificate warnings disabled
- **Credential Masking**: CSV passwords are displayed as asterisks in logs
- **No Password Storage**: Passwords are not logged or stored

## Troubleshooting

### Common Issues

1. **Authentication Failed**: Verify Move appliance credentials
2. **Provider Creation Failed**: Check source/target server connectivity and credentials
3. **CSV File Not Found**: Script will re-prompt for valid file path
4. **Network Mapping Issues**: Ensure network names/IDs are correct
5. **Interactive Mode Issues**: Use Ctrl+C to cancel at any prompt

### Debug Tips

1. Start with interactive mode to validate all inputs
2. Test CSV file reading separately with the provided test script
3. Verify network connectivity to all servers before running
4. Use `--verify-ssl` flag if working with production certificates

## Files Included

- `nutanix_move_migration.py`: Main script
- `vm_credentials_sample.csv`: Sample CSV format
- `test_csv_reading.py`: CSV validation test script
- `requirements.txt`: Python dependencies
- `README.md`: This documentation

## Next Steps After Plan Creation

1. **Verify in Move UI**: Check the migration plan in the Move web interface
2. **Prepare VMs**: Run preparation phase (manual or automatic)
3. **Readiness Checks**: Perform pre-migration validation
4. **Start Migration**: Begin the actual migration process
5. **Monitor Progress**: Watch migration status in Move UI
6. **Perform Cutover**: Complete the migration when ready

The script provides a solid foundation for creating migration plans, but the actual migration execution should be monitored through the Move web interface.
