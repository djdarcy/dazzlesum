# Usage Examples

This document provides practical examples for common dazzlesum use cases.

## Basic Workflow

### 1. Generate Checksums
```bash
# Start with current directory
dazzlesum

# Process entire project recursively
dazzlesum -r

# Use SHA512 for extra security
dazzlesum -r --algorithm sha512
```

### 2. Verify Integrity
```bash
# Verify all checksums
dazzlesum -r --verify

# Verbose verification to see what's happening
dazzlesum -r --verify -v

# Show all files, not just problems
dazzlesum -r --verify --show-all-verifications
```

### 3. Update Changed Files
```bash
# Update only changed files
dazzlesum -r --update

# Update with verbose output
dazzlesum -r --update -vv
```

## Integration Examples

### Backup Verification

Before creating a backup:
```bash
# Generate checksums for source data
dazzlesum -r /important/data --mode monolithic --output backup-checksums.sha256
```

After restoring from backup:
```bash
# Verify restored data matches original
dazzlesum -r /restored/data --verify --output backup-checksums.sha256
```

### CI/CD Pipeline

Generate checksums for build artifacts:
```bash
# Generate checksums for release artifacts
dazzlesum -r ./dist --mode monolithic --output release-checksums.sha256
```

Verify deployment:
```bash
# Verify deployed files match build
dazzlesum -r ./deployed --verify --output release-checksums.sha256
```

### Data Migration

On source system:
```bash
# Create backup of checksums
dazzlesum -r /data --manage backup --backup-dir /checksums
```

On target system:
```bash
# Restore checksums and verify
dazzlesum -r /migrated-data --manage restore --backup-dir /checksums
dazzlesum -r /migrated-data --verify -v
```

## File Organization

### Media Library Management
```bash
# Generate checksums for media collection
dazzlesum -r /media/library --include "*.mp4,*.mkv,*.mp3,*.flac"

# Verify after moving files
dazzlesum -r /media/library --verify --include "*.mp4,*.mkv,*.mp3,*.flac"
```

### Project Synchronization
```bash
# Generate checksums excluding temporary files
dazzlesum -r /project --exclude "*.tmp,*.log,node_modules/**,__pycache__/**"

# Verify project integrity after sync
dazzlesum -r /project --verify --exclude "*.tmp,*.log,node_modules/**,__pycache__/**"
```

## Performance Optimization

### Large Directory Trees
```bash
# Use quiet mode for large operations
dazzlesum -r /huge/directory --quiet

# Summary mode for progress tracking
dazzlesum -r /huge/directory --summary
```

### Network Storage
```bash
# Process network shares efficiently
dazzlesum -r "//server/share" --algorithm sha256

# Backup checksums before network operations
dazzlesum -r "//server/share" --manage backup --backup-dir ./network-checksums
```

## Troubleshooting

### Debug Mode
```bash
# Maximum verbosity for debugging
dazzlesum -r --verify -vvv

# Force Python implementation if native tools fail
dazzlesum -r --force-python
```

### Permission Issues
```bash
# Skip files with permission issues
dazzlesum -r --continue-on-error

# Dry run to see what would be processed
dazzlesum -r --manage remove --dry-run
```

## Cross-Platform Usage

### Windows Command Prompt
```cmd
REM Basic usage in Windows
dazzlesum.py -r C:\MyData

REM Verify with UNC paths
dazzlesum.py -r \\server\share --verify
```

### PowerShell
```powershell
# Use with PowerShell
python dazzlesum.py -r C:\Projects --mode both

# Backup to different drive
python dazzlesum.py -r C:\Data --manage backup --backup-dir D:\Checksums
```

### Unix/Linux
```bash
# Standard Unix usage
./dazzlesum.py -r ~/documents

# System-wide verification
sudo dazzlesum -r /etc --verify --exclude "*.tmp"
```

## Automation Scripts

### Batch Verification Script
```bash
#!/bin/bash
# verify-backups.sh

BACKUP_DIRS=("/backup/daily" "/backup/weekly" "/backup/monthly")

for dir in "${BACKUP_DIRS[@]}"; do
    echo "Verifying $dir..."
    if dazzlesum -r "$dir" --verify --quiet; then
        echo "✓ $dir verification passed"
    else
        echo "✗ $dir verification failed"
        exit 1
    fi
done
```

### Windows Batch File
```bat
@echo off
REM backup-with-checksums.bat

echo Generating checksums...
python dazzlesum.py -r C:\ImportantData --mode monolithic --output checksums.sha256

echo Copying files...
robocopy C:\ImportantData D:\Backup\Data /E /COPY:DAT

echo Verifying backup...
python dazzlesum.py -r D:\Backup\Data --verify --output checksums.sha256

echo Backup and verification complete.
```