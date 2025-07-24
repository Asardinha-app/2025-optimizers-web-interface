# Repository Synchronization Guide

## Overview

This project maintains two synchronized repositories:

1. **Web Interface Repository**: [https://github.com/Asardinha-app/2025-optimizers-web-interface.git](https://github.com/Asardinha-app/2025-optimizers-web-interface.git)
   - Contains the Streamlit web interface
   - Configuration management system
   - UI/UX components
   - Deployment configurations

2. **Main Optimizers Repository**: [https://github.com/Asardinha-app/2025-Optimizers.git](https://github.com/Asardinha-app/2025-Optimizers.git)
   - Contains all the core optimizer algorithms
   - Sport-specific optimizers (MLB, NFL, NBA, etc.)
   - Data processing utilities
   - Core optimization logic

## Repository Structure

```
2025 Optimizers/
├── web_interface/           # Web interface components
│   ├── frontend/           # Streamlit app
│   ├── config/             # Configuration management
│   └── ...
├── MLB_Optimizer/          # MLB optimizer
├── NFL Optimizer/          # NFL optimizer
├── NBA Optimizer/          # NBA optimizer
├── NHL Optimizer/          # NHL optimizer
├── PGA Optimizer/          # PGA optimizer
├── CFB Optimizer/          # CFB optimizer
├── WNBA Optimizer/         # WNBA optimizer
├── sync_repositories.py    # Synchronization script
└── REPOSITORY_SYNC_GUIDE.md
```

## Git Remotes Setup

The local repository is configured with two remotes:

```bash
# Web Interface Repository (primary)
origin  https://github.com/Asardinha-app/2025-optimizers-web-interface.git

# Main Optimizers Repository (secondary)
optimizers  https://github.com/Asardinha-app/2025-Optimizers.git
```

## Synchronization Workflow

### Automatic Synchronization

The `sync_repositories.py` script provides automated synchronization between repositories:

```bash
# Sync changes to both repositories
python sync_repositories.py sync "Your commit message"

# Check current status
python sync_repositories.py status

# Pull latest changes from optimizers repository
python sync_repositories.py pull

# Setup automation
python sync_repositories.py setup
```

### Manual Workflow

1. **Make Changes**: Edit files in your local repository
2. **Commit Changes**: 
   ```bash
   git add .
   git commit -m "Your commit message"
   ```
3. **Push to Web Interface Repository**:
   ```bash
   git push origin main
   ```
4. **Sync to Optimizers Repository**:
   ```bash
   git push optimizers main
   ```

## Development Workflow

### For Web Interface Changes

1. Make changes to web interface components
2. Test locally: `streamlit run web_interface/frontend/main_enhanced.py`
3. Commit and push:
   ```bash
   git add .
   git commit -m "Web interface: [description]"
   git push origin main
   ```
4. Sync to optimizers repository:
   ```bash
   python sync_repositories.py sync "Web interface: [description]"
   ```

### For Optimizer Changes

1. Make changes to optimizer algorithms
2. Test the specific optimizer
3. Commit and push:
   ```bash
   git add .
   git commit -m "Optimizer: [description]"
   git push optimizers main
   ```
4. Sync to web interface repository:
   ```bash
   git push origin main
   ```

## Best Practices

### Commit Messages

Use descriptive commit messages with prefixes:

- `Web interface: [description]` - For web interface changes
- `Optimizer: [description]` - For optimizer algorithm changes
- `Config: [description]` - For configuration changes
- `Fix: [description]` - For bug fixes
- `Feature: [description]` - For new features

### Branch Strategy

- **main**: Production-ready code
- **develop**: Development branch for new features
- **feature/***: Feature branches for specific development

### Testing Before Sync

Always test changes before synchronizing:

1. **Web Interface**: Test locally with Streamlit
2. **Optimizers**: Run optimizer tests
3. **Integration**: Test web interface with optimizers

## Automation Setup

### Automated Synchronization

The automation script can be set up to run automatically:

```bash
# Setup automation
python sync_repositories.py setup

# This creates automation/auto_sync.py
```

### Cron Job (Optional)

For automatic synchronization, you can set up a cron job:

```bash
# Edit crontab
crontab -e

# Add line for hourly sync (example)
0 * * * * cd /path/to/2025\ Optimizers && python sync_repositories.py sync
```

## Troubleshooting

### Common Issues

1. **Merge Conflicts**: 
   - Resolve conflicts manually
   - Test changes after resolution
   - Commit resolved changes

2. **Push Failures**:
   - Check network connection
   - Verify repository permissions
   - Check for authentication issues

3. **Sync Script Errors**:
   - Check log files in `logs/repo_sync.log`
   - Verify git configuration
   - Ensure all remotes are properly set up

### Recovery Steps

1. **Check Status**:
   ```bash
   python sync_repositories.py status
   git status
   ```

2. **Reset if Needed**:
   ```bash
   git reset --hard HEAD
   git clean -fd
   ```

3. **Re-sync**:
   ```bash
   python sync_repositories.py sync "Recovery sync"
   ```

## Monitoring and Logs

### Log Files

- `logs/repo_sync.log`: Synchronization activity
- `logs/`: General application logs

### Monitoring Commands

```bash
# Check recent sync activity
tail -f logs/repo_sync.log

# Check git status
git status

# Check remote status
git remote -v
```

## Security Considerations

1. **Authentication**: Use SSH keys or personal access tokens
2. **Permissions**: Ensure proper repository access
3. **Backup**: Regular backups of local repository
4. **Validation**: Always test changes before syncing

## Future Enhancements

1. **CI/CD Integration**: Automated testing and deployment
2. **Conflict Resolution**: Automated conflict detection and resolution
3. **Version Management**: Semantic versioning for releases
4. **Backup Strategy**: Automated backup to cloud storage

## Support

For issues with repository synchronization:

1. Check the logs: `logs/repo_sync.log`
2. Verify git configuration: `git config --list`
3. Test connectivity to repositories
4. Review this guide for troubleshooting steps

---

**Last Updated**: [Current Date]
**Version**: 1.0.0 