#!/usr/bin/env python3
"""
Troubleshooting script for list_vms.py

This script helps diagnose common issues when the VM listing script fails.
"""

import argparse
import sys
import subprocess
import socket
from urllib.parse import urlparse

def test_network_connectivity(pc_ip: str, port: int = 9440) -> bool:
    """Test basic network connectivity to Prism Central."""
    print(f"Testing network connectivity to {pc_ip}:{port}...")
    
    try:
        # Test basic socket connection
        sock = socket.create_connection((pc_ip, port), timeout=10)
        sock.close()
        print(f"✓ Network connectivity to {pc_ip}:{port} is working")
        return True
    except socket.timeout:
        print(f"✗ Connection timeout to {pc_ip}:{port}")
        return False
    except socket.gaierror as e:
        print(f"✗ DNS resolution failed for {pc_ip}: {e}")
        return False
    except Exception as e:
        print(f"✗ Network connection failed: {e}")
        return False

def test_ssl_connectivity(pc_ip: str) -> bool:
    """Test SSL connectivity using curl."""
    print(f"Testing SSL connectivity to {pc_ip}...")
    
    try:
        # Test with curl (ignoring SSL certificates)
        result = subprocess.run(
            ['curl', '-k', '-s', '-o', '/dev/null', '-w', '%{http_code}', 
             f'https://{pc_ip}:9440/'],
            capture_output=True, text=True, timeout=10
        )
        
        if result.returncode == 0:
            status_code = result.stdout.strip()
            if status_code in ['200', '302', '401', '403']:  # Any valid HTTP response
                print(f"✓ SSL connectivity works (HTTP {status_code})")
                return True
            else:
                print(f"✗ Unexpected HTTP status: {status_code}")
                return False
        else:
            print(f"✗ curl command failed: {result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        print("✗ SSL connection timeout")
        return False
    except FileNotFoundError:
        print("⚠ curl not found - cannot test SSL connectivity")
        return True  # Don't fail if curl isn't available
    except Exception as e:
        print(f"✗ SSL test failed: {e}")
        return False

def run_connection_test(pc_ip: str, username: str = None, password: str = None) -> bool:
    """Run the connection test from list_vms.py."""
    print(f"Running connection test using list_vms.py...")
    
    cmd = ['python3', 'list_vms.py', '--test-connection', '--verbose']
    
    if pc_ip:
        cmd.extend(['--pc-ip', pc_ip])
    if username:
        cmd.extend(['--username', username])
    if password:
        cmd.extend(['--password', password])
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        print("Connection test output:")
        if result.stdout:
            for line in result.stdout.split('\n'):
                if line.strip():
                    print(f"  {line}")
        
        if result.stderr:
            print("Errors:")
            for line in result.stderr.split('\n'):
                if line.strip():
                    print(f"  {line}")
        
        return result.returncode == 0
        
    except subprocess.TimeoutExpired:
        print("✗ Connection test timeout")
        return False
    except Exception as e:
        print(f"✗ Connection test failed: {e}")
        return False

def main():
    """Main troubleshooting function."""
    parser = argparse.ArgumentParser(
        description="Troubleshoot issues with list_vms.py",
        epilog="This script helps diagnose common connectivity and authentication issues."
    )
    
    parser.add_argument('--pc-ip', required=True, help='Prism Central IP address or FQDN')
    parser.add_argument('--username', help='Username for authentication (optional for basic tests)')
    parser.add_argument('--password', help='Password for authentication (optional for basic tests)')
    parser.add_argument('--skip-auth-test', action='store_true', 
                       help='Skip authentication test (only test network connectivity)')
    
    args = parser.parse_args()
    
    print("=== Nutanix Prism Central Troubleshooting ===")
    print()
    
    # Step 1: Basic network connectivity
    print("Step 1: Testing basic network connectivity...")
    network_ok = test_network_connectivity(args.pc_ip)
    print()
    
    if not network_ok:
        print("❌ Network connectivity failed. Please check:")
        print("  - Prism Central IP address is correct")
        print("  - Network connectivity to Prism Central")
        print("  - Firewall settings allow HTTPS (port 9440)")
        print("  - DNS resolution (if using FQDN)")
        sys.exit(1)
    
    # Step 2: SSL connectivity
    print("Step 2: Testing SSL connectivity...")
    ssl_ok = test_ssl_connectivity(args.pc_ip)
    print()
    
    if not ssl_ok:
        print("⚠ SSL connectivity issues detected. This may indicate:")
        print("  - SSL/TLS configuration problems")
        print("  - Network proxy interfering with HTTPS")
        print("  - Prism Central not responding on port 9440")
    
    # Step 3: Authentication and API test (if credentials provided)
    if not args.skip_auth_test and (args.username or args.password):
        print("Step 3: Testing authentication and API availability...")
        auth_ok = run_connection_test(args.pc_ip, args.username, args.password)
        print()
        
        if not auth_ok:
            print("❌ Authentication or API test failed. Please check:")
            print("  - Username and password are correct")
            print("  - User has appropriate permissions")
            print("  - Prism Central is running and responsive")
            print("  - VMM service is available")
            sys.exit(1)
        else:
            print("✅ All tests passed! The script should work normally.")
    else:
        print("Step 3: Skipping authentication test (no credentials provided)")
        print("To test authentication, run:")
        print(f"  python3 list_vms.py --pc-ip {args.pc_ip} --test-connection --verbose")
        print()
        
        if network_ok and ssl_ok:
            print("✅ Basic connectivity tests passed!")
            print("If you're still having issues, try the connection test with credentials.")
        else:
            print("⚠ Some connectivity tests failed. Address the issues above before proceeding.")

if __name__ == "__main__":
    main()
