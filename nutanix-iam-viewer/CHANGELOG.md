# Changelog

All notable changes to the Nutanix Prism Central IAM Manager will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial release of Nutanix Prism Central IAM Manager
- Role management functionality
- User search and analysis
- Authorization policy exploration
- Interactive command-line interface

### Features

#### Role Management
- Browse and examine IAM roles in Prism Central
- Display detailed role permissions and operations
- Distinguish between system-defined and user-defined roles
- View role descriptions and metadata

#### User Search & Analysis
- Smart user search with partial matching
- Search by username or display name
- View comprehensive user information
- Discover all authorization policies that apply to a specific user

#### Authorization Policy Management
- Browse and examine authorization policies
- View policy details including roles, entities, and identities
- See how policies link to roles and their operations
- Understand entity and identity mappings

#### Technical Features
- Full compliance with Nutanix IAM v4.1.b2 API specification
- Proper pagination handling for large datasets
- OData filtering support for efficient searches
- Comprehensive error handling and user feedback
- SSL support with self-signed certificate handling
- Rate limiting awareness (respects 100 records/request limit)

### API Endpoints Supported
- `/iam/v4.1.b2/authz/roles` - Role listing and management
- `/iam/v4.1.b2/authz/roles/{extId}` - Individual role details
- `/iam/v4.1.b2/authz/operations` - Operations and permissions
- `/iam/v4.1.b2/authn/users` - User search and listing
- `/iam/v4.1.b2/authn/users/{extId}` - Individual user details
- `/iam/v4.1.b2/authz/authorization-policies` - Policy listing
- `/iam/v4.1.b2/authz/authorization-policies/{extId}` - Individual policy details

### Security
- Runtime credential prompting (no storage)
- HTTPS-only API communication
- Read-only access to IAM resources
- No persistent sessions or credential storage

## [1.0.0] - 2024-01-22

### Added
- Initial stable release
- Complete IAM management functionality
- Comprehensive documentation
- MIT license
- Contributing guidelines

### Dependencies
- requests >= 2.25.1
- urllib3 >= 1.26.0

### Compatibility
- Python 3.6+
- Nutanix Prism Central with IAM v4.1.b2 API
- Tested on Linux, macOS, and Windows

### Documentation
- Comprehensive README with usage examples
- API endpoint documentation
- Troubleshooting guide
- Security considerations
- Installation instructions

---

## Release Notes Format

### Categories
- **Added** for new features
- **Changed** for changes in existing functionality
- **Deprecated** for soon-to-be removed features
- **Removed** for now removed features
- **Fixed** for any bug fixes
- **Security** for vulnerability fixes

### Version Numbering
- Major version (X.0.0): Breaking changes or major new features
- Minor version (0.X.0): New features, backward compatible
- Patch version (0.0.X): Bug fixes, backward compatible

### Planned Features for Future Releases

#### v1.1.0 (Planned)
- Export functionality (CSV, JSON formats)
- Configuration file support
- Advanced filtering options
- Role comparison utilities

#### v1.2.0 (Planned)
- Batch operations support
- Role creation and modification
- User group analysis
- Enhanced reporting features

#### v2.0.0 (Future)
- Web interface option
- REST API server mode
- Multi-cluster support
- Advanced analytics and dashboards
