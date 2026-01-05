import sys
import os
import pytest
import abiflib.devtools

# Add the project directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))


def pytest_addoption(parser):
    """Add a --force option to pytest."""
    parser.addoption(
        "--force", action="store_true", default=False, help="Force actions like creating directories."
    )


_original_logfile_singleton_new = abiflib.devtools.LogfileSingleton.__new__


def pytest_configure(config):
    """Monkeypatch LogfileSingleton if --force is used."""
    if config.option.force:
        def new_forced(cls, *args, **kwargs):
            kwargs['force_log'] = True
            return _original_logfile_singleton_new(cls, *args, **kwargs)
        abiflib.devtools.LogfileSingleton.__new__ = new_forced


def pytest_unconfigure(config):
    """Restore original LogfileSingleton.__new__."""
    abiflib.devtools.LogfileSingleton.__new__ = _original_logfile_singleton_new
