"""OpnSense HTTP client (best-effort scaffolding for OpnSense 26.1).

This client provides a thin wrapper around OpnSense REST endpoints and is
intended as a starting point. Many endpoints differ between deployments and
OpnSense versions; methods attempt multiple common endpoints and provide
clear errors listing which endpoints were tried when an operation is not
implemented.

Methods are synchronous (use hass.async_add_executor_job to call from async
context). I avoided hardcoding endpoints for destructive operations; if a
specific OpnSense installation uses different endpoints we can add them to
the lists below.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

import requests
from requests.auth import HTTPBasicAuth

_LOGGER = logging.getLogger(__name__)


class OpnSenseAPIError(RuntimeError):
    pass


class OpnSenseClient:
    def __init__(self, base_url: str, username: str, password: str, verify_ssl: bool = True, timeout: int = 15):
        self.base_url = base_url.rstrip("/")
        self.auth = HTTPBasicAuth(username, password)
        self.verify = verify_ssl
        self.timeout = timeout

    def _get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        url = f"{self.base_url}{path}"
        _LOGGER.debug("OpnSense GET %s", url)
        resp = requests.get(url, auth=self.auth, params=params, timeout=self.timeout, verify=self.verify)
        try:
            resp.raise_for_status()
        except Exception as err:
            _LOGGER.debug("GET %s failed: %s (code=%s) -> %s", url, err, resp.status_code, resp.text)
            raise OpnSenseAPIError(f"GET {url} failed: {err}")
        try:
            return resp.json()
        except Exception:
            return resp.text

    def _post(self, path: str, data: Optional[Dict[str, Any]] = None) -> Any:
        url = f"{self.base_url}{path}"
        _LOGGER.debug("OpnSense POST %s", url)
        headers = {"Content-Type": "application/json"}
        resp = requests.post(url, auth=self.auth, json=data or {}, headers=headers, timeout=self.timeout, verify=self.verify)
        try:
            resp.raise_for_status()
        except Exception as err:
            _LOGGER.debug("POST %s failed: %s (code=%s) -> %s", url, err, resp.status_code, resp.text)
            raise OpnSenseAPIError(f"POST {url} failed: {err}")
        try:
            return resp.json()
        except Exception:
            return resp.text

    def detect_api(self) -> Dict[str, Any]:
        """Probe common OpnSense endpoints to determine API availability.

        Returns a dict with keys found and raw responses.
        """
        tried = []
        results: Dict[str, Any] = {}

        candidates = [
            "/api/core/metadata",
            "/api/core/status",
            "/api/diagnostics/status",
            "/api/core/get_system_info",
        ]

        for path in candidates:
            tried.append(path)
            try:
                data = self._get(path)
                results[path] = data
            except OpnSenseAPIError as err:
                _LOGGER.debug("probe %s failed: %s", path, err)
                continue

        if not results:
            raise OpnSenseAPIError(f"No OpnSense API endpoints were reachable. Tried: {tried}")

        # Prefer the /api/core/metadata-like response if present
        for k, v in results.items():
            if isinstance(v, dict):
                # Normalize to a simple system info dict
                sys = {
                    "hostname": v.get("hostname") or v.get("host") or None,
                    "domain": v.get("domain") or None,
                    "device_id": v.get("device", {}).get("id") if isinstance(v.get("device"), dict) else v.get("device_id") if isinstance(v.get("device_id"), str) else None,
                    "raw": v,
                }
                return {"endpoint": k, "system_info": sys}

        # fallback: return first raw
        first = next(iter(results.items()))
        return {"endpoint": first[0], "system_info": {"raw": first[1]}}

    def get_system_info(self) -> Dict[str, Any]:
        """Return basic system identification information.

        Tries multiple endpoints and returns a normalized dict.
        """
        try:
            info = self.detect_api()
            return info.get("system_info", {})
        except OpnSenseAPIError:
            raise

    def get_interfaces(self) -> Any:
        """Attempt to fetch interface information using common OpnSense endpoints.

        Returns the first successful response.
        """
        candidates = [
            "/api/core/interfaces",
            "/api/interfaces",
            "/api/core/get_interfaces",
            "/api/system/interface",
        ]
        tried = []
        for path in candidates:
            tried.append(path)
            try:
                return self._get(path)
            except OpnSenseAPIError:
                continue
        raise OpnSenseAPIError(f"Could not fetch interfaces; tried: {tried}")

    def get_config(self) -> Any:
        """Attempt to retrieve the running configuration.

        Some OpnSense installations expose configuration via /api/core/config or
        a backup endpoint; this is best-effort and may not be available.
        """
        candidates = [
            "/api/core/config/backup",
            "/api/core/config/backup/download",
            "/api/core/config",
        ]
        tried = []
        for path in candidates:
            tried.append(path)
            try:
                return self._get(path)
            except OpnSenseAPIError:
                continue
        raise OpnSenseAPIError(f"Could not fetch configuration; tried: {tried}")

    def _find_firewall_rule(self, tracker: str) -> Optional[Dict[str, Any]]:
        """Search common firewall rule list endpoints for a rule matching tracker.

        The tracker value may be stored as 'tracker', 'created.time', 'uniqid',
        'id' or other property depending on the exporter; we attempt several
        common attributes.
        """
        candidates = [
            "/api/firewall/rule",
            "/api/firewall/filter/rule",
            "/api/filter/rule",
            "/api/firewall/rules",
        ]
        for path in candidates:
            try:
                data = self._get(path)
                # data can be dict or list depending on endpoint
                rules = None
                if isinstance(data, dict):
                    # try common keys
                    for k in ("rule", "data", "rules"):
                        if k in data and isinstance(data[k], list):
                            rules = data[k]
                            break
                    if rules is None and isinstance(data.get("rows"), list):
                        rules = data["rows"]
                elif isinstance(data, list):
                    rules = data

                if not rules:
                    continue

                for rule in rules:
                    if not isinstance(rule, dict):
                        continue
                    for key in ("tracker", "id", "uniqid", "created", "created.time"):
                        # created may be nested
                        if key in rule and str(rule.get(key)) == str(tracker):
                            rule_copy = rule.copy()
                            rule_copy["_source_path"] = path
                            return rule_copy
                        # try nested created.time
                        if key == "created.time":
                            created = rule.get("created")
                            if isinstance(created, dict) and str(created.get("time")) == str(tracker):
                                rule_copy = rule.copy()
                                rule_copy["_source_path"] = path
                                return rule_copy
            except OpnSenseAPIError:
                continue
        return None

    def _update_firewall_rule(self, source_path: str, rule_id: Any, data: Dict[str, Any]) -> Any:
        """Attempt to POST an update to a firewall rule based on the source path.

        This is heuristic – many OpnSense APIs differ. We attempt common update
        patterns and return the first successful response.
        """
        tried = []
        # Common patterns for updating a specific rule
        patterns = [
            f"{source_path}/{{id}}",
            f"{source_path}/{{id}}/update",
            f"{source_path}/update/{{id}}",
            f"{source_path}/set/{{id}}",
        ]
        for pat in patterns:
            tried.append(pat)
            path = pat.format(id=rule_id)
            try:
                return self._post(path, data=data)
            except OpnSenseAPIError:
                continue
        raise OpnSenseAPIError(f"Failed to update firewall rule {rule_id}; tried: {tried}")

    def enable_filter_rule_by_tracker(self, tracker: str) -> Any:
        """Enable a firewall rule identified by tracker (best effort).

        Finds the firewall rule and then attempts to clear a 'disabled' flag by
        posting an update. If updates are not possible the method raises an
        OpnSenseAPIError explaining which endpoints were tried.
        """
        rule = self._find_firewall_rule(tracker)
        if not rule:
            raise OpnSenseAPIError(f"Firewall rule with tracker {tracker} not found")

        source = rule.get("_source_path")
        rule_id = rule.get("id") or rule.get("uniqid") or rule.get("tracker")
        if rule_id is None:
            raise OpnSenseAPIError("Found rule but could not determine an identifier to update")

        # Build payload to clear disabled flag. Payload shape varies by API.
        payload_variants = [
            {"disabled": False},
            {"disabled": ""},
            {"disabled": None},
            {"enabled": True},
        ]

        last_err = None
        for payload in payload_variants:
            try:
                return self._update_firewall_rule(source, rule_id, payload)
            except OpnSenseAPIError as err:
                last_err = err
                continue

        raise OpnSenseAPIError(f"Failed to enable rule {tracker}: {last_err}")

    def disable_filter_rule_by_tracker(self, tracker: str) -> Any:
        """Disable a firewall rule identified by tracker (best effort).

        Symmetric to enable_filter_rule_by_tracker.
        """
        rule = self._find_firewall_rule(tracker)
        if not rule:
            raise OpnSenseAPIError(f"Firewall rule with tracker {tracker} not found")

        source = rule.get("_source_path")
        rule_id = rule.get("id") or rule.get("uniqid") or rule.get("tracker")
        if rule_id is None:
            raise OpnSenseAPIError("Found rule but could not determine an identifier to update")

        payload_variants = [
            {"disabled": True},
            {"disabled": ""},
            {"enabled": False},
        ]

        last_err = None
        for payload in payload_variants:
            try:
                return self._update_firewall_rule(source, rule_id, payload)
            except OpnSenseAPIError as err:
                last_err = err
                continue

        raise OpnSenseAPIError(f"Failed to disable rule {tracker}: {last_err}")

    # Nat rule enable/disable – look for created.time or id
    def enable_nat_rule_by_created_time(self, created_time: str) -> Any:
        candidates = ["/api/firewall/nat/port_forward", "/api/nat/port_forward", "/api/firewall/nat/rule"]
        tried = []
        for path in candidates:
            tried.append(path)
            try:
                data = self._get(path)
                rules = data if isinstance(data, list) else data.get("rule") if isinstance(data, dict) else None
                if not rules:
                    continue
                for rule in rules:
                    ct = None
                    if isinstance(rule.get("created"), dict):
                        ct = rule["created"].get("time")
                    if ct is None:
                        ct = rule.get("created.time") or rule.get("created_time")
                    if ct and str(ct) == str(created_time):
                        rule_id = rule.get("id") or rule.get("uniqid")
                        return self._update_firewall_rule(path, rule_id, {"disabled": False})
            except OpnSenseAPIError:
                continue
        raise OpnSenseAPIError(f"Could not find or enable NAT rule by created_time; tried: {tried}")

    def disable_nat_rule_by_created_time(self, created_time: str) -> Any:
        candidates = ["/api/firewall/nat/port_forward", "/api/nat/port_forward", "/api/firewall/nat/rule"]
        tried = []
        for path in candidates:
            tried.append(path)
            try:
                data = self._get(path)
                rules = data if isinstance(data, list) else data.get("rule") if isinstance(data, dict) else None
                if not rules:
                    continue
                for rule in rules:
                    ct = None
                    if isinstance(rule.get("created"), dict):
                        ct = rule["created"].get("time")
                    if ct is None:
                        ct = rule.get("created.time") or rule.get("created_time")
                    if ct and str(ct) == str(created_time):
                        rule_id = rule.get("id") or rule.get("uniqid")
                        return self._update_firewall_rule(path, rule_id, {"disabled": True})
            except OpnSenseAPIError:
                continue
        raise OpnSenseAPIError(f"Could not find or disable NAT rule by created_time; tried: {tried}")

    # Exec command is sensitive; OpnSense does not expose arbitrary command execution
    # by default. Provide a clear error and guidance.
    def exec_command(self, command: str, background: bool = False) -> Any:
        raise NotImplementedError(
            "OpnSense does not expose arbitrary command execution through the public API by default. "
            "If you need this functionality, implement a secure action plugin on the appliance or add a specific endpoint."
        )


