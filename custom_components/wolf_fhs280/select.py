"""Select platform for enum-like BWWP settings."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import RuntimeData
from .const import (
    BETRIEBSART_OPTIONS,
    DOMAIN,
    FERIEN_OPTIONS,
    LEGIONELLEN_OPTIONS,
    PV_MODUS_OPTIONS,
)
from .entity import BWWPBaseEntity

WRITE_REFRESH_DELAY_SECONDS = 0.2


@dataclass(frozen=True, kw_only=True)
class BWWPSelectDescription(SelectEntityDescription):
    """Description of one select register."""

    register: int
    state_key: str
    options_map: dict[str, int]


SELECT_DESCRIPTIONS: tuple[BWWPSelectDescription, ...] = (
    BWWPSelectDescription(
        key="betriebsart_control",
        name="Betriebsart",
        icon="mdi:cog-transfer",
        entity_category=EntityCategory.CONFIG,
        options=tuple(BETRIEBSART_OPTIONS.values()),
        register=12,
        state_key="betriebsart",
        options_map={label: code for code, label in BETRIEBSART_OPTIONS.items()},
    ),
    BWWPSelectDescription(
        key="legionellen_control",
        name="Legionellen",
        icon="mdi:bacteria-outline",
        entity_category=EntityCategory.CONFIG,
        options=tuple(LEGIONELLEN_OPTIONS.values()),
        register=13,
        state_key="legionellen",
        options_map={label: code for code, label in LEGIONELLEN_OPTIONS.items()},
    ),
    BWWPSelectDescription(
        key="pv_modus_control",
        name="PV Modus",
        icon="mdi:solar-power-variant-outline",
        entity_category=EntityCategory.CONFIG,
        options=tuple(PV_MODUS_OPTIONS.values()),
        register=17,
        state_key="pv_modus",
        options_map={label: code for code, label in PV_MODUS_OPTIONS.items()},
    ),
    BWWPSelectDescription(
        key="ferien_control",
        name="Ferienmodus",
        icon="mdi:beach",
        entity_category=EntityCategory.CONFIG,
        options=tuple(FERIEN_OPTIONS.values()),
        register=20,
        state_key="ferien",
        options_map={label: code for code, label in FERIEN_OPTIONS.items()},
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up BWWP select entities."""
    runtime: RuntimeData = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        BWWPSelect(runtime, entry, description)
        for description in SELECT_DESCRIPTIONS
    )


class BWWPSelect(BWWPBaseEntity, SelectEntity):
    """Writable BWWP select entity."""

    entity_description: BWWPSelectDescription

    def __init__(
        self,
        runtime: RuntimeData,
        entry: ConfigEntry,
        description: BWWPSelectDescription,
    ) -> None:
        super().__init__(runtime.coordinator, entry, description.key)
        self.entity_description = description
        self._attr_name = description.name
        self._hub = runtime.hub

    @property
    def current_option(self) -> str | None:
        data = self.coordinator.data or {}
        value = data.get(self.entity_description.state_key)
        if value in self.entity_description.options:
            return value
        return None

    async def async_select_option(self, option: str) -> None:
        if option not in self.entity_description.options_map:
            return
        await self._hub.async_write_register(
            address=self.entity_description.register,
            value=self.entity_description.options_map[option],
        )
        self._schedule_background_refresh(WRITE_REFRESH_DELAY_SECONDS)
