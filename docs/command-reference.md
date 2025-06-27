# Command Reference

This document provides a comprehensive reference for all dazzlesum commands and options.

## Core Options

| Option | Description |
|--------|-------------|
| `--algorithm`, `-a` | Hash algorithm: `md5`, `sha1`, `sha256`, `sha512` |
| `--recursive`, `-r` | Process subdirectories recursively |
| `--verify` | Verify existing checksums instead of generating |
| `--update`, `-u` | Update existing checksums (incremental) |

## Generation Modes

| Option | Description |
|--------|-------------|
| `--mode individual` | Individual `.shasum` files per directory (default) |
| `--mode monolithic` | Single checksum file for entire tree |
| `--mode both` | Both individual and monolithic files |
| `--output FILE` | Custom output filename for monolithic mode |
| `--shadow-dir DIR` | Store checksum files in parallel shadow directory |

## Management Operations

| Option | Description |
|--------|-------------|
| `--manage backup` | Backup `.shasum` files to parallel structure |
| `--manage remove` | Remove all `.shasum` files |
| `--manage restore` | Restore `.shasum` files from backup |
| `--manage list` | List all `.shasum` files with metadata |
| `--backup-dir DIR` | Directory for backup/restore operations |
| `--dry-run` | Preview operations without executing |

## Output Control

| Option | Description |
|--------|-------------|
| `-v`, `-vv`, `-vvv` | Increase verbosity level |
| `--quiet`, `-q` | Suppress progress output |
| `--show-all-verifications` | Show all verification results |
| `--summary` | Show progress bar and summary |

## Advanced Options

| Option | Description |
|--------|-------------|
| `--follow-symlinks` | Follow symbolic links and junctions |
| `--compatible` | Generate output compatible with standard tools |
| `--force-python` | Force Python implementation (skip native tools) |
| `--line-endings` | Line ending normalization strategy |
| `-y`, `--yes` | Auto-accept prompts |

## File Filtering

| Option | Description |
|--------|-------------|
| `--include PATTERN` | Include only files matching pattern |
| `--exclude PATTERN` | Exclude files matching pattern |

Pattern examples:
- `"*.txt,*.doc"` - Multiple extensions
- `"temp*"` - Files starting with "temp"
- `"**/cache/**"` - Files in cache directories

## Examples

### Basic Operations
```bash
# Current directory only
dazzlesum

# Recursive processing with SHA512
dazzlesum -r --algorithm sha512

# Verify with detailed output
dazzlesum -r --verify -v

# Update existing checksums
dazzlesum -r --update
```

### Generation Modes
```bash
# Individual .shasum files (default)
dazzlesum -r --mode individual

# Single monolithic file
dazzlesum -r --mode monolithic

# Both individual and monolithic
dazzlesum -r --mode both

# Custom monolithic filename
dazzlesum -r --mode monolithic --output project-checksums.sha256
```

### Shadow Directory Operations
```bash
# Keep source directories clean
dazzlesum -r --shadow-dir ./checksums

# Individual mode with shadow directory
dazzlesum -r --mode individual --shadow-dir ./verification

# Monolithic mode with shadow directory
dazzlesum -r --mode monolithic --shadow-dir ./checksums

# Both modes with shadow directory
dazzlesum -r --mode both --shadow-dir ./checksums

# Verify using shadow directory
dazzlesum -r --verify --shadow-dir ./checksums

# Custom monolithic filename in shadow directory
dazzlesum -r --mode monolithic --output custom.sha256 --shadow-dir ./checksums
```

### File Management
```bash
# Backup all .shasum files
dazzlesum -r --manage backup --backup-dir ./checksum-backup

# List all .shasum files with details
dazzlesum -r --manage list

# Remove all .shasum files (with confirmation)
dazzlesum -r --manage remove

# Restore from backup
dazzlesum -r --manage restore --backup-dir ./checksum-backup
```

### Verification Features
```bash
# Show only problems (default)
dazzlesum -r --verify

# Show all verification results
dazzlesum -r --verify --show-all-verifications

# Verbose verification with all details
dazzlesum -r --verify -vv
```

### File Filtering
```bash
# Include only specific patterns
dazzlesum -r --include "*.txt,*.doc"

# Exclude patterns
dazzlesum -r --exclude "*.tmp,*.log"

# Multiple include patterns
dazzlesum -r --include "*.py" --include "*.md"
```