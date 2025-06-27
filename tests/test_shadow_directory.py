#!/usr/bin/env python3
"""
Tests for shadow directory functionality.
"""

import unittest
import tempfile
import os
import sys
from pathlib import Path

# Add the parent directory to sys.path so we can import dazzlesum
sys.path.insert(0, str(Path(__file__).parent.parent))

import dazzlesum


class TestShadowPathResolver(unittest.TestCase):
    """Test ShadowPathResolver class functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.source_root = Path(self.temp_dir) / "source"
        self.shadow_root = Path(self.temp_dir) / "shadow"
        
        # Create source directory structure
        self.source_root.mkdir()
        (self.source_root / "subdir1").mkdir()
        (self.source_root / "subdir2").mkdir()
        (self.source_root / "subdir1" / "nested").mkdir()

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_shadow_resolver_initialization(self):
        """Test that ShadowPathResolver initializes correctly."""
        resolver = dazzlesum.ShadowPathResolver(self.source_root, self.shadow_root)
        
        self.assertEqual(resolver.source_root, self.source_root.resolve())
        self.assertEqual(resolver.shadow_root, self.shadow_root.resolve())
        self.assertTrue(self.shadow_root.exists())  # Should be created

    def test_get_shadow_shasum_path(self):
        """Test shadow .shasum path calculation."""
        resolver = dazzlesum.ShadowPathResolver(self.source_root, self.shadow_root)
        
        # Test root directory
        shadow_path = resolver.get_shadow_shasum_path(self.source_root)
        expected = self.shadow_root / ".shasum"
        self.assertEqual(shadow_path, expected)
        
        # Test subdirectory
        subdir = self.source_root / "subdir1"
        shadow_path = resolver.get_shadow_shasum_path(subdir)
        expected = self.shadow_root / "subdir1" / ".shasum"
        self.assertEqual(shadow_path, expected)
        
        # Test nested subdirectory
        nested_dir = self.source_root / "subdir1" / "nested"
        shadow_path = resolver.get_shadow_shasum_path(nested_dir)
        expected = self.shadow_root / "subdir1" / "nested" / ".shasum"
        self.assertEqual(shadow_path, expected)

    def test_get_shadow_shasum_path_invalid_directory(self):
        """Test shadow path calculation with invalid directory."""
        resolver = dazzlesum.ShadowPathResolver(self.source_root, self.shadow_root)
        
        # Test directory outside source root
        outside_dir = Path(self.temp_dir) / "outside"
        outside_dir.mkdir()
        
        with self.assertRaises(ValueError) as context:
            resolver.get_shadow_shasum_path(outside_dir)
        
        self.assertIn("not under source root", str(context.exception))

    def test_get_source_file_path(self):
        """Test source file path resolution."""
        resolver = dazzlesum.ShadowPathResolver(self.source_root, self.shadow_root)
        
        # Test simple file
        source_path = resolver.get_source_file_path("file.txt")
        expected = self.source_root / "file.txt"
        self.assertEqual(source_path, expected)
        
        # Test file in subdirectory
        source_path = resolver.get_source_file_path("subdir1/file.txt")
        expected = self.source_root / "subdir1" / "file.txt"
        self.assertEqual(source_path, expected)
        
        # Test file in nested subdirectory
        source_path = resolver.get_source_file_path("subdir1/nested/file.txt")
        expected = self.source_root / "subdir1" / "nested" / "file.txt"
        self.assertEqual(source_path, expected)

    def test_ensure_shadow_directory(self):
        """Test shadow directory creation."""
        resolver = dazzlesum.ShadowPathResolver(self.source_root, self.shadow_root)
        
        # Test creating nested shadow directory
        shadow_path = self.shadow_root / "subdir1" / "nested" / ".shasum"
        self.assertFalse(shadow_path.parent.exists())
        
        resolver.ensure_shadow_directory(shadow_path)
        self.assertTrue(shadow_path.parent.exists())

    def test_get_shadow_monolithic_path(self):
        """Test shadow monolithic path calculation."""
        resolver = dazzlesum.ShadowPathResolver(self.source_root, self.shadow_root)
        
        # Test default filename
        mono_path = resolver.get_shadow_monolithic_path("sha256")
        expected = self.shadow_root / "checksums.sha256"
        self.assertEqual(mono_path, expected)
        
        # Test custom filename
        mono_path = resolver.get_shadow_monolithic_path("sha256", "custom.sha256")
        expected = self.shadow_root / "custom.sha256"
        self.assertEqual(mono_path, expected)


class TestShadowDirectoryIntegration(unittest.TestCase):
    """Test shadow directory integration with ChecksumGenerator."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.source_root = Path(self.temp_dir) / "source"
        self.shadow_root = Path(self.temp_dir) / "shadow"
        
        # Create source directory with test files
        self.source_root.mkdir()
        (self.source_root / "file1.txt").write_text("Hello World")
        (self.source_root / "file2.txt").write_text("Test Content")
        
        # Create subdirectory with files
        subdir = self.source_root / "subdir"
        subdir.mkdir()
        (subdir / "file3.txt").write_text("Nested File")

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_shadow_directory_checksum_generation(self):
        """Test checksum generation with shadow directory."""
        generator = dazzlesum.ChecksumGenerator(
            algorithm='sha256',
            shadow_dir=str(self.shadow_root),
            generate_individual=True
        )
        
        # Process the directory tree (this initializes shadow resolver)
        generator.process_directory_tree(self.source_root, recursive=False)
        
        # Generate checksums for root directory
        checksums = generator.generate_checksums_for_directory(self.source_root)
        
        # Should have checksums for both files
        self.assertEqual(len(checksums), 2)
        self.assertIn("file1.txt", checksums)
        self.assertIn("file2.txt", checksums)
        
        # Verify source directory is clean (no .shasum file)
        source_shasum = self.source_root / ".shasum"
        self.assertFalse(source_shasum.exists())
        
        # Verify shadow directory has .shasum file
        shadow_shasum = self.shadow_root / ".shasum"
        self.assertTrue(shadow_shasum.exists())
        
        # Verify shadow .shasum content
        content = shadow_shasum.read_text()
        self.assertIn("file1.txt", content)
        self.assertIn("file2.txt", content)

    def test_shadow_directory_verification(self):
        """Test checksum verification with shadow directory."""
        generator = dazzlesum.ChecksumGenerator(
            algorithm='sha256',
            shadow_dir=str(self.shadow_root),
            generate_individual=True
        )
        
        # First generate checksums
        generator.process_directory_tree(self.source_root, recursive=False)
        generator.generate_checksums_for_directory(self.source_root)
        
        # Now verify checksums
        results = generator.verify_checksums_in_directory(self.source_root)
        
        # Should verify successfully
        self.assertNotIn('error', results)
        self.assertEqual(len(results['verified']), 2)
        self.assertEqual(len(results['failed']), 0)
        self.assertEqual(len(results['missing']), 0)


if __name__ == '__main__':
    unittest.main()