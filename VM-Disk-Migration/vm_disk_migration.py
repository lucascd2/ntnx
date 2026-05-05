#!/usr/bin/env python3
"""
Interactive VM Disk Migration Tool
Connects to Nutanix Prism Central to list VMs and Storage Containers,
then migrates selected VM disks to a chosen storage container.

APIs used (from Nutanix v4 specs):
  - GET  /storage/v4.0.a3/config/storage-containers
  - GET  /vmm/v4.2/ahv/config/vms
  - GET  /vmm/v4.2/ahv/config/vms/{extId}
  - GET  /vmm/v4.2/ahv/config/vms/{vmExtId}/disks
  - POST /vmm/v4.2/ahv/config/vms/{extId}/$actions/migrate-vm-disks
  - GET  /prism/v4.3/config/tasks/{extId}
"""

import getpass
import json
import sys
import time
import uuid
import argparse

try:
    import requests
    from requests.auth import HTTPBasicAuth
except ImportError:
    print("ERROR: 'requests' library is required. Install with: pip install requests")
    sys.exit(1)

# Suppress InsecureRequestWarning for self-signed certs
requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)

# ─── Constants ────────────────────────────────────────────────────────────────

BASE_PORT = 9440
PAGE_LIMIT = 100  # max per the API spec

STORAGE_CONTAINERS_URL = "/api/storage/v4.0.a3/config/storage-containers"
VMS_LIST_URL           = "/api/vmm/v4.2/ahv/config/vms"
VM_GET_URL             = "/api/vmm/v4.2/ahv/config/vms/{ext_id}"
VM_DISKS_URL           = "/api/vmm/v4.2/ahv/config/vms/{vm_ext_id}/disks"
MIGRATE_DISKS_URL      = "/api/vmm/v4.2/ahv/config/vms/{ext_id}/$actions/migrate-vm-disks"
TASK_URL               = "/api/prism/v4.3/config/tasks/{task_ext_id}"


# ─── Helpers ──────────────────────────────────────────────────────────────────

def build_url(pc_ip, path, **kwargs):
    """Build a full URL from the PC IP and path template."""
    return f"https://{pc_ip}:{BASE_PORT}{path.format(**kwargs)}"


def api_get(session, url, params=None):
    """Perform a GET request and return the response object."""
    resp = session.get(url, params=params, verify=False)
    resp.raise_for_status()
    return resp


def api_post(session, url, json_body, extra_headers=None):
    """Perform a POST request and return the response object."""
    headers = {"Content-Type": "application/json"}
    if extra_headers:
        headers.update(extra_headers)
    resp = session.post(url, json=json_body, headers=headers, verify=False)
    resp.raise_for_status()
    return resp


def paginate_get(session, url, key="data"):
    """Fetch all pages of a paginated list endpoint."""
    all_items = []
    page = 0
    while True:
        resp = api_get(session, url, params={"$page": page, "$limit": PAGE_LIMIT})
        body = resp.json()
        items = body.get(key) or body.get("data") or []
        if not items:
            break
        all_items.extend(items)
        if len(items) < PAGE_LIMIT:
            break
        page += 1
    return all_items


def format_bytes(size_bytes):
    """Human-readable byte size."""
    if size_bytes is None:
        return "N/A"
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(size_bytes) < 1024:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.2f} PB"


def prompt_selection(items, prompt_text, display_fn, allow_quit=True):
    """Display a numbered list and prompt the user to select one item."""
    if not items:
        print("  (none available)")
        return None

    for idx, item in enumerate(items, 1):
        print(f"  {idx:>3}. {display_fn(item)}")

    quit_text = ", or 'q' to quit" if allow_quit else ""
    while True:
        try:
            choice = input(f"\n{prompt_text} (1-{len(items)}{quit_text}): ").strip()
            if allow_quit and choice.lower() == "q":
                return None
            num = int(choice)
            if 1 <= num <= len(items):
                return items[num - 1]
            print(f"  Please enter a number between 1 and {len(items)}.")
        except ValueError:
            print("  Invalid input. Enter a number.")
        except (KeyboardInterrupt, EOFError):
            print("\nExiting.")
            return None


def prompt_yes_no(prompt_text):
    """Prompt for yes/no confirmation."""
    try:
        response = input(f"{prompt_text} (yes/no): ").strip().lower()
        return response in ("yes", "y")
    except (KeyboardInterrupt, EOFError):
        print("\nExiting.")
        return False


# ─── API Interactions ─────────────────────────────────────────────────────────

def get_storage_containers(session, pc_ip):
    """Fetch all storage containers."""
    url = build_url(pc_ip, STORAGE_CONTAINERS_URL)
    return paginate_get(session, url)


def get_vms(session, pc_ip):
    """Fetch all AHV VMs."""
    url = build_url(pc_ip, VMS_LIST_URL)
    return paginate_get(session, url)


def get_vm(session, pc_ip, vm_ext_id):
    """Fetch a single VM (needed for ETag)."""
    url = build_url(pc_ip, VM_GET_URL, ext_id=vm_ext_id)
    return api_get(session, url)


def get_vm_disks(session, pc_ip, vm_ext_id):
    """Fetch all disks for a VM."""
    url = build_url(pc_ip, VM_DISKS_URL, vm_ext_id=vm_ext_id)
    return paginate_get(session, url)


def migrate_vm_disks(session, pc_ip, vm_ext_id, etag, migration_body):
    """POST the migrate-vm-disks action."""
    url = build_url(pc_ip, MIGRATE_DISKS_URL, ext_id=vm_ext_id)
    extra_headers = {
        "If-Match": etag,
        "NTNX-Request-Id": str(uuid.uuid4()),
    }
    return api_post(session, url, migration_body, extra_headers)


def poll_task(session, pc_ip, task_ext_id, timeout=1800, interval=5):
    """Poll a Prism task until it completes or times out."""
    url = build_url(pc_ip, TASK_URL, task_ext_id=task_ext_id)
    elapsed = 0
    while elapsed < timeout:
        resp = api_get(session, url)
        task = resp.json().get("data", resp.json())
        status = task.get("status", "UNKNOWN")
        pct = task.get("progressPercentage") or task.get("percentageComplete") or ""
        pct_str = f" ({pct}%)" if pct else ""

        print(f"  Task status: {status}{pct_str}")

        if status in ("SUCCEEDED", "COMPLETED"):
            return True, task
        if status in ("FAILED", "ABORTED", "CANCELED"):
            error_msg = task.get("errorMessages") or task.get("errorDetail") or "Unknown error"
            return False, error_msg

        time.sleep(interval)
        elapsed += interval

    return False, "Timed out waiting for task to complete."


# ─── Disk-to-Container Mapping Helper ────────────────────────────────────────

def resolve_container_name(containers_by_id, disk):
    """Try to resolve the current storage container name for a disk."""
    backing = disk.get("backingInfo") or {}
    container_ref = backing.get("storageContainer") or {}
    ctr_id = container_ref.get("extId")
    if ctr_id and ctr_id in containers_by_id:
        return containers_by_id[ctr_id]["name"], ctr_id
    return "Unknown", ctr_id


# ─── Migration Workflow ───────────────────────────────────────────────────────

def perform_migration(session, pc_ip, containers, containers_by_id, vms):
    """Execute a single VM disk migration workflow."""
    
    # ── Select a VM ───────────────────────────────────────────────────────
    print("\nAvailable VMs:")
    selected_vm = prompt_selection(
        vms,
        "Select a VM",
        lambda v: f"{v.get('name', 'N/A'):<40} (extId: {v.get('extId', 'N/A')})"
    )
    if not selected_vm:
        return False  # User quit

    vm_ext_id = selected_vm.get("extId")
    vm_name = selected_vm.get("name", "N/A")
    print(f"\nSelected VM: {vm_name} ({vm_ext_id})")

    # ── Fetch VM disks ────────────────────────────────────────────────────
    print("Fetching VM disks...")
    try:
        disks = get_vm_disks(session, pc_ip, vm_ext_id)
    except requests.HTTPError as e:
        print(f"ERROR fetching disks: {e}")
        return True  # Continue to menu

    # Filter to only VmDisk-backed disks (exclude volume group references, CD-ROMs, etc.)
    migratable_disks = []
    for d in disks:
        backing = d.get("backingInfo") or {}
        obj_type = backing.get("$objectType", "")
        # VmDisk-backed disks have a diskExtId
        if backing.get("diskExtId") or "VmDisk" in obj_type:
            migratable_disks.append(d)

    if not migratable_disks:
        print("No migratable disks found on this VM.")
        return True  # Continue to menu

    print(f"\nDisks on VM '{vm_name}':")
    print("-" * 90)
    print(f"  {'#':>3}  {'Bus/Index':<14} {'Disk ExtId':<38} {'Size':<12} {'Current Container'}")
    print("-" * 90)
    for idx, d in enumerate(migratable_disks, 1):
        addr = d.get("diskAddress") or {}
        bus = addr.get("busType", "?")
        index = addr.get("index", "?")
        backing = d.get("backingInfo") or {}
        disk_ext_id = backing.get("diskExtId", "N/A")
        size = format_bytes(backing.get("diskSizeBytes"))
        ctr_name, _ = resolve_container_name(containers_by_id, d)
        print(f"  {idx:>3}  {bus}/{index:<12} {disk_ext_id:<38} {size:<12} {ctr_name}")
    print("-" * 90)

    # ── Select target storage container ───────────────────────────────────
    print("\nAvailable Storage Containers:")
    selected_container = prompt_selection(
        containers,
        "Select a target storage container",
        lambda c: f"{c.get('name', 'N/A'):<40} (extId: {c.get('_resolved_id', 'N/A')})"
    )
    if not selected_container:
        return False  # User quit

    target_ctr_id = selected_container["_resolved_id"]
    target_ctr_name = selected_container.get("name", "N/A")
    print(f"\nTarget container: {target_ctr_name} ({target_ctr_id})")

    # ── Choose migration mode ─────────────────────────────────────────────
    print("\nMigration options:")
    print("  1. Migrate ALL disks to the selected container")
    print("  2. Choose specific disks to migrate")

    while True:
        try:
            mode = input("\nSelect option (1 or 2, or 'q' to quit): ").strip().lower()
            if mode == "q":
                return False
            if mode in ("1", "2"):
                break
            print("  Please enter 1 or 2.")
        except (KeyboardInterrupt, EOFError):
            print("\nExiting.")
            return False

    if mode == "1":
        # AllDisksMigrationPlan — migrate all disks to one container
        migration_body = {
            "migrateDisks": {
                "$objectType": "vmm.v4.ahv.config.AllDisksMigrationPlan",
                "storageContainer": {
                    "extId": target_ctr_id,
                    "$objectType": "vmm.v4.ahv.config.VmDiskContainerReference"
                }
            },
            "$objectType": "vmm.v4.ahv.config.DiskMigrationParams"
        }
        print(f"\nWill migrate ALL {len(migratable_disks)} disk(s) to '{target_ctr_name}'.")
    else:
        # Per-disk migration plan
        print("\nSelect disks to migrate (comma-separated numbers, e.g. 1,3):")
        while True:
            try:
                choices = input("Disk numbers (or 'q' to quit): ").strip().lower()
                if choices == "q":
                    return False
                indices = [int(x.strip()) for x in choices.split(",")]
                if all(1 <= i <= len(migratable_disks) for i in indices):
                    break
                print(f"  Numbers must be between 1 and {len(migratable_disks)}.")
            except ValueError:
                print("  Invalid input. Use comma-separated numbers.")
            except (KeyboardInterrupt, EOFError):
                print("\nExiting.")
                return False

        selected_disks = [migratable_disks[i - 1] for i in indices]
        vm_disk_refs = []
        for d in selected_disks:
            backing = d.get("backingInfo") or {}
            vm_disk_refs.append({
                "diskExtId": backing["diskExtId"],
                "$objectType": "vmm.v4.ahv.config.MigrateDiskReference"
            })

        migration_body = {
            "migrateDisks": {
                "$objectType": "vmm.v4.ahv.config.MigrationPlans",
                "plans": [
                    {
                        "storageContainer": {
                            "extId": target_ctr_id,
                            "$objectType": "vmm.v4.ahv.config.VmDiskContainerReference"
                        },
                        "vmDisks": vm_disk_refs,
                        "$objectType": "vmm.v4.ahv.config.ADSFDiskMigrationPlan"
                    }
                ]
            },
            "$objectType": "vmm.v4.ahv.config.DiskMigrationParams"
        }
        print(f"\nWill migrate {len(selected_disks)} disk(s) to '{target_ctr_name}'.")

    # ── Confirm ───────────────────────────────────────────────────────────
    if not prompt_yes_no("\nProceed with migration?"):
        print("Migration cancelled.")
        return True  # Continue to menu

    # ── Get VM ETag ───────────────────────────────────────────────────────
    print("\nRetrieving VM ETag...")
    try:
        vm_resp = get_vm(session, pc_ip, vm_ext_id)
        etag = vm_resp.headers.get("ETag") or vm_resp.headers.get("etag")
        if not etag:
            print("ERROR: Could not retrieve ETag from VM GET response.")
            print("  Response headers:", dict(vm_resp.headers))
            return True  # Continue to menu
    except requests.HTTPError as e:
        print(f"ERROR fetching VM for ETag: {e}")
        return True  # Continue to menu

    # ── Execute migration ─────────────────────────────────────────────────
    print("Submitting disk migration request...")
    try:
        migrate_resp = migrate_vm_disks(session, pc_ip, vm_ext_id, etag, migration_body)
    except requests.HTTPError as e:
        print(f"ERROR during migration request: {e}")
        try:
            print(f"  Response body: {e.response.json()}")
        except Exception:
            print(f"  Response text: {e.response.text}")
        return True  # Continue to menu

    migrate_data = migrate_resp.json()

    # Extract task ID from response
    task_data = migrate_data.get("data") or {}
    task_ext_id = task_data.get("extId")

    if not task_ext_id:
        print("Migration submitted. Response:")
        print(json.dumps(migrate_data, indent=2))
        return True  # Continue to menu

    print(f"Migration task created: {task_ext_id}")

    # ── Poll task ─────────────────────────────────────────────────────────
    print("Monitoring task progress...\n")
    success, result = poll_task(session, pc_ip, task_ext_id)

    if success:
        print("\n✓ Disk migration completed successfully!")
    else:
        print(f"\n✗ Disk migration failed: {result}")

    return True  # Continue to menu

# ─── Argument Parsing ─────────────────────────────────────────────────────────

def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Nutanix VM Disk Migration Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive mode (prompt for all credentials)
  %(prog)s

  # Provide PC IP only (prompt for username/password)
  %(prog)s --pc-ip 10.42.159.5

  # Provide all credentials
  %(prog)s --pc-ip 10.42.159.5 --username admin --password mypass

  # Use environment variables for password (more secure)
  export PC_PASSWORD=mypass
  %(prog)s --pc-ip 10.42.159.5 --username admin --password "$PC_PASSWORD"
        """
    )
    
    parser.add_argument(
        "--pc-ip", "--pc", "-p",
        dest="pc_ip",
        help="Prism Central IP address or FQDN"
    )
    
    parser.add_argument(
        "--username", "--user", "-u",
        dest="username",
        help="Prism Central username"
    )
    
    parser.add_argument(
        "--password", "--pass", "-w",
        dest="password",
        help="Prism Central password (consider using environment variables for security)"
    )
    
    return parser.parse_args()



# ─── Main Flow ────────────────────────────────────────────────────────────────

def main():
    print("=" * 64)
    print("  Nutanix VM Disk Migration Tool")
    print("=" * 64)

    # ── Connection details ────────────────────────────────────────────────
    # ── Parse command-line arguments ──────────────────────────────────────
    args = parse_arguments()

    try:
        # Use command-line arg or prompt for PC IP
        if args.pc_ip:
            pc_ip = args.pc_ip
            print(f"\nPrism Central IP/FQDN: {pc_ip}")
        else:
            pc_ip = input("\nPrism Central IP/FQDN: ").strip()
            if not pc_ip:
                print("No IP provided. Exiting.")
                sys.exit(1)
        
        # Use command-line arg or prompt for username
        if args.username:
            username = args.username
            print(f"Username: {username}")
        else:
            username = input("Username: ").strip()
        
        # Use command-line arg or prompt for password
        if args.password:
            password = args.password
            print("Password: ********")
        else:
            password = getpass.getpass("Password: ")
            
    except (KeyboardInterrupt, EOFError):
        print("\nExiting.")
        sys.exit(0)

    session = requests.Session()
    session.auth = HTTPBasicAuth(username, password)

    # ── Fetch storage containers (once) ───────────────────────────────────
    print("\nFetching storage containers...")
    try:
        containers = get_storage_containers(session, pc_ip)
    except requests.HTTPError as e:
        print(f"ERROR fetching storage containers: {e}")
        sys.exit(1)

    if not containers:
        print("No storage containers found.")
        sys.exit(1)

    # Build lookup by extId (use containerExtId or extId depending on response)
    containers_by_id = {}
    for c in containers:
        cid = c.get("containerExtId") or c.get("extId") or ""
        c["_resolved_id"] = cid
        if cid:
            containers_by_id[cid] = c

    print(f"Found {len(containers)} storage container(s).")

    # ── Main menu loop ────────────────────────────────────────────────────
    while True:
        print("\n" + "=" * 64)
        print("  Main Menu")
        print("=" * 64)
        print("  1. Perform VM disk migration")
        print("  Q. Quit")
        
        try:
            choice = input("\nSelect an option: ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting.")
            sys.exit(0)

        if choice == "q":
            print("Exiting.")
            sys.exit(0)
        elif choice == "1":
            # Fetch VMs fresh each time
            print("\nFetching VMs...")
            try:
                vms = get_vms(session, pc_ip)
            except requests.HTTPError as e:
                print(f"ERROR fetching VMs: {e}")
                continue

            if not vms:
                print("No VMs found.")
                continue

            # Sort VMs alphabetically by name
            vms.sort(key=lambda v: (v.get("name") or "").lower())
            print(f"Found {len(vms)} VM(s).")

            # Perform migration workflow
            continue_running = perform_migration(session, pc_ip, containers, containers_by_id, vms)
            if not continue_running:
                print("Exiting.")
                sys.exit(0)
        else:
            print("  Invalid option. Please enter 1 or Q.")


if __name__ == "__main__":
    main()
