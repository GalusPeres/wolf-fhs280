"""Coordinator and Modbus adapter for Wolf FHS280."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any, TYPE_CHECKING

from homeassistant.components.modbus.const import (
    CALL_TYPE_REGISTER_HOLDING,
    CALL_TYPE_REGISTER_INPUT,
    CALL_TYPE_WRITE_REGISTER,
)
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from pymodbus.exceptions import ModbusException

from .const import ENUM_MAPPINGS, ENUM_SOURCE_KEYS, READ_REGISTERS

if TYPE_CHECKING:
    from homeassistant.components.modbus.modbus import ModbusHub as HAModbusHub

LOGGER = logging.getLogger(__name__)


class BWWPModbusHub:
    """Thin async wrapper around Home Assistant's shared ModbusHub."""

    def __init__(self, hub: "HAModbusHub", hub_name: str, slave_id: int) -> None:
        self._hub = hub
        self._hub_name = hub_name
        self._slave_id = slave_id

    @property
    def hub_name(self) -> str:
        return self._hub_name

    @property
    def slave_id(self) -> int:
        return self._slave_id

    @property
    def host(self) -> str | None:
        params = getattr(self._hub, "_pb_params", {})
        host = params.get("host")
        return str(host) if host is not None else None

    @property
    def port(self) -> int | None:
        params = getattr(self._hub, "_pb_params", {})
        port = params.get("port")
        try:
            return int(port) if port is not None else None
        except (TypeError, ValueError):
            return None

    async def async_close(self) -> None:
        """No-op: shared modbus hub lifecycle is handled by HA modbus integration."""
        return None

    async def async_read_register(self, register_type: str, address: int) -> int:
        """Read one register (holding or input) via shared ModbusHub."""
        call_type = (
            CALL_TYPE_REGISTER_HOLDING
            if register_type == "holding"
            else CALL_TYPE_REGISTER_INPUT
        )

        result = await self._hub.async_pb_call(self._slave_id, address, 1, call_type)
        if result is None or not hasattr(result, "registers"):
            raise ModbusException(
                f"Read failed for hub={self._hub_name} slave={self._slave_id} address={address}"
            )

        registers = getattr(result, "registers", None)
        if not registers:
            raise ModbusException(
                f"No register data for hub={self._hub_name} slave={self._slave_id} address={address}"
            )

        return int(registers[0])

    async def async_write_register(self, address: int, value: int) -> None:
        """Write one holding register via shared ModbusHub."""
        write_value = value & 0xFFFF
        result = await self._hub.async_pb_call(
            self._slave_id,
            address,
            write_value,
            CALL_TYPE_WRITE_REGISTER,
        )
        if result is None:
            raise ModbusException(
                f"Write failed for hub={self._hub_name} slave={self._slave_id} address={address}"
            )


class BWWPDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Poll all known BWWP registers and expose parsed values."""

    def __init__(
        self,
        hass,
        hub: BWWPModbusHub,
        scan_interval_seconds: int,
    ) -> None:
        super().__init__(
            hass,
            LOGGER,
            name="Wolf FHS280",
            update_interval=timedelta(seconds=scan_interval_seconds),
        )
        self.hub = hub

    async def _async_update_data(self) -> dict[str, Any]:
        data: dict[str, Any] = {}
        failed_reads = 0

        for definition in READ_REGISTERS:
            try:
                raw = await self.hub.async_read_register(
                    register_type=definition.register_type,
                    address=definition.address,
                )
            except ModbusException as err:
                failed_reads += 1
                LOGGER.debug(
                    "Read failed (%s @ %s): %s",
                    definition.key,
                    definition.address,
                    err,
                )
                data[definition.key] = None
                continue

            signed_value = _to_signed_int16(raw)
            scaled_value = signed_value * definition.scale
            if definition.precision is not None:
                scaled_value = round(scaled_value, definition.precision)

            if definition.scale == 1.0 and definition.precision is None:
                data[definition.key] = int(scaled_value)
            else:
                data[definition.key] = scaled_value

        if failed_reads == len(READ_REGISTERS):
            raise UpdateFailed("No register could be read from BWWP")

        for enum_key, source_key in ENUM_SOURCE_KEYS.items():
            raw_value = data.get(source_key)
            if raw_value is None:
                data[enum_key] = "Unknown"
                continue

            mapping = ENUM_MAPPINGS[enum_key]
            data[enum_key] = mapping.get(int(raw_value), "Unknown")

        return data


def _to_signed_int16(value: int) -> int:
    """Convert unsigned register value to signed int16."""
    if value > 0x7FFF:
        return value - 0x10000
    return value
