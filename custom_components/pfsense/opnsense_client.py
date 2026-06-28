"""OpnSense API client for hass-OpnSense

Provides:
- async detection of API vs XML-RPC
- async call_api for /api/ endpoints
- async xmlrpc_call for legacy xmlrpc.php endpoints

Designed to be thin and dependency-free (uses aiohttp and stdlib xmlrpc.client).
"""

from __future__ import annotations

import asyncio
import base64
import logging
from typing import Any, Dict, List, Optional, Tuple

import aiohttp
import xmlrpc.client

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
        self.mode: Optional[str] = None  # 'api' or 'xmlrpc'

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

        Returns 'api' or 'xmlrpc'. Raises on transport error.
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
        except Exception as exc:  # network / SSL errors
            _LOGGER.debug("API probe network error: %s", exc)

        # try xmlrpc probe
        xmlrpc_url = f"{self.base_url}/xmlrpc.php"
        body = xmlrpc.client.dumps(("system.listMethods",), methodname=None)
        headers_rpc = {"Content-Type": "text/xml"}
        if headers := self._auth_header():
            headers_rpc.update(headers)
        _LOGGER.debug("Falling back to xmlrpc probe at %s", xmlrpc_url)
        try:
            async with session.post(xmlrpc_url, data=body, headers=headers_rpc, ssl=self.verify_ssl) as resp:
                text = await resp.text()
                if resp.status == 200 and text.strip().startswith("<?xml"):
                    _LOGGER.debug("Detected xmlrpc endpoint at %s", xmlrpc_url)
                    self.mode = "xmlrpc"
                    return "xmlrpc"
                _LOGGER.debug("xmlrpc probe returned status %s and body: %s", resp.status, text[:200])
        except Exception as exc:
            _LOGGER.debug("xmlrpc probe network error: %s", exc)

        # default to api if uncertain
        self.mode = "api"
        return "api"

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

        if self.mode == "xmlrpc":
            # No generic mapping available; raise to let caller choose xmlrpc method explicitly
            raise RuntimeError("API mode is xmlrpc; use xmlrpc_call() instead")

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

    async def xmlrpc_call(self, method: str, params: Optional[Tuple] = None) -> Any:
        """Perform an XML-RPC call against /xmlrpc.php.

        Uses xmlrpc.client to build/parse payloads, and aiohttp for transport.
        """
        session = await self._get_session()
        xmlrpc_url = f"{self.base_url}/xmlrpc.php"
        params = params or ()
        body = xmlrpc.client.dumps(params, methodname=method)
        headers = {"Content-Type": "text/xml"}
        if auth := self._auth_header():
            headers.update(auth)
        _LOGGER.debug("XMLRPC call %s -> %s", method, xmlrpc_url)
        async with session.post(xmlrpc_url, data=body, headers=headers, ssl=self.verify_ssl) as resp:
            text = await resp.text()
            if resp.status != 200:
                _LOGGER.error("XMLRPC %s returned %s: %s", method, resp.status, text[:1000])
                resp.raise_for_status()
            try:
                params, methodname = xmlrpc.client.loads(text)
                # xmlrpc.client.loads returns a tuple (params, methodname)
                return params[0] if params else None
            except Exception as exc:
                _LOGGER.exception("Failed parsing xmlrpc response: %s", exc)
                raise

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
