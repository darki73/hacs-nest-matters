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

_BASE_FEATURES = (
    ClimateEntityFeature.TARGET_TEMPERATURE
    | ClimateEntityFeature.TURN_ON
    | ClimateEntityFeature.TURN_OFF
)


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
    """Unified climate entity combining Matter and Google Nest.

    Implements full failover between source entities:
    - Temperature: prefer Matter (local, fast), fall back to Google
    - HVAC mode: prefer Google (full features), fall back to Matter
    - Fan/humidity: Google only (no Matter equivalent)
    - Supported features: FAN_MODE toggled dynamically based on Google availability
    - Availability: requires at least one source entity to be reachable
    """

    _attr_should_poll = False
    _attr_has_entity_name = True
    _attr_name = None
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_supported_features = _BASE_FEATURES | ClimateEntityFeature.FAN_MODE

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
        # Source entity state attributes contain temperatures already converted
        # to the HA system unit. Declare the same unit to prevent
        # double-conversion (e.g. treating 72°F as 72°C → 161.6°F).
        self._attr_temperature_unit = self.hass.config.units.temperature_unit

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

    def _is_entity_available(self, entity_id: str) -> bool:
        """Check if a source entity is available."""
        state = self.hass.states.get(entity_id)
        return state is not None and state.state != "unavailable"

    @callback
    def _async_update_attrs(self) -> None:
        """Update all cached attributes from source entity states.

        Implements failover: prefers the primary source for each data category,
        falls back to the other source when the primary is unavailable.
        """
        matter_state = self.hass.states.get(self._matter_entity_id)
        google_state = self.hass.states.get(self._google_entity_id)

        matter_available = (
            matter_state is not None and matter_state.state != "unavailable"
        )
        google_available = (
            google_state is not None and google_state.state != "unavailable"
        )

        self._attr_available = matter_available or google_available

        # --- Temperature: prefer Matter (local, fast), fall back to Google ---
        if matter_available and matter_state.attributes:
            matter_attrs = matter_state.attributes
            self._attr_current_temperature = matter_attrs.get("current_temperature")
            self._attr_target_temperature = matter_attrs.get("temperature")
            self._attr_min_temp = matter_attrs.get("min_temp", 7)
            self._attr_max_temp = matter_attrs.get("max_temp", 35)
        elif google_available and google_state.attributes:
            google_attrs = google_state.attributes
            self._attr_current_temperature = google_attrs.get("current_temperature")
            self._attr_target_temperature = google_attrs.get("temperature")
            self._attr_min_temp = google_attrs.get("min_temp", 7)
            self._attr_max_temp = google_attrs.get("max_temp", 35)

        # --- HVAC mode: prefer Google (full features), fall back to Matter ---
        if google_available and google_state.state:
            self._attr_hvac_mode = google_state.state
            if google_state.attributes:
                self._attr_hvac_modes = google_state.attributes.get(
                    "hvac_modes", []
                )
        elif matter_available and matter_state.state:
            self._attr_hvac_mode = matter_state.state
            if matter_state.attributes:
                self._attr_hvac_modes = matter_state.attributes.get(
                    "hvac_modes", []
                )

        # --- Fan / humidity: Google only (no Matter equivalent) ---
        if google_available and google_state.attributes:
            google_attrs = google_state.attributes
            self._attr_fan_mode = google_attrs.get("fan_mode")
            self._attr_fan_modes = google_attrs.get("fan_modes", [])
            self._attr_current_humidity = google_attrs.get("current_humidity")

        # --- Dynamic features: toggle FAN_MODE based on Google availability ---
        if google_available:
            self._attr_supported_features = (
                _BASE_FEATURES | ClimateEntityFeature.FAN_MODE
            )
        else:
            self._attr_supported_features = _BASE_FEATURES

    async def _async_call_service(
        self,
        service: str,
        data: dict[str, Any],
        primary_entity_id: str,
        fallback_entity_id: str,
    ) -> None:
        """Call a climate service with failover between source entities."""
        if self._is_entity_available(primary_entity_id):
            target_id = primary_entity_id
        elif self._is_entity_available(fallback_entity_id):
            _LOGGER.info(
                "Primary entity %s unavailable for %s, falling back to %s",
                primary_entity_id,
                service,
                fallback_entity_id,
            )
            target_id = fallback_entity_id
        else:
            raise HomeAssistantError(
                f"Cannot {service}: both source entities are unavailable"
            )

        data["entity_id"] = target_id
        await self.hass.services.async_call(
            "climate",
            service,
            data,
            blocking=True,
            context=self._context,
        )

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set temperature — prefer Matter, fall back to Google."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return

        await self._async_call_service(
            "set_temperature",
            {"temperature": temperature},
            self._matter_entity_id,
            self._google_entity_id,
        )

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set HVAC mode — prefer Google, fall back to Matter."""
        await self._async_call_service(
            "set_hvac_mode",
            {"hvac_mode": hvac_mode},
            self._google_entity_id,
            self._matter_entity_id,
        )

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        """Set fan mode — Google only (no Matter equivalent)."""
        if not self._is_entity_available(self._google_entity_id):
            raise HomeAssistantError(
                "Cannot set fan mode: Google Nest entity is unavailable"
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
        """Turn on — prefer Google, fall back to Matter."""
        await self._async_call_service(
            "turn_on",
            {},
            self._google_entity_id,
            self._matter_entity_id,
        )

    async def async_turn_off(self) -> None:
        """Turn off — prefer Google, fall back to Matter."""
        await self._async_call_service(
            "turn_off",
            {},
            self._google_entity_id,
            self._matter_entity_id,
        )
