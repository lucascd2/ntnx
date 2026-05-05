# VM Disk Migration Tool

Interactive Python script to migrate VM disks between storage containers on Nutanix AHV via Prism Central v4 APIs.

## Features

- **Lists Storage Containers** from your Nutanix cluster
- **Lists Virtual Machines** with filtering and selection
- **Shows VM Disk Details** including current storage container, disk size, and bus type
- **Migrate Options**:
  - Migrate **all disks** to a single target container
  - Migrate **specific disks** to a target container
- **Task Monitoring** with real-time progress updates
- Handles pagination for large environments
- Secure password input with `getpass`

## Requirements

- Python 3.6+
- `requests` library

Install dependencies:

```bash
pip install requests
```

## Usage

Run the script:

```bash
./vm_disk_migration.py
# or
python3 vm_disk_migration.py
```

### Interactive Workflow

1. **Enter Prism Central connection details:**
   - IP/FQDN
   - Username
   - Password (hidden input)

2. **Select a VM** from the list of all VMs

3. **View VM disks** with their current storage containers

4. **Select a target storage container** from the available list

5. **Choose migration mode:**
   - Option 1: Migrate ALL disks to the target container
   - Option 2: Select specific disks to migrate (comma-separated, e.g., `1,3`)

6. **Confirm** the operation

7. **Monitor** the migration task until completion

## APIs Used

Based on Nutanix v4 API specifications in the current directory:

| API Endpoint | Purpose |
|-------------|---------|
| `GET /storage/v4.0.a3/config/storage-containers` | List storage containers |
| `GET /vmm/v4.2/ahv/config/vms` | List all VMs |
| `GET /vmm/v4.2/ahv/config/vms/{extId}` | Get VM details (for ETag) |
| `GET /vmm/v4.2/ahv/config/vms/{vmExtId}/disks` | List VM disks |
| `POST /vmm/v4.2/ahv/config/vms/{extId}/$actions/migrate-vm-disks` | Migrate VM disks |
| `GET /prism/v4.3/config/tasks/{extId}` | Poll task status |

## API Schemas

The script constructs proper v4 API payloads using:

- `DiskMigrationParams` with `$objectType` discriminators
- `AllDisksMigrationPlan` for migrating all disks to one container
- `MigrationPlans` with `ADSFDiskMigrationPlan` for per-disk migrations
- `If-Match` header with ETag from the VM GET response
- `NTNX-Request-Id` header with a UUID for idempotence

## Example Output

```
================================================================
  Nutanix VM Disk Migration Tool
================================================================

Prism Central IP/FQDN: 10.0.0.100
Username: admin
Password: 

Fetching storage containers...
Found 5 storage container(s).

Fetching VMs...
Found 23 VM(s).

Available VMs:
    1. webserver-01                             (extId: 444e5d33-e20c-40dd-be24-aca2cf0b7eea)
    2. database-vm                              (extId: 6cab6790-dd0a-42c6-a3e4-335779de6c63)
    ...

Select a VM (1-23, or 'q' to quit): 1

Selected VM: webserver-01 (444e5d33-e20c-40dd-be24-aca2cf0b7eea)
Fetching VM disks...

Disks on VM 'webserver-01':
------------------------------------------------------------------------------------------
    #  Bus/Index      Disk ExtId                              Size         Current Container
------------------------------------------------------------------------------------------
    1  SCSI/0         77c3a8f2-9234-410e-80c2-ea8e6ef07535    100.00 GB    default-container
    2  SCSI/1         de793b0a-b45f-4d8a-a465-94682b47ba48    500.00 GB    default-container
------------------------------------------------------------------------------------------

Available Storage Containers:
    1. default-container                        (extId: a3fb4acf-9a14-4e4a-bfcd-77b7015da37b)
    2. ssd-container                            (extId: b6930d37-03e0-4bb1-ac2b-a63b91a96e83)
    ...

Select a target storage container (1-5, or 'q' to quit): 2

Target container: ssd-container (b6930d37-03e0-4bb1-ac2b-a63b91a96e83)

Migration options:
  1. Migrate ALL disks to the selected container
  2. Choose specific disks to migrate

Select option (1 or 2): 1

Will migrate ALL 2 disk(s) to 'ssd-container'.

Proceed with migration? (yes/no): yes

Retrieving VM ETag...
Submitting disk migration request...
Migration task created: d8ebd03d-7b1b-41d1-9a7f-cc18d3c8b4ec
Monitoring task progress...

  Task status: RUNNING (20%)
  Task status: RUNNING (60%)
  Task status: SUCCEEDED

✓ Disk migration completed successfully!
```

## Notes

- The script uses **HTTPS with self-signed certificate verification disabled** (suitable for lab environments)
- **ETag** is required for the migrate operation to ensure data consistency
- The script filters to show only **VmDisk-backed disks** (excludes volume groups, CD-ROMs)
- Task polling runs for up to **1800 seconds (30 minutes)** with **5-second intervals** (configurable in code)
- For production use, consider adding proper certificate validation and error handling

## API Documentation

Refer to the OpenAPI spec files in this directory:
- `swagger-storage-v4.0.a3-all.yaml`
- `swagger-vmm-v4.2-all.yaml`
- `swagger-prism-v4.3-all.yaml`

## License

This script is provided as-is for use with Nutanix environments.

## Command-Line Arguments

The script now supports optional command-line arguments for automated workflows:

```bash
# View help
./vm_disk_migration.py --help

# Interactive mode (default - prompts for all credentials)
./vm_disk_migration.py

# Provide PC IP only (prompts for username/password)
./vm_disk_migration.py --pc-ip 10.42.159.5

# Provide PC IP and username (prompts for password only)
./vm_disk_migration.py --pc-ip 10.42.159.5 --username admin

# Provide all credentials (fully non-interactive for connection)
./vm_disk_migration.py --pc-ip 10.42.159.5 --username admin --password mypass

# Use environment variables for password (recommended for scripts)
export PC_PASSWORD="your_password_here"
./vm_disk_migration.py --pc-ip 10.42.159.5 --username admin --password "$PC_PASSWORD"

# Short argument forms
./vm_disk_migration.py -p 10.42.159.5 -u admin -w "$PC_PASSWORD"
```

### Arguments

| Argument | Short Form | Description |
|----------|------------|-------------|
| `--pc-ip` | `-p`, `--pc` | Prism Central IP address or FQDN |
| `--username` | `-u`, `--user` | Prism Central username |
| `--password` | `-w`, `--pass` | Prism Central password |

**Note:** If any argument is omitted, the script will prompt interactively for that value. After connecting, the workflow remains interactive (VM selection, container selection, etc.).

