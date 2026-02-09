"""The Nest Matters integration."""
from __future__ import annotations

import logging
from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant

from .const import PLATFORMS

_LOGGER = logging.getLogger(__name__)


@dataclass
class NestMattersData:
    """Runtime data for Nest Matters integration."""

    matter_entity: str
    google_entity: str
    name: str


type NestMattersConfigEntry = ConfigEntry[NestMattersData]


async def async_setup_entry(hass: HomeAssistant, entry: NestMattersConfigEntry) -> bool:
    """Set up Nest Matters from a config entry."""
    _LOGGER.debug("Setting up Nest Matters integration")

    entry.runtime_data = NestMattersData(
        matter_entity=entry.data["matter_entity"],
        google_entity=entry.data["google_entity"],
        name=entry.options.get(CONF_NAME, entry.data.get(CONF_NAME, "Unified Thermostat")),
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: NestMattersConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.debug("Unloading Nest Matters integration")

    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
