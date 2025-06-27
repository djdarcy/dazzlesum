# Shadow Directory & Command Structure Redesign

## Problem Analysis

### Core Problem
Currently, dazzle-checksum operates directly on source directories, creating `.shasum` files within them. This "pollutes" source directories with checksum metadata. Users want:

1. **Clean Source Directories**: Generate/verify checksums without littering source directories with `.shasum` files
2. **Parallel Verification**: Use backup directories as shadow structures for verification
3. **Flexible Workflows**: Switch between "dirty" (in-place) and "clean" (shadow) operations seamlessly

### Secondary Problems
1. **Command Clarity**: Current flags (`--verify`, `--update`, implicit create) lack clarity about intent
2. **Smart Defaults**: Tool should infer user intent based on existing files
3. **Integration Complexity**: Shadow directories must work with ALL existing modes and operations

## Conceptual Exploration

### Mental Models

#### Model 1: Shadow as Parallel Universe
Think of shadow directory as a complete parallel filesystem structure:
- **Source**: `/data/projects/myproject/` (clean, no .shasum files)
- **Shadow**: `/checksums/myproject/` (contains all .shasum files in parallel structure)
- **Verification**: Read checksums from shadow, verify files in source
- **Generation**: Write checksums to shadow, never touch source

#### Model 2: Shadow as Workspace
Shadow directory as a working area for checksum operations:
- **Generate**: Create checksums in shadow while reading from source
- **Verify**: Use checksums from shadow to validate source
- **Update**: Modify checksums in shadow based on source changes
- **Clean**: Source directories remain pristine

#### Model 3: Unified Command Model
Restructure all operations around explicit commands:
- **Command Intent**: `--command {create,update,verify,manage}`
- **Location Intent**: `--shadow-dir` for clean operations, omit for dirty operations
- **Smart Defaults**: Infer command based on existing files and context

## Solution Exploration

### Option 1: Minimal Shadow Addition

**Approach**: Add `--shadow-dir` parameter to existing structure
```bash
# Traditional (dirty) operations
dazzle-checksum.py -r                    # Create .shasum in source dirs
dazzle-checksum.py -r --verify           # Verify using source .shasum files

# New shadow (clean) operations  
dazzle-checksum.py -r --shadow-dir ./checksums            # Create .shasum in shadow
dazzle-checksum.py -r --verify --shadow-dir ./checksums   # Verify using shadow .shasum files
```

**Pros**:
- Minimal changes to existing interface
- Backward compatibility preserved
- Clear separation between dirty and clean modes

**Cons**:
- Dual-mode complexity increases
- Every operation needs shadow handling
- Command intent still unclear (verify vs create)

**Implementation Impact**:
- Modify ChecksumGenerator to accept shadow_dir parameter
- Update all path resolution logic
- Modify verification methods to resolve paths between shadow and source

### Option 2: Command-First Redesign

**Approach**: Explicit command structure with shadow support
```bash
# New primary interface
dazzle-checksum.py -r --command create                          # Default: create in source
dazzle-checksum.py -r --command create --shadow-dir ./checksums # Create in shadow
dazzle-checksum.py -r --command verify --shadow-dir ./checksums # Verify from shadow
dazzle-checksum.py -r --command update --shadow-dir ./checksums # Update shadow from source

# Backward compatibility (syntactic sugar)
dazzle-checksum.py -r              # Maps to: --command create
dazzle-checksum.py -r --verify     # Maps to: --command verify  
dazzle-checksum.py -r --update     # Maps to: --command update
```

**Pros**:
- Crystal clear command intent
- Natural shadow directory integration
- Extensible for future commands
- Maintains backward compatibility

**Cons**:
- More complex argument parsing
- Users must learn new interface
- Migration path needed for existing scripts

**Implementation Impact**:
- Major refactor of argument parsing
- Redesign main() function flow
- Update all documentation and help text

### Option 3: Smart Default Behavior

**Approach**: Infer intent based on existing files and context
```bash
# Smart defaults based on context
dazzle-checksum.py -r                           # If .shasum exists: verify, else: create
dazzle-checksum.py -r --shadow-dir ./checksums  # If shadow .shasum exists: verify, else: create
dazzle-checksum.py -r --force-create            # Always create, regardless of existing files
dazzle-checksum.py -r --force-verify            # Always verify, error if no checksums exist
```

**Pros**:
- Minimal user cognitive load
- Intuitive behavior matches user expectations
- Reduces command-line verbosity

**Cons**:
- Behavior can be surprising/unpredictable
- Harder to script reliably
- Complex logic to determine intent

**Implementation Impact**:
- Smart detection logic in main()
- Fallback mechanisms for ambiguous cases
- Extensive testing of edge cases

### Option 4: Hybrid Approach

**Approach**: Combine explicit commands with smart defaults and shadow support
```bash
# Explicit commands (recommended for scripting)
dazzle-checksum.py -r --command create --shadow-dir ./checksums
dazzle-checksum.py -r --command verify --shadow-dir ./checksums

# Smart defaults (recommended for interactive use)
dazzle-checksum.py -r --shadow-dir ./checksums    # Smart: verify if exists, create if not
dazzle-checksum.py -r                              # Smart: verify if exists, create if not

# Management operations (unchanged)
dazzle-checksum.py -r --manage backup --backup-dir ./checksums
```

**Pros**:
- Best of all worlds: explicit when needed, smart when convenient
- Excellent for both scripting and interactive use
- Natural migration path from current interface

**Cons**:
- Most complex implementation
- Largest documentation surface area
- Potential for user confusion about which mode they're in

**Implementation Impact**:
- Complete redesign of command processing
- Smart detection plus explicit override logic
- Comprehensive testing matrix

## Detailed Analysis

### Shadow Directory Implementation Details

#### Path Resolution Logic
```python
def resolve_paths(source_dir: Path, shadow_dir: Path, relative_path: Path):
    """
    source_dir:     /data/projects/myproject/
    shadow_dir:     /checksums/myproject/ 
    relative_path:  subdir/file.txt
    
    Returns:
        source_file: /data/projects/myproject/subdir/file.txt
        shadow_file: /checksums/myproject/subdir/.shasum
    """
```

#### Mode Interactions
1. **Individual Mode + Shadow**:
   - Source: `/data/project/subdir/file.txt`
   - Shadow: `/checksums/project/subdir/.shasum`
   - Read checksums from shadow, verify files in source

2. **Monolithic Mode + Shadow**:
   - Source: `/data/project/` (entire tree)
   - Shadow: `/checksums/project.sha256` (single file)
   - Relative paths in monolithic file resolve to source tree

3. **Both Mode + Shadow**:
   - Generate both individual and monolithic in shadow
   - All verification happens from shadow files

#### Management Operations Integration
```bash
# Create shadow structure from existing source .shasum files
dazzle-checksum.py -r --manage backup --backup-dir ./checksums

# Verify using shadow structure (no source .shasum files needed)
dazzle-checksum.py -r --verify --shadow-dir ./checksums

# Update shadow structure based on source file changes
dazzle-checksum.py -r --update --shadow-dir ./checksums

# Generate new shadow structure (clean slate)
dazzle-checksum.py -r --create --shadow-dir ./checksums
```

### Edge Cases & Considerations

#### 1. Path Resolution Edge Cases
- **Symbolic Links**: How to handle symlinks between source and shadow?
- **Relative vs Absolute**: Should shadow paths be relative or absolute?
- **Cross-Platform**: Windows drive letters vs Unix paths
- **UNC Paths**: Network path handling with unctools integration

#### 2. Concurrency Issues
- **Multiple Processes**: Two processes modifying same shadow directory
- **File Locking**: Platform-specific file locking mechanisms
- **Atomic Operations**: Ensure shadow updates are atomic

#### 3. Error Recovery
- **Partial Shadow**: What if shadow directory is incomplete?
- **Corrupted Checksums**: Recovery from corrupted shadow files
- **Permission Issues**: Handling read-only source or shadow directories

#### 4. Performance Implications
- **Network Paths**: Shadow on network drive, source on local
- **Large Trees**: Memory usage for path mapping large directory trees
- **Caching**: Cache path mappings for better performance

#### 5. Backward Compatibility
- **Existing Scripts**: Must not break existing command lines
- **File Formats**: Maintain compatibility with existing .shasum formats
- **Tool Interop**: Ensure compatibility with standard checksum tools

### Long-term Considerations

#### Extensibility
1. **Remote Shadows**: Shadow directories on cloud storage, network shares
2. **Compression**: Compressed shadow directory formats
3. **Encryption**: Encrypted shadow directories for sensitive data
4. **Versioning**: Version control integration for shadow directories

#### Maintenance
1. **Code Complexity**: Shadow support adds significant complexity
2. **Testing Matrix**: Exponential growth in test scenarios
3. **Documentation**: Much more complex user documentation
4. **Support**: More edge cases for user support

#### Integration Opportunities
1. **Git Integration**: `.gitignore` awareness, git hooks
2. **CI/CD Systems**: Integration with build pipelines
3. **Backup Tools**: Integration with backup/sync solutions
4. **Monitoring**: Health checks for shadow directory consistency

## Recommended Implementation

### Final Design Choice: Hybrid Approach with Staged Rollout

After analyzing all options, I recommend **Option 4: Hybrid Approach** with a carefully planned rollout:

#### Phase 1: Foundation (Immediate)
1. **Add `--shadow-dir` parameter** to existing interface
2. **Implement basic shadow verification** for individual mode
3. **Maintain full backward compatibility**
4. **Extensive testing** with existing workflows

```bash
# Phase 1 capabilities
dazzle-checksum.py -r --verify --shadow-dir ./checksums   # New: shadow verification
dazzle-checksum.py -r --verify                            # Existing: source verification
```

#### Phase 2: Command Structure (Next)
1. **Add `--command {create,verify,update}` parameter**
2. **Implement smart defaults** when command not specified
3. **Maintain backward compatibility** with existing flags
4. **Update documentation** with recommended practices

```bash
# Phase 2 capabilities
dazzle-checksum.py -r --command verify --shadow-dir ./checksums  # Explicit
dazzle-checksum.py -r --shadow-dir ./checksums                   # Smart default
dazzle-checksum.py -r --verify                                   # Backward compatible
```

#### Phase 3: Full Integration (Future)
1. **Extend shadow support** to monolithic and both modes
2. **Integrate with management operations**
3. **Add advanced features** (compression, remote shadows)
4. **Deprecation path** for old syntax (with warnings)

#### Implementation Strategy

**1. Path Resolution Core**
```python
class ShadowPathResolver:
    def __init__(self, source_root: Path, shadow_root: Path):
        self.source_root = source_root
        self.shadow_root = shadow_root
    
    def get_shadow_shasum_path(self, source_dir: Path) -> Path:
        """Get shadow .shasum path for source directory"""
        rel_path = source_dir.relative_to(self.source_root)
        return self.shadow_root / rel_path / SHASUM_FILENAME
    
    def get_source_file_path(self, shadow_relative_path: str) -> Path:
        """Resolve shadow-relative path to source file"""
        return self.source_root / shadow_relative_path
```

**2. Enhanced ChecksumGenerator**
```python
class ChecksumGenerator:
    def __init__(self, ..., shadow_dir=None, command=None):
        self.shadow_resolver = ShadowPathResolver(source_root, shadow_dir) if shadow_dir else None
        self.command = command or self._infer_command()
    
    def _infer_command(self):
        """Smart default: verify if checksums exist, create otherwise"""
        # Implementation of smart logic
```

**3. Argument Processing**
```python
def main():
    # Handle command inference and validation
    if args.command is None:
        args.command = infer_command(args)
    
    # Validate command/parameter combinations
    validate_arguments(args)
    
    # Route to appropriate operation
    if args.command == 'verify':
        handle_verify(args)
    elif args.command == 'create':
        handle_create(args)
    # etc.
```

#### Testing Strategy
1. **Backward Compatibility Tests**: Ensure all existing commands work unchanged
2. **Shadow Operation Tests**: Test all shadow directory scenarios
3. **Cross-Platform Tests**: Windows, Linux, macOS path handling
4. **Performance Tests**: Large directory trees, network paths
5. **Integration Tests**: Interaction with management operations

#### Documentation Strategy
1. **Migration Guide**: Help users transition to new interface
2. **Best Practices**: When to use shadow vs source operations
3. **Troubleshooting**: Common shadow directory issues
4. **Examples**: Real-world workflow examples

### Risk Assessment

#### High Risk
- **Backward Compatibility**: Breaking existing scripts/workflows
- **Complexity**: Shadow path resolution edge cases
- **Performance**: Network path performance degradation

#### Medium Risk  
- **User Confusion**: Too many ways to accomplish same task
- **Maintenance**: Increased code complexity and testing burden
- **Platform Issues**: Cross-platform path handling differences

#### Low Risk
- **Feature Creep**: Temptation to add more shadow features
- **Documentation**: Keeping docs current with features
- **Support**: More complex user support scenarios

## Conclusion

The shadow directory feature represents a significant enhancement that addresses real user needs for clean source directories while maintaining powerful verification capabilities. The hybrid approach provides the best balance of functionality, usability, and maintainability.

The staged rollout approach minimizes risk while delivering immediate value, and the smart default behavior reduces cognitive load for interactive users while maintaining explicit control for scripting scenarios.

Key success factors:
1. **Maintain backward compatibility** throughout rollout
2. **Extensive testing** of path resolution logic
3. **Clear documentation** of migration path
4. **Performance monitoring** with network paths
5. **User feedback integration** during each phase

This design provides a solid foundation for the shadow directory feature while maintaining the tool's core principles of cross-platform compatibility, DOS-shell friendliness, and user-centric design.