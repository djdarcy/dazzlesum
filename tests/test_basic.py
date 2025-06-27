#!/usr/bin/env python3
"""
Basic tests for dazzlesum functionality.
"""

import unittest
import tempfile
import os
import sys
from pathlib import Path

# Add the parent directory to sys.path so we can import dazzlesum
sys.path.insert(0, str(Path(__file__).parent.parent))

import dazzlesum


class TestBasicFunctionality(unittest.TestCase):
    """Test basic dazzlesum functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_dir = tempfile.mkdtemp()
        self.test_file = os.path.join(self.test_dir, "test.txt")
        with open(self.test_file, 'w') as f:
            f.write("Hello, world!")

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_import_works(self):
        """Test that we can import dazzlesum."""
        self.assertTrue(hasattr(dazzlesum, 'main'))
        self.assertTrue(hasattr(dazzlesum, '__version__'))

    def test_version_string(self):
        """Test that version string exists and is reasonable."""
        version = dazzlesum.__version__
        self.assertIsInstance(version, str)
        self.assertTrue(len(version) > 0)
        # Should be in format like "1.1.0"
        parts = version.split('.')
        self.assertGreaterEqual(len(parts), 2)

    def test_supported_algorithms(self):
        """Test that supported algorithms are defined."""
        self.assertTrue(hasattr(dazzlesum, 'SUPPORTED_ALGORITHMS'))
        algorithms = dazzlesum.SUPPORTED_ALGORITHMS
        self.assertIn('sha256', algorithms)
        self.assertIn('md5', algorithms)
        self.assertIn('sha1', algorithms)
        self.assertIn('sha512', algorithms)

    def test_default_algorithm(self):
        """Test that default algorithm is defined."""
        self.assertTrue(hasattr(dazzlesum, 'DEFAULT_ALGORITHM'))
        default = dazzlesum.DEFAULT_ALGORITHM
        self.assertEqual(default, 'sha256')

    def test_shasum_filename_constant(self):
        """Test that SHASUM_FILENAME constant is defined."""
        self.assertTrue(hasattr(dazzlesum, 'SHASUM_FILENAME'))
        filename = dazzlesum.SHASUM_FILENAME
        self.assertEqual(filename, '.shasum')


class TestHelperFunctions(unittest.TestCase):
    """Test helper functions if accessible."""

    def test_is_windows_function(self):
        """Test that is_windows function exists and returns boolean."""
        # The function might be imported or defined
        if hasattr(dazzlesum, 'is_windows'):
            result = dazzlesum.is_windows()
            self.assertIsInstance(result, bool)


if __name__ == '__main__':
    unittest.main()
