#!/usr/bin/env python3
"""
Test script to reproduce the EXTRA filtering issue at level -4.
Creates a directory with .shasum file but additional EXTRA files.
"""

import os
import sys
import tempfile
import subprocess
import hashlib
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

def calculate_sha256(content):
    """Calculate SHA256 hash of content."""
    return hashlib.sha256(content.encode()).hexdigest()

def setup_extra_with_shasum_test():
    """Create a test directory with .shasum and EXTRA files."""
    test_dir = tempfile.mkdtemp(prefix="dazzlesum_extra_shasum_test_")
    test_path = Path(test_dir)
    
    # Create a directory with some verified files AND extra files
    test_dir_inner = test_path / "has_extras"
    test_dir_inner.mkdir()
    
    # Create a verified file
    verified_file = test_dir_inner / "verified.txt"
    content = "This file is verified"
    verified_file.write_text(content)
    
    # Create extra files not in .shasum
    extra_file1 = test_dir_inner / "extra1.txt"
    extra_file1.write_text("Extra file 1")
    
    extra_file2 = test_dir_inner / "extra2.txt"
    extra_file2.write_text("Extra file 2")
    
    # Create .shasum file that only includes the verified file
    shasum_file = test_dir_inner / ".shasum"
    correct_checksum = calculate_sha256(content)
    shasum_file.write_text(f"{correct_checksum}  verified.txt\n")
    
    return test_path

def run_dazzlesum_with_level(test_dir, level):
    """Run dazzlesum with specified verbosity level and return output."""
    cmd = [sys.executable, str(project_root / "dazzlesum.py"), "verify", "-r", f"-{'q' * abs(level)}", str(test_dir)]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "Timeout"

def test_extra_with_verified_files():
    """Test level -4 with directories that have both verified and EXTRA files."""
    print("Testing EXTRA filtering with mixed verified+extra files...")
    
    test_dir = setup_extra_with_shasum_test()
    print(f"Created test directory: {test_dir}")
    
    try:
        # Test level -4 
        exit_code, stdout, stderr = run_dazzlesum_with_level(test_dir, -4)
        
        print(f"\nLevel -4 output:")
        print(f"Exit code: {exit_code}")
        print(f"STDERR:\n{stderr}")
        
        # Look for status lines
        all_output = stdout + stderr
        lines = all_output.strip().split('\n')
        
        status_lines = [line for line in lines if 'has_extras' in line and ': ' in line and 'verified' in line]
        
        print(f"\nStatus lines for directory with extras: {len(status_lines)}")
        for line in status_lines:
            print(f"  {line}")
        
        # At level -4, EXTRA=True means individual EXTRA files are squelched
        # But if the directory has verified files too, it should show status line
        # This is different from EXTRA-only directories
        
        if len(status_lines) > 0:
            # Check if this directory has only EXTRA files or mixed
            has_verified = any('1 verified' in line for line in status_lines)
            has_extra = any('extra' in line for line in status_lines)
            
            if has_verified and has_extra:
                print("\n✅ EXPECTED: Directory has verified files + extras, should show status line")
                return True
            elif not has_verified and has_extra:
                print("\n❌ ISSUE: Directory with only extras should not show status line at level -4")
                return False
        else:
            print("\n❓ UNCLEAR: No status lines shown - need to check why")
            return False
            
    finally:
        # Cleanup
        import shutil
        shutil.rmtree(test_dir)
        print(f"\nCleaned up test directory: {test_dir}")

def test_pure_extra_only_directory():
    """Test level -4 with a directory that has ONLY extra files.""" 
    print("\nTesting pure EXTRA-only directory...")
    
    test_dir = tempfile.mkdtemp(prefix="dazzlesum_pure_extra_test_")
    test_path = Path(test_dir)
    
    # Create directory with only extra files
    extra_dir = test_path / "pure_extra"
    extra_dir.mkdir()
    
    # Create extra files
    extra1 = extra_dir / "extra1.txt"
    extra1.write_text("Extra 1")
    extra2 = extra_dir / "extra2.txt" 
    extra2.write_text("Extra 2")
    
    # Create empty .shasum (no files listed = all are extra)
    shasum_file = extra_dir / ".shasum"
    shasum_file.write_text("")
    
    try:
        exit_code, stdout, stderr = run_dazzlesum_with_level(test_dir, -4)
        
        print(f"Pure EXTRA-only test output:")
        print(f"Exit code: {exit_code}")
        print(f"STDERR:\n{stderr}")
        
        all_output = stdout + stderr
        status_lines = [line for line in all_output.split('\n') if 'pure_extra' in line and ': ' in line]
        
        print(f"Status lines for pure EXTRA directory: {len(status_lines)}")
        for line in status_lines:
            print(f"  {line}")
            
        # This should NOT show status lines at level -4
        if len(status_lines) == 0:
            print("✅ CORRECT: Pure EXTRA-only directory hidden at level -4")
            return True
        else:
            print("❌ ISSUE: Pure EXTRA-only directory should be hidden at level -4")
            return False
            
    finally:
        import shutil
        shutil.rmtree(test_dir)

if __name__ == "__main__":
    print("=" * 70)
    print("TESTING EXTRA FILTERING SCENARIOS AT LEVEL -4")
    print("=" * 70)
    
    success1 = test_extra_with_verified_files()
    success2 = test_pure_extra_only_directory()
    
    print("\n" + "=" * 70)
    if success1 and success2:
        print("🎉 ALL TESTS PASSED - EXTRA filtering working correctly!")
    else:
        print("💥 SOME TESTS FAILED - EXTRA filtering needs fixes")
    print("=" * 70)
    
    sys.exit(0 if success1 and success2 else 1)