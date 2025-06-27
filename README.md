# Dazzlesum

A cross-platform file checksum utility with DOS compatibility and advanced verification features.

[![Python](https://img.shields.io/badge/python-3.7+-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)]()

## Overview

Dazzlesum is a handy checksum tool designed for data integrity verification across different machines and operating systems. It generates folder-specific checksum files (`.shasum`) that enable verification of file collections, with special attention to DOS shell compatibility and cross-platform consistency.

## Key Features

### **Core Functionality**
- **Multiple Hash Algorithms**: SHA256 (default), SHA512, SHA1, MD5
- **Cross-Platform**: Windows, macOS, Linux, BSD with consistent behavior
- **DOS Compatible**: ASCII-only output, works in Windows Command Prompt
- **Native Tool Integration**: Uses system tools (certutil, shasum, fsum) with Python fallback

### **Flexible Generation Modes**
- **Individual Mode**: One `.shasum` file per directory (default)
- **Monolithic Mode**: Single checksum file for entire directory tree
- **Both Mode**: Generate both individual and monolithic files simultaneously

### **Advanced Verification**
- **Problems-Only Output**: Shows only failed, missing, or extra files by default
- **Comprehensive Statistics**: Detailed verification summaries
- **Smart Monolithic Detection**: Auto-detects monolithic files and suggests recursive verification

### **Management Operations**
- **Backup**: Create parallel directory structure for `.shasum` files
- **Remove**: Safely remove `.shasum` files with confirmation
- **Restore**: Restore `.shasum` files from backup
- **List**: Display all `.shasum` files with metadata

### **Enhanced Logging**
- **Verbosity Levels**: `-v` (standard), `-vv` (detailed), `-vvv` (debug)
- **Directory Separation**: Visual separation between directory processing
- **Progress Tracking**: Clear progress indication for large operations

## Quick Start

### Installation

Dazzlesum is a single Python file with no required dependencies:

```bash
# Download the script
curl -O https://raw.githubusercontent.com/djdarcy/dazzlesum/main/dazzlesum.py

# Make executable (Unix/Linux/macOS)
chmod +x dazzlesum.py

# Run directly
python dazzlesum.py --help
```

### Basic Usage

```bash
# Generate checksums for current directory
python dazzlesum.py

# Generate checksums recursively
python dazzlesum.py -r

# Verify existing checksums
python dazzlesum.py -r --verify

# Generate with verbose output
python dazzlesum.py -r -vv

# Create monolithic checksum file
python dazzlesum.py -r --mode monolithic
```

## Usage Examples

### Basic Operations

```bash
# Current directory only
python dazzlesum.py

# Recursive processing with SHA512
python dazzlesum.py -r --algorithm sha512

# Verify with detailed output
python dazzlesum.py -r --verify -v

# Update existing checksums
python dazzlesum.py -r --update
```

### Generation Modes

```bash
# Individual .shasum files (default)
python dazzlesum.py -r --mode individual

# Single monolithic file
python dazzlesum.py -r --mode monolithic

# Both individual and monolithic
python dazzlesum.py -r --mode both

# Custom monolithic filename
python dazzlesum.py -r --mode monolithic --output project-checksums.sha256
```

### File Management

```bash
# Backup all .shasum files
python dazzlesum.py -r --manage backup --backup-dir ./checksum-backup

# List all .shasum files with details
python dazzlesum.py -r --manage list

# Remove all .shasum files (with confirmation)
python dazzlesum.py -r --manage remove

# Restore from backup
python dazzlesum.py -r --manage restore --backup-dir ./checksum-backup
```

### Verification Features

```bash
# Show only problems (default)
python dazzlesum.py -r --verify

# Show all verification results
python dazzlesum.py -r --verify --show-all-verifications

# Verbose verification with all details
python dazzlesum.py -r --verify -vv
```

### File Filtering

```bash
# Include only specific patterns
python dazzlesum.py -r --include "*.txt,*.doc"

# Exclude patterns
python dazzlesum.py -r --exclude "*.tmp,*.log"

# Multiple include patterns
python dazzlesum.py -r --include "*.py" --include "*.md"
```

## Command Reference

### Core Options

| Option | Description |
|--------|-------------|
| `--algorithm`, `-a` | Hash algorithm: `md5`, `sha1`, `sha256`, `sha512` |
| `--recursive`, `-r` | Process subdirectories recursively |
| `--verify` | Verify existing checksums instead of generating |
| `--update`, `-u` | Update existing checksums (incremental) |

### Generation Modes

| Option | Description |
|--------|-------------|
| `--mode individual` | Individual `.shasum` files per directory (default) |
| `--mode monolithic` | Single checksum file for entire tree |
| `--mode both` | Both individual and monolithic files |
| `--output FILE` | Custom output filename for monolithic mode |

### Management Operations

| Option | Description |
|--------|-------------|
| `--manage backup` | Backup `.shasum` files to parallel structure |
| `--manage remove` | Remove all `.shasum` files |
| `--manage restore` | Restore `.shasum` files from backup |
| `--manage list` | List all `.shasum` files with metadata |
| `--backup-dir DIR` | Directory for backup/restore operations |
| `--dry-run` | Preview operations without executing |

### Output Control

| Option | Description |
|--------|-------------|
| `-v`, `-vv`, `-vvv` | Increase verbosity level |
| `--quiet`, `-q` | Suppress progress output |
| `--show-all-verifications` | Show all verification results |
| `--summary` | Show progress bar and summary |

### Advanced Options

| Option | Description |
|--------|-------------|
| `--follow-symlinks` | Follow symbolic links and junctions |
| `--compatible` | Generate output compatible with standard tools |
| `--force-python` | Force Python implementation (skip native tools) |
| `--line-endings` | Line ending normalization strategy |
| `-y`, `--yes` | Auto-accept prompts |

## File Formats

### Individual .shasum Format

```
# Dazzle checksum tool v1.1.0 - sha256 - 2025-06-27T09:00:00Z
abc123def456...  file1.txt
789012fed345...  file2.doc
# End of checksums
```

### Monolithic Format

```
# Dazzle monolithic checksum file v1.1.0 - sha256 - 2025-06-27T09:00:00Z
# Root directory: /path/to/project
abc123def456...  folder1/file1.txt
789012fed345...  folder1/file2.doc
fed456abc789...  folder2/subfolder/file3.py
# End of checksums
```

## Platform Support

### Windows
- **Command Prompt**: Full ASCII compatibility
- **PowerShell**: Native support
- **Tools**: Uses `certutil` when available
- **Paths**: Handles UNC paths with optional [`unctools` package](https://github.com/djdarcy/UNCtools)

### macOS/Linux
- **Terminal**: Full compatibility
- **Tools**: Uses `shasum` when available
- **Paths**: Native Unix path handling
- **Performance**: Optimized for large file trees

### Cross-Platform Features
- **Path Normalization**: Automatic path separator handling
- **Line Ending Support**: Configurable line ending strategies
- **Symlink Safety**: Intelligent symlink and junction detection
- **Encoding**: UTF-8 with fallback handling

## Memory Efficiency

Dazzlesum is designed for efficient processing of large directory trees:

- **FIFO Processing**: Processes directories in order without loading entire tree
- **Streaming I/O**: Large files processed in chunks
- **Memory Management**: Minimal memory footprint even with thousands of files
- **Progress Tracking**: Real-time progress for long operations

## Integration Examples

### Backup Verification

```bash
# Before backup
python dazzlesum.py -r /important/data --mode monolithic --output backup-checksums.sha256

# After restore
python dazzlesum.py -r /restored/data --verify --output backup-checksums.sha256
```

### CI/CD Pipeline

```bash
# Generate checksums for artifacts
python dazzlesum.py -r ./dist --mode monolithic --output release-checksums.sha256

# Verify deployment
python dazzlesum.py -r ./deployed --verify --output release-checksums.sha256
```

### Data Migration

```bash
# Source system
python dazzlesum.py -r /data --manage backup --backup-dir /checksums

# Target system
python dazzlesum.py -r /migrated-data --manage restore --backup-dir /checksums
python dazzlesum.py -r /migrated-data --verify -v
```

## Requirements

- **Python**: 3.7 or higher
- **Operating System**: Windows, macOS, Linux, BSD
- **Dependencies**: None (pure Python standard library)
- **Optional**: [`unctools` package](https://github.com/djdarcy/UNCtools) for enhanced Windows UNC path support

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Development Areas
- Shadow directory feature implementation
- Performance optimizations
- Additional hash algorithms
- Platform-specific integrations
- Documentation and examples

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Changelog

### v1.1.0 (Current)
- Enhanced logging system with verbosity levels
- .shasum management operations (backup/remove/restore/list)
- Dual-mode generation (individual/monolithic/both)
- Verification improvements (problems-only default)
- Smart monolithic detection
- DOS compatibility improvements

### Future Features (Planned)
- **Shadow Directory Support**: Parallel verification directories
- **Incremental Updates**: Smart update detection
- **Compression**: Archive support for checksum collections
- **Remote Storage**: Cloud backup integration? (maybe)

## Support

- **Issues**: [GitHub Issues](https://github.com/djdarcy/dazzlesum/issues)
- **Discussions**: [GitHub Discussions](https://github.com/djdarcy/dazzlesum/discussions)
- **Documentation**: Check the [docs/](docs/) folder for additional guides

---

Made with ❤️ for reliable data integrity verification across all platforms.