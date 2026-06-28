"""Small helper: call to opnsense probe from config flow tests.

This file is intentionally minimal and dependency-free (uses aiohttp which is
already available in Home Assistant runtime).
"""

from .opnsense_client import probe_opnsense, OpnSenseClient

__all__ = ["probe_opnsense", "OpnSenseClient"]
