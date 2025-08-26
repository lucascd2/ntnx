# Contributing to NGT Auto Installation Script

Thank you for your interest in contributing to the NGT Auto Installation Script! This document provides guidelines for contributing to the project.

## 🎯 How to Contribute

We welcome contributions in many forms:
- 🐛 Bug reports and fixes
- ✨ New features and enhancements
- 📚 Documentation improvements
- 🧪 Tests and test improvements
- 💡 Ideas and suggestions

## 🚀 Getting Started

### Prerequisites
- Python 3.8 or higher
- Access to a Nutanix environment for testing
- Basic understanding of Nutanix APIs and NGT

### Development Setup

1. **Fork and clone the repository:**
   ```bash
   git clone https://github.com/your-username/ngt-auto-install.git
   cd ngt-auto-install
   ```

2. **Create a virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Create a feature branch:**
   ```bash
   git checkout -b feature/your-feature-name
   ```

## 📋 Development Guidelines

### Code Style

- **PEP 8**: Follow Python PEP 8 style guidelines
- **Type Hints**: Use type hints for function parameters and return values
- **Docstrings**: Include docstrings for all functions and classes
- **Comments**: Add meaningful comments for complex logic

**Example:**
```python
def find_vm_by_uuid(self, vm_uuid: str) -> Optional[Dict]:
    """Find a VM by UUID using the VMM API.
    
    Args:
        vm_uuid: The UUID of the VM to find
        
    Returns:
        VM data dictionary if found, None otherwise
        
    Raises:
        Exception: If API request fails
    """
    logger.info(f"Searching for VM with UUID: {vm_uuid}")
    # Implementation...
```

### Error Handling

- **Comprehensive Error Handling**: Always handle potential exceptions
- **Informative Messages**: Provide clear, actionable error messages
- **Logging**: Use appropriate logging levels (DEBUG, INFO, WARNING, ERROR)

**Example:**
```python
try:
    response = self.api.get(f'vmm/v4.0/ahv/config/vms/{vm_uuid}')
    return response.json()
except requests.exceptions.RequestException as e:
    logger.error(f"API request failed: {e}")
    raise
except json.JSONDecodeError as e:
    logger.error(f"Invalid JSON response: {e}")
    return None
```

### Testing

- **Test Environment**: Test in a safe Nutanix environment
- **Multiple Scenarios**: Test various VM states and configurations
- **Error Conditions**: Test error handling and edge cases
- **API Versions**: Test with different Nutanix API versions

## 🐛 Reporting Bugs

When reporting bugs, please include:

### Bug Report Template
```markdown
**Description**
A clear description of the bug.

**Environment**
- Python version: 3.x
- Nutanix API version: v4.x
- Operating system: 
- NGT script version:

**Steps to Reproduce**
1. Run command: `./ngt_auto_install.py ...`
2. Observe error: ...

**Expected Behavior**
What you expected to happen.

**Actual Behavior**
What actually happened.

**Logs**
Include relevant log output (use --debug flag).

**Additional Context**
Any other relevant information.
```

## ✨ Feature Requests

For new features, please:

1. **Check existing issues** to avoid duplicates
2. **Describe the use case** - why is this feature needed?
3. **Propose the solution** - how should it work?
4. **Consider alternatives** - are there other approaches?

### Feature Request Template
```markdown
**Feature Description**
A clear description of the desired feature.

**Use Case**
Why is this feature needed? What problem does it solve?

**Proposed Solution**
How should the feature work?

**Alternatives Considered**
What other approaches were considered?

**Implementation Notes**
Any technical considerations or constraints.
```

## 🔀 Pull Request Process

### Before Submitting

1. **Test thoroughly** in your development environment
2. **Update documentation** if needed
3. **Check code style** and add type hints
4. **Add/update tests** for new functionality
5. **Update CHANGELOG.md** with your changes

### Pull Request Template
```markdown
**Description**
Brief description of the changes.

**Type of Change**
- [ ] Bug fix
- [ ] New feature
- [ ] Documentation update
- [ ] Refactoring
- [ ] Performance improvement

**Testing**
- [ ] Tested in development environment
- [ ] Tested with multiple VM configurations
- [ ] Tested error handling
- [ ] Added/updated tests

**Checklist**
- [ ] Code follows project style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] CHANGELOG.md updated
```

### Review Process

1. **Automated Checks**: Ensure all checks pass
2. **Code Review**: Address reviewer feedback
3. **Testing**: Verify functionality works as expected
4. **Approval**: Get approval from maintainers
5. **Merge**: Maintainers will merge approved PRs

## 📚 Documentation Guidelines

### Code Documentation

- **Docstrings**: Use Google-style docstrings
- **Type Hints**: Always include parameter and return types
- **Examples**: Include usage examples where helpful

### README Updates

- **New Features**: Add usage examples for new features
- **Configuration**: Document new configuration options
- **Troubleshooting**: Add common issues and solutions

### Changelog

Update `CHANGELOG.md` following [Keep a Changelog](https://keepachangelog.com/) format:

```markdown
## [Unreleased]

### Added
- New feature description

### Fixed
- Bug fix description

### Changed
- Modification description
```

## 🧪 Testing Guidelines

### Manual Testing Checklist

- [ ] **API Connectivity**: Test connection to Nutanix cluster
- [ ] **VM Detection**: Test UUID and hostname detection
- [ ] **NGT Installation**: Test complete installation process
- [ ] **Verification**: Test NGT status verification
- [ ] **Error Handling**: Test various error conditions
- [ ] **API Versions**: Test v4.0 and v4.1 compatibility

### Test Environments

- **Development**: Use non-production Nutanix environment
- **VM Types**: Test with different guest OS types
- **Network**: Test from different network locations
- **Credentials**: Test with different user permissions

## 🏗️ Architecture Guidelines

### Code Organization

```
ngt_auto_install.py
├── NutanixAPIClient    # API communication
├── NGTInstaller        # NGT installation logic
├── Utility functions   # Helper functions
└── Main function       # Command-line interface
```

### Key Principles

- **Separation of Concerns**: Keep API client separate from business logic
- **Error Handling**: Handle errors at appropriate levels
- **Logging**: Provide comprehensive logging for debugging
- **Configuration**: Make behavior configurable where appropriate

## 🔐 Security Considerations

### Credential Handling
- Never log passwords or sensitive information
- Use secure input methods for passwords
- Recommend environment variables over command-line arguments

### API Security
- Support SSL verification in production environments
- Use proper authentication methods
- Implement request timeouts and retries

## 📊 Performance Guidelines

### API Efficiency
- Minimize API calls where possible
- Use appropriate timeouts
- Implement proper retry logic

### Resource Usage
- Handle large responses efficiently
- Clean up resources properly
- Avoid memory leaks in long-running operations

## 🚦 Release Process

### Version Numbering
- Follow [Semantic Versioning](https://semver.org/)
- **MAJOR**: Breaking changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes

### Release Checklist
- [ ] Update version in script
- [ ] Update CHANGELOG.md
- [ ] Tag release in Git
- [ ] Create GitHub release
- [ ] Update documentation

## 🤝 Community

### Communication
- **Issues**: Use GitHub issues for bug reports and feature requests
- **Discussions**: Use GitHub discussions for questions and ideas
- **Code Review**: Participate in pull request reviews

### Code of Conduct
- Be respectful and inclusive
- Focus on constructive feedback
- Help others learn and contribute
- Follow the project's code of conduct

## 📝 License

By contributing to this project, you agree that your contributions will be licensed under the same MIT License that covers the project.

## 🆘 Getting Help

- **Documentation**: Check README.md and examples/
- **Issues**: Search existing issues
- **Questions**: Use GitHub discussions
- **Contact**: Create an issue with the "question" label

---

Thank you for contributing to the NGT Auto Installation Script! Your contributions help make Nutanix environments more manageable for everyone.
