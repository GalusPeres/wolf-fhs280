"""Shared entity base classes."""

from __future__ import annotations

import asyncio
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from homeassistant.const import CONF_HOST

from .const import CONF_NAME, DEFAULT_NAME, DOMAIN
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

        host = str(
            entry.options.get(CONF_HOST, entry.data.get(CONF_HOST, coordinator.hub.host))
        )
        name = entry.options.get(CONF_NAME, entry.data.get(CONF_NAME, DEFAULT_NAME))

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=name,
            manufacturer="WOLF",
            model="FHS 280",
            configuration_url=f"http://{host}" if host else None,
            sw_version=None,
        )

    def _apply_local_update(self, updates: dict[str, Any]) -> None:
        """Update coordinator data immediately so UI reflects writes quickly."""
        merged = dict(self.coordinator.data or {})
        merged.update(updates)
        self.coordinator.async_set_updated_data(merged)

    def _schedule_background_refresh(self, delay_seconds: float = 0.2) -> None:
        """Refresh values in background without blocking the service call."""

        async def _refresh_later() -> None:
            if delay_seconds > 0:
                await asyncio.sleep(delay_seconds)
            await self.coordinator.async_request_refresh()

        self.hass.async_create_task(_refresh_later())
