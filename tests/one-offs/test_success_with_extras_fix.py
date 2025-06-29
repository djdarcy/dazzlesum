#!/usr/bin/env python3
"""
Test script to verify the SUCCESS+extras filtering fix at level -4.
Ensures that SUCCESS directories with extra files are properly squelched.
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

def setup_success_with_extras_test():
    """Create test directories that mirror the user's scenario."""
    test_dir = tempfile.mkdtemp(prefix="dazzlesum_success_extras_test_")
    test_path = Path(test_dir)
    
    # 1. SUCCESS directory with extras (should be HIDDEN at level -4)
    success_extras_dir = test_path / "success_with_extras"
    success_extras_dir.mkdir()
    
    # Create verified files
    for i in range(3):
        verified_file = success_extras_dir / f"verified{i}.txt"
        content = f"Verified content {i}"
        verified_file.write_text(content)
    
    # Create extra files not in .shasum
    for i in range(2):
        extra_file = success_extras_dir / f"extra{i}.txt"
        extra_file.write_text(f"Extra content {i}")
    
    # Create .shasum file that only includes verified files
    shasum_file = success_extras_dir / ".shasum"
    shasum_content = ""
    for i in range(3):
        content = f"Verified content {i}"
        checksum = calculate_sha256(content)
        shasum_content += f"{checksum}  verified{i}.txt\n"
    shasum_file.write_text(shasum_content)
    
    # 2. FAIL directory with extras (should be SHOWN at level -4)
    fail_extras_dir = test_path / "fail_with_extras"
    fail_extras_dir.mkdir()
    
    # Create a file that will fail verification
    fail_file = fail_extras_dir / "fail.txt"
    fail_file.write_text("Content that will fail")
    
    # Create extra files
    extra_fail = fail_extras_dir / "extra_in_fail.txt"
    extra_fail.write_text("Extra in fail dir")
    
    # Create .shasum with wrong checksum for fail.txt
    shasum_fail = fail_extras_dir / ".shasum"
    shasum_fail.write_text("wrongchecksum123456789abcdef  fail.txt\n")
    
    # 3. Pure SUCCESS directory (should be HIDDEN at level -4)
    pure_success_dir = test_path / "pure_success"
    pure_success_dir.mkdir()
    
    success_file = pure_success_dir / "success.txt"
    success_content = "Pure success content"
    success_file.write_text(success_content)
    
    shasum_pure = pure_success_dir / ".shasum"
    shasum_pure.write_text(f"{calculate_sha256(success_content)}  success.txt\n")
    
    return test_path

def run_dazzlesum_with_level(test_dir, level):
    """Run dazzlesum with specified verbosity level and return output."""
    cmd = [sys.executable, str(project_root / "dazzlesum.py"), "verify", "-r", f"-{'q' * abs(level)}", str(test_dir)]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "Timeout"

def test_success_with_extras_filtering():
    """Test that level -4 properly handles SUCCESS directories with extras."""
    print("Testing SUCCESS+extras filtering fix at level -4...")
    
    test_dir = setup_success_with_extras_test()
    print(f"Created test directory: {test_dir}")
    
    try:
        # Test level -4 
        exit_code, stdout, stderr = run_dazzlesum_with_level(test_dir, -4)
        
        print(f"\nLevel -4 output:")
        print(f"Exit code: {exit_code}")
        print(f"STDERR:\n{stderr}")
        
        # Analyze output
        all_output = stdout + stderr
        lines = all_output.strip().split('\n')
        
        # Look for specific directory status lines
        success_extras_lines = [line for line in lines if 'success_with_extras' in line and ': ' in line]
        fail_extras_lines = [line for line in lines if 'fail_with_extras' in line and ': ' in line]
        pure_success_lines = [line for line in lines if 'pure_success' in line and ': ' in line]
        
        print(f"\nDirectory status line analysis:")
        print(f"SUCCESS+extras directories: {len(success_extras_lines)} (should be 0)")
        for line in success_extras_lines:
            print(f"  {line}")
        
        print(f"FAIL+extras directories: {len(fail_extras_lines)} (should be 1)")
        for line in fail_extras_lines:
            print(f"  {line}")
            
        print(f"Pure SUCCESS directories: {len(pure_success_lines)} (should be 0)")
        for line in pure_success_lines:
            print(f"  {line}")
        
        # Verify expected behavior
        success = True
        
        if len(success_extras_lines) != 0:
            print("❌ FAIL: SUCCESS+extras directories should be hidden at level -4")
            success = False
        else:
            print("✅ PASS: SUCCESS+extras directories correctly hidden")
            
        if len(fail_extras_lines) != 1:
            print("❌ FAIL: FAIL+extras directories should be shown at level -4")
            success = False
        else:
            print("✅ PASS: FAIL+extras directories correctly shown")
            
        if len(pure_success_lines) != 0:
            print("❌ FAIL: Pure SUCCESS directories should be hidden at level -4")
            success = False
        else:
            print("✅ PASS: Pure SUCCESS directories correctly hidden")
        
        return success
            
    finally:
        # Cleanup
        import shutil
        shutil.rmtree(test_dir)
        print(f"\nCleaned up test directory: {test_dir}")

def test_level_comparison():
    """Test that different levels show different amounts of information."""
    print("\nTesting level comparison to ensure fix doesn't break progression...")
    
    test_dir = setup_success_with_extras_test()
    
    try:
        levels_to_test = [-5, -4, -3, 0]
        results = {}
        
        for level in levels_to_test:
            exit_code, stdout, stderr = run_dazzlesum_with_level(test_dir, level)
            all_output = stdout + stderr
            status_lines = [line for line in all_output.split('\n') if ': ' in line and 'verified' in line]
            results[level] = len(status_lines)
            print(f"Level {level}: {len(status_lines)} status lines")
        
        # Level -4 should show more than -5 but less than 0
        success = True
        if results[-4] <= results[-5]:
            print("❌ FAIL: Level -4 should show more than level -5")
            success = False
        else:
            print("✅ PASS: Level -4 shows more than level -5")
            
        if results[0] <= results[-4]:
            print("❌ FAIL: Level 0 should show more than level -4")
            success = False
        else:
            print("✅ PASS: Level 0 shows more than level -4")
            
        return success
            
    finally:
        import shutil
        shutil.rmtree(test_dir)

if __name__ == "__main__":
    print("=" * 70)
    print("TESTING SUCCESS+EXTRAS FILTERING FIX AT LEVEL -4")
    print("=" * 70)
    
    success1 = test_success_with_extras_filtering()
    success2 = test_level_comparison()
    
    print("\n" + "=" * 70)
    if success1 and success2:
        print("🎉 ALL TESTS PASSED - SUCCESS+extras filtering fix working!")
        print("✅ SUCCESS+extras directories: Correctly hidden at level -4")
        print("✅ FAIL+extras directories: Correctly shown at level -4")
        print("✅ Progressive verbosity: Maintained across levels")
    else:
        print("💥 SOME TESTS FAILED - Fix needs more work")
    print("=" * 70)
    
    sys.exit(0 if success1 and success2 else 1)