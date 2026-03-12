# NGT Auto Installation Script - PowerShell Version

This is the PowerShell version of the NGT (Nutanix Guest Tools) auto-installation script, designed to work on Windows VMs running in Nutanix environments.

## Features

- **Auto-detection**: Automatically detects the local Windows VM and finds it in Nutanix
- **UUID Detection**: Uses WMI and Registry to detect the VM UUID
- **API Version Support**: Supports both Nutanix v4.1 and v4.0 APIs with automatic fallback
- **Complete NGT Installation**: Handles CD-ROM insertion and NGT installation with proper verification
- **Task Monitoring**: Monitors installation progress and provides status updates
- **Comprehensive Error Handling**: Detailed error messages and debugging information

## Requirements

- **PowerShell 5.0 or later**
- **Windows VM** running on Nutanix AHV
- **Network access** to Prism Central
- **Administrative privileges** on the local VM
- **Valid Nutanix cluster credentials**

## Usage Examples

### Basic Usage (Interactive Mode)
```powershell
.\ngt_auto_install.ps1
```

### Specify Prism Central and Username
```powershell
.\ngt_auto_install.ps1 -PCIp "10.38.11.74" -Username "admin"
```

### Full Parameters
```powershell
.\ngt_auto_install.ps1 -PCIp "10.38.11.74" -Username "admin" -VMUsername "administrator"
```

### Specify VM UUID Directly
```powershell
.\ngt_auto_install.ps1 -VMUUID "a6b7070a-ea76-4689-8d2a-861374694953" -PCIp "10.38.11.74" -Username "admin"
```

### Dry Run (Test Mode)
```powershell
.\ngt_auto_install.ps1 -PCIp "10.38.11.74" -Username "admin" -DryRun
```

### Skip Reboot After Installation
```powershell
.\ngt_auto_install.ps1 -PCIp "10.38.11.74" -Username "admin" -NoReboot
```

### Force API Version
```powershell
.\ngt_auto_install.ps1 -PCIp "10.38.11.74" -Username "admin" -ForceAPIVersion "v4.0"
```

### Debug Mode
```powershell
.\ngt_auto_install.ps1 -PCIp "10.38.11.74" -Username "admin" -Debug
```

## Parameters

| Parameter | Type | Description | Required |
|-----------|------|-------------|----------|
| `PCIp` | String | Prism Central IP address | No* |
| `Username` | String | Nutanix cluster username | No* |
| `Password` | String | Nutanix cluster password (not recommended for production) | No* |
| `Port` | Int | API port number (default: 9440) | No |
| `VMUsername` | String | VM guest OS username | No* |
| `VMPassword` | String | VM guest OS password | No* |
| `VMUUID` | String | VM UUID (overrides auto-detection) | No |
| `VMName` | String | VM name (overrides auto-detection) | No |
| `ForceAPIVersion` | String | Force API version (v4.0 or v4.1) | No |
| `DryRun` | Switch | Test mode - show what would be done | No |
| `NoReboot` | Switch | Skip VM reboot after installation | No |
| `SkipInstall` | Switch | Only check status, don't install | No |
| `Debug` | Switch | Enable verbose debug logging | No |

*\* Required parameters will be prompted if not provided*

## VM Detection Methods

The script uses multiple methods to detect the local VM:

1. **WMI UUID Detection**: Uses `Win32_ComputerSystemProduct.UUID`
2. **Registry Machine GUID**: Uses `HKLM:\SOFTWARE\Microsoft\Cryptography\MachineGuid`
3. **Hostname Fallback**: Uses computer name and FQDN

## Installation Process

1. **VM Discovery**: Finds the local VM in Nutanix using UUID or hostname
2. **Status Check**: Verifies current NGT installation status
3. **ISO Insertion**: Inserts the NGT ISO into the VM's CD-ROM
4. **Installation**: Installs NGT using provided VM credentials
5. **Task Monitoring**: Monitors the installation task progress
6. **Verification**: Verifies successful installation and activation

## Security Notes

- **SSL Certificate Validation** is disabled for self-signed certificates
- **Credentials** are prompted securely when not provided as parameters
- **Passwords** should not be passed as command-line parameters in production
- **Execution Policy** may need to be adjusted to run the script

## Execution Policy

You may need to adjust PowerShell's execution policy:

```powershell
# For current user only (recommended)
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Or for the entire machine (requires admin rights)
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope LocalMachine
```

## Troubleshooting

### Common Issues

1. **VM Not Found**
   - Ensure the script is running inside a Nutanix VM
   - Check that the VM name in Nutanix matches the Windows computer name
   - Use `-VMUUID` parameter to specify the UUID directly

2. **API Connection Issues**
   - Verify Prism Central IP and port accessibility
   - Check network connectivity and firewall settings
   - Ensure credentials are correct

3. **NGT Installation Fails**
   - Verify VM credentials are correct and have admin privileges
   - Ensure the VM has sufficient resources
   - Check if antivirus software is blocking the installation

4. **PowerShell Execution Issues**
   - Check PowerShell execution policy
   - Ensure PowerShell 5.0 or later is installed
   - Run PowerShell as Administrator if needed

### Debug Mode

Use the `-Debug` parameter for verbose logging:

```powershell
.\ngt_auto_install.ps1 -PCIp "10.38.11.74" -Username "admin" -Debug
```

This will provide detailed information about:
- API requests and responses
- VM detection process
- Installation steps
- Error details

## Comparison with Python Version

| Feature | Python Version | PowerShell Version |
|---------|----------------|-------------------|
| OS Support | Linux/Unix/Windows | Windows |
| UUID Detection | dmidecode, /sys/hypervisor | WMI, Registry |
| Dependencies | requests, urllib3 | Built-in .NET classes |
| Error Handling | Python exceptions | PowerShell error handling |
| SSL Handling | urllib3.disable_warnings | ServicePointManager |
| JSON Handling | json module | ConvertTo-Json/ConvertFrom-Json |

## License

This script follows the same license as the original Python version.

## Support

For issues and support, please refer to the original repository or contact your Nutanix administrator.
