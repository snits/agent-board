# ABOUTME: Package marker so setuptools includes frontend static files in the distribution.
# ABOUTME: Provides root_dir() to locate installed frontend assets at runtime.

from pathlib import Path


def root_dir() -> Path:
    return Path(__file__).parent
