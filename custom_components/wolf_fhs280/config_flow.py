"""Config flow for Wolf FHS280."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import voluptuous as vol
from homeassistant.components.modbus import get_hub
from homeassistant.components.modbus.modbus import DATA_MODBUS_HUBS
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import selector
from pymodbus.exceptions import ModbusException

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
from .coordinator import BWWPModbusHub

LOGGER = logging.getLogger(__name__)


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


def _build_schema(defaults: dict[str, Any], available_hubs: list[str]) -> vol.Schema:
    hub_default = defaults.get(CONF_HUB) or (available_hubs[0] if available_hubs else DEFAULT_HUB)

    return vol.Schema(
        {
            vol.Required(CONF_NAME, default=defaults.get(CONF_NAME, DEFAULT_NAME)): str,
            vol.Required(CONF_HUB, default=hub_default): str,
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


def _available_hubs(hass) -> list[str]:
    hubs = hass.data.get(DATA_MODBUS_HUBS, {})
    return sorted(hubs.keys())


async def _async_validate_input(hass, user_input: dict[str, Any]) -> dict[str, Any]:
    """Validate hub existence and one known register read via HA modbus hub."""
    cleaned = _normalize_user_input(user_input)
    if not cleaned[CONF_HUB]:
        raise HubNotFound

    try:
        modbus_hub = get_hub(hass, cleaned[CONF_HUB])
    except KeyError as err:
        raise HubNotFound from err

    hub = BWWPModbusHub(
        hub=modbus_hub,
        hub_name=cleaned[CONF_HUB],
        slave_id=cleaned[CONF_SLAVE_ID],
    )

    try:
        await hub.async_read_register("holding", 4)
    except (OSError, asyncio.TimeoutError, ModbusException) as err:
        LOGGER.debug("Config flow connection test failed: %s", err)
        raise CannotConnect from err

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
            except CannotConnect:
                errors["base"] = "cannot_connect"
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

        return self.async_show_form(
            step_id="user",
            data_schema=_build_schema(user_input or {}, _available_hubs(self.hass)),
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
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception:
                LOGGER.exception("Unexpected error while validating options flow input")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(title="", data=user_input)

        defaults = {**self._config_entry.data, **self._config_entry.options}
        return self.async_show_form(
            step_id="init",
            data_schema=_build_schema(defaults, _available_hubs(self.hass)),
            errors=errors,
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class HubNotFound(HomeAssistantError):
    """Error to indicate selected modbus hub does not exist."""