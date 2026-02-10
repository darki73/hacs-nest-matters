"""Diagnostic sensor platform for Nest Matters integration."""
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.const import EntityCategory
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import (
    EventStateChangedData,
    async_track_state_change_event,
)

from . import NestMattersConfigEntry
from .const import DOMAIN

# (key, display name, primary source, fallback source or None)
_SOURCE_SENSORS: list[tuple[str, str, str, str | None]] = [
    ("temperature_source", "Temperature Source", "matter", "google"),
    ("hvac_source", "HVAC Source", "google", "matter"),
    ("fan_source", "Fan Source", "google", None),
]


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: NestMattersConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up diagnostic sensors for Nest Matters."""
    data = config_entry.runtime_data

    async_add_entities(
        [
            NestMattersSourceSensor(
                matter_entity_id=data.matter_entity,
                google_entity_id=data.google_entity,
                entry_id=config_entry.entry_id,
                device_name=data.name,
                sensor_key=key,
                sensor_name=name,
                primary=primary,
                fallback=fallback,
            )
            for key, name, primary, fallback in _SOURCE_SENSORS
        ]
    )


class NestMattersSourceSensor(SensorEntity):
    """Diagnostic sensor showing which source entity is active."""

    _attr_should_poll = False
    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        matter_entity_id: str,
        google_entity_id: str,
        entry_id: str,
        device_name: str,
        sensor_key: str,
        sensor_name: str,
        primary: str,
        fallback: str | None,
    ) -> None:
        """Initialize the diagnostic sensor."""
        self._matter_entity_id = matter_entity_id
        self._google_entity_id = google_entity_id
        self._primary = primary
        self._fallback = fallback

        self._attr_unique_id = f"{DOMAIN}_{entry_id}_{sensor_key}"
        self._attr_name = sensor_name
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry_id)},
        )
        self._attr_native_value: str = "unavailable"

    async def async_added_to_hass(self) -> None:
        """Subscribe to source entity state changes."""
        self.async_on_remove(
            async_track_state_change_event(
                self.hass,
                [self._matter_entity_id, self._google_entity_id],
                self._handle_source_state_change,
            )
        )
        self._async_update_value()

    @callback
    def _handle_source_state_change(
        self, event: Event[EventStateChangedData]
    ) -> None:
        """Handle state changes from source entities."""
        self._async_update_value()
        self.async_write_ha_state()

    def _is_source_available(self, source: str) -> bool:
        """Check if a named source (matter/google) is available."""
        entity_id = (
            self._matter_entity_id if source == "matter"
            else self._google_entity_id
        )
        state = self.hass.states.get(entity_id)
        return state is not None and state.state != "unavailable"

    @callback
    def _async_update_value(self) -> None:
        """Compute which source is active."""
        if self._is_source_available(self._primary):
            self._attr_native_value = self._primary
        elif self._fallback and self._is_source_available(self._fallback):
            self._attr_native_value = f"{self._fallback} (fallback)"
        else:
            self._attr_native_value = "unavailable"
