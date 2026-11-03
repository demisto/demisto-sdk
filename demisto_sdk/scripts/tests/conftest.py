"""Conftest for scripts tests to handle Packs directory during session setup."""

import os
from pathlib import Path


def pytest_configure(config):
    """
    Hook that runs before any tests or fixtures.
    Create Packs directory to prevent FileNotFoundError during register_commands().
    """
    original_dir = os.getcwd()

    # Create a temporary Packs directory in current location if it doesn't exist
    packs_dir = Path.cwd() / "Packs"
    if not packs_dir.exists():
        packs_dir.mkdir(exist_ok=True)
        # Mark it for cleanup
        config._packs_dir_created = packs_dir
        config._original_dir = original_dir


def pytest_unconfigure(config):
    """
    Hook that runs after all tests complete.
    Clean up the Packs directory if we created it.
    """
    if hasattr(config, "_packs_dir_created"):
        import shutil

        try:
            if config._packs_dir_created.exists():
                shutil.rmtree(config._packs_dir_created)
        except Exception:
            pass

    if hasattr(config, "_original_dir"):
        try:
            os.chdir(config._original_dir)
        except Exception:
            pass
