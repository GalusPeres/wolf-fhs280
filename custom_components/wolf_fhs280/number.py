"""Number platform for writable BWWP values."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

from homeassistant.components.number import NumberEntity, NumberEntityDescription, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import RuntimeData
from .const import DOMAIN
from .entity import BWWPBaseEntity

WRITE_SETTLE_SECONDS = 0.5


@dataclass(frozen=True, kw_only=True)
class BWWPNumberDescription(NumberEntityDescription):
    """Description of one writable Modbus register."""

    register: int
    state_key: str


NUMBER_DESCRIPTIONS: tuple[BWWPNumberDescription, ...] = (
    BWWPNumberDescription(
        key="setpoint_control",
        name="Solltemperatur einstellen",
        native_min_value=20,
        native_max_value=65,
        native_step=1,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        register=4,
        state_key="t_setpoint",
    ),
    BWWPNumberDescription(
        key="abwesenheitstage_control",
        name="Abwesenheitstage einstellen",
        native_min_value=0,
        native_max_value=30,
        native_step=1,
        native_unit_of_measurement=UnitOfTime.DAYS,
        register=21,
        state_key="abwesenheits_tage",
    ),
    BWWPNumberDescription(
        key="start_hour_control",
        name="Startzeit Stunde",
        native_min_value=0,
        native_max_value=23,
        native_step=1,
        register=8,
        state_key="start_h",
    ),
    BWWPNumberDescription(
        key="start_minute_control",
        name="Startzeit Minute",
        native_min_value=0,
        native_max_value=59,
        native_step=1,
        register=9,
        state_key="start_min",
    ),
    BWWPNumberDescription(
        key="stop_hour_control",
        name="Stoppzeit Stunde",
        native_min_value=0,
        native_max_value=23,
        native_step=1,
        register=10,
        state_key="stop_h",
    ),
    BWWPNumberDescription(
        key="stop_minute_control",
        name="Stoppzeit Minute",
        native_min_value=0,
        native_max_value=59,
        native_step=1,
        register=11,
        state_key="stop_min",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up BWWP number entities."""
    runtime: RuntimeData = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        BWWPNumber(runtime, entry, description)
        for description in NUMBER_DESCRIPTIONS
    )


class BWWPNumber(BWWPBaseEntity, NumberEntity):
    """Writable BWWP number entity."""

    entity_description: BWWPNumberDescription

    def __init__(
        self,
        runtime: RuntimeData,
        entry: ConfigEntry,
        description: BWWPNumberDescription,
    ) -> None:
        super().__init__(runtime.coordinator, entry, description.key)
        self.entity_description = description
        self._attr_name = description.name
        self._attr_mode = NumberMode.BOX
        self._hub = runtime.hub

    @property
    def native_value(self) -> float | None:
        value = self.coordinator.data.get(self.entity_description.state_key)
        if value is None:
            return None
        return float(value)

    async def async_set_native_value(self, value: float) -> None:
        await self._hub.async_write_register(
            address=self.entity_description.register,
            value=int(round(value)),
        )
        await asyncio.sleep(WRITE_SETTLE_SECONDS)
        await self.coordinator.async_request_refresh()
