# Windows Color Support Test

## Testing ANSI Colors in Windows Command Prompt

To test if colors work in your Windows environment:

### Option 1: Force Colors On
```cmd
set DAZZLESUM_FORCE_COLOR=1
dazzlesum
```

### Option 2: Install Colorama (Recommended)
```cmd
pip install colorama
dazzlesum
```

### Option 3: Disable Colors if They Don't Work
```cmd
set DAZZLESUM_NO_COLOR=1
dazzlesum
```

## Expected Behavior

**With Colors Working:**
- `FAIL` should appear in red
- `verified` should appear in green  
- `missing` should appear in yellow
- Numbers should appear bold
- `INFO` should appear in light green

**Without Color Support:**
- All text appears in normal terminal colors
- No ANSI escape sequences visible (no `←[91m` etc.)

## Troubleshooting

1. **If you see escape sequences like `←[91m`:**
   - Your terminal doesn't support ANSI colors
   - Use `set DAZZLESUM_NO_COLOR=1` to disable

2. **If colors don't appear but no escape sequences:**
   - Try installing colorama: `pip install colorama`
   - Or force colors: `set DAZZLESUM_FORCE_COLOR=1`

3. **Modern Windows 10/11:**
   - Should work automatically with the built-in ANSI support

4. **Older Windows or restricted environments:**
   - Install colorama or use `DAZZLESUM_NO_COLOR=1`