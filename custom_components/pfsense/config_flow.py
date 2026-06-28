*** Begin Patch
*** Update File: custom_components/pfsense/config_flow.py
@@
-from .pypfsense import Client
+from .pypfsense_opnsense import probe_opnsense, OpnSenseClient
@@
-    client = Client(url, username, password, {"verify_ssl": verify_ssl})
-    system_info = await self.hass.async_add_executor_job(
-        client.get_system_info
-    )
-    if name is None:
-        name = "{}.{}".format(
-            system_info["hostname"], system_info["domain"]
-        )
+    # validate via OpnSense API probe (async)
+    try:
+        await probe_opnsense(url, username, password, verify_ssl=verify_ssl)
+    except Exception as err:
+        _LOGGER.debug("OpnSense API probe failed: %s", err)
+        # translate errors to flow-friendly responses
+        errors = {"base": "cannot_connect"}
+        return self.async_show_form(step_id="user", data=user_input, errors=errors)
+
+    # If probe succeeded, build a client for later use (constructed in setup)
+    name = name or f"{url}"
*** End Patch
