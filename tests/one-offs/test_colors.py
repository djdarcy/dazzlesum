#!/usr/bin/env python3
"""Quick test to see color output."""

import sys
sys.path.insert(0, '.')
from dazzlesum import ColorFormatter

# Test color formatter
cf = ColorFormatter(use_colors=True)  # Force colors on

print("Testing ANSI color support:")
print(f"Success: {cf.success('verified')}")
print(f"Error: {cf.error('FAIL')}")
print(f"Warning: {cf.warning('MISS')}")
print(f"Info: {cf.info('INFO')}")
print(f"Extra: {cf.extra('EXTRA')}")
print(f"Bold number: {cf.bold_number(389)}")

print("\nSample verification line:")
print(f"{cf.error('FAIL')} /path: {cf.bold_number(389)} {cf.success('verified')}, {cf.bold_number(3)} {cf.error('failed')}, {cf.bold_number(1)} {cf.warning('missing')}, {cf.bold_number(0)} {cf.extra('extra')}")