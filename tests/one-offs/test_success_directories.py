#!/usr/bin/env python3
"""
Test script to demonstrate the FORCE_SUMMARY SUCCESS filtering issue.
Creates test directories with SUCCESS cases to show unwanted status lines at level -4.
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

def setup_test_directory_with_success():
    """Create a test directory structure with SUCCESS directories."""
    test_dir = tempfile.mkdtemp(prefix="dazzlesum_success_test_")
    test_path = Path(test_dir)
    
    # Create a directory with ONLY SUCCESS (should NOT show status line at level -4)
    success_dir = test_path / "success_only"
    success_dir.mkdir()
    
    # Create a file and corresponding .shasum with correct checksum
    test_file = success_dir / "test.txt"
    content = "Hello World"
    test_file.write_text(content)
    
    correct_checksum = calculate_sha256(content)
    shasum_file = success_dir / ".shasum"
    shasum_file.write_text(f"{correct_checksum}  test.txt\n")
    
    # Create another SUCCESS directory
    success_dir2 = test_path / "success_only2"
    success_dir2.mkdir()
    
    test_file2 = success_dir2 / "test2.txt"
    content2 = "Another file"
    test_file2.write_text(content2)
    
    correct_checksum2 = calculate_sha256(content2)
    shasum_file2 = success_dir2 / ".shasum"
    shasum_file2.write_text(f"{correct_checksum2}  test2.txt\n")
    
    # Create a directory with FAIL issues (should show status line at level -4)
    fail_dir = test_path / "fail_only"
    fail_dir.mkdir()
    
    fail_file = fail_dir / "fail.txt"
    fail_file.write_text("This will fail")
    
    shasum_fail = fail_dir / ".shasum"
    # Intentionally wrong checksum
    shasum_fail.write_text("wrongchecksum123456789abcdef  fail.txt\n")
    
    return test_path

def run_dazzlesum_with_level(test_dir, level):
    """Run dazzlesum with specified verbosity level and return output."""
    cmd = [sys.executable, str(project_root / "dazzlesum.py"), "verify", "-r", f"-{'q' * abs(level)}", str(test_dir)]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "Timeout"

def test_success_filtering_issue():
    """Test that demonstrates the SUCCESS filtering issue with FORCE_SUMMARY."""
    print("Testing FORCE_SUMMARY SUCCESS filtering issue...")
    
    test_dir = setup_test_directory_with_success()
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
        
        success_status_lines = [line for line in lines if 'SUCCESS' in line and ': ' in line and 'verified' in line]
        fail_status_lines = [line for line in lines if 'FAILURE' in line and ': ' in line and 'verified' in line]
        
        print(f"\nSUCCESS status lines found: {len(success_status_lines)}")
        for line in success_status_lines:
            print(f"  {line}")
        
        print(f"\nFAILURE status lines found: {len(fail_status_lines)}")
        for line in fail_status_lines:
            print(f"  {line}")
        
        # The issue: level -4 should NOT show SUCCESS status lines because SUCCESS is squelched
        # But FORCE_SUMMARY is overriding this logic
        if len(success_status_lines) > 0:
            print("\n❌ ISSUE CONFIRMED: Level -4 showing SUCCESS status lines despite SUCCESS being squelched")
            print("FORCE_SUMMARY is overriding SUCCESS squelching logic")
            return False
        else:
            print("\n✅ WORKING: Level -4 not showing unwanted SUCCESS status lines")
            return True
            
    finally:
        # Cleanup
        import shutil
        shutil.rmtree(test_dir)
        print(f"\nCleaned up test directory: {test_dir}")

if __name__ == "__main__":
    print("=" * 60)
    print("TESTING FORCE_SUMMARY SUCCESS FILTERING ISSUE")
    print("=" * 60)
    
    success = test_success_filtering_issue()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 NO ISSUE FOUND - FORCE_SUMMARY is working correctly!")
    else:
        print("💥 ISSUE CONFIRMED - FORCE_SUMMARY needs SUCCESS filtering")
    print("=" * 60)
    
    sys.exit(0 if success else 1)