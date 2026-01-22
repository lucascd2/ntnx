# GitHub Setup Instructions for Nutanix Prism Central IAM Manager

This document provides step-by-step instructions to prepare your project for GitHub and push it to a repository.

## 📋 Prerequisites

- Git installed on your system
- GitHub account created
- Basic familiarity with Git commands

## 📁 Project Structure

Your project should now have the following structure:
```
nutanix-iam-manager/
├── prism_iam_users_policies.py    # Main script
├── swagger-iam-v4.1.b2-all.yaml   # API specification
├── README.md                      # Project documentation
├── requirements.txt               # Python dependencies
├── LICENSE                        # MIT license
├── CONTRIBUTING.md                # Contribution guidelines
├── CHANGELOG.md                   # Version history
├── .gitignore                     # Git ignore rules
└── GITHUB_SETUP_INSTRUCTIONS.md   # This file
```

## 🚀 Step-by-Step GitHub Setup

### Step 1: Initialize Git Repository

```bash
# Navigate to your project directory
cd /home/nutanix/API-Dev

# Initialize git repository
git init

# Add all files to staging
git add .

# Make initial commit
git commit -m "Initial commit: Nutanix Prism Central IAM Manager v1.0.0

- Add comprehensive IAM management tool
- Support for role management and user search  
- Authorization policy exploration
- Interactive CLI interface
- Full API v4.1.b2 compliance"
```

### Step 2: Create GitHub Repository

#### Option A: Using GitHub CLI (gh)
```bash
# Install GitHub CLI if not already installed
# Ubuntu: sudo apt install gh
# macOS: brew install gh

# Authenticate with GitHub
gh auth login

# Create repository
gh repo create nutanix-iam-manager --public --description "Comprehensive Python tool for managing Nutanix Prism Central IAM - roles, users, and authorization policies"

# Add remote origin
git remote add origin https://github.com/yourusername/nutanix-iam-manager.git
```

#### Option B: Using GitHub Web Interface
1. Go to https://github.com
2. Click "New repository" (+ icon in top right)
3. Repository name: `nutanix-iam-manager`
4. Description: `Comprehensive Python tool for managing Nutanix Prism Central IAM - roles, users, and authorization policies`
5. Set as Public (or Private if preferred)
6. **DO NOT** initialize with README, .gitignore, or license (we already have these)
7. Click "Create repository"
8. Add remote origin:
```bash
git remote add origin https://github.com/yourusername/nutanix-iam-manager.git
```

### Step 3: Push to GitHub

```bash
# Push to GitHub
git branch -M main
git push -u origin main
```

### Step 4: Configure Repository Settings

#### Repository Topics (Tags)
Add these topics to help with discoverability:
- `nutanix`
- `prism-central`
- `iam`
- `python`
- `api-client`
- `security`
- `authorization`
- `rbac`

#### Repository Description
```
Comprehensive Python tool for managing Nutanix Prism Central IAM - roles, users, and authorization policies through the v4.1.b2 API
```

#### Website URL (if applicable)
Leave blank or add your documentation site

### Step 5: Set Up GitHub Features

#### Enable Issues
1. Go to Settings > General > Features
2. Ensure "Issues" is checked

#### Create Issue Templates
```bash
mkdir .github
mkdir .github/ISSUE_TEMPLATE

cat > .github/ISSUE_TEMPLATE/bug_report.md << 'EOT'
---
name: Bug report
about: Create a report to help us improve
title: '[BUG] '
labels: bug
assignees: ''
---

**Environment:**
- Nutanix Prism Central version: 
- Python version: 
- Operating System: 

**Describe the bug**
A clear and concise description of what the bug is.

**To Reproduce**
Steps to reproduce the behavior:
1. Run script with '...'
2. Select option '....'
3. Enter '....'
4. See error

**Expected behavior**
A clear and concise description of what you expected to happen.

**Error Output**
```
Paste any error messages or stack traces here
```

**Additional context**
Add any other context about the problem here.
EOT

cat > .github/ISSUE_TEMPLATE/feature_request.md << 'EOT'
---
name: Feature request
about: Suggest an idea for this project
title: '[FEATURE] '
labels: enhancement
assignees: ''
---

**Is your feature request related to a problem? Please describe.**
A clear and concise description of what the problem is. Ex. I'm always frustrated when [...]

**Describe the solution you'd like**
A clear and concise description of what you want to happen.

**Describe alternatives you've considered**
A clear and concise description of any alternative solutions or features you've considered.

**Additional context**
Add any other context or screenshots about the feature request here.

**API Compatibility**
Does this feature require new Nutanix API endpoints?
EOT
```

#### Create Pull Request Template
```bash
cat > .github/PULL_REQUEST_TEMPLATE.md << 'EOT'
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix (non-breaking change that fixes an issue)
- [ ] New feature (non-breaking change that adds functionality)  
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update

## Testing
- [ ] Tested with Nutanix Prism Central
- [ ] Added/updated documentation
- [ ] Follows code style guidelines

## Checklist
- [ ] My code follows the style guidelines of this project
- [ ] I have performed a self-review of my own code
- [ ] I have made corresponding changes to the documentation
- [ ] My changes generate no new warnings

## Additional Notes
Any additional information about the changes
EOT
```

### Step 6: Add GitHub Actions (Optional)

Create basic CI/CD workflow:
```bash
mkdir -p .github/workflows

cat > .github/workflows/python-app.yml << 'EOT'
name: Python Application

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.6, 3.7, 3.8, 3.9, '3.10', '3.11']

    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v3
      with:
        python-version: ${{ matrix.python-version }}
        
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        
    - name: Lint with flake8
      run: |
        pip install flake8
        # stop the build if there are Python syntax errors or undefined names
        flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
        # exit-zero treats all errors as warnings. The GitHub editor is 127 chars wide
        flake8 . --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics
        
    - name: Basic syntax check
      run: |
        python -m py_compile prism_iam_users_policies.py
EOT
```

### Step 7: Final Commit and Push

```bash
# Add GitHub-specific files
git add .github/
git commit -m "Add GitHub templates and workflows

- Add bug report and feature request templates
- Add pull request template  
- Add basic Python CI workflow
- Configure repository for open source collaboration"

git push origin main
```

## 📊 Repository Configuration Checklist

After pushing to GitHub, configure these settings:

### General Settings
- [ ] Repository name: `nutanix-iam-manager`
- [ ] Description added
- [ ] Topics/tags added
- [ ] Default branch: `main`

### Features
- [ ] Issues enabled
- [ ] Wiki enabled (optional)
- [ ] Projects enabled (optional)
- [ ] Discussions enabled (optional)

### Security
- [ ] Dependency graph enabled
- [ ] Dependabot alerts enabled
- [ ] Secret scanning enabled (if available)

### Pages (if documentation site needed)
- [ ] GitHub Pages configured
- [ ] Source: Deploy from branch
- [ ] Branch: main, folder: / (root) or /docs

## 🎯 Post-Setup Recommendations

### README Badges
Add these badges to your README.md:
```markdown
![Python](https://img.shields.io/badge/python-3.6+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Platform](https://img.shields.io/badge/platform-linux%20%7C%20macos%20%7C%20windows-lightgrey.svg)
[![GitHub issues](https://img.shields.io/github/issues/yourusername/nutanix-iam-manager.svg)](https://github.com/yourusername/nutanix-iam-manager/issues)
[![GitHub stars](https://img.shields.io/github/stars/yourusername/nutanix-iam-manager.svg)](https://github.com/yourusername/nutanix-iam-manager/stargazers)
```

### Release Management
1. Create your first release (v1.0.0)
2. Use semantic versioning
3. Include release notes
4. Attach compiled binaries if applicable

### Documentation
1. Consider adding a `docs/` directory for extended documentation
2. Add screenshots to README
3. Create a getting started guide
4. Document API compatibility matrix

## 🔧 Troubleshooting

### Common Issues

**Permission denied (publickey)**
```bash
# Use HTTPS instead of SSH if you haven't set up SSH keys
git remote set-url origin https://github.com/yourusername/nutanix-iam-manager.git
```

**Repository already exists**
```bash
# If you created the repo with README/license, clone first:
git clone https://github.com/yourusername/nutanix-iam-manager.git
cd nutanix-iam-manager
# Copy your files here, then add and commit
```

**Large file issues**
The swagger YAML file might be large. If you get warnings:
```bash
# Check file size
ls -lh swagger-iam-v4.1.b2-all.yaml

# If over 100MB, use Git LFS
git lfs track "*.yaml"
git add .gitattributes
git add swagger-iam-v4.1.b2-all.yaml
git commit -m "Add API specification with Git LFS"
```

## 📚 Next Steps

1. **Star your own repository** to show it's active
2. **Share with the community** - announce on relevant forums
3. **Monitor for issues** and respond promptly
4. **Plan next features** using GitHub Issues and Projects
5. **Set up notifications** for issues and pull requests

## 🎉 Success!

Your Nutanix Prism Central IAM Manager is now ready for the world! The repository includes:

✅ Professional documentation
✅ Proper licensing  
✅ Contribution guidelines
✅ Issue templates
✅ CI/CD workflow
✅ Proper Python packaging
✅ Security best practices

Happy coding! 🚀
