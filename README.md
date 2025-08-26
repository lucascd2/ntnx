# NGT Auto Installation Script

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A Python script that automatically installs Nutanix Guest Tools (NGT) on local virtual machines by detecting the VM in Nutanix and performing the installation remotely.

## 🚀 Features

- **Automatic VM Detection**: Detects local VM UUID and finds the corresponding VM in Nutanix
- **API Version Compatibility**: Auto-detects and uses the correct Nutanix API version (v4.0/v4.1)
- **CD-ROM Management**: Automatically handles CD-ROM requirements for NGT installation
- **Enhanced Verification**: Robust verification system with proper error handling
- **ETag Support**: Uses proper ETag handling for API operations
- **Interactive Mode**: Prompts for credentials when not provided via command line
- **Dry Run Mode**: Preview what the script will do without making changes
- **Flexible Authentication**: Support for both interactive and scripted authentication
- **Cross-Platform**: Works on Linux, Windows, and other platforms supported by NGT

## 📋 Requirements

### System Requirements
- Python 3.8 or higher
- Running inside a Nutanix VM (for auto-detection to work)
- Network connectivity to Nutanix Prism Central

### Python Dependencies
- `requests` >= 2.25.0
- `urllib3` >= 1.26.0

### Nutanix Environment
- Nutanix Prism Central with API access
- Valid admin/user credentials with VM management permissions
- Nutanix AHV cluster with NGT support

## 📦 Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/ngt-auto-install.git
   cd ngt-auto-install
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Make the script executable (Linux/macOS):**
   ```bash
   chmod +x ngt_auto_install.py
   ```

## 🔧 Usage

### Basic Usage (Interactive Mode)
```bash
./ngt_auto_install.py
```
The script will prompt for:
- Prism Central IP address
- Username and password
- VM credentials (for NGT installation inside guest OS)

### Command Line Arguments
```bash
./ngt_auto_install.py --pc-ip "10.0.0.X" --username "admin" --vm-username "administrator"
```

### Full Command Line Example
```bash
./ngt_auto_install.py \
    --pc-ip "10.0.0.X" \
    --username "admin" \
    --password "your-password" \
    --vm-username "administrator" \
    --vm-password "vm-password" \
    --debug
```

### Check NGT Status Only
```bash
./ngt_auto_install.py --pc-ip "10.0.0.X" --username "admin" --skip-install
```

### Dry Run Mode
```bash
./ngt_auto_install.py --pc-ip "10.0.0.X" --username "admin" --dry-run
```

## 📖 Command Line Options

| Option | Description |
|--------|-------------|
| `--pc-ip PC_IP` | Prism Central IP address |
| `--username USERNAME` | Username for Nutanix authentication |
| `--password PASSWORD` | Password for Nutanix authentication (not recommended for production) |
| `--port PORT` | Port number (default: 9440) |
| `--verify-ssl` | Verify SSL certificates |
| `--vm-username VM_USERNAME` | Username for VM (guest OS) authentication |
| `--vm-password VM_PASSWORD` | Password for VM (guest OS) authentication |
| `--vm-uuid VM_UUID` | VM UUID to install NGT on (overrides auto-detection) |
| `--vm-name VM_NAME` | Override VM name detection |
| `--debug` | Enable debug logging |
| `--force-api-version {v4.0,v4.1}` | Force specific API version |
| `--dry-run` | Show what would be done without making changes |
| `--no-reboot` | Do not reboot VM after NGT installation |
| `--skip-install` | Only check status, do not install |

## 🔍 How It Works

1. **VM Detection**: 
   - Detects local VM UUID using system commands (`dmidecode`, WMI, etc.)
   - Falls back to hostname-based detection if UUID detection fails

2. **API Version Detection**:
   - Tests v4.1 API first, falls back to v4.0 if not available
   - Uses the detected version for all subsequent operations

3. **NGT Installation Process**:
   - Inserts NGT ISO into VM's CD-ROM drive
   - Initiates NGT installation using provided VM credentials
   - Monitors installation progress via API tasks
   - Verifies successful installation

4. **Verification**:
   - Checks multiple indicators (installed, enabled, version, reachable)
   - Provides clear status reporting
   - Handles edge cases and API response variations

## 🎯 Use Cases

- **Automated VM Provisioning**: Integrate NGT installation into VM deployment pipelines
- **Infrastructure Automation**: Bulk NGT installation across multiple VMs
- **Development Environments**: Automate NGT setup for development VMs

## 🧪 Testing

### Test Installation Status
```bash
./ngt_auto_install.py --skip-install --debug
```

### Test API Connectivity
```bash
./ngt_auto_install.py --dry-run --debug
```

### Test Specific VM
```bash
./ngt_auto_install.py --vm-uuid "your-vm-uuid" --skip-install
```

## 📝 Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history and changes.

## ⚖️ License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🔗 Related Documentation

- [Nutanix NGT Documentation](https://portal.nutanix.com/page/documents/details?targetId=Web-Console-Guide-Prism-v7_3:man-nutanix-guest-tool-c.html)
- [Nutanix API Documentation](https://www.nutanix.dev/)
- [Prism Central API Guide](https://portal.nutanix.com/page/documents/details?targetId=Prism-Central-Guide-v2023_4:arc-api-overview-c.html)


---

**Note**: This script is designed to work with Nutanix AHV environments and requires appropriate API access. Always test in a development environment before using in production.
