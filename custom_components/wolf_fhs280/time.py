"""Time platform for BWWP time controls."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import time

from homeassistant.components.time import TimeEntity, TimeEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import RuntimeData
from .const import DOMAIN
from .entity import BWWPBaseEntity

WRITE_REFRESH_DELAY_SECONDS = 0.2


@dataclass(frozen=True, kw_only=True)
class BWWPTimeDescription(TimeEntityDescription):
    """Description of one time pair mapped to two Modbus registers."""

    hour_register: int
    minute_register: int
    hour_state_key: str
    minute_state_key: str


TIME_DESCRIPTIONS: tuple[BWWPTimeDescription, ...] = (
    BWWPTimeDescription(
        key="start_time_control",
        name="Startzeit einstellen",
        icon="mdi:clock-start",
        entity_category=EntityCategory.CONFIG,
        hour_register=8,
        minute_register=9,
        hour_state_key="start_h",
        minute_state_key="start_min",
    ),
    BWWPTimeDescription(
        key="stop_time_control",
        name="Stoppzeit einstellen",
        icon="mdi:clock-end",
        entity_category=EntityCategory.CONFIG,
        hour_register=10,
        minute_register=11,
        hour_state_key="stop_h",
        minute_state_key="stop_min",
    ),
    BWWPTimeDescription(
        key="current_time_control",
        name="Aktuelle Uhrzeit einstellen",
        icon="mdi:clock-outline",
        entity_category=EntityCategory.CONFIG,
        hour_register=0,
        minute_register=1,
        hour_state_key="current_h",
        minute_state_key="current_min",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up BWWP time entities."""
    runtime: RuntimeData = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        BWWPTime(runtime, entry, description) for description in TIME_DESCRIPTIONS
    )


class BWWPTime(BWWPBaseEntity, TimeEntity):
    """Writable BWWP time entity."""

    entity_description: BWWPTimeDescription

    def __init__(
        self,
        runtime: RuntimeData,
        entry: ConfigEntry,
        description: BWWPTimeDescription,
    ) -> None:
        super().__init__(runtime.coordinator, entry, description.key)
        self.entity_description = description
        self._attr_name = description.name
        self._hub = runtime.hub

    @property
    def native_value(self) -> time | None:
        hour_raw = self.coordinator.data.get(self.entity_description.hour_state_key)
        minute_raw = self.coordinator.data.get(self.entity_description.minute_state_key)
        if hour_raw is None or minute_raw is None:
            return None

        try:
            hour = int(hour_raw)
            minute = int(minute_raw)
        except (TypeError, ValueError):
            return None

        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            return None
        return time(hour=hour, minute=minute)

    async def async_set_value(self, value: time) -> None:
        hour = int(value.hour)
        minute = int(value.minute)
        await self._hub.async_write_register(
            address=self.entity_description.hour_register,
            value=hour,
        )
        await self._hub.async_write_register(
            address=self.entity_description.minute_register,
            value=minute,
        )
        self._apply_local_update(
            {
                self.entity_description.hour_state_key: hour,
                self.entity_description.minute_state_key: minute,
            }
        )
        self._schedule_background_refresh(WRITE_REFRESH_DELAY_SECONDS)
