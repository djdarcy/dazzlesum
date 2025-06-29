#!/usr/bin/env python3
"""
Comprehensive test for level -4 FORCE_SUMMARY behavior with smart category filtering.
Tests all the scenarios identified in the dev-workflow-process analysis.
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

def setup_comprehensive_test_directory():
    """Create a test directory structure with all issue types."""
    test_dir = tempfile.mkdtemp(prefix="dazzlesum_level4_comprehensive_")
    test_path = Path(test_dir)
    
    # 1. SUCCESS-only directory (should NOT show at level -4)
    success_dir = test_path / "success_only"
    success_dir.mkdir()
    test_file = success_dir / "success.txt"
    content = "Success content"
    test_file.write_text(content)
    shasum_file = success_dir / ".shasum"
    shasum_file.write_text(f"{calculate_sha256(content)}  success.txt\n")
    
    # 2. FAIL-only directory (should show at level -4)
    fail_dir = test_path / "fail_only"
    fail_dir.mkdir()
    fail_file = fail_dir / "fail.txt"
    fail_file.write_text("Fail content")
    shasum_fail = fail_dir / ".shasum"
    shasum_fail.write_text("wrongchecksum123456789abcdef  fail.txt\n")
    
    # 3. MISSING-only directory (should show at level -4)
    missing_dir = test_path / "missing_only"
    missing_dir.mkdir()
    shasum_missing = missing_dir / ".shasum"
    shasum_missing.write_text(f"{calculate_sha256('missing')}  missing.txt\n")
    
    # 4. EXTRA-only directory (should NOT show at level -4 due to EXTRA_SUMMARY)
    extra_dir = test_path / "extra_only"
    extra_dir.mkdir()
    extra_file = extra_dir / "extra.txt"
    extra_file.write_text("Extra content")
    # No .shasum file = EXTRA file
    
    # 5. Mixed issues directory (should show at level -4)
    mixed_dir = test_path / "mixed_issues"
    mixed_dir.mkdir()
    # Success file
    success_file = mixed_dir / "success.txt"
    success_content = "Mixed success"
    success_file.write_text(success_content)
    # Fail file  
    fail_file = mixed_dir / "fail.txt"
    fail_file.write_text("Mixed fail")
    # Shasum with one correct, one wrong
    shasum_mixed = mixed_dir / ".shasum"
    shasum_mixed.write_text(f"{calculate_sha256(success_content)}  success.txt\nwrongchecksum123  fail.txt\n")
    
    return test_path

def run_dazzlesum_with_level(test_dir, level):
    """Run dazzlesum with specified verbosity level and return output."""
    cmd = [sys.executable, str(project_root / "dazzlesum.py"), "verify", "-r", f"-{'q' * abs(level)}", str(test_dir)]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "Timeout"

def test_level_4_comprehensive():
    """Comprehensive test of level -4 behavior."""
    print("Testing level -4 comprehensive FORCE_SUMMARY behavior...")
    
    test_dir = setup_comprehensive_test_directory()
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
        
        # Find status lines for each directory type
        success_lines = [line for line in lines if 'success_only' in line and ': ' in line]
        fail_lines = [line for line in lines if 'fail_only' in line and ': ' in line]
        missing_lines = [line for line in lines if 'missing_only' in line and ': ' in line]
        extra_lines = [line for line in lines if 'extra_only' in line and ': ' in line]
        mixed_lines = [line for line in lines if 'mixed_issues' in line and ': ' in line]
        
        print(f"\nStatus line analysis:")
        print(f"SUCCESS-only directories: {len(success_lines)} (should be 0)")
        print(f"FAIL-only directories: {len(fail_lines)} (should be 1)")
        print(f"MISSING-only directories: {len(missing_lines)} (should be 1)")
        print(f"EXTRA-only directories: {len(extra_lines)} (should be 0)")
        print(f"Mixed issues directories: {len(mixed_lines)} (should be 1)")
        
        # Verify expected behavior
        success = True
        
        if len(success_lines) != 0:
            print("❌ FAIL: SUCCESS-only directories should not show status lines at level -4")
            success = False
        else:
            print("✅ PASS: SUCCESS-only directories correctly hidden")
            
        if len(fail_lines) != 1:
            print("❌ FAIL: FAIL-only directories should show status lines at level -4")
            success = False
        else:
            print("✅ PASS: FAIL-only directories correctly shown")
            
        if len(missing_lines) != 1:
            print("❌ FAIL: MISSING-only directories should show status lines at level -4")
            success = False
        else:
            print("✅ PASS: MISSING-only directories correctly shown")
            
        if len(extra_lines) != 0:
            print("❌ FAIL: EXTRA-only directories should not show status lines at level -4")
            success = False
        else:
            print("✅ PASS: EXTRA-only directories correctly hidden")
            
        if len(mixed_lines) != 1:
            print("❌ FAIL: Mixed issues directories should show status lines at level -4")
            success = False
        else:
            print("✅ PASS: Mixed issues directories correctly shown")
        
        return success
            
    finally:
        # Cleanup
        import shutil
        shutil.rmtree(test_dir)
        print(f"\nCleaned up test directory: {test_dir}")

def test_level_comparison():
    """Test that level -4 behaves differently from adjacent levels."""
    print("\nTesting level comparison (-5, -4, -3)...")
    
    test_dir = setup_comprehensive_test_directory()
    
    try:
        # Test multiple levels
        levels_to_test = [-5, -4, -3]
        results = {}
        
        for level in levels_to_test:
            exit_code, stdout, stderr = run_dazzlesum_with_level(test_dir, level)
            all_output = stdout + stderr
            status_lines = [line for line in all_output.split('\n') if ': ' in line and 'verified' in line]
            results[level] = len(status_lines)
            print(f"Level {level}: {len(status_lines)} status lines")
        
        # Level -4 should show more than -5 but potentially same or less than -3
        if results[-4] > results[-5]:
            print("✅ PASS: Level -4 shows more status lines than level -5")
            return True
        else:
            print("❌ FAIL: Level -4 should show more status lines than level -5")
            return False
            
    finally:
        import shutil
        shutil.rmtree(test_dir)

if __name__ == "__main__":
    print("=" * 70)
    print("COMPREHENSIVE LEVEL -4 FORCE_SUMMARY TEST")
    print("=" * 70)
    
    success = True
    
    success &= test_level_4_comprehensive()
    success &= test_level_comparison()
    
    print("\n" + "=" * 70)
    if success:
        print("🎉 ALL TESTS PASSED - Level -4 smart FORCE_SUMMARY working correctly!")
        print("✅ SUCCESS filtering: Working")
        print("✅ EXTRA_SUMMARY filtering: Working")  
        print("✅ FORCE_SUMMARY for issues: Working")
    else:
        print("💥 SOME TESTS FAILED - Level -4 needs more fixes")
    print("=" * 70)
    
    sys.exit(0 if success else 1)