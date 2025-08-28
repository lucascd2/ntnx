# Changelog

All notable changes to the NGT Auto Installation Script will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2025-08-26

### 🔧 Fixed
- **BREAKING FIX**: Resolved 404 Client Error during NGT installation verification
- Fixed API version compatibility issues between v4.1 spec and v4.0 cluster implementations
- Improved handling of `None` values in NGT status responses for uninstalled NGT
- Enhanced verification logic with multiple validation criteria
- Removed dependency on v4.1 API endpoints that don't exist on many clusters

### ✨ Added
- Automatic API version detection with v4.1/v4.0 fallback
- Enhanced verification system with multiple status indicators
- Better error messages and troubleshooting information
- Improved debug logging for API interactions
- More robust handling of edge cases in NGT status detection

### 🚀 Improved
- Better handling of clusters that only support v4.0 APIs
- More informative verification failure messages
- Enhanced error reporting for troubleshooting
- Cleaner separation between v4.1 specification and v4.0 implementation

### 🏗️ Technical Changes
- Refactored `get_guest_tools_info_with_fallback()` method to handle API version differences
- Updated `verify_ngt_installation()` with proper None value handling
- Improved error handling in API client for better debugging
- Added comprehensive logging for API version detection

## [1.0.0] - 2025-08-25

### ✨ Initial Release
- Automatic VM detection using UUID and hostname methods
- NGT installation with CD-ROM ISO insertion and installation
- Support for Nutanix v4.0 and v4.1 APIs (as per specifications)
- Interactive and command-line authentication modes
- ETag support for proper API operations
- Dry run mode for testing
- Comprehensive logging and error handling

### 🚀 Features
- Auto-detects local VM UUID using multiple methods:
  - `dmidecode` (Linux/Unix)
  - `/sys/hypervisor/uuid` (Linux)
  - WMI (Windows)
  - Machine ID formatting (Linux)
- Supports both Prism Central authentication modes
- Handles CD-ROM requirements automatically
- Monitors installation tasks with proper timeout handling
- Cross-platform compatibility (Linux, Windows, macOS)

### 🏗️ Architecture
- Object-oriented design with separate API client and installer classes
- Comprehensive error handling and logging
- Modular approach for easy maintenance and extension
- Support for different authentication scenarios

---

## Migration Notes

### From v1.0.0 to v2.0.0

**Breaking Changes:**
- NGT verification now works correctly with v4.0-only clusters
- Some debug output format has changed for better clarity

**API Changes:**
- No changes to command-line interface
- All existing scripts and automation will continue to work
- Improved error handling provides more actionable feedback

**Recommended Actions:**
1. Update to v2.0.0 to resolve verification issues
2. Test in your environment to confirm compatibility
3. Update any error handling that relies on specific error messages

### Known Issues Fixed

#### v1.0.0 Issues Resolved in v2.0.0:
- ❌ "404 Client Error: NOT FOUND" during verification → ✅ Fixed with proper API version detection
- ❌ Verification failures on successful NGT installations → ✅ Enhanced verification logic
- ❌ Confusing error messages for API compatibility → ✅ Clear, actionable error reporting
- ❌ Inconsistent handling of uninstalled NGT states → ✅ Proper None value handling

## Compatibility Matrix

| Script Version | Nutanix API | Status | Notes |
|---------------|-------------|--------|--------|
| v2.0.0 | v4.0 | ✅ Fully Supported | Auto-detection, verified compatibility |
| v2.0.0 | v4.1 | ✅ Supported | Auto-detection if available |
| v1.0.0 | v4.0 | ⚠️ Verification Issues | Upgrade recommended |
| v1.0.0 | v4.1 | ✅ Works | If v4.1 actually available |

## Development Notes

### v2.0.0 Development Focus
- **Reliability**: Fixed critical verification failures
- **Compatibility**: Works with real-world Nutanix deployments
- **Usability**: Better error messages and troubleshooting
- **Maintainability**: Cleaner code structure and better separation of concerns

### Future Roadmap
- [ ] Support for additional Nutanix API versions
- [ ] Bulk NGT installation across multiple VMs  
- [ ] Configuration file support
- [ ] NGT upgrade capabilities
- [ ] Enhanced monitoring and reporting features

---

**For detailed technical information about changes, see the git commit history.**
