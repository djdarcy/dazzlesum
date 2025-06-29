#!/usr/bin/env python3
"""
Test the new automated versioning system.
"""

import os
import sys
import unittest
from pathlib import Path

# Add parent directory to path so we can import dazzlesum
sys.path.insert(0, str(Path(__file__).parent.parent))

import dazzlesum


class TestVersioningSystem(unittest.TestCase):
    """Test the automated versioning system."""

    def test_version_format_development(self):
        """Test that development version follows expected format."""
        version = dazzlesum.__version__
        
        # Should be string
        self.assertIsInstance(version, str)
        
        if '_' in version:
            # Development build: 1.3.0_33-20250629-9938568e-dev
            base, build_info = version.split('_', 1)
            
            # Base version should be semantic
            parts = base.split('.')
            self.assertEqual(len(parts), 3)
            for part in parts:
                self.assertTrue(part.isdigit())
            
            # Build info should match pattern: Build#-YYYYMMDD-CommitHash[-dev]
            self.assertRegex(build_info, r'^\d+-\d{8}-[a-f0-9]{8}')
            
            # Should end with -dev for development builds (when not in CI)
            if not (os.environ.get('CI') or os.environ.get('GITHUB_ACTIONS')):
                self.assertTrue(build_info.endswith('-dev'))
        else:
            # Fallback version: 1.3.0
            parts = version.split('.')
            self.assertGreaterEqual(len(parts), 3)

    def test_version_ci_injection(self):
        """Test that CI environment variable injection works."""
        # Save original version
        original_version = dazzlesum.__version__
        
        # Test CI injection
        test_version = "1.4.0_50-20250630-abcd1234"
        os.environ['DAZZLESUM_VERSION'] = test_version
        
        # Reload version
        from importlib import reload
        reload(dazzlesum)
        
        # Should use injected version
        self.assertEqual(dazzlesum.__version__, test_version)
        
        # Cleanup
        del os.environ['DAZZLESUM_VERSION']
        reload(dazzlesum)

    def test_version_components_accessible(self):
        """Test that version components can be extracted."""
        version = dazzlesum.__version__
        
        if '_' in version:
            base_version, build_info = version.split('_', 1)
            
            # Should be able to extract build number
            build_parts = build_info.split('-')
            build_number = build_parts[0]
            self.assertTrue(build_number.isdigit())
            
            # Should be able to extract date
            if len(build_parts) >= 2:
                date_part = build_parts[1]
                self.assertEqual(len(date_part), 8)  # YYYYMMDD
                self.assertTrue(date_part.isdigit())
            
            # Should be able to extract commit hash
            if len(build_parts) >= 3:
                commit_part = build_parts[2]
                # Remove -dev suffix if present
                if commit_part.endswith('-dev'):
                    commit_part = commit_part[:-4]
                self.assertEqual(len(commit_part), 8)  # 8-character hash
                self.assertRegex(commit_part, r'^[a-f0-9]{8}$')

    def test_version_comparison_compatibility(self):
        """Test that version can be compared for basic ordering."""
        version = dazzlesum.__version__
        
        # Extract base version for comparison
        if '_' in version:
            base_version = version.split('_')[0]
        else:
            base_version = version
        
        # Should be greater than previous version
        self.assertGreater(base_version, "1.2.0")
        
        # Should be semantic version compatible
        parts = base_version.split('.')
        major, minor, patch = map(int, parts[:3])
        self.assertGreaterEqual(major, 1)
        self.assertGreaterEqual(minor, 0)
        self.assertGreaterEqual(patch, 0)


if __name__ == '__main__':
    unittest.main()