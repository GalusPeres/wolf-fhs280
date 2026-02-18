"""Wolf FHS280 custom integration."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.modbus import get_hub
from homeassistant.components.modbus.modbus import DATA_MODBUS_HUBS
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import (
    CONF_HUB,
    CONF_SCAN_INTERVAL,
    CONF_SLAVE_ID,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_SLAVE_ID,
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

    modbus_hubs = hass.data.get(DATA_MODBUS_HUBS, {})
    if not modbus_hubs:
        raise ConfigEntryNotReady(
            "No Home Assistant modbus hub is configured. Configure modbus: first."
        )

    hub_name = _resolve_hub_name(hass, entry)
    try:
        modbus_hub = get_hub(hass, hub_name)
    except KeyError as err:
        raise ConfigEntryNotReady(f"Configured modbus hub '{hub_name}' not found") from err

    slave_id = int(_entry_value(entry, CONF_SLAVE_ID, DEFAULT_SLAVE_ID))
    scan_interval = int(_entry_value(entry, CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL))

    hub = BWWPModbusHub(hub=modbus_hub, hub_name=hub_name, slave_id=slave_id)
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


def _resolve_hub_name(hass: HomeAssistant, entry: ConfigEntry) -> str:
    """Resolve configured modbus hub with backward-compatible fallback."""
    hubs = hass.data.get(DATA_MODBUS_HUBS, {})

    configured_hub = _entry_value(entry, CONF_HUB)
    if configured_hub and configured_hub in hubs:
        return configured_hub

    # Backward compatibility for older entries that stored host/port.
    legacy_host = _entry_value(entry, CONF_HOST)
    legacy_port = _entry_value(entry, CONF_PORT)
    if legacy_host:
        legacy_port_str = str(legacy_port) if legacy_port is not None else None
        for name, hub in hubs.items():
            params = getattr(hub, "_pb_params", {})
            if str(params.get("host", "")) != str(legacy_host):
                continue
            if legacy_port_str and str(params.get("port")) != legacy_port_str:
                continue
            return name

    if len(hubs) == 1:
        return next(iter(hubs))

    if configured_hub:
        raise ConfigEntryNotReady(
            f"Configured modbus hub '{configured_hub}' not found."
        )

    raise ConfigEntryNotReady("No modbus hub selected for this entry.")