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
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import RuntimeData
from .const import DOMAIN
from .entity import BWWPBaseEntity


@dataclass(frozen=True, kw_only=True)
class BWWPSensorDescription(SensorEntityDescription):
    """Description for one BWWP sensor."""


SENSORS: tuple[BWWPSensorDescription, ...] = (
    BWWPSensorDescription(
        key="t_min",
        name="T min",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    BWWPSensorDescription(
        key="t2_min",
        name="T2 min",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    BWWPSensorDescription(
        key="t_pv_wp",
        name="Temperatur PV WP",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    BWWPSensorDescription(
        key="t_pv_el",
        name="Temperatur PV Heizstab",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    BWWPSensorDescription(
        key="legionellen_tage",
        name="Legionellen Tage",
        native_unit_of_measurement=UnitOfTime.DAYS,
    ),
    BWWPSensorDescription(
        key="t_max",
        name="Temperatur max",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    BWWPSensorDescription(
        key="t1",
        name="Verdampfertemperatur",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    BWWPSensorDescription(
        key="t2",
        name="Speichertemperatur",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    BWWPSensorDescription(key="kompressor", name="Kompressor"),
    BWWPSensorDescription(key="heizstab", name="Heizstab"),
    BWWPSensorDescription(key="ventilator", name="Ventilator"),
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
        self._attr_name = description.name

    @property
    def native_value(self):
        return self.coordinator.data.get(self.entity_description.key)
