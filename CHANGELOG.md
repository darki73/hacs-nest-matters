# Changelog

## [1.3.0] - 2026-02-10
### Added
- Source routing attributes (`temperature_source`, `hvac_source`, `fan_source`) exposed via climate entity state attributes
- Diagnostic sensor entities for source routing — appear in the device's Diagnostic section, showing which source is active for temperature, HVAC, and fan data (e.g. `matter`, `google (fallback)`, `unavailable`)

## [1.2.1] - 2026-02-10
### Fixed
- Fixed entity registration failure caused by missing class-level `_attr_temperature_unit` default — HA's `capability_attributes` reads `temperature_unit` before `async_added_to_hass` runs

## [1.2.0] - 2026-02-10
### Added
- Full failover between source entities — temperature reads fall back from Matter to Google, HVAC/fan control falls back from Google to Matter
- Dynamic feature toggling — `FAN_MODE` is removed from supported features when Google is unavailable and restored when it recovers
- Shared `_async_call_service` helper with automatic primary/fallback routing and logging

### Changed
- Availability now requires only one source entity (was both) — entity stays functional during single-source outages
- Service calls (`set_temperature`, `set_hvac_mode`, `turn_on`, `turn_off`) now automatically fail over to the other source entity instead of raising immediately

## [1.1.1] - 2026-02-10
### Fixed
- Fixed temperature unit double-conversion for Fahrenheit users — entity now reads the HA system's configured unit instead of hardcoding Celsius (fixes #1)

## [1.1.0] - 2026-02-09
### Changed
- Updated for Home Assistant 2026.2.1 compatibility
- Migrated to `runtime_data` pattern (replaces `hass.data[DOMAIN]`)
- Migrated to `ConfigFlowResult` (replaces deprecated `FlowResult`)
- Options flow now uses `OptionsFlowWithReload` for automatic reload on change
- Replaced per-property `hass.states.get()` calls with atomic `_attr_*` caching
- Entity is now push-based (`should_poll = False`) with event-driven state updates
- All service calls now use `blocking=True` and propagate context for logbook attribution

### Added
- Proper device registry integration (`DeviceInfo`, `has_entity_name`)
- `TURN_ON` / `TURN_OFF` feature flags with explicit handlers (required since HA 2025.1+)
- Availability guards on all service calls — raises `HomeAssistantError` if source entity is unavailable
- Context propagation for logbook and trace attribution

### Fixed
- Entity registration failure ("This device has no entities") caused by missing `_attr_*` defaults
- `async_turn_on` raising `NotImplementedError` for thermostats with 4+ HVAC modes
- Listener lifecycle — replaced manual cleanup with `async_on_remove()`
- Options flow now correctly stores name in `entry.options` instead of mutating `entry.data`

### Removed
- Unused constants (`DEFAULT_TEMP_SOURCE`, `DEFAULT_MODE_SOURCE`, `DEFAULT_FAN_SOURCE`, etc.)
- Invalid `icon` field from `manifest.json`

## [1.0.0] - 2025-07-15
### Added
- Initial release
- Auto-discovery of Matter + Google Nest thermostat pairs
- Unified climate entity with intelligent routing
- Temperature control via Matter (no rate limits)
- HVAC/fan control via Google Nest (full features)
- Web UI configuration (no YAML required)
- Translations support