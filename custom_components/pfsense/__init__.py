*** Begin Patch
*** Update File: custom_components/pfsense/__init__.py
@@
-    client = pfSenseClient(url, username, password, {"verify_ssl": verify_ssl})
-    data = PfSenseData(client, entry, hass)
+    # Construct OpnSense API client
+    client = OpnSenseClient(url, username, password, verify_ssl=verify_ssl)
+    # Validate API presence
+    await client.detect_api()
+    data = PfSenseData(client, entry, hass)
*** End Patch
