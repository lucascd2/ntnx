#!/usr/bin/env python3
"""Test script to validate CSV reading functionality"""

import sys
sys.path.append('.')
from nutanix_move_migration import read_vm_credentials

def test_csv_reading():
    """Test the CSV reading function"""
    try:
        print("Testing CSV reading with sample file...")
        credentials = read_vm_credentials("vm_credentials_sample.csv")
        
        print("\nCredentials loaded:")
        for vm_name, creds in credentials.items():
            print(f"  {vm_name}: {creds['username']} / {'*' * len(creds['password'])}")
        
        print(f"\nTotal VMs with credentials: {len(credentials)}")
        return True
        
    except Exception as e:
        print(f"Error testing CSV reading: {e}")
        return False

if __name__ == "__main__":
    success = test_csv_reading()
    sys.exit(0 if success else 1)
