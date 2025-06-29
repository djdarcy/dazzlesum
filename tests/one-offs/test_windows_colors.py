#!/usr/bin/env python3
"""Test Windows color support with different approaches."""

import sys
import os
sys.path.insert(0, '../..')
from dazzlesum import ColorFormatter

def test_basic_colors():
    """Test basic color functionality."""
    print("=== Testing Basic Colors ===")
    cf = ColorFormatter(use_colors=True)
    
    print(f"Success: {cf.success('verified')}")
    print(f"Error: {cf.error('FAIL')}")
    print(f"Warning: {cf.warning('MISS')}")
    print(f"Info: {cf.info('INFO')}")
    print(f"Extra: {cf.extra('EXTRA')}")
    print(f"Bold number: {cf.bold_number(389)}")

def test_auto_detection():
    """Test auto-detection logic."""
    print("\n=== Testing Auto-Detection ===")
    cf = ColorFormatter()  # Auto-detect
    print(f"Auto-detected color support: {cf.use_colors}")
    print(f"Colorama available: {cf.colorama_available}")
    
    if cf.use_colors:
        print(f"Colors enabled: {cf.success('SUCCESS')}")
    else:
        print("Colors disabled: SUCCESS")

def test_forced_disabled():
    """Test with colors explicitly disabled."""
    print("\n=== Testing Forced Disabled ===")
    cf = ColorFormatter(use_colors=False)
    print(f"Forced disabled: {cf.success('SUCCESS')} {cf.error('FAIL')}")

if __name__ == '__main__':
    print(f"Platform: {os.name}")
    print(f"Is TTY: {sys.stdout.isatty()}")
    print(f"TERM: {os.environ.get('TERM', 'not set')}")
    
    test_auto_detection()
    test_basic_colors()
    test_forced_disabled()