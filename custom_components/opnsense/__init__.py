"""OpnSense integration migration and setup."""

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN as OPNSENSE_DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """Set up the OpnSense integration and migrate pfSense entries if present.

    This will search for existing config entries under the old 'pfsense'
    domain and create equivalent entries for 'opnsense', attempting to
    preserve data and options. The old entries will be removed after a
    successful copy. This is a best-effort migration and users should
    verify entities and automations after upgrade.
    """
    # Migrate existing pfsense config entries to opnsense
    old_domain = "pfsense"
    entries = hass.config_entries.async_entries(old_domain)
    if not entries:
        return True

    _LOGGER.info("Found %d existing '%s' config entries to migrate", len(entries), old_domain)

    for entry in entries:
        try:
            _LOGGER.info("Migrating config entry '%s' (%s) to '%s'", entry.title, entry.entry_id, OPNSENSE_DOMAIN)
            # Create a new config entry for opnsense with same data/options
            hass.config_entries.async_create(
                domain=OPNSENSE_DOMAIN,
                title=entry.title,
                data=entry.data,
                options=entry.options,
                source="migration",
            )
            # Remove the old entry
            await hass.config_entries.async_remove(entry.entry_id)
            _LOGGER.info("Migrated and removed old entry %s", entry.entry_id)
        except Exception as err:
            _LOGGER.exception("Failed to migrate entry %s: %s", entry.entry_id, err)

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up OpnSense from a config entry (stub).

    The full runtime code (coordinators, entities) will be implemented
    in the opnsense package modules. This stub ensures the integration
    can be loaded and the migration runs on startup.
    """
    _LOGGER.debug("Setting up OpnSense entry %s", entry.entry_id)
    return True
