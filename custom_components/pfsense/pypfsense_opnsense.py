"""Exports for opnsense helpers (API-only)
"""

from .opnsense_client import probe_opnsense, OpnSenseClient

__all__ = ["probe_opnsense", "OpnSenseClient"]
