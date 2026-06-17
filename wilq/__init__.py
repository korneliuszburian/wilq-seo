"""WILQ Marketing Operating System shared package."""

from wilq.credentials.runtime import load_local_env

load_local_env()

__all__ = ["__version__"]

__version__ = "0.1.0"
