"""Sensor platform for Wolf FHS280."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import RuntimeData
from .const import DOMAIN
from .entity import BWWPBaseEntity


@dataclass(frozen=True, kw_only=True)
class BWWPSensorDescription(SensorEntityDescription):
    """Description for one BWWP sensor."""


SENSORS: tuple[BWWPSensorDescription, ...] = (
    BWWPSensorDescription(
        key="t_pv_wp",
        translation_key="t_pv_wp",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    BWWPSensorDescription(
        key="t_pv_el",
        translation_key="t_pv_el",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    BWWPSensorDescription(
        key="legionellen_tage",
        translation_key="legionellen_tage",
        native_unit_of_measurement=UnitOfTime.DAYS,
    ),
    BWWPSensorDescription(
        key="t_max",
        translation_key="t_max",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    BWWPSensorDescription(
        key="t1",
        translation_key="t1",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    BWWPSensorDescription(
        key="t2",
        translation_key="t2",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    BWWPSensorDescription(
        key="kompressor",
        translation_key="kompressor",
        icon="mdi:engine-outline",
    ),
    BWWPSensorDescription(
        key="heizstab",
        translation_key="heizstab",
        icon="mdi:radiator",
    ),
    BWWPSensorDescription(
        key="betriebsstatus",
        translation_key="betriebsstatus",
        icon="mdi:heat-pump-outline",
    ),
    BWWPSensorDescription(
        key="device_time",
        translation_key="device_time",
        icon="mdi:clock-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    BWWPSensorDescription(
        key="ventilator",
        translation_key="ventilator",
        icon="mdi:fan",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up BWWP sensors."""
    runtime: RuntimeData = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(BWWPSensor(runtime, entry, description) for description in SENSORS)


class BWWPSensor(BWWPBaseEntity, SensorEntity):
    """Coordinator-backed BWWP sensor."""

    entity_description: BWWPSensorDescription

    def __init__(
        self,
        runtime: RuntimeData,
        entry: ConfigEntry,
        description: BWWPSensorDescription,
    ) -> None:
        super().__init__(runtime.coordinator, entry, description.key)
        self.entity_description = description

    @property
    def native_value(self):
        data = self.coordinator.data or {}
        return data.get(self.entity_description.key)
