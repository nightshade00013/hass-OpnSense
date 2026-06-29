"""Converted switch module for OpnSense (partial conversion)."""

from __future__ import annotations

import logging

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback

from .const import DOMAIN
from . import CoordinatorEntityManager, OpnSenseEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    """Set up OpnSense switches (placeholder).

    This module contains a partial conversion of the pfSense switch logic to
    OpnSense. It should be extended to match all original functionality.
    """
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    # For now, register no switches and rely on CoordinatorEntityManager
    cem = CoordinatorEntityManager(hass, coordinator, entry, None, async_add_entities)
    cem.process_entities()

    return True
