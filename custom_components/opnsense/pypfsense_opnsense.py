"""A lightweight OpnSense API probe helper adapted from pypfsense.

This module provides a probe_opnsense() coroutine that attempts to query
basic system information from an OpnSense device using a minimal API
approach. It is intended for configuration-time validation only.
"""

from __future__ import annotations

import logging
import asyncio
import json
from typing import Any

import aiohttp

_LOGGER = logging.getLogger(__name__)


async def probe_opnsense(url: str, username: str, password: str, verify_ssl: bool = True) -> dict:
    """Attempt to contact an OpnSense host and return system information.

    This performs a simple HTTP(S) request to a known OpnSense API endpoint
    and returns a minimal dict containing hostname/device id when possible.
    """
    # Example endpoint; OpnSense deployments may vary. This is best-effort.
    api_url = f"{url}/api/core/metadata"
    timeout = aiohttp.ClientTimeout(total=10)
    conn = aiohttp.TCPConnector(ssl=verify_ssl)
    async with aiohttp.ClientSession(timeout=timeout, connector=conn) as session:
        try:
            async with session.get(api_url, auth=aiohttp.BasicAuth(username, password)) as resp:
                text = await resp.text()
                try:
                    data = json.loads(text)
                except Exception:
                    data = {"raw": text}
                # Normalize returned data
                info = {
                    "hostname": data.get("hostname") if isinstance(data, dict) else None,
                    "device": {"id": data.get("device_id") if isinstance(data, dict) else None},
                }
                return info
        except Exception as err:
            _LOGGER.debug("OpnSense probe failed contacting %s: %s", api_url, err)
            raise
