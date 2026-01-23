# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-01-23

### Added
- Initial release of VM Network Category Assigner
- Interactive CLI for subnet, category, and value selection
- Automatic VM discovery based on subnet connection
- Support for UI-visible categories only (filters hidden/system categories)
- Existing category value suggestions
- Proper API pagination handling (100-result limit)
- Bulk category assignment to multiple VMs
- v3 API implementation with full metadata preservation
- Utility scripts for debugging and testing:
  - `get_ui_visible_categories.py` - List UI-visible category keys
  - `verify_vm_categories.py` - Check VM category assignments
  - `check_category_exists.py` - Verify category key existence
- Comprehensive README with usage examples
- MIT License
- Requirements file for Python dependencies

### Technical Details
- Uses Nutanix Prism Central v3 API for VM updates
- Uses v4 APIs for subnet and category discovery
- Handles full metadata preservation for category assignment
- Supports both interactive and command-line modes

### Known Limitations
- Requires category KEY to exist before assignment
- API rate limit of 100 results per request
- Must preserve all metadata fields for successful assignment
- v4 API category assignment doesn't work (requires v3 API)

## [Unreleased]

### Planned Features
- Configuration file support for common settings
- Dry-run mode to preview changes before applying
- Export category assignments to CSV
- Import category assignments from CSV
- Multi-subnet selection for bulk operations
- Category removal/update operations
- Logging to file option
- Progress bar for large VM sets

