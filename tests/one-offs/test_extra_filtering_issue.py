#!/usr/bin/env python3
"""
Test script to reproduce the EXTRA filtering issue at level -4.
Level -4 should hide status lines for directories with only EXTRA files
because EXTRA=True in the squelch mapping.
"""

import os
import sys
import tempfile
import subprocess
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

def setup_extra_only_test():
    """Create a test directory with only EXTRA files."""
    test_dir = tempfile.mkdtemp(prefix="dazzlesum_extra_test_")
    test_path = Path(test_dir)
    
    # Create a directory with ONLY EXTRA files
    extra_dir = test_path / "extra_only"
    extra_dir.mkdir()
    
    # Create files without corresponding .shasum entries
    extra_file1 = extra_dir / "extra1.txt"
    extra_file1.write_text("Extra file 1")
    
    extra_file2 = extra_dir / "extra2.txt"
    extra_file2.write_text("Extra file 2")
    
    # Create empty .shasum or don't create it at all
    # No .shasum file = all files are EXTRA
    
    return test_path

def run_dazzlesum_with_level(test_dir, level):
    """Run dazzlesum with specified verbosity level and return output."""
    cmd = [sys.executable, str(project_root / "dazzlesum.py"), "verify", "-r", f"-{'q' * abs(level)}", str(test_dir)]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "Timeout"

def test_extra_filtering_at_level_4():
    """Test that level -4 properly filters EXTRA-only directories."""
    print("Testing EXTRA filtering issue at level -4...")
    
    test_dir = setup_extra_only_test()
    print(f"Created test directory: {test_dir}")
    
    try:
        # Test level -4 
        exit_code, stdout, stderr = run_dazzlesum_with_level(test_dir, -4)
        
        print(f"\nLevel -4 output:")
        print(f"Exit code: {exit_code}")
        print(f"STDERR:\n{stderr}")
        
        # Look for status lines about the extra_only directory
        all_output = stdout + stderr
        lines = all_output.strip().split('\n')
        
        extra_status_lines = [line for line in lines if 'extra_only' in line and ': ' in line and 'extra' in line]
        
        print(f"\nEXTRA-only directory status lines: {len(extra_status_lines)}")
        for line in extra_status_lines:
            print(f"  {line}")
        
        # Level -4 has EXTRA=True, so should NOT show status lines for EXTRA-only directories
        if len(extra_status_lines) > 0:
            print("\n❌ ISSUE CONFIRMED: Level -4 showing status lines for EXTRA-only directories")
            print("FORCE_SUMMARY is not properly respecting EXTRA=True squelching")
            return False
        else:
            print("\n✅ WORKING: Level -4 correctly hiding EXTRA-only directory status lines")
            return True
            
    finally:
        # Cleanup
        import shutil
        shutil.rmtree(test_dir)
        print(f"\nCleaned up test directory: {test_dir}")

if __name__ == "__main__":
    print("=" * 60)
    print("TESTING EXTRA FILTERING ISSUE AT LEVEL -4")
    print("=" * 60)
    
    success = test_extra_filtering_at_level_4()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 NO ISSUE FOUND - EXTRA filtering working correctly!")
    else:
        print("💥 ISSUE CONFIRMED - EXTRA filtering needs fix")
    print("=" * 60)
    
    sys.exit(0 if success else 1)