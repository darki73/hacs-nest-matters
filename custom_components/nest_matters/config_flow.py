"""Config flow for Nest Matters integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult, OptionsFlowWithReload
from homeassistant.const import CONF_NAME
from homeassistant.core import callback
from homeassistant.helpers import entity_registry as er, selector

from .const import (
    CONF_GOOGLE_ENTITY,
    CONF_MATTER_ENTITY,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


class NestMattersConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Nest Matters."""

    VERSION = 1
    MINOR_VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._discovered_pairs: list[dict[str, str]] = []

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        # Try to discover thermostat pairs automatically
        self._discovered_pairs = await self._discover_thermostat_pairs()

        if self._discovered_pairs:
            return await self.async_step_discovery()
        return await self.async_step_manual()

    async def async_step_discovery(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle auto-discovery step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            selected_option = user_input.get("selected_option")

            # User chose manual setup
            if selected_option == "manual":
                return await self.async_step_manual()

            # User selected a specific pair
            if selected_option is not None:
                try:
                    pair_index = int(selected_option)
                    if 0 <= pair_index < len(self._discovered_pairs):
                        pair = self._discovered_pairs[pair_index]
                        return await self._create_entry_from_pair(pair)
                except (ValueError, IndexError):
                    errors["base"] = "invalid_selection"

        # Show discovery options
        discovery_options = []
        for i, pair in enumerate(self._discovered_pairs):
            discovery_options.append({
                "value": str(i),
                "label": f"{pair['name']} ({pair['matter']} + {pair['google']})"
            })

        # Add manual setup as an option in the main selector
        discovery_options.append({
            "value": "manual",
            "label": "Configure Manually Instead"
        })

        schema = vol.Schema({
            vol.Required("selected_option"): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=discovery_options
                )
            ),
        })

        return self.async_show_form(
            step_id="discovery",
            data_schema=schema,
            errors=errors,
            description_placeholders={
                "count": str(len(self._discovered_pairs))
            },
        )

    async def async_step_manual(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle manual configuration step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Validate the input
            errors = await self._validate_input(user_input)

            if not errors:
                # Check if already configured
                unique_id = f"{user_input[CONF_MATTER_ENTITY]}_{user_input[CONF_GOOGLE_ENTITY]}"
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=user_input[CONF_NAME],
                    data=user_input,
                )

        # Get available climate entities
        climate_entities = await self._get_climate_entities()

        if not climate_entities:
            return self.async_abort(reason="no_entities")

        schema = vol.Schema({
            vol.Required(CONF_NAME, default="Unified Thermostat"): str,
            vol.Required(CONF_MATTER_ENTITY): selector.EntitySelector(
                selector.EntitySelectorConfig(
                    domain="climate",
                    include_entities=climate_entities,
                )
            ),
            vol.Required(CONF_GOOGLE_ENTITY): selector.EntitySelector(
                selector.EntitySelectorConfig(
                    domain="climate",
                    include_entities=climate_entities,
                )
            ),
        })

        return self.async_show_form(
            step_id="manual",
            data_schema=schema,
            errors=errors,
        )

    async def _discover_thermostat_pairs(self) -> list[dict[str, str]]:
        """Discover potential thermostat pairs automatically."""
        climate_entities = await self._get_climate_entities()

        # Look for patterns: *_matter and corresponding base entity
        matter_entities = [e for e in climate_entities if "_matter" in e]
        pairs = []

        for matter_entity in matter_entities:
            # Try to find corresponding Google entity
            base_name = matter_entity.replace("_matter", "")
            if base_name in climate_entities:
                # Check if this pair is already configured
                unique_id = f"{matter_entity}_{base_name}"
                if not self._is_already_configured(unique_id):
                    # Extract room name for display
                    room_name = base_name.replace("climate.", "").replace("_", " ").title()
                    pairs.append({
                        "name": room_name,
                        "matter": matter_entity,
                        "google": base_name,
                    })

        _LOGGER.debug("Discovered %d available thermostat pairs: %s", len(pairs), pairs)
        return pairs

    def _is_already_configured(self, unique_id: str) -> bool:
        """Check if a unique_id is already configured."""
        existing_entries = self._async_current_entries()
        return any(entry.unique_id == unique_id for entry in existing_entries)

    async def _get_climate_entities(self) -> list[str]:
        """Get all available climate entities."""
        entity_registry = er.async_get(self.hass)
        climate_entities = []

        for entity in entity_registry.entities.values():
            if entity.domain == "climate":
                climate_entities.append(entity.entity_id)

        # Also add entities from current states (for entities not in registry)
        for entity_id in self.hass.states.async_entity_ids("climate"):
            if entity_id not in climate_entities:
                climate_entities.append(entity_id)

        return sorted(climate_entities)

    async def _validate_input(self, user_input: dict[str, Any]) -> dict[str, str]:
        """Validate user input."""
        errors = {}

        matter_entity = user_input[CONF_MATTER_ENTITY]
        google_entity = user_input[CONF_GOOGLE_ENTITY]

        # Check if entities are the same
        if matter_entity == google_entity:
            errors["base"] = "same_entity"
            return errors

        # Check if entities exist and are climate entities
        for entity_id, conf_key in [
            (matter_entity, CONF_MATTER_ENTITY),
            (google_entity, CONF_GOOGLE_ENTITY),
        ]:
            state = self.hass.states.get(entity_id)
            if not state:
                errors[conf_key] = "invalid_entity"
                continue

            if state.domain != "climate":
                errors[conf_key] = "entity_not_climate"
                continue

            if state.state == "unavailable":
                errors[conf_key] = "entity_unavailable"

        return errors

    async def _create_entry_from_pair(self, pair: dict[str, str]) -> ConfigFlowResult:
        """Create config entry from discovered pair."""
        config_data = {
            CONF_NAME: f"{pair['name']} Unified",
            CONF_MATTER_ENTITY: pair["matter"],
            CONF_GOOGLE_ENTITY: pair["google"],
        }

        # Set unique ID and check if already configured
        unique_id = f"{pair['matter']}_{pair['google']}"
        await self.async_set_unique_id(unique_id)
        self._abort_if_unique_id_configured()

        return self.async_create_entry(
            title=config_data[CONF_NAME],
            data=config_data,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> OptionsFlowHandler:
        """Get options flow."""
        return OptionsFlowHandler()


class OptionsFlowHandler(OptionsFlowWithReload):
    """Handle options flow with automatic reload on change."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle options flow."""
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        schema = vol.Schema({
            vol.Optional(
                CONF_NAME,
                default=self.config_entry.options.get(
                    CONF_NAME,
                    self.config_entry.data.get(CONF_NAME, ""),
                ),
            ): str,
        })

        return self.async_show_form(
            step_id="init",
            data_schema=schema,
        )
