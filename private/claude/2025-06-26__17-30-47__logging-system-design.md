# Enhanced Logging System Design

## Feature Overview
Implement a multi-level verbosity system with clearer visual separation and more intelligent output formatting for better user experience.

## Verbosity Levels

### Level 0: Default (No flags)
- Show only essential information
- Errors and warnings always visible
- Progress summary for each directory
- Final summary statistics

### Level 1: Verbose (-v)
- All Level 0 output
- Info-level messages
- File processing details for failures
- Detailed verification results

### Level 2: Very Verbose (-vv)  
- All Level 1 output
- Directory entry/exit messages
- File-by-file processing status
- Performance metrics per directory

### Level 3: Debug (-vvv)
- All Level 2 output  
- Native tool selection details
- Hash calculation methods used
- Memory usage statistics
- Symlink resolution details

## Visual Improvements

### Directory Separation
Add blank lines between directory sections for clarity:
```
INFO - Processing directory: C:\Users\Downloads
INFO - Found 99 files in C:\Users\Downloads
INFO - Directory C:\Users\Downloads: 98 processed, 1 skipped in 30.57s

INFO - Processing directory: C:\Users\Downloads\subfolder
INFO - Found 2 files in C:\Users\Downloads\subfolder
INFO - Directory C:\Users\Downloads\subfolder: 2 processed, 0 skipped in 0.14s
```

### Structured Output Format
- Use consistent prefixes for different message types
- Indent sub-operations for visual hierarchy
- Color coding support (if terminal supports it)

## Implementation Approach

### 1. Logger Wrapper Class
```python
class DazzleLogger:
    def __init__(self, verbosity=0, use_color=True):
        self.verbosity = verbosity
        self.use_color = use_color and self._supports_color()
        self._configure_handlers()
    
    def directory_start(self, path):
        if self.verbosity >= 0:
            self._emit_with_spacing(f"Processing directory: {path}")
    
    def directory_complete(self, path, stats):
        if self.verbosity >= 0:
            self._emit(f"Directory {path}: {stats}")
            self._add_blank_line()
```

### 2. Conditional Logging
Replace direct logger calls with verbosity-aware methods:
- `logger.info()` → `dazzle_logger.info(msg, level=1)`
- `logger.debug()` → `dazzle_logger.debug(msg, level=3)`

### 3. Context-Aware Formatting
Track operation context to provide better formatting:
- Current directory being processed
- Operation type (generate/verify)
- Nesting level for sub-operations

## Pros
- **User-Friendly**: Clear visual separation makes output easier to parse
- **Flexible**: Multiple verbosity levels suit different use cases
- **Backwards Compatible**: Default behavior remains similar
- **Debugging**: -vvv provides detailed troubleshooting info
- **Automation-Friendly**: Structured output can be parsed

## Cons  
- **Complexity**: More code to maintain
- **Performance**: Slight overhead from verbosity checks
- **Terminal Dependency**: Color support varies by platform

## Edge Cases
- Piped output should disable colors automatically
- Very long paths might need truncation
- Unicode in paths needs proper handling
- Progress bars conflict with logged output

## Future Considerations
- JSON output mode for automation
- Log rotation for long-running operations  
- Filtering by message category
- Integration with Python logging config files
- Real-time log streaming to file while showing summary on console

## Implementation Priority
1. Basic verbosity levels (-v, -vv, -vvv)
2. Directory separation with blank lines
3. Conditional message display
4. Color support (optional)
5. Structured formatters