"""Config flow for Wolf FHS280."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import selector

from .const import (
    CONF_HUB,
    CONF_NAME,
    CONF_SCAN_INTERVAL,
    CONF_SLAVE_ID,
    DEFAULT_HUB,
    DEFAULT_NAME,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_SLAVE_ID,
    DOMAIN,
)

LOGGER = logging.getLogger(__name__)

LEGACY_CONF_HUB = "hub"


def _number_box(
    *, min_value: float, max_value: float, step: float
) -> selector.NumberSelector:
    """Build a numeric textbox selector (no slider)."""
    return selector.NumberSelector(
        selector.NumberSelectorConfig(
            min=min_value,
            max=max_value,
            step=step,
            mode=selector.NumberSelectorMode.BOX,
        )
    )


def _with_legacy_defaults(defaults: dict[str, Any]) -> dict[str, Any]:
    """Map old options/data to current defaults where possible."""
    merged = dict(defaults)
    legacy_hub = merged.get(LEGACY_CONF_HUB)
    if not merged.get(CONF_HUB) and legacy_hub:
        merged[CONF_HUB] = str(legacy_hub)
    return merged


def _build_schema(defaults: dict[str, Any]) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(CONF_NAME, default=defaults.get(CONF_NAME, DEFAULT_NAME)): str,
            vol.Required(CONF_HUB, default=defaults.get(CONF_HUB, DEFAULT_HUB)): str,
            vol.Required(
                CONF_SLAVE_ID, default=defaults.get(CONF_SLAVE_ID, DEFAULT_SLAVE_ID)
            ): _number_box(min_value=1, max_value=247, step=1),
            vol.Required(
                CONF_SCAN_INTERVAL,
                default=defaults.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
            ): _number_box(min_value=1, max_value=3600, step=1),
        }
    )


def _normalize_user_input(user_input: dict[str, Any]) -> dict[str, Any]:
    """Cast selector values into the expected runtime types."""
    return {
        **user_input,
        CONF_NAME: str(user_input[CONF_NAME]).strip(),
        CONF_HUB: str(user_input[CONF_HUB]).strip(),
        CONF_SLAVE_ID: int(user_input[CONF_SLAVE_ID]),
        CONF_SCAN_INTERVAL: int(user_input[CONF_SCAN_INTERVAL]),
    }


async def _async_validate_hub_exists(hass, hub_name: str) -> None:
    """Validate that the named Home Assistant Modbus hub exists."""
    if not hub_name:
        raise HubNotFound

    try:
        from homeassistant.components.modbus import get_hub

        get_hub(hass, hub_name)
    except Exception as err:
        LOGGER.debug("Configured modbus hub '%s' not found: %s", hub_name, err)
        raise HubNotFound from err


async def _async_validate_input(hass, user_input: dict[str, Any]) -> dict[str, Any]:
    """Validate config flow input."""
    cleaned = _normalize_user_input(user_input)
    await _async_validate_hub_exists(hass, cleaned[CONF_HUB])
    return cleaned


class BWWPConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle config flow for Wolf FHS280."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                user_input = await _async_validate_input(self.hass, user_input)
            except HubNotFound:
                errors["base"] = "hub_not_found"
            except Exception:
                LOGGER.exception("Unexpected error while validating config flow input")
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(
                    f"{user_input[CONF_HUB]}:{user_input[CONF_SLAVE_ID]}"
                )
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=user_input[CONF_NAME], data=user_input
                )

        defaults = _with_legacy_defaults(user_input or {})
        return self.async_show_form(
            step_id="user",
            data_schema=_build_schema(defaults),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        return BWWPOptionsFlow(config_entry)


class BWWPOptionsFlow(config_entries.OptionsFlow):
    """Handle options for an existing BWWP entry."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                user_input = await _async_validate_input(self.hass, user_input)
            except HubNotFound:
                errors["base"] = "hub_not_found"
            except Exception:
                LOGGER.exception("Unexpected error while validating options flow input")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(title="", data=user_input)

        defaults = {**self._config_entry.data, **self._config_entry.options}
        defaults = _with_legacy_defaults(defaults)
        return self.async_show_form(
            step_id="init",
            data_schema=_build_schema(defaults),
            errors=errors,
        )


class HubNotFound(HomeAssistantError):
    """Error to indicate configured modbus hub does not exist."""
