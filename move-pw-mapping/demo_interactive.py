#!/usr/bin/env python3
"""Demo script to show interactive prompts without API calls"""

import sys
import getpass
import os

def prompt_for_input(prompt: str, default: str = None, password: bool = False, required: bool = True) -> str:
    """Demo version of prompt function"""
    if default:
        display_prompt = f"{prompt} [{default}]: "
    else:
        display_prompt = f"{prompt}: "
    
    while True:
        if password:
            value = getpass.getpass(display_prompt)
        else:
            value = input(display_prompt)
        
        if not value and default:
            value = default
        
        if required and not value:
            print("This field is required. Please enter a value.")
            continue
        
        return value

def demo_interactive():
    """Demo the interactive prompts"""
    print("\n=== Interactive Mode Demo ===\n")
    
    print("Move Server Configuration:")
    move_server = prompt_for_input("Move server IP/FQDN", "demo.nutanix.com")
    move_username = prompt_for_input("Move username", "admin")
    move_password = prompt_for_input("Move password", password=True)
    
    print(f"\nDemo Results:")
    print(f"Move Server: {move_server}")
    print(f"Username: {move_username}")
    print(f"Password: {'*' * len(move_password)}")
    
    print(f"\nDemo completed successfully!")

if __name__ == "__main__":
    try:
        demo_interactive()
    except KeyboardInterrupt:
        print("\n\nDemo cancelled by user.")
        sys.exit(1)
