# Verify Mode Improvements Design

## Feature Overview
Enhance verification output to show only problems by default, making it easier to identify issues in large directory trees. Provide comprehensive statistics at completion.

## Current vs Proposed Behavior

### Current Behavior
- Shows every file verification (verified, failed, missing, extra)
- Verbose output makes problems hard to spot
- No summary statistics at the end

### Proposed Behavior  
- Default: Show only problems (failed hashes, missing files, extra files)
- Option for full output with --show-all-verifications
- Comprehensive summary statistics at completion
- Clear problem categorization

## Output Modes

### Default Mode (Problems Only)
```
INFO - Verifying directory: /home/user/data

ERROR - Hash mismatch: config.json
  Expected: a3f5b2c1...
  Actual:   d4e6f7a8...

WARNING - Missing file: readme.txt

WARNING - Extra file: temp.log

INFO - Verification complete for /home/user/data
  Verified: 245 files
  Failed:   1 file  
  Missing:  1 file
  Extra:    1 file
```

### Verbose Mode (--show-all-verifications or -v)
```
INFO - Verifying directory: /home/user/data
  OK file1.txt
  OK file2.dat
  FAIL config.json - Hash mismatch
  MISS readme.txt - Missing
  EXTRA temp.log - Extra
  ...
```

## Implementation Design

### 1. Verification Result Collector
```python
class VerificationCollector:
    def __init__(self, show_all=False):
        self.show_all = show_all
        self.results = {
            'verified': [],
            'failed': [],
            'missing': [], 
            'extra': []
        }
    
    def add_verified(self, filename):
        self.results['verified'].append(filename)
        if self.show_all:
            self._display_success(filename)
    
    def add_failed(self, filename, expected, actual):
        self.results['failed'].append({
            'file': filename,
            'expected': expected,
            'actual': actual
        })
        self._display_failure(filename, expected, actual)
```

### 2. Summary Statistics
```python
class VerificationSummary:
    def __init__(self):
        self.start_time = time.time()
        self.total_files = 0
        self.total_bytes = 0
        self.by_directory = {}
    
    def display_summary(self):
        # Show overall statistics
        # Show problem breakdown
        # Show performance metrics
```

### 3. Problem Grouping
Group similar problems for cleaner output:
- Consecutive missing files in same directory
- Files with same hash mismatch pattern
- Extra files by type/extension

## Command Line Options

### New Flags
- `--show-all-verifications`: Display all file verifications, not just problems
- `--verify-summary-only`: Show only final statistics, no individual problems
- `--verify-format`: Choose output format (text, json, csv)

### Modified Behavior
- Default verify shows only problems
- `-v` during verify enables show-all mode
- `--quiet` shows only error summary

## Pros
- **Clarity**: Problems immediately visible in large verifications
- **Efficiency**: Less console output to process
- **Actionable**: Focus on what needs attention
- **Flexible**: Multiple output modes for different needs
- **Performance**: Reduced I/O for console output

## Cons
- **Breaking Change**: Default behavior differs from current
- **Learning Curve**: Users need to know about --show-all flag
- **Complexity**: More code paths to maintain

## Edge Cases
- Empty directories (no files to verify)
- Directories with only problems (no successes to report)
- Very long filenames breaking formatting
- Unicode filenames in problem reports
- Symbolic links in verification

## Future Enhancements
- Problem severity levels (critical vs warning)
- Suggested fixes for common issues
- Batch problem resolution commands
- Integration with file movement detection
- Historical verification tracking

## Migration Strategy
1. Add new behavior behind feature flag
2. Deprecation warning for old behavior
3. Switch default in next major version
4. Maintain backwards compatibility flag

## Testing Approach
- Unit tests for each problem type
- Integration tests with various directory structures
- Performance tests with large file counts
- Terminal width handling tests