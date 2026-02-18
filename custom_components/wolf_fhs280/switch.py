"""Switch platform for simple on/off BWWP controls."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import RuntimeData
from .const import DOMAIN
from .entity import BWWPBaseEntity

WRITE_REFRESH_DELAY_SECONDS = 0.2


@dataclass(frozen=True, kw_only=True)
class BWWPSwitchDescription(SwitchEntityDescription):
    """Description of one switch-like register."""

    register: int
    state_key: str


SWITCH_DESCRIPTIONS: tuple[BWWPSwitchDescription, ...] = (
    BWWPSwitchDescription(
        key="timer_control",
        translation_key="timer_control",
        icon="mdi:timer-outline",
        entity_category=EntityCategory.CONFIG,
        register=7,
        state_key="timer_raw",
    ),
    BWWPSwitchDescription(
        key="boost_control",
        translation_key="boost_control",
        icon="mdi:rocket-launch-outline",
        entity_category=EntityCategory.CONFIG,
        register=22,
        state_key="boost_raw",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up BWWP switch entities."""
    runtime: RuntimeData = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        BWWPSwitch(runtime, entry, description)
        for description in SWITCH_DESCRIPTIONS
    )


class BWWPSwitch(BWWPBaseEntity, SwitchEntity):
    """Writable BWWP switch entity."""

    entity_description: BWWPSwitchDescription

    def __init__(
        self,
        runtime: RuntimeData,
        entry: ConfigEntry,
        description: BWWPSwitchDescription,
    ) -> None:
        super().__init__(runtime.coordinator, entry, description.key)
        self.entity_description = description
        self._hub = runtime.hub

    @property
    def is_on(self) -> bool | None:
        data = self.coordinator.data or {}
        value = data.get(self.entity_description.state_key)
        if value is None:
            return None
        return int(value) == 1

    async def async_turn_on(self, **kwargs) -> None:
        await self._hub.async_write_register(
            address=self.entity_description.register,
            value=1,
        )
        self._schedule_background_refresh(WRITE_REFRESH_DELAY_SECONDS)

    async def async_turn_off(self, **kwargs) -> None:
        await self._hub.async_write_register(
            address=self.entity_description.register,
            value=0,
        )
        self._schedule_background_refresh(WRITE_REFRESH_DELAY_SECONDS)
