"""
Centralized exception definitions for UCAS.
"""

class LaunchError(Exception):
    """Error during command launch."""
    pass

class MergerError(LaunchError):
    """Error during configuration merging."""
    pass
