"""OpnSense integration migration and setup with entity registry migration."""

import json
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import device_registry as dr

from .const import DOMAIN as OPNSENSE_DOMAIN

_LOGGER = logging.getLogger(__name__)


async def _migrate_entities_and_devices(hass: HomeAssistant, old_entry, new_entry):
    """Migrate entity registry entries from old_entry to new_entry.

    This is best-effort: it updates entity registry entries (entity_id and
    config_entry_id) so entities move from pfsense.<name> -> opnsense.<name>.
    Device registry entries are enumerated and logged for manual inspection.
    """
    entity_registry = er.async_get(hass)
    device_registry = dr.async_get(hass)

    migrated_entities = []
    affected_devices = []

    # Find entities for the old config entry
    for entity in list(entity_registry.entities.values()):
        if entity.config_entry_id != old_entry.entry_id:
            continue

        old_entity_id = entity.entity_id
        if old_entity_id.startswith(f"{old_entry.domain}."):
            # Replace domain in entity_id string
            new_entity_id = old_entity_id.replace("pfsense.", "opnsense.")
        else:
            # Fallback: replace prefix if present
            new_entity_id = old_entity_id.replace("pfsense_", "opnsense_")

        try:
            entity_registry.async_update_entity(
                entity.entity_id,
                new_entity_id=new_entity_id,
                new_config_entry_id=new_entry.entry_id,
            )
            migrated_entities.append({"old": old_entity_id, "new": new_entity_id})
            _LOGGER.info("Migrated entity %s -> %s", old_entity_id, new_entity_id)
        except Exception as err:
            _LOGGER.exception("Failed to migrate entity %s: %s", old_entity_id, err)

    # Enumerate devices for manual migration guidance
    for device in dr.async_entries_for_config_entry(device_registry, old_entry.entry_id):
        affected_devices.append({"device_id": device.id, "name": device.name})

    return migrated_entities, affected_devices


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """Set up the OpnSense integration and migrate pfSense entries if present.

    This will search for existing config entries under the old 'pfsense'
    domain and create equivalent entries for 'opnsense', attempting to
    preserve data and options. The old entries will be removed after a
    successful copy. This is a best-effort migration and users should
    verify entities and automations after upgrade.
    """
    old_domain = "pfsense"
    entries = hass.config_entries.async_entries(old_domain)
    if not entries:
        return True

    _LOGGER.info("Found %d existing '%s' config entries to migrate", len(entries), old_domain)

    migration_map = {"entries": [], "entities": [], "devices": []}

    for entry in entries:
        try:
            _LOGGER.info("Migrating config entry '%s' (%s) to '%s'", entry.title, entry.entry_id, OPNSENSE_DOMAIN)
            # Create a new config entry for opnsense with same data/options
            new_entry = hass.config_entries.async_create(
                domain=OPNSENSE_DOMAIN,
                title=entry.title,
                data=entry.data,
                options=entry.options,
                source="migration",
            )

            # Migrate entities in entity registry to point to new entry
            migrated_entities, affected_devices = await _migrate_entities_and_devices(hass, entry, new_entry)

            migration_map["entries"].append({"old_entry_id": entry.entry_id, "new_entry_id": new_entry.entry_id})
            migration_map["entities"].extend(migrated_entities)
            migration_map["devices"].append({"old_entry_id": entry.entry_id, "devices": affected_devices})

            # Remove the old entry
            await hass.config_entries.async_remove(entry.entry_id)
            _LOGGER.info("Migrated and removed old entry %s", entry.entry_id)
        except Exception as err:
            _LOGGER.exception("Failed to migrate entry %s: %s", entry.entry_id, err)

    # Persist migration map to HA config directory for audit/rollback
    try:
        path = hass.config.path("opnsense_migration_map.json")
        with open(path, "w") as fh:
            json.dump(migration_map, fh, indent=2)
        _LOGGER.info("Wrote opnsense migration map to %s", path)
    except Exception as err:
        _LOGGER.exception("Failed to write migration map: %s", err)

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up OpnSense from a config entry (stub).

    The full runtime code (coordinators, entities) will be implemented
    in the opnsense package modules.
    """
    _LOGGER.debug("Setting up OpnSense entry %s", entry.entry_id)
    return True
