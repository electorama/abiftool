#!/usr/bin/env python3
"""
PEP8 compliance tests for abiftool Python files.

This test uses pycodestyle to check code formatting for all .py files in abiftool.
"""

import os
import sys
import unittest
from pathlib import Path
import subprocess

class TestAbiftoolPEP8Compliance(unittest.TestCase):
    """Test that abiftool Python files follow PEP8 style guidelines."""

    IGNORED_ERRORS = [
        'E501', 'E302', 'E303', 'E305', 'E402', 'E265', 'E713', 'E275', 'E225', 'E231',
        'E201', 'E202', 'E111', 'E251', 'E124', 'E261', 'E304', 'E306', 'E722', 'W291',
        'W293', 'W391', 'E222', 'E226', 'E711', 'W504', 'E121', 'E122', 'E126', 'E721',
        'E131'
    ]  # Ignore all baseline errors for now

    def setUp(self):
        self.project_dir = Path(__file__).parent.parent
        try:
            result = subprocess.run(
                ['git', 'ls-files', '*.py'],
                cwd=self.project_dir,
                capture_output=True,
                text=True,
                check=True
            )
            self.python_files = [
                self.project_dir / Path(f)
                for f in result.stdout.strip().split('\n') if f
            ]
        except Exception as e:
            self.python_files = []
            print(f"Warning: Could not get git-tracked Python files: {e}")
        self.maxDiff = None

    def test_pep8_compliance(self):
        """Test that all abiftool Python files pass pycodestyle checks."""
        try:
            import pycodestyle
        except ImportError:
            self.skipTest("pycodestyle not installed. Install with: pip install pycodestyle")

        style_guide = pycodestyle.StyleGuide(
            ignore=self.IGNORED_ERRORS,
            quiet=True
        )

        if not self.python_files:
            self.skipTest("No Python files found to check")

        files_to_check = [str(f) for f in self.python_files]
        result = style_guide.check_files(files_to_check)

        if result.total_errors > 0:
            # Show relative paths from project root for easier command use
            rel_paths = [str(f.relative_to(self.project_dir)) for f in self.python_files]
            file_list = ' '.join(rel_paths)
            ignore_opts = f"--ignore={','.join(self.IGNORED_ERRORS)}"
            self.fail(
                f"PEP8 compliance check failed with {result.total_errors} errors.\n"
                f"Run 'pycodestyle {ignore_opts} {file_list}' to see detailed errors and fix them."
            )

        self.assertEqual(result.total_errors, 0,
                         "All abiftool Python files should pass PEP8 style checks")

    def test_pep8_compliance_cli(self):
        """Test PEP8 compliance using command-line pycodestyle."""
        if not self.python_files:
            self.skipTest("No Python files found to check")

        files_to_check = [str(f) for f in self.python_files]

        try:
            cmd = ['pycodestyle', '--max-line-length=79', f'--ignore={",".join(self.IGNORED_ERRORS)}'] + files_to_check
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
        except FileNotFoundError:
            self.skipTest("pycodestyle command not found. Install with: pip install pycodestyle")
        except subprocess.TimeoutExpired:
            self.fail("pycodestyle check timed out")

        if result.returncode != 0:
            errors = result.stdout.strip().split('\n') if result.stdout else []
            rel_paths = [str(f.relative_to(self.project_dir)) for f in self.python_files]
            file_list = ' '.join(rel_paths)
            ignore_opts = f"--ignore={','.join(self.IGNORED_ERRORS)}"
            self.fail(
                f"PEP8 compliance check failed with {len(errors)} errors.\n"
                f"Run 'pycodestyle {ignore_opts} {file_list}' to see details."
            )

        self.assertEqual(result.returncode, 0,
                         "pycodestyle should return exit code 0 for compliant code")

    def test_file_exists(self):
        """Test that abiftool Python files exist."""
        self.assertTrue(len(self.python_files) > 0,
                        f"At least one abiftool Python file should exist. Found: {[f.name for f in self.python_files]}")

    def test_file_is_readable(self):
        """Test that abiftool Python files are readable."""
        for file_path in self.python_files:
            self.assertTrue(file_path.is_file(),
                            f"{file_path} should be a readable file")

if __name__ == '__main__':
    unittest.main(verbosity=2)

