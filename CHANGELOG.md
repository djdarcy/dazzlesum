# Changelog

All notable changes to dazzlesum will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Comprehensive documentation in `docs/` folder
- VS Code debug configurations in `.vscode/launch.json`
- Proper pip installation support with `setup.py`
- Enhanced GitHub repository structure

### Changed
- License updated from MIT to GPL-3.0
- README.md simplified and restructured for better user experience
- Requirements.txt now references UNCtools GitHub repository directly

## [1.1.0] - 2025-06-27

### Added
- Enhanced logging system with verbosity levels (`-v`, `-vv`, `-vvv`)
- .shasum management operations (backup/remove/restore/list)
- Dual-mode generation (individual/monolithic/both)
- Smart monolithic detection and recursive verification suggestions
- DOS compatibility improvements
- Problems-only verification output (shows only failed, missing, or extra files by default)
- Visual directory separation in output
- Progress tracking for large operations
- Comprehensive statistics for verification operations

### Changed
- Verification now shows only problems by default (use `--show-all-verifications` for full output)
- Improved cross-platform compatibility
- Enhanced error handling and user feedback
- Better integration with native system tools (certutil, shasum, fsum)

### Fixed
- Line ending normalization for consistent checksums across platforms
- Symlink/junction loop detection
- Memory efficiency improvements for large directory trees

## [1.0.0] - Initial Release

### Added
- Cross-platform file checksum generation
- Support for multiple hash algorithms (MD5, SHA1, SHA256, SHA512)
- Individual and monolithic checksum file modes
- Recursive directory processing
- Checksum verification functionality
- Incremental update capability
- File filtering with include/exclude patterns
- Native tool integration with Python fallback
- FIFO directory processing for memory efficiency
- Compatible output format with standard tools

### Features
- Windows, macOS, Linux, and BSD support
- DOS shell compatibility
- UNC path handling (with optional unctools package)
- Symlink and junction detection
- Progress tracking and verbose output options
- Configurable line ending strategies
- Backup and restore functionality for checksum files

---

## Future Planned Features

### Shadow Directory Support
Parallel verification directories for clean source verification without "dirtying" source directories with `.shasum` files.

### Incremental Updates
Smart update detection that only processes changed files while maintaining consistency.

### Compression Support
Archive support for checksum collections to reduce storage overhead.

### Remote Storage Integration
Potential cloud backup integration for checksum files (under consideration).

---

## Migration Notes

### From 1.0.x to 1.1.x
- No breaking changes
- New verbosity options available
- Enhanced verification output (problems-only by default)
- New management operations for `.shasum` files

### License Change Notice
Starting with version 1.1.0, dazzlesum is licensed under GPL-3.0. Previous versions were under MIT license.