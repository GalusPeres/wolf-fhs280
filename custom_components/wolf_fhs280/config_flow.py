"""Config flow for Wolf FHS280."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import selector

from .const import (
    CONF_NAME,
    CONF_SCAN_INTERVAL,
    CONF_SLAVE_ID,
    CONF_TIMEOUT,
    DEFAULT_NAME,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_SLAVE_ID,
    DEFAULT_TIMEOUT,
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


def _build_schema(defaults: dict[str, Any]) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(CONF_NAME, default=defaults.get(CONF_NAME, DEFAULT_NAME)): str,
            vol.Required(CONF_HOST, default=defaults.get(CONF_HOST, "")): str,
            vol.Required(
                CONF_PORT, default=defaults.get(CONF_PORT, DEFAULT_PORT)
            ): _number_box(min_value=1, max_value=65535, step=1),
            vol.Required(
                CONF_SLAVE_ID, default=defaults.get(CONF_SLAVE_ID, DEFAULT_SLAVE_ID)
            ): _number_box(min_value=1, max_value=247, step=1),
            vol.Required(
                CONF_SCAN_INTERVAL,
                default=defaults.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
            ): _number_box(min_value=1, max_value=3600, step=1),
            vol.Required(
                CONF_TIMEOUT, default=defaults.get(CONF_TIMEOUT, DEFAULT_TIMEOUT)
            ): _number_box(min_value=0.5, max_value=60, step=0.5),
        }
    )


def _normalize_user_input(user_input: dict[str, Any]) -> dict[str, Any]:
    """Cast selector values into the expected runtime types."""
    return {
        **user_input,
        CONF_NAME: str(user_input[CONF_NAME]).strip(),
        CONF_HOST: str(user_input[CONF_HOST]).strip(),
        CONF_PORT: int(user_input[CONF_PORT]),
        CONF_SLAVE_ID: int(user_input[CONF_SLAVE_ID]),
        CONF_SCAN_INTERVAL: int(user_input[CONF_SCAN_INTERVAL]),
        CONF_TIMEOUT: float(user_input[CONF_TIMEOUT]),
    }


async def _async_validate_input(user_input: dict[str, Any]) -> dict[str, Any]:
    """Validate connection and one known register read."""
    cleaned = _normalize_user_input(user_input)
    if not cleaned[CONF_HOST]:
        raise CannotConnect

    hub = BWWPModbusHub(
        host=cleaned[CONF_HOST],
        port=cleaned[CONF_PORT],
        slave_id=cleaned[CONF_SLAVE_ID],
        timeout=cleaned[CONF_TIMEOUT],
    )
    try:
        await hub.async_read_register("holding", 4)
    except (OSError, asyncio.TimeoutError, Exception) as err:
        raise CannotConnect from err
    finally:
        await hub.async_close()

    return cleaned


class BWWPConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle config flow for Wolf FHS280."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                user_input = await _async_validate_input(user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception:
                LOGGER.exception("Unexpected error while validating config flow input")
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(
                    f"{user_input[CONF_HOST]}:{user_input[CONF_PORT]}:{user_input[CONF_SLAVE_ID]}"
                )
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=user_input[CONF_NAME], data=user_input
                )

        return self.async_show_form(
            step_id="user",
            data_schema=_build_schema(user_input or {}),
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
                user_input = await _async_validate_input(user_input)
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
            data_schema=_build_schema(defaults),
            errors=errors,
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""