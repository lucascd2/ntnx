# Nutanix Prism Central IAM Manager

A comprehensive Python tool for viewing Identity and Access Management (IAM) in Nutanix Prism Central. This interactive script allows you to explore roles, search users, and analyze authorization policies through the Nutanix IAM v4.1.b2 API.

## Features

### 🔐 Role Management
- **View IAM Roles**: Browse and examine all roles in your Prism Central
- **Role Permissions**: Display detailed permissions and operations for each role
- **System vs Custom**: Distinguish between system-defined and user-defined roles

### 👥 User Search & Analysis
- **Smart User Search**: Find users by username or display name with partial matching
- **User Details**: View comprehensive user information
- **Authorization Policy Discovery**: Find all policies that apply to a specific user

### 📋 Authorization Policy Management
- **Policy Exploration**: Browse and examine authorization policies
- **Role Integration**: See how policies link to roles and their operations
- **Entity & Identity Mapping**: Understand what entities policies cover and which users they apply to

## Prerequisites

- Python 3.6 or higher
- Network access to Nutanix Prism Central
- Valid Prism Central credentials with appropriate IAM permissions

Install required Python packages:
```bash
pip install -r requirements.txt
```

## Usage

### Basic Usage

Run the script with:
```bash
python3 prism_iam_users_policies.py
```

The script will prompt you for:
- Prism Central IP address
- Username
- Password (hidden input)

### Main Menu Options

```
============================================================
Nutanix Prism Central IAM Manager
============================================================

Options:
• Enter a number (1-X) to view role permissions
• Enter 'u' to search users and view their authorization policies
• Enter 'r' to refresh the role list
• Enter 'q' to quit
```

### User Search Workflow

1. **Enter 'u'** from the main menu
2. **Search**: Enter username (supports partial matches)
   - Example: "john" finds "john.doe", "johnsmith", "John Admin"
3. **Select User**: Choose from the list of found users
4. **View Policies**: See all authorization policies assigned to that user
5. **Examine Details**: Select specific policies for detailed information

### Example Session

```bash
$ python3 prism_iam_users_policies.py

Nutanix Prism Central IAM Manager
=============================================
Enter Prism Central IP address: 10.1.1.100
Enter username: admin
Enter password: [hidden]

============================================================
Nutanix Prism Central IAM Manager
============================================================

Fetching IAM roles...

#    Role Name                               Description                                       System  
--------------------------------------------------------------------------------------------------
1    Cluster Admin                          Full cluster administration access                Yes     
2    Cluster Viewer                         Read-only cluster access                         Yes     
3    Custom Security Admin                  Custom role for security team                    No      

Options:
• Enter a number (1-3) to view role permissions
• Enter 'u' to search users and view their authorization policies
• Enter 'r' to refresh the role list
• Enter 'q' to quit

Your choice: u

============================================================
User Authorization Policy Search
============================================================
Enter username to search for: john

Searching for users matching 'john'...
Found 2 user(s):

#    Username                  Display Name                   Type            Status    
------------------------------------------------------------------------------------
1    john.doe                 John Doe                       LOCAL           Active    
2    john.admin               John Smith (Admin)             LDAP            Active    

Select user (1-2): 1

Analyzing authorization policies for: john.doe

Searching for authorization policies for user: john.doe
Checking page 1 (50 policies)...
Checking page 2 (23 policies)...

Found 3 authorization policies for user: john.doe

#    Policy Name                             Type                 Users    System  
--------------------------------------------------------------------------------
1    Development Team Access                USER_DEFINED         12       No      
2    VM Management Policy                   USER_DEFINED         8        No      
3    Backup Operations                      SERVICE_DEFINED      25       Yes     

Options:
• Enter a number (1-3) to view policy details
• Enter 'q' to return to main menu

Your choice: 1

Policy: Development Team Access
Description: Provides development team with necessary VM and network access
Type: USER_DEFINED
System Defined: No
External ID: a1b2c3d4-e5f6-7890-abcd-ef1234567890
Assigned Users: 12
Assigned User Groups: 3

Assigned Role:
  Role Name: VM Power User
  Operations: 45 permissions

Entities (2):
  • Entity 1: {'entityType': 'vm', 'filterCriteria': {'categories': ['Environment:Development']}}
  • Entity 2: {'entityType': 'network', 'filterCriteria': {'names': ['Dev-Network-*']}}

Identities (1):
  • Identity 1: {'userGroup': {'name': 'Development-Team'}}

Press Enter to continue...
```

## API Endpoints Used

The script interacts with the following Nutanix IAM v4.1.b2 API endpoints:

| Feature | Endpoint | Description |
|---------|----------|-------------|
| Role Management | `/iam/v4.1.b2/authz/roles` | List and retrieve role information |
| Role Details | `/iam/v4.1.b2/authz/roles/{extId}` | Get detailed role information |
| Operations | `/iam/v4.1.b2/authz/operations` | List available operations/permissions |
| User Search | `/iam/v4.1.b2/authn/users` | Search and list users |
| User Details | `/iam/v4.1.b2/authn/users/{extId}` | Get detailed user information |
| Policy List | `/iam/v4.1.b2/authz/authorization-policies` | List authorization policies |
| Policy Details | `/iam/v4.1.b2/authz/authorization-policies/{extId}` | Get detailed policy information |

## Configuration

### SSL Certificate Verification

By default, SSL certificate verification is disabled to work with self-signed certificates common in Nutanix environments. To enable SSL verification, modify the `verify_ssl` parameter in the `PrismCentralIAM` class initialization.

### API Limits

The script respects Nutanix API limitations:
- Maximum 100 records per request
- Automatic pagination for large datasets
- Proper error handling for rate limits

## Troubleshooting

### Common Issues

1. **Connection Error**: Verify Prism Central IP and network connectivity
2. **Authentication Failed**: Check username and password
3. **Permission Denied**: Ensure user has IAM read permissions
4. **SSL Certificate Error**: SSL verification is disabled by default, but check certificate configuration if needed

### Debug Mode

For debugging API issues, you can modify the `_make_request` method to print request/response details.

### Logs

The script provides real-time feedback for:
- API request progress
- Search results
- Error conditions
- Data loading status

## Security Considerations

- **Credentials**: Script prompts for credentials at runtime (no storage)
- **SSL**: Uses HTTPS for all API communications
- **Permissions**: Requires only read permissions for IAM resources
- **Session**: No persistent sessions or credential storage

## Limitations

- **Read-Only**: Script provides read-only access to IAM resources
- **Identity Filters**: Complex identity filter matching is simplified
- **Large Datasets**: Performance may be impacted with thousands of users/policies
- **API Version**: Designed for Nutanix IAM v4.1.b2

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## API Specification

This tool is based on the Nutanix IAM v4.1.b2 API specification. The OpenAPI specification file (`swagger-iam-v4.1.b2-all.yaml`) is included for reference.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

For issues and questions:
- Create an issue in this repository
- Check the troubleshooting section
- Verify API compatibility with your Nutanix version

## Acknowledgments

- Built for Nutanix Prism Central IAM v4.1.b2
- Follows Nutanix API best practices
- Designed for security and compliance use cases
