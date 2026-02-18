"""Coordinator and Modbus client for Wolf FHS280."""

from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import Any

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from pymodbus.client import AsyncModbusTcpClient
from pymodbus.exceptions import ModbusException

from .const import ENUM_MAPPINGS, ENUM_SOURCE_KEYS, READ_REGISTERS

LOGGER = logging.getLogger(__name__)


class BWWPModbusHub:
    """Thin async wrapper around pymodbus TCP client."""

    def __init__(self, host: str, port: int, slave_id: int, timeout: float) -> None:
        self._host = host
        self._port = port
        self._slave_id = slave_id
        self._timeout = timeout
        self._client = AsyncModbusTcpClient(host=host, port=port, timeout=timeout)
        self._lock = asyncio.Lock()

    @property
    def host(self) -> str:
        return self._host

    @property
    def port(self) -> int:
        return self._port

    @property
    def slave_id(self) -> int:
        return self._slave_id

    async def async_close(self) -> None:
        """Close network connection."""
        self._client.close()

    def _is_connected(self) -> bool:
        return bool(getattr(self._client, "connected", False))

    async def _ensure_connection(self) -> None:
        if self._is_connected():
            return
        connected = await self._client.connect()
        if not connected:
            raise ModbusException(
                f"Unable to connect to Modbus target {self._host}:{self._port}"
            )

    async def async_read_register(self, register_type: str, address: int) -> int:
        """Read one register (holding or input)."""
        async with self._lock:
            await self._ensure_connection()
            if register_type == "holding":
                result = await self._async_read_holding_register(address)
            else:
                result = await self._async_read_input_register(address)

            if result.isError():
                raise ModbusException(str(result))
            return int(result.registers[0])

    async def async_write_register(self, address: int, value: int) -> None:
        """Write one holding register."""
        write_value = value & 0xFFFF
        async with self._lock:
            await self._ensure_connection()
            result = await self._async_write_holding_register(address, write_value)
            if result.isError():
                raise ModbusException(str(result))

    async def _async_read_holding_register(self, address: int):
        """Read one holding register with pymodbus API compatibility."""
        try:
            return await self._client.read_holding_registers(
                address=address,
                count=1,
                device_id=self._slave_id,
            )
        except TypeError:
            return await self._client.read_holding_registers(
                address=address,
                count=1,
                slave=self._slave_id,
            )

    async def _async_read_input_register(self, address: int):
        """Read one input register with pymodbus API compatibility."""
        try:
            return await self._client.read_input_registers(
                address=address,
                count=1,
                device_id=self._slave_id,
            )
        except TypeError:
            return await self._client.read_input_registers(
                address=address,
                count=1,
                slave=self._slave_id,
            )

    async def _async_write_holding_register(self, address: int, value: int):
        """Write one holding register with pymodbus API compatibility."""
        try:
            return await self._client.write_register(
                address=address,
                value=value,
                device_id=self._slave_id,
            )
        except TypeError:
            return await self._client.write_register(
                address=address,
                value=value,
                slave=self._slave_id,
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


