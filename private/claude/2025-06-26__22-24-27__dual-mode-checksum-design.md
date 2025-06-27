# Dual-Mode Checksum Generation Design

## 1. Problem Analysis

### Core Problem
Users may want BOTH individual `.shasum` files per directory AND a monolithic checksum file for the entire tree. Currently, it's an either/or choice with `--monolithic` flag.

### Use Cases
1. **Backup Verification**: Monolithic file for quick overall integrity check
2. **Local Operations**: Individual .shasum files for per-directory verification
3. **Hybrid Workflows**: Both for redundancy and flexibility
4. **Migration Scenarios**: Transitioning between modes without losing existing files

### Sub-problems
- **Mode Selection**: How to express "both", "monolithic only", or "individual only"
- **Performance**: Writing both means double the I/O operations
- **Consistency**: Ensuring both outputs contain identical checksums
- **File Management**: Handling conflicts between modes
- **User Experience**: Clear and intuitive command-line interface

### Current Behavior Analysis
```bash
# Current: Either/or
dazzle-checksum.py --recursive            # Individual .shasum files only
dazzle-checksum.py --recursive --monolithic  # Monolithic file only

# Missing: Both at once
dazzle-checksum.py --recursive --monolithic --also-individual?  # Awkward
```

## 2. Conceptual Exploration

### Mental Models

#### Model 1: Mode Selection
Think of it as output modes like a compiler:
- `--output-mode individual` (default)
- `--output-mode monolithic`
- `--output-mode both`

#### Model 2: Additive Flags
Build up what you want:
- Default: individual files
- `--monolithic`: ONLY monolithic
- `--also-monolithic`: BOTH (keeps individual)
- `--no-individual`: Only monolithic (alternative syntax)

#### Model 3: Explicit Boolean Flags
Be explicit about each output type:
- `--individual` (default true)
- `--monolithic` (default false)
- `--no-individual --monolithic` (monolithic only)

### Design Patterns
- **Strategy Pattern**: Different output strategies selected at runtime
- **Composite Pattern**: Multiple writers working in parallel
- **Builder Pattern**: Constructing output configuration

## 3. Solution Exploration

### Option 1: Mode-Based Approach
```bash
--output-mode {individual,monolithic,both}
```

**Pros:**
- Clear, explicit selection
- Extensible for future modes
- Self-documenting

**Cons:**
- Breaking change (current --monolithic would need migration)
- Longer command lines
- Not backward compatible

**Edge Cases:**
- What if user specifies both --monolithic and --output-mode?
- Migration path for existing scripts

### Option 2: Additive Flag Approach
```bash
--also-individual  # When used with --monolithic
--also-monolithic  # When generating individual files
```

**Pros:**
- Backward compatible
- Intuitive naming
- Gradual adoption possible

**Cons:**
- Two flags for same feature feels redundant
- Confusing which flag to use when

**Edge Cases:**
- Using both flags together
- Interaction with --output flag

### Option 3: Keep --monolithic, Add --dual-mode
```bash
--monolithic       # Monolithic only (current behavior)
--dual-mode        # Both monolithic and individual
```

**Pros:**
- Backward compatible
- Simple addition
- Clear intent

**Cons:**
- Not extensible for future modes
- --monolithic --dual-mode is contradictory

**Edge Cases:**
- User specifies both flags
- Verification with dual mode files

### Option 4: Enhanced --monolithic Behavior
```bash
--monolithic             # Changed to mean "also monolithic" (both)
--monolithic-only        # New flag for exclusive monolithic
```

**Pros:**
- Most common case (both) is simplest
- Backward compatible for verification
- Natural progression

**Cons:**
- Breaking change for generation
- Surprising behavior change

### Option 5: Configuration-Based
```bash
--checksum-outputs individual,monolithic
--checksum-outputs both  # Shorthand
```

**Pros:**
- Extremely flexible
- Clear configuration
- Future-proof

**Cons:**
- Verbose
- Requires parsing
- Over-engineered for current needs

## 4. Synthesis and Recommendation

### Recommended Solution: Hybrid of Options 2 & 3

Implement a clear, backward-compatible approach:

```bash
# Current behavior (unchanged)
dazzle-checksum.py --recursive              # Individual .shasum files
dazzle-checksum.py --recursive --monolithic # Monolithic only

# New behavior
dazzle-checksum.py --recursive --monolithic --keep-individual  # Both
# OR
dazzle-checksum.py --recursive --both-modes # Clear shorthand for both
```

### Implementation Strategy

#### 1. Add New Flags
```python
parser.add_argument('--keep-individual', action='store_true',
                   help='Keep individual .shasum files when using --monolithic')
parser.add_argument('--both-modes', action='store_true',
                   help='Generate both individual .shasum files and monolithic file')
```

#### 2. Mode Detection Logic
```python
# In main()
if args.both_modes:
    generate_individual = True
    generate_monolithic = True
elif args.monolithic:
    generate_individual = args.keep_individual
    generate_monolithic = True
else:
    generate_individual = True
    generate_monolithic = False
```

#### 3. Modify ChecksumGenerator
```python
class ChecksumGenerator:
    def __init__(self, ..., generate_individual=True, generate_monolithic=False):
        self.generate_individual = generate_individual
        self.generate_monolithic = generate_monolithic
        # Remove single monolithic_mode flag
```

#### 4. Update Directory Processing
```python
def process_single_directory(directory: Path):
    checksums = self.generate_checksums_for_directory(directory)
    
    if checksums:
        # Always append to monolithic if enabled
        if self.generate_monolithic and monolithic_writer:
            monolithic_writer.append_directory_checksums(directory, checksums)
        
        # Also write individual if enabled
        if self.generate_individual:
            self.write_shasum_file(directory, checksums)
```

### User Experience

#### Clear Examples
```bash
# Individual files only (default)
dazzle-checksum.py -r /data

# Monolithic only (current)
dazzle-checksum.py -r --monolithic /data

# Both files (new!)
dazzle-checksum.py -r --both-modes /data
# OR
dazzle-checksum.py -r --monolithic --keep-individual /data

# With custom output
dazzle-checksum.py -r --both-modes --output full-backup.sha256 /data
```

#### Help Text Updates
```
File Generation Modes:
  --monolithic          Generate single checksum file for entire tree
  --keep-individual     Also generate individual .shasum files (with --monolithic)
  --both-modes          Generate both individual and monolithic files
  
  Default: Individual .shasum files in each directory
  Common: Use --both-modes for maximum flexibility
```

### Verification Considerations

When verifying with both modes:
1. Check for monolithic file first (faster for full tree verify)
2. Fall back to individual files if needed
3. Option to force which mode to verify against

```bash
# Auto-detect (prefer monolithic if available)
dazzle-checksum.py --verify /data

# Force individual verification even if monolithic exists
dazzle-checksum.py --verify --prefer-individual /data
```

### Performance Optimization

Since we're calculating checksums once but writing twice:
1. Keep checksums in memory while writing both outputs
2. Use same hash calculation for both modes
3. Consider parallel writes if on different disks

### Migration Path

1. **Phase 1**: Add new flags, maintain current behavior
2. **Phase 2**: Update documentation with examples
3. **Phase 3**: Consider making --both-modes default in v2.0

## 5. Implementation Plan

### Step 1: Add Argument Parsing
- Add --keep-individual flag
- Add --both-modes flag  
- Add validation logic

### Step 2: Refactor Mode Handling
- Replace monolithic_mode boolean with two flags
- Update ChecksumGenerator constructor
- Modify directory processing logic

### Step 3: Update File Writing
- Ensure both modes can write simultaneously
- Handle file conflicts gracefully
- Maintain atomic operations

### Step 4: Enhance Verification
- Auto-detect available checksum files
- Add preference flags
- Update verification output

### Step 5: Testing
- Test all mode combinations
- Verify backward compatibility
- Check performance impact

### Step 6: Documentation
- Update help text
- Add examples to README
- Create migration guide

## 6. Future Considerations

### Extensibility
- Easy to add new output formats (JSON, XML)
- Could support multiple monolithic files with different algorithms
- Remote storage integration (S3, Azure Blob)

### Performance
- Parallel hash calculation
- Streaming writes to multiple outputs
- Memory-mapped file handling for large trees

### User Experience
- Configuration file support for default modes
- Progress indication for dual-mode operation
- Dry-run option to preview what would be generated

## Conclusion

The recommended approach (--both-modes flag) provides a clean, backward-compatible solution that addresses the user need without complicating the interface. It maintains the simplicity of the current design while adding flexibility for users who want comprehensive checksum coverage.

The implementation is straightforward, requiring minimal changes to existing code paths, and sets up the codebase for future enhancements without architectural constraints.