# Examples

This directory contains practical examples for using the NGT Auto Installation Script in various scenarios.

## 📁 Files

### `basic_usage.sh`
Interactive shell script that demonstrates common usage patterns:
- Interactive mode
- Command-line usage
- Status checking
- Dry run mode
- Debug mode
- VM-specific installation

**Usage:**
```bash
./basic_usage.sh
```

### `automation_example.py`
Python examples showing integration with automation workflows:
- Single VM installation
- Bulk VM installation
- Infrastructure-as-Code integration
- Error handling and reporting

**Usage:**
```bash
python3 automation_example.py
```

## 🚀 Quick Start

1. **First-time users**: Start with the basic usage examples:
   ```bash
   cd examples
   ./basic_usage.sh
   ```

2. **Automation developers**: Review the automation examples:
   ```bash
   python3 automation_example.py
   ```

## 🎯 Use Case Examples

### Development Environment
```bash
# Quick NGT installation for development VM
../ngt_auto_install.py --pc-ip "10.38.11.74" --username "admin" --debug
```

### Production Deployment
```bash
# Secure production installation (prompts for passwords)
../ngt_auto_install.py \
  --pc-ip "prod-pc.company.com" \
  --username "admin" \
  --verify-ssl \
  --no-reboot
```

### Bulk Installation
See `automation_example.py` for a complete implementation of bulk NGT installation across multiple VMs.

### CI/CD Integration
```bash
# Non-interactive installation for CI/CD pipelines
../ngt_auto_install.py \
  --pc-ip "$NUTANIX_PC_IP" \
  --username "$NUTANIX_USERNAME" \
  --password "$NUTANIX_PASSWORD" \
  --vm-uuid "$VM_UUID" \
  --vm-username "$VM_USERNAME" \
  --vm-password "$VM_PASSWORD"
```

## 🔧 Configuration Examples

### Environment Variables
```bash
export NUTANIX_PC_IP="10.38.11.74"
export NUTANIX_USERNAME="admin"
export NUTANIX_PASSWORD="secure-password"
export VM_USERNAME="administrator"
export VM_PASSWORD="vm-password"

# Use environment variables in script
../ngt_auto_install.py \
  --pc-ip "$NUTANIX_PC_IP" \
  --username "$NUTANIX_USERNAME" \
  --password "$NUTANIX_PASSWORD" \
  --vm-username "$VM_USERNAME" \
  --vm-password "$VM_PASSWORD"
```

### Configuration File (Future Enhancement)
```yaml
# ngt_config.yaml (planned feature)
nutanix:
  pc_ip: "10.38.11.74"
  username: "admin"
  port: 9440
  verify_ssl: false

vm_credentials:
  username: "administrator"
  password: "encrypted-password"

options:
  debug: true
  no_reboot: false
  timeout: 600
```

## 🐛 Troubleshooting Examples

### Debug Mode
```bash
# Get detailed logs for troubleshooting
../ngt_auto_install.py --debug --pc-ip "10.38.11.74" --username "admin"
```

### Connection Testing
```bash
# Test connectivity without installing
../ngt_auto_install.py --dry-run --pc-ip "10.38.11.74" --username "admin"
```

### Status Checking
```bash
# Check current NGT status
../ngt_auto_install.py --skip-install --pc-ip "10.38.11.74" --username "admin"
```

## 📚 Integration Patterns

### Ansible Playbook
```yaml
# Example Ansible task (requires ansible-nutanix collection)
- name: Install NGT on VMs
  shell: |
    /path/to/ngt_auto_install.py \
      --pc-ip "{{ nutanix_pc_ip }}" \
      --username "{{ nutanix_username }}" \
      --password "{{ nutanix_password }}" \
      --vm-uuid "{{ vm_uuid }}" \
      --vm-username "{{ vm_username }}" \
      --vm-password "{{ vm_password }}"
  delegate_to: "{{ inventory_hostname }}"
```

### Terraform Integration
```hcl
# Example Terraform null_resource
resource "null_resource" "install_ngt" {
  provisioner "remote-exec" {
    inline = [
      "/path/to/ngt_auto_install.py --pc-ip ${var.pc_ip} --username ${var.username} --password ${var.password}"
    ]
    connection {
      type     = "ssh"
      user     = var.vm_user
      password = var.vm_password
      host     = var.vm_ip
    }
  }
  
  depends_on = [nutanix_virtual_machine.vm]
}
```

## 📝 Notes

- Always use secure credential management in production
- Test scripts in development environment first
- Review logs for troubleshooting
- Consider using `--no-reboot` for critical systems
- Use `--verify-ssl` in production environments

## 🔗 Related Documentation

- [Main README](../README.md)
- [CHANGELOG](../CHANGELOG.md)
- [CONTRIBUTING](../CONTRIBUTING.md)
