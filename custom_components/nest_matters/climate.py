"""Climate platform for Nest Matters integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import (
    EventStateChangedData,
    async_track_state_change_event,
)

from . import NestMattersConfigEntry
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: NestMattersConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Nest Matters climate platform."""
    data = config_entry.runtime_data

    async_add_entities(
        [
            NestMattersClimate(
                data.name,
                data.matter_entity,
                data.google_entity,
                config_entry.entry_id,
            )
        ]
    )


class NestMattersClimate(ClimateEntity):
    """Unified climate entity combining Matter and Google Nest."""

    _attr_should_poll = False
    _attr_has_entity_name = True
    _attr_name = None
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.FAN_MODE
        | ClimateEntityFeature.TURN_ON
        | ClimateEntityFeature.TURN_OFF
    )

    def __init__(
        self,
        name: str,
        matter_entity_id: str,
        google_entity_id: str,
        entry_id: str,
    ) -> None:
        """Initialize the unified climate entity."""
        self._matter_entity_id = matter_entity_id
        self._google_entity_id = google_entity_id

        self._attr_unique_id = f"{DOMAIN}_{entry_id}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry_id)},
            name=name,
            manufacturer="Google",
            model="Nest Thermostat (Unified)",
        )

        # Defaults for properties without base-class defaults.
        # These are populated from source entities in _async_update_attrs()
        # but must exist before the first state write during entity registration.
        self._attr_hvac_mode = None
        self._attr_hvac_modes = []
        self._attr_fan_mode = None
        self._attr_fan_modes = []
        self._attr_target_temperature = None
        self._attr_min_temp = 7
        self._attr_max_temp = 35
        self._attr_current_humidity = None
        self._attr_available = False

    async def async_added_to_hass(self) -> None:
        """Subscribe to source entity state changes."""
        self.async_on_remove(
            async_track_state_change_event(
                self.hass,
                [self._matter_entity_id, self._google_entity_id],
                self._handle_source_state_change,
            )
        )

        # Initial attribute population
        self._async_update_attrs()

    @callback
    def _handle_source_state_change(
        self, event: Event[EventStateChangedData]
    ) -> None:
        """Handle state changes from source entities."""
        self.async_set_context(event.context)
        self._async_update_attrs()
        self.async_write_ha_state()

    @callback
    def _async_update_attrs(self) -> None:
        """Update all cached attributes from source entity states."""
        matter_state = self.hass.states.get(self._matter_entity_id)
        google_state = self.hass.states.get(self._google_entity_id)

        # Availability: both source entities must be present and not unavailable
        self._attr_available = (
            matter_state is not None
            and matter_state.state != "unavailable"
            and google_state is not None
            and google_state.state != "unavailable"
        )

        # From Matter entity (temperature data — fast local reads, no rate limits)
        if matter_state and matter_state.attributes:
            matter_attrs = matter_state.attributes
            self._attr_current_temperature = matter_attrs.get("current_temperature")
            self._attr_target_temperature = matter_attrs.get("temperature")
            self._attr_min_temp = matter_attrs.get("min_temp", 7)
            self._attr_max_temp = matter_attrs.get("max_temp", 35)
        else:
            self._attr_current_temperature = None
            self._attr_target_temperature = None
            self._attr_min_temp = 7
            self._attr_max_temp = 35

        # From Google entity (HVAC/fan data — full feature set)
        if google_state:
            self._attr_hvac_mode = google_state.state
            if google_state.attributes:
                google_attrs = google_state.attributes
                self._attr_hvac_modes = google_attrs.get("hvac_modes", [])
                self._attr_fan_mode = google_attrs.get("fan_mode")
                self._attr_fan_modes = google_attrs.get("fan_modes", [])
                self._attr_current_humidity = google_attrs.get("current_humidity")
            else:
                self._attr_hvac_modes = []
                self._attr_fan_mode = None
                self._attr_fan_modes = []
                self._attr_current_humidity = None
        else:
            self._attr_hvac_mode = None
            self._attr_hvac_modes = []
            self._attr_fan_mode = None
            self._attr_fan_modes = []
            self._attr_current_humidity = None

    def _check_entity_available(self, entity_id: str) -> None:
        """Raise if a source entity is unavailable."""
        state = self.hass.states.get(entity_id)
        if state is None or state.state == "unavailable":
            raise HomeAssistantError(
                f"Cannot perform action: source entity {entity_id} is unavailable"
            )

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set temperature via Matter entity (avoid rate limits)."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return

        self._check_entity_available(self._matter_entity_id)

        _LOGGER.debug(
            "Setting temperature to %s via Matter entity %s",
            temperature,
            self._matter_entity_id,
        )

        await self.hass.services.async_call(
            "climate",
            "set_temperature",
            {
                "entity_id": self._matter_entity_id,
                "temperature": temperature,
            },
            blocking=True,
            context=self._context,
        )

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set HVAC mode via Google entity (full features)."""
        self._check_entity_available(self._google_entity_id)

        _LOGGER.debug(
            "Setting HVAC mode to %s via Google entity %s",
            hvac_mode,
            self._google_entity_id,
        )

        await self.hass.services.async_call(
            "climate",
            "set_hvac_mode",
            {
                "entity_id": self._google_entity_id,
                "hvac_mode": hvac_mode,
            },
            blocking=True,
            context=self._context,
        )

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        """Set fan mode via Google entity."""
        self._check_entity_available(self._google_entity_id)

        _LOGGER.debug(
            "Setting fan mode to %s via Google entity %s",
            fan_mode,
            self._google_entity_id,
        )

        await self.hass.services.async_call(
            "climate",
            "set_fan_mode",
            {
                "entity_id": self._google_entity_id,
                "fan_mode": fan_mode,
            },
            blocking=True,
            context=self._context,
        )

    async def async_turn_on(self) -> None:
        """Turn on via Google entity.

        Delegate directly to the Google Nest entity rather than using
        the base class default, which only handles the 2-mode case.
        Nest thermostats typically have 4+ HVAC modes (OFF, HEAT, COOL,
        HEAT_COOL), so the default would raise NotImplementedError.
        """
        self._check_entity_available(self._google_entity_id)

        _LOGGER.debug(
            "Turning on via Google entity %s",
            self._google_entity_id,
        )

        await self.hass.services.async_call(
            "climate",
            "turn_on",
            {"entity_id": self._google_entity_id},
            blocking=True,
            context=self._context,
        )

    async def async_turn_off(self) -> None:
        """Turn off via Google entity."""
        self._check_entity_available(self._google_entity_id)

        _LOGGER.debug(
            "Turning off via Google entity %s",
            self._google_entity_id,
        )

        await self.hass.services.async_call(
            "climate",
            "turn_off",
            {"entity_id": self._google_entity_id},
            blocking=True,
            context=self._context,
        )
