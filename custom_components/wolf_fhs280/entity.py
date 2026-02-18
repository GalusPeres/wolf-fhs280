"""Shared entity base classes."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_NAME, CONF_SLAVE_ID, DEFAULT_NAME, DOMAIN
from .coordinator import BWWPDataUpdateCoordinator


class BWWPBaseEntity(CoordinatorEntity[BWWPDataUpdateCoordinator]):
    """Base entity for all BWWP platforms."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: BWWPDataUpdateCoordinator,
        entry: ConfigEntry,
        unique_key: str,
    ) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_{unique_key}"

        host = entry.options.get(CONF_HOST, entry.data.get(CONF_HOST, ""))
        name = entry.options.get(CONF_NAME, entry.data.get(CONF_NAME, DEFAULT_NAME))
        slave_id = entry.options.get(CONF_SLAVE_ID, entry.data.get(CONF_SLAVE_ID))

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=name,
            manufacturer="WOLF",
            model="FHS 280",
            configuration_url=f"http://{host}" if host else None,
            sw_version=f"Modbus ID {slave_id}",
        )
