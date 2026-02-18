"""Button platform for one-shot actions."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from . import RuntimeData
from .const import DOMAIN
from .entity import BWWPBaseEntity

WRITE_REFRESH_DELAY_SECONDS = 0.2


@dataclass(frozen=True, kw_only=True)
class BWWPButtonDescription(ButtonEntityDescription):
    """Description for one BWWP button action."""

    hour_register: int
    minute_register: int


BUTTON_DESCRIPTIONS: tuple[BWWPButtonDescription, ...] = (
    BWWPButtonDescription(
        key="sync_device_clock",
        name="Uhrzeit synchronisieren",
        icon="mdi:clock-sync",
        entity_category=EntityCategory.CONFIG,
        hour_register=105,
        minute_register=104,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up BWWP button entities."""
    runtime: RuntimeData = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        BWWPButton(runtime, entry, description) for description in BUTTON_DESCRIPTIONS
    )


class BWWPButton(BWWPBaseEntity, ButtonEntity):
    """One-shot BWWP control button."""

    entity_description: BWWPButtonDescription

    def __init__(
        self,
        runtime: RuntimeData,
        entry: ConfigEntry,
        description: BWWPButtonDescription,
    ) -> None:
        super().__init__(runtime.coordinator, entry, description.key)
        self.entity_description = description
        self._attr_name = description.name
        self._hub = runtime.hub

    async def async_press(self) -> None:
        now = dt_util.now()
        await self._hub.async_write_register(
            address=self.entity_description.hour_register,
            value=int(now.hour),
        )
        await self._hub.async_write_register(
            address=self.entity_description.minute_register,
            value=int(now.minute),
        )
        self._schedule_background_refresh(WRITE_REFRESH_DELAY_SECONDS)
