#!/bin/bash

# NGT Auto Installation Script - Basic Usage Examples
# ====================================================

# Set your Nutanix environment details
PRISM_CENTRAL_IP="10.38.11.74"
ADMIN_USERNAME="admin"

echo "NGT Auto Installation Script - Usage Examples"
echo "=============================================="

echo ""
echo "1. Interactive Mode (Recommended for first-time use)"
echo "   This will prompt for all required information:"
echo "   ./ngt_auto_install.py"

echo ""
echo "2. Basic Command Line Usage"
echo "   Provide Prism Central details, script will prompt for passwords:"
echo "   ./ngt_auto_install.py --pc-ip '$PRISM_CENTRAL_IP' --username '$ADMIN_USERNAME'"

echo ""
echo "3. Check NGT Status Only (No Installation)"
echo "   Use this to verify current NGT status:"
echo "   ./ngt_auto_install.py --pc-ip '$PRISM_CENTRAL_IP' --username '$ADMIN_USERNAME' --skip-install"

echo ""
echo "4. Dry Run Mode (Preview Actions)"
echo "   See what the script would do without making changes:"
echo "   ./ngt_auto_install.py --pc-ip '$PRISM_CENTRAL_IP' --username '$ADMIN_USERNAME' --dry-run"

echo ""
echo "5. Debug Mode (Troubleshooting)"
echo "   Get detailed logging for troubleshooting:"
echo "   ./ngt_auto_install.py --pc-ip '$PRISM_CENTRAL_IP' --username '$ADMIN_USERNAME' --debug"

echo ""
echo "6. Specific VM by UUID"
echo "   Install NGT on a specific VM (useful if auto-detection fails):"
echo "   ./ngt_auto_install.py --pc-ip '$PRISM_CENTRAL_IP' --username '$ADMIN_USERNAME' --vm-uuid 'your-vm-uuid-here'"

echo ""
echo "7. No VM Reboot After Installation"
echo "   Install NGT but don't reboot the VM automatically:"
echo "   ./ngt_auto_install.py --pc-ip '$PRISM_CENTRAL_IP' --username '$ADMIN_USERNAME' --no-reboot"

echo ""
echo "8. Complete Command Line Example (Not Recommended for Production)"
echo "   Provide all credentials via command line:"
echo "   ./ngt_auto_install.py \\"
echo "     --pc-ip '$PRISM_CENTRAL_IP' \\"
echo "     --username '$ADMIN_USERNAME' \\"
echo "     --password 'admin-password' \\"
echo "     --vm-username 'vm-user' \\"
echo "     --vm-password 'vm-password'"

echo ""
echo "Security Notes:"
echo "- Avoid using --password and --vm-password in production"
echo "- The script will prompt securely for passwords when not provided"
echo "- Use --verify-ssl in production environments"

echo ""
echo "Troubleshooting:"
echo "- Always start with --debug flag if you encounter issues"
echo "- Use --skip-install to test connectivity without changes"
echo "- Check the README.md for detailed troubleshooting guide"
