# Dazzlesum

[![GitHub Workflow Status](https://github.com/djdarcy/dazzlesum/actions/workflows/python.yml/badge.svg)](https://github.com/djdarcy/dazzlesum/actions)
[![Version](https://img.shields.io/badge/version-1.1.0-blue.svg)](https://github.com/djdarcy/dazzlesum/releases/tag/v1.1.0)
[![Python Version](https://img.shields.io/badge/python-%3E%3D3.7-brightgreen)](https://python.org)
[![License](https://img.shields.io/badge/license-GPL--3.0-blue)](LICENSE)

Dazzlesum is a handy checksum tool designed for data integrity verification across different machines and operating systems. It generates folder-specific checksum files (`.shasum`) that enable verification of file collections, with special attention to DOS shell compatibility and cross-platform consistency.

## Features

- **Multiple Hash Algorithms**: SHA256 (default), SHA512, SHA1, MD5 with consistent cross-platform behavior
- **Cross-Platform Support**: Seamlessly handle checksums between Windows, macOS, Linux, and BSD
- **DOS Compatibility**: ASCII-only output that works perfectly in Windows Command Prompt
- **Native Tool Integration**: Uses system tools (certutil, shasum, fsum) with intelligent Python fallback
- **Flexible Generation Modes**: Individual `.shasum` files per directory, monolithic files, or both simultaneously
- **Advanced Verification**: Problems-only output shows only failed, missing, or extra files by default
- **Management Operations**: Backup, remove, restore, and list `.shasum` files with comprehensive metadata
- **Enhanced Logging**: Multiple verbosity levels with visual directory separation and progress tracking
- **Shadow Directory Support**: Keep source directories clean by storing checksum files in parallel shadow structure

## Use Cases

### 🔧 Data Integrity Verification

Maintain consistent checksum verification across different operating systems. Generate checksums on your Windows machine and verify them on your Linux environment without losing any data integrity checks.

### ⚙️ System Administration

Simplify management of complex directory structures and checksum file collections. Document and reproduce checksum configurations for backup or disaster recovery scenarios.

### 📁 Content Organization

Create organizational structures using checksum verification, then export and share these verification systems with others. Perfect for media libraries (similar to SFVs), project references, or any scenario where data integrity needs to be maintained across multiple locations.

### 🌐 Network Path Management

Automatically handle different representations of network paths across systems while maintaining all checksum metadata and verification capabilities.

## Installation

### Prerequisites

- Python 3.7 or higher
- Operating System: Windows, macOS, Linux, BSD
- Dependencies: None (pure Python standard library)
- Optional: [`unctools` package](https://github.com/djdarcy/UNCtools) for enhanced Windows UNC path support

### Install from PyPI

```bash
pip install dazzlesum
```

### Manual Installation

```bash
git clone https://github.com/djdarcy/dazzlesum.git
cd dazzlesum
pip install -e .
```

On Windows:
```cmd
pip install -e ".[windows]"
```

Other potential dependencies down the line:
```bash
pip install -e ".[dev,test,docs]"
```

## Quick Start

### Generate checksums

```bash
# Generate checksums for current directory
dazzlesum

# Generate checksums recursively
dazzlesum -r

# Create monolithic checksum file
dazzlesum -r --mode monolithic

# Generate with verbose output
dazzlesum -r -vv

# Keep source directories clean with shadow directory
dazzlesum -r --shadow-dir ./checksums

# Generate monolithic checksum in shadow directory
dazzlesum -r --mode monolithic --shadow-dir ./checksums
```

### Verify checksums

```bash
# Verify existing checksums
dazzlesum -r --verify

# Verify with detailed output
dazzlesum -r --verify -v

# Show all verification results
dazzlesum -r --verify --show-all-verifications

# Verify checksums stored in shadow directory
dazzlesum -r --verify --shadow-dir ./checksums
```

### Manage checksum files

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

## Documentation

- **[Installation Guide](docs/installation.md)** - Detailed installation instructions for all platforms
- **[Usage Examples](docs/usage-examples.md)** - Practical examples for common use cases
- **[Shadow Directory Guide](docs/shadow-directory.md)** - Complete guide to shadow directory operations
- **[Command Reference](docs/command-reference.md)** - Complete command-line reference
- **[File Formats](docs/file-formats.md)** - Details about `.shasum` file formats and compatibility

## Platform Support

### Windows
- **Command Prompt**: Full ASCII compatibility
- **PowerShell**: Native support
- **Tools**: Uses `certutil` or `fsum` when available
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

## Requirements

- **Python**: 3.7 or higher
- **Operating System**: Windows, macOS, Linux, BSD
- **Dependencies**: None (pure Python standard library)
- **Optional**: [`unctools` package](https://github.com/djdarcy/UNCtools) for enhanced Windows UNC path support

## Future Possible Features
- **Incremental Updates**: Smart update detection
- **Compression**: Archive support for checksum collections
- **Remote Storage**: Cloud backup integration? (maybe)

## Contributing

Contributions are welcome! Issues, suggestions, and bug reports are all appreciated. Please open an [issue](https://github.com/djdarcy/dazzlesum/issues) if you find something that can be improved. Or: 

1. Fork this repository and clone a fork.
2. Make changes on a new branch (e.g., `feature/new_thing`).
3. Submit a pull request describing your changes.

Please see [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

Like the project?

[!["Buy Me A Coffee"](https://camo.githubusercontent.com/0b448aabee402aaf7b3b256ae471e7dc66bcf174fad7d6bb52b27138b2364e47/68747470733a2f2f7777772e6275796d6561636f666665652e636f6d2f6173736574732f696d672f637573746f6d5f696d616765732f6f72616e67655f696d672e706e67)](https://www.buymeacoffee.com/djdarcy)

## License

This project is licensed under the GPL-3.0 License - see the [LICENSE](LICENSE) file for details.

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history and release notes.

## Support

- **Issues**: [GitHub Issues](https://github.com/djdarcy/dazzlesum/issues)
- **Discussions**: [GitHub Discussions](https://github.com/djdarcy/dazzlesum/discussions)
- **Documentation**: Check the [docs/](docs/) folder for additional guides

---

Made with ❤️ for reliable, consistent data integrity verification across all platforms.
