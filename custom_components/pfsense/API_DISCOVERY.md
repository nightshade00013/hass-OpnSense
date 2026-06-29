# OPNsense API discovery and samples

This file documents the API endpoints discovered and validated against an OPNsense instance (examples used with curl -k -u "KEY":"SECRET" http://HOST:PORT). The content below contains endpoint paths and representative response snippets captured during testing. Keep secrets out of these examples; UUIDs, IDs, created timestamps are preserved.

## How to reproduce
- Use the same key/secret authentication pair that worked for `/api/core/firmware/status`.
- Replace HOST:PORT and KEY/SECRET as needed.
- Many endpoints return JSON; some return CSV and one is server‑sent events (SSE).

---

## Endpoints and examples

### 1) Firmware status
GET /api/core/firmware/status

Example response (truncated):

{"api_version":"2","connection":"ok","os_version":"FreeBSD 14.3-RELEASE-p15","product_version":"26.1.10","status":"none","status_msg":"There are no updates available on the selected mirror.","product":{...}}

curl example:
```
curl -k -u "KEY":"SECRET" http://HOST_IP:PORT/api/core/firmware/status
```

---

### 2) Firewall rules (CSV download)
GET /api/firewall/filter/download_rules

This returns a CSV with a header. The first column is the rule UUID and the second column is an enabled flag (1 = enabled). The header fields include "uuid;enabled;...;description".

Sample rows (CSV excerpt):
```
@uuid;enabled;statetype;state-policy;sequence;action;...;description
31018a5d-df82-43f4-bb53-a8e1b818d7b4;1;keep;;1;pass;...;;
7e47a75e-f135-4f2f-a3b8-d28776867ac3;1;keep;;11;pass;...;;
760c7222-0b64-4a07-9e9d-dc869876289c;1;keep;;21;pass;...;"WAN - Inbound WireGuard VPN Tunnel"
```

curl example:
```
curl -k -u "KEY":"SECRET" http://HOST_IP:PORT/api/firewall/filter/download_rules
```

Notes: parse the header to map values to fields; UUID is canonical identifier.

---

### 3) Dashboard
GET /api/core/dashboard/get_dashboard

Returns widget/module metadata and configured widgets.

Sample (truncated):
```
{"modules":[{"id":"caddydomain","module":"CaddyDomain.js","link":"/ui/caddy/reverse_proxy",...}],"dashboard":{"widgets":[{"id":"cpu","minW":2,...}],"layouts":{...}}}
```

curl example:
```
curl -k -u "KEY":"SECRET" http://HOST_IP:PORT/api/core/dashboard/get_dashboard
```

---

### 4) hassync / hasync services
GET /api/core/hasync_status/services

Sample response when empty:
```
{"total":0,"rowCount":0,"current":1,"rows":[]}
```

---

### 5) System status
GET /api/core/system/status

Sample response:
```
{"metadata":{"system":{"status":2,"message":"No pending messages","title":"System"},"translations":{...},"subsystems":[]}}
```

---

### 6) Tunables
GET /api/core/tunables/get

Returns a JSON object keyed by UUID. Each entry contains fields like: tunable, value, descr, default_value, type.

Sample entry (truncated):
```
{"sysctl":{"item":{"449ebd67-49bb-43ef-9d79-81a426ff5705":{"tunable":"net.inet.ip.portrange.first","value":"","descr":"Set the ephemeral port range to be lower.","default_value":"1024","type":"w"}, ...}}}
```

curl example:
```
curl -k -u "KEY":"SECRET" http://HOST_IP:PORT/api/core/tunables/get
```

---

### 7) Cron jobs
GET /api/cron/settings/get

Returns cron jobs keyed by UUID with schedule and available commands.

Sample (truncated):
```
{"job":{"jobs":{"2e6852e3-...":{"origin":"IDS","enabled":"1","minutes":"0","hours":"2","command":{"ids update":{"value":"Update and reload intrusion detection rules","selected":1},...},"description":"ids rule updates"}, ...}}}
```

---

### 8) Diagnostics — activity / top
GET /api/diagnostics/activity/get_activity

Returns arrays of header strings and a "details" list with processes and stats (similar to top output).

---

### 9) CPU type
GET /api/diagnostics/cpu_usage/get_c_p_u_type

Response example:
```
["Intel(R) Xeon(R) CPU E3-1226 v3 @ 3.30GHz (4 cores, 4 threads)"]
```

---

### 10) CPU usage stream (SSE)
GET /api/diagnostics/cpu_usage/stream

This is a Server-Sent Events (SSE) endpoint. Example event form:
```
event: message
data: {"total":4,"user":3,"nice":0,"sys":1,"intr":0,"idle":96}
```

Consume by reading SSE lines and parsing JSON from lines that start with `data:`.

---

### 11) DNS diagnostic (POST)
POST /api/diagnostics/dns_diagnostics/set

Payload example:
```
{"dns":{"settings":{"hostname":"www.google.com","server":""}}}
```

Response sample (truncated):
```
{"result":"ok","response":{"A":{"answers":["www.google.com.\t297\tIN\tA\t142.251.151.119",...],"query_time":"8 msec","server":"1.1.1.1"},"AAAA":{...}}}
```

curl example:
```
curl -k -u "KEY":"SECRET" --json '{"dns":{"settings":{"hostname":"www.google.com","server":""}}}' http://HOST_IP:PORT/api/diagnostics/dns_diagnostics/set
```

This is a safe, non‑destructive diagnostic POST and can be added as a helper in the client.

---

## Notes about mutating operations

Read-only discovery is well-covered above. To implement safe mutating operations (enable/disable firewall rules, toggle NAT rules, kill states, service control, WOL, set default gateway) we still need exact UI-captured XHR requests showing the URL, HTTP method, and payload the web UI uses. The UI reliably calls the correct API controllers; capturing one example per mutating action (DevTools → Network → XHR → Copy as cURL) is enough for implementation.

Priority to capture from the UI (recommended):
- Firewall rule toggle (enable/disable) — highest priority
- NAT port forward toggle (enable/disable)
- Kill/reset state table action
- Service start/stop/restart
- Wake-on-LAN action
- Set default gateway

If you provide the "Copy as cURL" text for each action, the client implementation can mirror the UI exactly (including savepoint/apply logic) and be safe.

---

## What I (the integration) will add next
- Read-only client helpers to call the endpoints above and return parsed results.
  - Examples: get_firmware_status(), get_firewall_rules_downloaded() (CSV parser -> list[dict]), get_tunables(), get_cron_jobs(), get_dashboard(), get_activity(), get_cpu_type(), stream_cpu_usage(callback), run_dns_diagnostic(hostname, server)
- A small CSV header-to-dict parser for `download_rules` to return rule dicts with keys: uuid, enabled, sequence, action, interface, description, etc.
- Unit tests that mock the captured responses and verify parsing behavior.

If you want, I will now open a PR with the read-only client changes (new helpers + tests) and a follow-up PR for mutating actions once you provide UI-captured toggle requests.

---

Files added/updated to repository:
- custom_components/pfsense/API_DISCOVERY.md (this file)

