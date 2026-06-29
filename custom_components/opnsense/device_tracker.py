"""Converted device_tracker module for OpnSense (partial conversion)."""

from __future__ import annotations

import logging

from homeassistant.components.device_tracker import SourceType
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from . import CoordinatorEntityManager, OpnSenseEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    """Set up OpnSense device tracker (placeholder).

    Partial conversion; please test in staging.
    """
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    cem = CoordinatorEntityManager(hass, coordinator, entry, None, async_add_entities)
    cem.process_entities()

    return True
