# Contributing to Nutanix VM Network Category Assigner

Thank you for your interest in contributing! This document provides guidelines for contributing to this project.

## How to Contribute

### Reporting Bugs

If you find a bug, please create an issue on GitHub with:
- Clear description of the problem
- Steps to reproduce
- Expected vs actual behavior
- Your environment (Python version, Prism Central version, OS)
- Relevant error messages or logs

### Suggesting Features

Feature suggestions are welcome! Please create an issue with:
- Clear description of the proposed feature
- Use case and benefits
- Any implementation ideas (optional)

### Code Contributions

1. **Fork the repository**
   ```bash
   git fork https://github.com/yourusername/nutanix-vm-category-assigner.git
   ```

2. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

3. **Make your changes**
   - Follow existing code style
   - Add comments for complex logic
   - Update documentation if needed

4. **Test your changes**
   - Test with a Nutanix Prism Central instance
   - Ensure existing functionality still works
   - Test edge cases

5. **Commit your changes**
   ```bash
   git add .
   git commit -m "feat: add your feature description"
   ```

6. **Push to your fork**
   ```bash
   git push origin feature/your-feature-name
   ```

7. **Create a Pull Request**
   - Provide clear description of changes
   - Reference any related issues
   - Include testing notes

## Code Style

- Follow PEP 8 style guide for Python
- Use descriptive variable and function names
- Add docstrings to functions and classes
- Keep functions focused and modular
- Use type hints where appropriate

## Commit Message Guidelines

Use conventional commits format:

- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation changes
- `refactor:` - Code refactoring
- `test:` - Adding or updating tests
- `chore:` - Maintenance tasks

Examples:
```
feat: add dry-run mode for category assignment
fix: handle connection timeout errors gracefully
docs: update README with troubleshooting section
```

## Testing

Before submitting a PR:

1. Test the main script end-to-end
2. Test with different Prism Central configurations
3. Verify utility scripts still work
4. Check for any breaking changes

## Questions?

Feel free to open an issue for any questions about contributing!

## Code of Conduct

- Be respectful and inclusive
- Focus on constructive feedback
- Help others learn and grow
- Keep discussions professional

Thank you for contributing!
