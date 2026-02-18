"""Number platform for writable BWWP values."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.number import NumberEntity, NumberEntityDescription, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import RuntimeData
from .const import CONF_SETPOINT_MAX, DEFAULT_SETPOINT_MAX, DOMAIN
from .entity import BWWPBaseEntity

WRITE_REFRESH_DELAY_SECONDS = 0.2


@dataclass(frozen=True, kw_only=True)
class BWWPNumberDescription(NumberEntityDescription):
    """Description of one writable Modbus register."""

    register: int
    state_key: str


NUMBER_DESCRIPTIONS: tuple[BWWPNumberDescription, ...] = (
    BWWPNumberDescription(
        key="setpoint_control",
        name="Solltemperatur",
        icon="mdi:thermometer-chevron-up",
        entity_category=EntityCategory.CONFIG,
        native_min_value=20,
        native_max_value=DEFAULT_SETPOINT_MAX,
        native_step=1,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        register=4,
        state_key="t_setpoint",
    ),
    BWWPNumberDescription(
        key="t_min_control",
        name="T min",
        icon="mdi:thermometer-low",
        entity_category=EntityCategory.CONFIG,
        native_min_value=20,
        native_max_value=80,
        native_step=1,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        register=5,
        state_key="t_min",
    ),
    BWWPNumberDescription(
        key="t2_min_control",
        name="T2 min",
        icon="mdi:thermometer-low",
        entity_category=EntityCategory.CONFIG,
        native_min_value=20,
        native_max_value=80,
        native_step=1,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        register=6,
        state_key="t2_min",
    ),
    BWWPNumberDescription(
        key="abwesenheitstage_control",
        name="Abwesenheitstage",
        icon="mdi:calendar-edit",
        entity_category=EntityCategory.CONFIG,
        native_min_value=0,
        native_max_value=30,
        native_step=1,
        native_unit_of_measurement=UnitOfTime.DAYS,
        register=21,
        state_key="abwesenheits_tage",
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
        self._attr_suggested_display_precision = 0
        self._hub = runtime.hub
        if description.key == "setpoint_control":
            configured_max = int(
                entry.options.get(
                    CONF_SETPOINT_MAX,
                    entry.data.get(CONF_SETPOINT_MAX, DEFAULT_SETPOINT_MAX),
                )
            )
            configured_max = max(20, min(configured_max, 80))
            self._attr_native_max_value = float(configured_max)

    @property
    def native_value(self) -> float | None:
        value = self.coordinator.data.get(self.entity_description.state_key)
        if value is None:
            return None
        return int(value)

    async def async_set_native_value(self, value: float) -> None:
        rounded_value = int(round(value))
        min_value = self.native_min_value
        max_value = self.native_max_value
        if min_value is not None and rounded_value < int(float(min_value)):
            raise HomeAssistantError(
                f"Value {rounded_value} is below minimum {int(float(min_value))}"
            )
        if max_value is not None and rounded_value > int(float(max_value)):
            raise HomeAssistantError(
                f"Value {rounded_value} is above maximum {int(float(max_value))}"
            )
        await self._hub.async_write_register(
            address=self.entity_description.register,
            value=rounded_value,
        )
        self._schedule_background_refresh(WRITE_REFRESH_DELAY_SECONDS)
