"""Coordinator and Modbus client for Wolf FHS280."""

from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import Any, TYPE_CHECKING

from homeassistant.components.modbus.const import (
    CALL_TYPE_REGISTER_HOLDING,
    CALL_TYPE_REGISTER_INPUT,
    CALL_TYPE_WRITE_REGISTER,
)
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from pymodbus.client import AsyncModbusTcpClient
from pymodbus.exceptions import ModbusException
from pymodbus.pdu import ExceptionResponse

from .const import ENUM_MAPPINGS, ENUM_SOURCE_KEYS, READ_REGISTERS

if TYPE_CHECKING:
    from homeassistant.components.modbus.modbus import ModbusHub as HAModbusHub

LOGGER = logging.getLogger(__name__)

MODBUS_EXCEPTION_LABELS: dict[int, str] = {
    1: "illegal function",
    2: "illegal data address",
    3: "illegal data value",
    4: "server device failure",
}


class NonRetryableModbusException(ModbusException):
    """A device-side protocol error where retrying the same request is pointless."""


class BWWPModbusHub:
    """Thin async wrapper around pymodbus TCP client."""

    def __init__(self, host: str, port: int, slave_id: int, timeout: float) -> None:
        self._host = host
        self._port = port
        self._slave_id = slave_id
        self._timeout = timeout
        # Use separate clients for read and write so controls are not blocked
        # behind long polling reads.
        self._read_client = AsyncModbusTcpClient(host=host, port=port, timeout=timeout)
        self._write_client = AsyncModbusTcpClient(host=host, port=port, timeout=timeout)
        self._read_lock = asyncio.Lock()
        self._write_lock = asyncio.Lock()

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
        self._read_client.close()
        self._write_client.close()

    @staticmethod
    def _is_connected(client: AsyncModbusTcpClient) -> bool:
        return bool(getattr(client, "connected", False))

    async def _ensure_connection(self, client: AsyncModbusTcpClient) -> None:
        if self._is_connected(client):
            return
        connected = await asyncio.wait_for(
            client.connect(), timeout=self._request_timeout()
        )
        if not connected:
            raise ModbusException(
                f"Unable to connect to Modbus target {self._host}:{self._port}"
            )

    async def _reset_connection(self, client: AsyncModbusTcpClient) -> None:
        """Close current connection so next call forces reconnect."""
        client.close()

    def _request_timeout(self) -> float:
        """Hard upper bound for one network call to avoid hanging tasks."""
        return max(0.5, float(self._timeout)) + 1.0

    async def async_read_registers(
        self, register_type: str, address: int, count: int
    ) -> list[int]:
        """Read multiple contiguous registers."""
        if count < 1:
            return []

        async with self._read_lock:
            last_error: Exception | None = None
            for attempt in range(2):
                try:
                    await self._ensure_connection(self._read_client)
                    if register_type == "holding":
                        result = await self._async_read_holding_registers(
                            self._read_client, address, count
                        )
                    else:
                        result = await self._async_read_input_registers(
                            self._read_client, address, count
                        )

                    if not result.isError():
                        registers = getattr(result, "registers", None) or []
                        if len(registers) < count:
                            raise ModbusException(
                                f"Expected {count} registers but got {len(registers)}"
                            )
                        return [int(value) for value in registers[:count]]

                    if isinstance(result, ExceptionResponse):
                        raise self._build_non_retryable_error(
                            response=result,
                            action=f"read {register_type} addr={address} count={count}",
                        )

                    last_error = ModbusException(str(result))
                except NonRetryableModbusException:
                    raise
                except (OSError, asyncio.TimeoutError, ModbusException) as err:
                    last_error = err

                if attempt == 0:
                    await self._reset_connection(self._read_client)

            raise last_error or ModbusException("Unknown Modbus read error")

    async def async_read_register(self, register_type: str, address: int) -> int:
        """Read one register (holding or input)."""
        registers = await self.async_read_registers(register_type, address, 1)
        return int(registers[0])

    async def async_write_register(self, address: int, value: int) -> None:
        """Write one holding register."""
        write_value = value & 0xFFFF
        async with self._write_lock:
            last_error: Exception | None = None
            for attempt in range(2):
                try:
                    await self._ensure_connection(self._write_client)
                    result = await self._async_write_holding_register(
                        self._write_client, address, write_value
                    )
                    if not result.isError():
                        return

                    if isinstance(result, ExceptionResponse):
                        raise self._build_non_retryable_error(
                            response=result,
                            action=f"write addr={address} value={write_value}",
                        )

                    last_error = ModbusException(str(result))
                except NonRetryableModbusException:
                    raise
                except (OSError, asyncio.TimeoutError, ModbusException) as err:
                    last_error = err

                if attempt == 0:
                    await self._reset_connection(self._write_client)

            raise last_error or ModbusException("Unknown Modbus write error")

    async def _async_read_holding_registers(
        self, client: AsyncModbusTcpClient, address: int, count: int
    ):
        """Read holding registers with pymodbus API compatibility."""
        try:
            return await asyncio.wait_for(
                client.read_holding_registers(
                    address=address,
                    count=count,
                    device_id=self._slave_id,
                ),
                timeout=self._request_timeout(),
            )
        except TypeError:
            return await asyncio.wait_for(
                client.read_holding_registers(
                    address=address,
                    count=count,
                    slave=self._slave_id,
                ),
                timeout=self._request_timeout(),
            )

    async def _async_read_input_registers(
        self, client: AsyncModbusTcpClient, address: int, count: int
    ):
        """Read input registers with pymodbus API compatibility."""
        try:
            return await asyncio.wait_for(
                client.read_input_registers(
                    address=address,
                    count=count,
                    device_id=self._slave_id,
                ),
                timeout=self._request_timeout(),
            )
        except TypeError:
            return await asyncio.wait_for(
                client.read_input_registers(
                    address=address,
                    count=count,
                    slave=self._slave_id,
                ),
                timeout=self._request_timeout(),
            )

    async def _async_write_holding_register(
        self, client: AsyncModbusTcpClient, address: int, value: int
    ):
        """Write one holding register with pymodbus API compatibility."""
        try:
            return await asyncio.wait_for(
                client.write_register(
                    address=address,
                    value=value,
                    device_id=self._slave_id,
                ),
                timeout=self._request_timeout(),
            )
        except TypeError:
            return await asyncio.wait_for(
                client.write_register(
                    address=address,
                    value=value,
                    slave=self._slave_id,
                ),
                timeout=self._request_timeout(),
            )

    def _build_non_retryable_error(
        self, response: ExceptionResponse, action: str
    ) -> NonRetryableModbusException:
        """Convert Modbus exception responses into explicit user-facing errors."""
        code = int(getattr(response, "exception_code", -1))
        label = MODBUS_EXCEPTION_LABELS.get(code, f"exception code {code}")
        if code == 3:
            return NonRetryableModbusException(
                f"Device rejected value ({label}) on slave={self._slave_id}: {action}. "
                "Check allowed range and required operating mode."
            )
        return NonRetryableModbusException(
            f"Modbus protocol error ({label}) on slave={self._slave_id}: {action}"
        )


class BWWPSharedModbusHub:
    """Adapter that reuses Home Assistant's existing modbus hub."""

    def __init__(self, hub: "HAModbusHub", hub_name: str, slave_id: int) -> None:
        self._hub = hub
        self._hub_name = hub_name
        self._slave_id = slave_id

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

    @property
    def slave_id(self) -> int:
        return self._slave_id

    async def async_close(self) -> None:
        """Shared hub lifecycle is handled by Home Assistant."""
        return None

    async def async_read_registers(
        self, register_type: str, address: int, count: int
    ) -> list[int]:
        """Read multiple contiguous registers through HA modbus hub."""
        call_type = (
            CALL_TYPE_REGISTER_HOLDING
            if register_type == "holding"
            else CALL_TYPE_REGISTER_INPUT
        )
        result = await self._hub.async_pb_call(self._slave_id, address, count, call_type)
        if result is None:
            raise ModbusException(
                f"Read failed for hub={self._hub_name} slave={self._slave_id} address={address}"
            )
        if result.isError():
            raise ModbusException(str(result))

        registers = getattr(result, "registers", None) or []
        if len(registers) < count:
            raise ModbusException(
                f"Expected {count} registers but got {len(registers)}"
            )
        return [int(value) for value in registers[:count]]

    async def async_read_register(self, register_type: str, address: int) -> int:
        """Read one register through HA modbus hub."""
        registers = await self.async_read_registers(register_type, address, 1)
        return int(registers[0])

    async def async_write_register(self, address: int, value: int) -> None:
        """Write one holding register through HA modbus hub."""
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
        if hasattr(result, "isError") and result.isError():
            raise ModbusException(str(result))


class BWWPDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Poll all known BWWP registers and expose parsed values."""

    def __init__(
        self,
        hass,
        hub: BWWPModbusHub | BWWPSharedModbusHub,
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

        by_type: dict[str, list[Any]] = {"holding": [], "input": []}
        for definition in READ_REGISTERS:
            by_type[definition.register_type].append(definition)

        for register_type, definitions in by_type.items():
            definitions.sort(key=lambda item: item.address)
            for block in _contiguous_blocks(definitions):
                block_start = block[0].address
                block_count = block[-1].address - block_start + 1
                try:
                    raw_values = await self.hub.async_read_registers(
                        register_type=register_type,
                        address=block_start,
                        count=block_count,
                    )
                except ModbusException as err:
                    LOGGER.debug(
                        "Block read failed (%s @ %s len %s): %s",
                        register_type,
                        block_start,
                        block_count,
                        err,
                    )
                    for definition in block:
                        try:
                            raw = await self.hub.async_read_register(
                                register_type=definition.register_type,
                                address=definition.address,
                            )
                        except ModbusException as single_err:
                            failed_reads += 1
                            LOGGER.debug(
                                "Read failed (%s @ %s): %s",
                                definition.key,
                                definition.address,
                                single_err,
                            )
                            data[definition.key] = None
                        else:
                            _store_scaled_value(data, definition, raw)
                    continue

                for definition in block:
                    raw = raw_values[definition.address - block_start]
                    _store_scaled_value(data, definition, raw)

        if failed_reads == len(READ_REGISTERS):
            raise UpdateFailed("No register could be read from BWWP")

        for enum_key, source_key in ENUM_SOURCE_KEYS.items():
            raw_value = data.get(source_key)
            if raw_value is None:
                data[enum_key] = "Unknown"
                continue

            mapping = ENUM_MAPPINGS[enum_key]
            data[enum_key] = mapping.get(int(raw_value), "Unknown")

        kompressor_raw = data.get("kompressor_raw")
        heizstab_raw = data.get("heizstab_raw")
        if kompressor_raw is None and heizstab_raw is None:
            data["betriebsstatus"] = "Unknown"
        else:
            kompressor_on = kompressor_raw is not None and int(kompressor_raw) == 1
            heizstab_on = heizstab_raw is not None and int(heizstab_raw) == 1
            if kompressor_on and heizstab_on:
                data["betriebsstatus"] = "W\u00e4rmepumpe + Heizstab"
            elif heizstab_on:
                data["betriebsstatus"] = "Heizstab"
            elif kompressor_on:
                data["betriebsstatus"] = "W\u00e4rmepumpe"
            else:
                data["betriebsstatus"] = "Aus"

        return data


def _to_signed_int16(value: int) -> int:
    """Convert unsigned register value to signed int16."""
    if value > 0x7FFF:
        return value - 0x10000
    return value


def _store_scaled_value(data: dict[str, Any], definition, raw: int) -> None:
    """Apply scaling/precision and write to coordinator state."""
    signed_value = _to_signed_int16(raw)
    scaled_value = signed_value * definition.scale
    if definition.precision is not None:
        scaled_value = round(scaled_value, definition.precision)

    if definition.scale == 1.0 and definition.precision is None:
        data[definition.key] = int(scaled_value)
    else:
        data[definition.key] = scaled_value


def _contiguous_blocks(definitions: list[Any]) -> list[list[Any]]:
    """Split register definitions into contiguous address blocks."""
    if not definitions:
        return []

    blocks: list[list[Any]] = []
    current: list[Any] = [definitions[0]]

    for definition in definitions[1:]:
        if definition.address == current[-1].address + 1:
            current.append(definition)
            continue
        blocks.append(current)
        current = [definition]

    blocks.append(current)
    return blocks

