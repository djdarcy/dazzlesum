# Smart File Movement Detection Design

## Feature Overview
Detect when files have been moved rather than deleted/created, providing more accurate verification results and helping users understand actual changes in their file system.

## Detection Strategies

### 1. Simple Same-Directory Detection (Always Enabled)
- Track all hashes within current directory during verification
- If missing file hash matches an extra file hash → movement detected
- Minimal memory impact (only current directory hashes)

### 2. Global Monolithic Detection (Default for Monolithic Mode)
- Build hash index while reading monolithic file
- Check missing file hashes against entire tree
- Memory usage: O(n) where n = total files

### 3. Memory-Bounded Cross-Directory Detection
- User specifies memory limit (e.g., --movement-memory 100MB)
- Build partial hash index within memory constraints
- Use LRU eviction for hash entries

### 4. Two-Pass Detection (Explicit Flag Required)
- First pass: Collect all problems
- Second pass: Search for matching hashes
- Most accurate but doubles verification time

## Implementation Approach

### Core Data Structure
```python
class MovementDetector:
    def __init__(self, memory_limit_mb=0, enable_two_pass=False):
        self.memory_limit = memory_limit_mb * 1024 * 1024
        self.two_pass = enable_two_pass
        self.hash_index = {}  # hash -> [paths]
        self.missing_hashes = {}  # path -> hash
        self.extra_files = set()
        self.movements = []  # [(old_path, new_path)]
        
    def add_verified_file(self, path, hash_value):
        if self.memory_limit == 0 or self._memory_usage() < self.memory_limit:
            self.hash_index.setdefault(hash_value, []).append(path)
    
    def add_missing_file(self, path, expected_hash):
        self.missing_hashes[path] = expected_hash
        self._check_movement(path, expected_hash)
    
    def add_extra_file(self, path):
        self.extra_files.add(path)
        # Calculate hash and check against missing
        actual_hash = self._calculate_hash(path)
        self._check_reverse_movement(path, actual_hash)
```

### Detection Algorithm
```python
def _check_movement(self, missing_path, hash_value):
    # Check if this hash exists elsewhere
    if hash_value in self.hash_index:
        candidates = self.hash_index[hash_value]
        # Find best match (closest path similarity)
        best_match = self._find_best_match(missing_path, candidates)
        if best_match and best_match in self.extra_files:
            self.movements.append((missing_path, best_match))
            return True
    return False

def _find_best_match(self, original_path, candidates):
    # Score candidates by:
    # 1. Same filename (highest score)
    # 2. Path similarity (edit distance)
    # 3. Same file extension
    # 4. Similar file size/timestamp
```

### Memory Management
```python
class BoundedHashIndex:
    def __init__(self, max_bytes):
        self.max_bytes = max_bytes
        self.current_bytes = 0
        self.index = OrderedDict()
        self.entry_sizes = {}
    
    def add(self, hash_value, path):
        entry_size = len(hash_value) + len(str(path)) + 32  # overhead
        
        # Evict oldest entries if needed
        while self.current_bytes + entry_size > self.max_bytes:
            self._evict_oldest()
        
        self.index.setdefault(hash_value, []).append(path)
        self.current_bytes += entry_size
```

## Output Format

### Default Display
```
INFO - Movement detected: 5 files

Moved files:
  config.json → settings/config.json
  data.csv → archive/2024/data.csv
  img001.png → images/photo001.png
  
Similar movements (same directory):
  doc1.txt → doc1_backup.txt
  test.py → test_old.py
```

### Detailed Display (-v)
```
Movement Analysis:
  config.json → settings/config.json
    Hash: a3f5b2c1d4e5f6a7
    Confidence: High (100% - exact hash match)
    
  data.csv → archive/2024/data.csv  
    Hash: b4c5d6e7f8a9b0c1
    Confidence: High (100% - exact hash match)
    Path similarity: 45%
```

## Command Line Options

### New Flags
- `--detect-movements`: Enable movement detection (auto-enabled for monolithic)
- `--movement-memory <MB>`: Set memory limit for hash index
- `--movement-two-pass`: Enable two-pass detection for accuracy
- `--movement-threshold <0-100>`: Minimum confidence for movement detection

### Integration with Existing
- Movement detection respects `--follow-symlinks`
- Works with both regular and monolithic modes
- Combines with verify improvements for cleaner output

## Pros
- **Accurate**: Distinguishes moves from delete/create
- **Flexible**: Multiple strategies for different use cases
- **Memory-Conscious**: Configurable memory limits
- **Informative**: Shows where files moved to
- **Performance**: Same-directory detection adds minimal overhead

## Cons
- **Memory Usage**: Global detection requires memory
- **Complexity**: Multiple detection strategies to maintain
- **False Positives**: Identical files might not be moves
- **Performance**: Two-pass mode doubles verification time

## Edge Cases
- Multiple files with same hash (duplicates)
- Renamed and modified files (partial detection)
- Cross-volume moves on Windows
- Circular moves (A→B, B→C, C→A)
- Moved directories (need to detect pattern)
- Hash collisions (extremely rare)

## Algorithm Optimizations
1. **Bloom Filter Pre-Check**: Quick hash existence check
2. **Path Similarity Cache**: Reuse edit distance calculations
3. **Incremental Hash Index**: Build while verifying
4. **Parallel Hash Calculation**: For extra files
5. **Smart Eviction**: Keep hashes likely to match

## Integration Points
1. **Verification Results**: Modify to separate moves from missing/extra
2. **Summary Statistics**: Add movement count
3. **Progress Tracking**: Show movement detection phase
4. **Logging System**: Movement-specific log entries
5. **JSON Output**: Structured movement data

## Future Enhancements
- Directory movement detection
- Partial file movement (file split/merged)
- Movement history tracking
- Undo movement suggestions
- Integration with file system watchers
- Machine learning for better matching

## Testing Strategy
- Unit tests for each detection strategy
- Memory limit compliance tests
- Performance benchmarks
- Edge case coverage
- Integration with verification tests