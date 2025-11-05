# Nutanix Move Migration Plan Creator

An interactive Python CLI tool for creating and managing VM migration plans via the Nutanix Move v2 API. This tool automates the entire migration workflow from plan creation through preparation, readiness checks, and migration execution.

[![Python 3.7+](https://img.shields.io/badge/python-3.7+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 🎯 Features

### Plan Creation
- **Interactive CLI Interface** - User-friendly menu-driven workflow
- **JWT Authentication** - Secure token-based authentication with Nutanix Move API
- **Provider Management** - Browse and select source/target providers
- **VM Selection** - Interactive VM browser with filtering and pagination
- **Smart Network Mapping** - Auto-mapping, manual selection, or numbered selection
- **Test Network Support** - Separate network configuration for test migrations
- **Credential Management** - CSV-based VM credentials with auto-detection
- **Auto-Selection** - Automatically selects single clusters/containers

### Migration Workflow
- **VM Preparation** - Auto/manual prep modes with NGT installation
- **Guest Tools Management** - Install NGT, uninstall VMware Tools/Hyper-V IC
- **IP Retention** - Optional IP address retention during migration
- **Readiness Checks** - Automated validation before migration
- **Migration Start** - Initiate data sync with configurable snapshot frequency
- **Workload Monitoring** - Track VM migration status and progress
- **Test/Cutover Actions** - Execute test migrations or final cutover

## 📋 Prerequisites

- Python 3.7 or higher
- Access to Nutanix Move API (typically port 443)
- Network connectivity to Move server
- Valid Move credentials

### Python Dependencies

```bash
pip install -r requirements.txt
```

Or manually:
```bash
pip install requests urllib3
```

## 🚀 Quick Start

### 1. Clone and Setup

```bash
git clone <repository-url>
cd nutanix-move-tools
cp credential-mapping.csv.example credential-mapping.csv
# Edit credential-mapping.csv with your VM credentials
```

### 2. Run the Script

```bash
# Interactive mode (recommended)
python3 move_plan_create.py --server <move-server-ip> --username nutanix

# Non-interactive authentication
python3 move_plan_create.py --server <move-server-ip> --username nutanix --password <password>
```

## 📝 Configuration

### Credential Mapping

Create `credential-mapping.csv` with VM credentials:

```csv
servername,username,password
vm-web-01,administrator,SecurePass123
vm-db-01,root,DBPassword456
vm-app-01,admin,AppPass789
```

**Important:** The CSV file should match VM names in your source environment.

### Network Mapping

During plan creation, you'll be prompted to map networks:

1. **Auto-mapping** - Automatically matches networks by name (if names are identical)
2. **Manual selection** - Choose target network from list
3. **Test network** - Optionally specify a separate network for test migrations

## 🔄 Migration Workflow

The script supports the complete Nutanix Move migration workflow:

### 1. Create Migration Plan
- Select source and target environments
- Choose VMs to migrate
- Configure network mappings (including test networks)
- Apply VM credentials
- Create the plan in Move

### 2. Prepare VMs (Optional Interactive Workflow)
After plan creation, optionally proceed with:

**Preparation Options:**
- Auto/manual prep mode
- Install Nutanix Guest Tools (NGT)
- Uninstall existing guest tools (VMware Tools/Hyper-V IC)
- IP address retention

### 3. Readiness Checks
- Validates VM readiness
- Displays passed/failed checks
- Identifies issues before migration

### 4. Start Migration
- Initiates data synchronization
- Optional snapshot frequency configuration
- VMs progress toward "Cutover Ready" state

### 5. Monitor Progress
- Real-time workload status
- Migration progress percentage
- State information per VM

### 6. Test/Cutover
- **Test Migration** - Boot VM on target (source remains running)
- **Cutover** - Final migration (source VM shut down)

## 📊 Example Session

```bash
$ python3 move_plan_create.py --server 10.38.18.23 --username nutanix
Password: ********

Connected to Move API: 10.38.18.23
Move Version: v2.3.0

==================================================
SELECT MIGRATION DIRECTION
==================================================
Source Providers (FROM):
   1. VMware-vCenter-01 (VMware vCenter)
   
Target Providers (TO):
   1. Nutanix-PHX-Cluster (Nutanix AHV)

Enter source provider number: 1
Enter target provider number: 1

[Interactive VM selection...]
[Network mapping...]
[Credential application...]

✅ Migration plan 'Migration-Plan-2024' created successfully!
🆔 Plan UUID: abc123...
📊 Plan includes 3 VMs
📤 Source: VMware-vCenter-01
📥 Target: Nutanix-PHX-Cluster

Do you want to proceed with test migration workflow? (yes/no): yes

VM Preparation mode (auto/manual) [auto]: auto
Install NGT on target VMs? (yes/no) [yes]: yes
Uninstall existing guest tools? (yes/no) [yes]: yes
Skip IP retention? (yes/no) [no]: no

✅ Prepare request submitted successfully
✅ Readiness checks passed
✅ Migration started successfully
```

## 🔧 Command-Line Options

```bash
python3 move_plan_create.py --help

Options:
  --server SERVER        Move server IP or hostname (required)
  --username USERNAME    Move username (required)
  --password PASSWORD    Move password (will prompt if not provided)
  --port PORT           Move API port (default: 443)
  --verify-ssl          Enable SSL certificate verification (default: disabled)
  --no-interactive      Non-interactive mode (skip prompts)
```

## 📂 Project Structure

```
.
├── move_plan_create.py           # Main migration plan script (complete workflow)
├── list_move_environments.py     # List/browse Move environments
├── test_move_auth.py             # Test authentication
├── credential-mapping.csv        # VM credentials (gitignored)
├── credential-mapping.csv.example # Credential template
├── requirements.txt              # Python dependencies
└── README.md                     # This file
```

## 🔐 Security Notes

- **Credentials**: Never commit `credential-mapping.csv` to version control
- **SSL Verification**: By default, SSL verification is disabled (common in lab environments)
- **Passwords**: Use `--password` carefully; prefer interactive prompts
- **API Tokens**: Tokens are session-based and automatically managed

## 🐛 Troubleshooting

### Authentication Issues
```bash
# Test authentication separately
python3 test_move_auth.py
```

### Connection Problems
- Verify Move server is accessible: `ping <move-server>`
- Check port 443 is open: `telnet <move-server> 443`
- Review SSL certificate settings

### VM Not Found
- Ensure VM names in `credential-mapping.csv` match exactly
- Check case sensitivity
- Verify VMs are visible in source provider

### Network Mapping Errors
- If test network equals production network, you'll get API error 20538
- Ensure test and production networks are different
- Leave test network blank (press Enter) to skip test network configuration

## 📖 API Documentation

This tool is based on the official Nutanix Move API v2 specification. Key endpoints used:

- `/move/v2/token` - Authentication
- `/move/v2/providers/list` - List source/target providers
- `/move/v2/vms/list` - List VMs in provider
- `/move/v2/plans` - Create migration plan
- `/move/v2/plans/{id}/prepare` - Prepare VMs for migration
- `/move/v2/plans/{id}/readiness` - Check migration readiness
- `/move/v2/plans/{id}/start` - Start migration
- `/move/v2/plans/{id}/workloads/list` - Monitor workload status

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📜 License

MIT License - see LICENSE file for details

## ⚠️ Disclaimer

This tool is provided as-is for educational and operational purposes. Always test in a lab environment before using in production. The authors are not responsible for any data loss or system issues.

## 🆘 Support

For issues, questions, or contributions:
- Open an issue on GitHub
- Review Nutanix Move documentation
- Check Nutanix community forums

---

**Version:** 2.0.0  
**Compatible with:** Nutanix Move v2.3.0+  
**Last Updated:** November 2024
