# Contributing to Nutanix Prism Central IAM Manager

Thank you for your interest in contributing to this project! This document provides guidelines for contributing to the Nutanix Prism Central IAM Manager.

## Getting Started

### Prerequisites

- Python 3.6 or higher
- Access to a Nutanix Prism Central environment for testing
- Basic understanding of Nutanix IAM concepts
- Familiarity with REST APIs and JSON

### Development Setup

1. Fork the repository
2. Clone your fork:
```bash
git clone https://github.com/yourusername/nutanix-iam-manager.git
cd nutanix-iam-manager
```

3. Create a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

4. Install dependencies:
```bash
pip install -r requirements.txt
```

5. Create a feature branch:
```bash
git checkout -b feature/your-feature-name
```

## Code Style Guidelines

### Python Style
- Follow PEP 8 guidelines
- Use descriptive variable and function names
- Include docstrings for all functions and classes
- Maximum line length: 120 characters
- Use type hints where appropriate

### Example Function Structure
```python
def get_user_policies(self, user_id: str, include_inherited: bool = True) -> list:
    """
    Get all authorization policies for a specific user.
    
    Args:
        user_id: The external ID of the user
        include_inherited: Whether to include policies from group membership
        
    Returns:
        List of authorization policy dictionaries
        
    Raises:
        APIError: If the API request fails
    """
    # Implementation here
    pass
```

### API Integration Guidelines
- Always use pagination for list operations
- Respect API rate limits (max 100 records per request)
- Include proper error handling for all API calls
- Use OData filtering when available
- Follow the existing request/response patterns

## Testing

### Manual Testing
- Test with different Nutanix versions when possible
- Verify functionality with both system and user-defined roles
- Test error conditions (invalid credentials, network issues)
- Test with large datasets (many users, roles, policies)

### Test Scenarios
1. **Role Management**:
   - List roles with pagination
   - View role permissions
   - Handle system vs custom roles
   
2. **User Search**:
   - Search with partial matches
   - Handle users with no policies
   - Test with LDAP/SAML users
   
3. **Authorization Policies**:
   - Complex identity filters
   - Policies with multiple entities
   - System-defined policies

## Submitting Changes

### Pull Request Process

1. **Update Documentation**: Ensure README.md is updated for new features
2. **Test Thoroughly**: Test your changes with real Nutanix environments
3. **Commit Messages**: Use clear, descriptive commit messages
4. **Pull Request Description**: Explain what your changes do and why

### Commit Message Format
```
type(scope): brief description

Longer description if needed.

- List any breaking changes
- Reference issue numbers if applicable
```

Types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`

### Example Pull Request
```markdown
## Description
Add support for filtering roles by client name

## Changes
- Added client name filtering in `list_roles()` method
- Updated UI to show client information
- Added error handling for invalid filters

## Testing
- Tested with Prism Central 2023.4
- Verified filtering works with system and custom roles
- Tested edge cases with special characters

## Documentation
- Updated README.md with new filtering options
- Added docstrings for new parameters
```

## Feature Requests

### New Feature Guidelines

When proposing new features, consider:

1. **API Compatibility**: Ensure the feature uses available Nutanix APIs
2. **User Experience**: Maintain the intuitive command-line interface
3. **Performance**: Consider impact on large environments
4. **Security**: Don't introduce security vulnerabilities

### Popular Feature Ideas
- Export functionality (CSV, JSON)
- Advanced filtering and search
- Batch operations
- Configuration file support
- Role comparison utilities

## Bug Reports

### Before Reporting
1. Check existing issues
2. Test with the latest version
3. Verify your Nutanix environment is supported

### Bug Report Template
```markdown
**Environment:**
- Nutanix Prism Central version: 
- Python version: 
- Operating System: 

**Description:**
Clear description of the bug

**Steps to Reproduce:**
1. Step one
2. Step two
3. Step three

**Expected Behavior:**
What should happen

**Actual Behavior:**
What actually happens

**Error Messages:**
Include any error messages or stack traces

**Additional Context:**
Any other relevant information
```

## Code Review Process

### What We Look For
- **Functionality**: Does the code work as intended?
- **Security**: Are credentials handled safely?
- **Performance**: Is the code efficient for large datasets?
- **Maintainability**: Is the code easy to understand and modify?
- **API Usage**: Does it follow Nutanix API best practices?

### Review Timeline
- Initial response: Within 1-2 days
- Full review: Within 1 week
- Merge: After approval and CI passes

## API Guidelines

### Nutanix API Best Practices
- Use proper HTTP methods (GET, POST, PUT, DELETE)
- Include appropriate headers (Content-Type, Accept)
- Handle pagination correctly
- Implement proper error handling
- Respect rate limits

### Error Handling Pattern
```python
def api_call_example(self):
    try:
        response = self._make_request("GET", "/api/endpoint")
        if not response or 'data' not in response:
            print("Warning: No data received from API")
            return []
        return response['data']
    except requests.exceptions.RequestException as e:
        print(f"API Error: {e}")
        return None
```

## Questions and Support

- **GitHub Issues**: For bug reports and feature requests
- **Discussions**: For questions and general discussion
- **Documentation**: Check the README.md for common issues

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

Thank you for contributing to the Nutanix Prism Central IAM Manager!
