# Repository renamed for OpnSense integration

This repository has been converted from the original pfSense integration to target OpnSense.

Notes:
- The old integration folder custom_components/pfsense has been left in this branch as an archive.
- The new integration lives at custom_components/opnsense and uses domain "opnsense".
- A best-effort migration is performed at startup: existing config entries under domain "pfsense" are copied to new "opnsense" entries and the old entries are removed.

After verifying the new integration works, you may safely remove custom_components/pfsense from your Home Assistant custom_components directory.
