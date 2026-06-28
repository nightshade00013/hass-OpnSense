"""OpnSense API client for hass-OpnSense (API-only variant)

Provides:
- async detection of OpnSense /api/ endpoints
- async call_api for /api/{package}/{controller}/{action}/

This simplified client drops legacy XML-RPC support (xmlrpc.php) as requested.
"""

from __future__ import annotations

import base64
import logging
from typing import Any, Dict, Optional

import aiohttp

_LOGGER = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 10


class OpnSenseClient:
    def __init__(
        self,
        base_url: str,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        verify_ssl: bool = True,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.api_secret = api_secret
        self.verify_ssl = verify_ssl
        self.timeout = timeout
        self._session: Optional[aiohttp.ClientSession] = None
        self.mode: Optional[str] = None  # 'api'

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            # trust_env=False to avoid proxy surprises in HA
            self._session = aiohttp.ClientSession(timeout=timeout, trust_env=False)
        return self._session

    def _auth_header(self) -> Optional[Dict[str, str]]:
        if self.api_key is None and self.api_secret is None:
            return None
        token = f"{self.api_key}:{self.api_secret}".encode("utf-8")
        b64 = base64.b64encode(token).decode("ascii")
        return {"Authorization": f"Basic {b64}"}

    async def detect_api(self) -> str:
        """Detect whether the host exposes the OpnSense /api/ endpoints.

        Returns 'api' on success. Raises RuntimeError on failure to detect a usable API.
        """
        session = await self._get_session()
        headers = self._auth_header() or {}
        url = f"{self.base_url}/api/core/backup/providers"
        _LOGGER.debug("Detecting OpnSense API at %s", url)
        try:
            async with session.get(url, headers=headers, ssl=self.verify_ssl) as resp:
                text = await resp.text()
                if resp.status == 200:
                    _LOGGER.debug("Detected OpnSense API (200) at %s", url)
                    self.mode = "api"
                    return "api"
                _LOGGER.debug("API probe returned status %s and body: %s", resp.status, text[:200])
        except aiohttp.ClientResponseError as exc:
            _LOGGER.debug("API probe response error: %s", exc)
            raise
        except Exception as exc:  # network / SSL errors
            _LOGGER.debug("API probe network error: %s", exc)
            raise

        raise RuntimeError("OpnSense API not detected at provided base_url")

    async def call_api(
        self,
        package: str,
        controller: str,
        action: str,
        method: str = "get",
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """Call an OpnSense /api/{package}/{controller}/{action}/ endpoint.

        Raises aiohttp.ClientError on transport issues. Returns parsed JSON on 2xx, otherwise raises.
        """
        if self.mode is None:
            await self.detect_api()

        url = f"{self.base_url}/api/{package}/{controller}/{action}/"
        headers = self._auth_header() or {}
        session = await self._get_session()
        _LOGGER.debug("Calling OpnSense API %s %s", method.upper(), url)

        async with session.request(method.upper(), url, params=params, json=json, headers=headers, ssl=self.verify_ssl) as resp:
            text = await resp.text()
            if 200 <= resp.status < 300:
                try:
                    return await resp.json(content_type=None)
                except Exception:
                    # If response not JSON, return raw text
                    return text
            _LOGGER.error("OpnSense API %s %s failed: %s - %s", method.upper(), url, resp.status, text[:1000])
            resp.raise_for_status()

    async def close(self) -> None:
        if self._session is not None and not self._session.closed:
            await self._session.close()


# convenience helper for quick detection
async def probe_opnsense(base_url: str, api_key: Optional[str] = None, api_secret: Optional[str] = None, verify_ssl: bool = True) -> str:
    client = OpnSenseClient(base_url, api_key, api_secret, verify_ssl=verify_ssl)
    try:
        return await client.detect_api()
    finally:
        await client.close()
