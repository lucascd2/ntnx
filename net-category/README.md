# Nutanix VM Network Category Assigner

Automatically assign categories to Nutanix VMs based on their network/subnet connections using Prism Central APIs.

## Overview

This tool helps automate the process of assigning categories to VMs based on which subnet/network they are connected to. Instead of manually assigning categories in the Prism Central UI, you can use this script to bulk-assign categories to all VMs on a specific network.

## Features

- ✅ **Interactive CLI** - User-friendly prompts for subnet, category, and value selection
- ✅ **Network-based assignment** - Automatically finds VMs connected to selected subnet
- ✅ **Category value suggestions** - Shows existing category values or create new ones
- ✅ **Proper pagination** - Handles APIs with 100-result limits correctly
- ✅ **UI-visible categories only** - Filters to show categories that appear in Prism Central UI
- ✅ **Bulk assignment** - Assigns categories to multiple VMs at once
- ✅ **v3 API** - Uses the reliable Nutanix v3 API with full metadata preservation

## Requirements

- Python 3.6+
- Nutanix Prism Central (tested with v4 APIs)
- Network access to Prism Central
- User account with permissions to assign categories

### Python Dependencies

```bash
pip install requests urllib3
```

Or install from requirements file:
```bash
pip install -r requirements.txt
```

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/nutanix-vm-category-assigner.git
cd nutanix-vm-category-assigner
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Make the script executable (optional):
```bash
chmod +x vm_category_assigner_final.py
```

## Usage

### Interactive Mode (Recommended)

Run the script and follow the prompts:

```bash
python vm_category_assigner_final.py
```

You'll be prompted for:
1. **Prism Central IP address**
2. **Username**
3. **Password** (hidden input)
4. **Subnet selection** from available networks
5. **Category key** from UI-visible categories
6. **Category value** from existing values or create new

### Command Line Mode

Provide credentials as arguments:

```bash
python vm_category_assigner_final.py <PC_IP> <USERNAME> <PASSWORD>
```

Example:
```bash
python vm_category_assigner_final.py 10.42.42.40 admin mypassword
```

## Workflow Example

```
=== VM Network Category Assigner (v3 API) ===

Fetching all subnets...
Found 25 subnets

Available Subnets:
------------------------------------------------------------
  1. Production-Network (96121986-697a-44d9-8fdf-98d144d1abed)
  2. Development-Network (87231097-808b-55ea-af0e-09e255e2bcfe)
  3. Test-Network (73342108-919c-66fb-bg1f-10f366f3cdgf)

Select subnet (1-3): 1

Selected subnet: Production-Network

Finding VMs connected to subnet...
Found 15 VMs connected to subnet

VMs connected to 'Production-Network':
------------------------------------------------------------
  1. web-server-01 (fe4a6be2-f5ad-4540-5e83-28576450f449)
  2. app-server-01 (a1b2c3d4-e5f6-7890-1a2b-3c4d5e6f7g8h)
  ...

Fetching UI-visible categories...
Found 111 UI-visible category keys

Available Category Keys:
----------------------------------------
  1. Environment
  2. AppTier
  3. Department
  ...

Select category key (1-111): 1

Fetching existing values for category 'Environment'...
Found 4 existing values for 'Environment'

Existing values for 'Environment':
----------------------------------------
  1. Development
  2. Production
  3. Staging
  4. Testing
  5. [Enter new value]

Select value (1-5): 2

Ready to assign:
  Category: Environment:Production
  To 15 VMs on subnet: Production-Network

Proceed? (y/n): y

Assigning category to 15 VMs...
  Assigning to web-server-01...
    ✓ Success
  Assigning to app-server-01...
    ✓ Success
  ...

Assignment complete!
  Successfully assigned: 15/15 VMs
  Category: Environment:Production

Please check Prism Central UI to verify the assignments.
```

## How It Works

1. **Fetches all subnets** from Prism Central using the Networking API
2. **Finds VMs** connected to the selected subnet using v3 VMs API
3. **Lists UI-visible categories** (filters hidden/system categories)
4. **Shows existing category values** for consistency
5. **Assigns categories** using v3 API with full metadata preservation
6. **Verifies** assignments are visible in Prism Central UI

