"""Services and helpers for OpnSense."""

import logging
from typing import Any

from homeassistant.core import HomeAssistant

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


def _get_pfsense_client(hass: HomeAssistant, entry_id: str):
    """Helper to fetch the client object for an entry. Backwards-compatible name kept."""
    return hass.data[DOMAIN][entry_id].get("opnsense_client")


async def async_setup_services(hass: HomeAssistant) -> None:
    """Register services for the OpnSense integration."""
    # Note: Older pfsense service names are intentionally not registered to
    # avoid namespace collision; this integration uses opnsense.<service>.
    # Users must update automations accordingly.
    _LOGGER.debug("Setting up OpnSense services")
