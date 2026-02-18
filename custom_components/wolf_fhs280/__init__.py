"""Wolf FHS280 custom integration."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant

from .const import (
    CONF_SCAN_INTERVAL,
    CONF_SLAVE_ID,
    CONF_TIMEOUT,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_SLAVE_ID,
    DEFAULT_TIMEOUT,
    DOMAIN,
    PLATFORMS,
)
from .coordinator import BWWPDataUpdateCoordinator, BWWPModbusHub


@dataclass
class RuntimeData:
    """Runtime objects for one config entry."""

    hub: BWWPModbusHub
    coordinator: BWWPDataUpdateCoordinator


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up BWWP from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    host = _entry_value(entry, CONF_HOST)
    port = int(_entry_value(entry, CONF_PORT, DEFAULT_PORT))
    slave_id = int(_entry_value(entry, CONF_SLAVE_ID, DEFAULT_SLAVE_ID))
    timeout = float(_entry_value(entry, CONF_TIMEOUT, DEFAULT_TIMEOUT))
    scan_interval = int(
        _entry_value(entry, CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    )

    hub = BWWPModbusHub(host=host, port=port, slave_id=slave_id, timeout=timeout)
    coordinator = BWWPDataUpdateCoordinator(
        hass=hass,
        hub=hub,
        scan_interval_seconds=scan_interval,
    )
    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = RuntimeData(hub=hub, coordinator=coordinator)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
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


