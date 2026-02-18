"""Wolf FHS280 custom integration."""

from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import (
    CONF_HUB,
    CONF_SCAN_INTERVAL,
    CONF_SLAVE_ID,
    DEFAULT_HUB,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_SLAVE_ID,
    DOMAIN,
    PLATFORMS,
)
from .coordinator import BWWPDataUpdateCoordinator, BWWPSharedModbusHub
LOGGER = logging.getLogger(__name__)


@dataclass
class RuntimeData:
    """Runtime objects for one config entry."""

    hub: Any
    coordinator: BWWPDataUpdateCoordinator


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up BWWP from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    hub_name = str(_entry_value(entry, CONF_HUB, DEFAULT_HUB)).strip()
    if not hub_name:
        raise ConfigEntryNotReady(
            "No Modbus hub configured. Set a hub name in integration options."
        )

    slave_id = int(_entry_value(entry, CONF_SLAVE_ID, DEFAULT_SLAVE_ID))
    scan_interval = int(
        _entry_value(entry, CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    )

    try:
        from homeassistant.components.modbus import get_hub

        modbus_hub = get_hub(hass, hub_name)
    except Exception as err:
        raise ConfigEntryNotReady(
            f"Modbus hub '{hub_name}' not found. Configure it in configuration.yaml under modbus:."
        ) from err

    hub = BWWPSharedModbusHub(modbus_hub, hub_name, slave_id)

    coordinator = BWWPDataUpdateCoordinator(
        hass=hass,
        hub=hub,
        scan_interval_seconds=scan_interval,
    )
    hass.data[DOMAIN][entry.entry_id] = RuntimeData(hub=hub, coordinator=coordinator)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    # Do not block Home Assistant startup on first Modbus poll.
    hass.async_create_task(coordinator.async_refresh())
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if not unload_ok:
        return False

    runtime: RuntimeData = hass.data[DOMAIN].pop(entry.entry_id)
    await runtime.hub.async_close()

    if not hass.data[DOMAIN]:
        hass.data.pop(DOMAIN)

    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload entry when options change."""
    await hass.config_entries.async_reload(entry.entry_id)


def _entry_value(entry: ConfigEntry, key: str, default=None):
    """Read key from options first, then fallback to entry data."""
    return entry.options.get(key, entry.data.get(key, default))
