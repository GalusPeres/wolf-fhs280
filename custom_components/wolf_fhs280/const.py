"""Constants for the Wolf FHS280."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Literal

from homeassistant.const import CONF_HOST, CONF_PORT, CONF_TIMEOUT, Platform

DOMAIN: Final = "wolf_fhs280"

CONF_NAME: Final = "name"
CONF_SCAN_INTERVAL: Final = "scan_interval"
CONF_SLAVE_ID: Final = "slave_id"

DEFAULT_NAME: Final = "Wolf FHS280"
DEFAULT_PORT: Final = 502
DEFAULT_SCAN_INTERVAL: Final = 30
DEFAULT_SLAVE_ID: Final = 3
DEFAULT_TIMEOUT: Final = 5.0

PLATFORMS: Final = [
    Platform.SENSOR,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SWITCH,
]

RegisterType = Literal["holding", "input"]


@dataclass(frozen=True)
class RegisterDefinition:
    """Definition of one Modbus register."""

    key: str
    address: int
    register_type: RegisterType
    scale: float = 1.0
    precision: int | None = None


READ_REGISTERS: Final[tuple[RegisterDefinition, ...]] = (
    RegisterDefinition("t_setpoint", 4, "holding"),
    RegisterDefinition("t_min", 5, "holding"),
    RegisterDefinition("t2_min", 6, "holding"),
    RegisterDefinition("timer_raw", 7, "holding"),
    RegisterDefinition("start_h", 8, "holding"),
    RegisterDefinition("start_min", 9, "holding"),
    RegisterDefinition("stop_h", 10, "holding"),
    RegisterDefinition("stop_min", 11, "holding"),
    RegisterDefinition("betriebsart_raw", 12, "holding"),
    RegisterDefinition("legio_raw", 13, "holding"),
    RegisterDefinition("ventilator_raw", 15, "holding"),
    RegisterDefinition("pv_modus_raw", 17, "holding"),
    RegisterDefinition("t_pv_wp", 18, "holding"),
    RegisterDefinition("t_pv_el", 19, "holding"),
    RegisterDefinition("holiday_raw", 20, "holding"),
    RegisterDefinition("abwesenheits_tage", 21, "holding"),
    RegisterDefinition("boost_raw", 22, "holding"),
    RegisterDefinition("t_max", 28, "holding"),
    RegisterDefinition("legionellen_tage", 33, "holding"),
    RegisterDefinition("t1", 7, "input", scale=0.1, precision=1),
    RegisterDefinition("t2", 8, "input", scale=0.1, precision=1),
    RegisterDefinition("kompressor_raw", 9, "input"),
    RegisterDefinition("heizstab_raw", 10, "input"),
    RegisterDefinition("status_raw", 16, "input"),
)

TIMER_OPTIONS: Final[dict[int, str]] = {
    0: "Aus",
    1: "An",
}
BETRIEBSART_OPTIONS: Final[dict[int, str]] = {
    0: "Aus",
    1: "Nur Wärmepumpe",
    2: "Nur Heizstab",
    3: "Wärmepumpe + Heizstab",
    4: "Boiler",
    5: "Wärmepumpe + Boiler",
}
LEGIONELLEN_OPTIONS: Final[dict[int, str]] = {
    0: "Aus",
    1: "60C",
    2: "65C",
}
PV_MODUS_OPTIONS: Final[dict[int, str]] = {
    0: "Aus",
    1: "Nur Wärmepumpe",
    2: "Nur Heizstab",
    3: "Heizstab + Wärmepumpe",
}
FERIEN_OPTIONS: Final[dict[int, str]] = {
    0: "Aus",
    1: "1 Woche",
    2: "2 Wochen",
    3: "3 Wochen",
    4: "3 Tage",
    5: "Manuell",
}
AN_AUS_OPTIONS: Final[dict[int, str]] = {
    0: "Aus",
    1: "An",
}
VENTILATOR_OPTIONS: Final[dict[int, str]] = {
    0: "Niedrig",
    1: "Hoch",
}

ENUM_MAPPINGS: Final[dict[str, dict[int, str]]] = {
    "timer": TIMER_OPTIONS,
    "betriebsart": BETRIEBSART_OPTIONS,
    "legionellen": LEGIONELLEN_OPTIONS,
    "pv_modus": PV_MODUS_OPTIONS,
    "ferien": FERIEN_OPTIONS,
    "kompressor": AN_AUS_OPTIONS,
    "heizstab": AN_AUS_OPTIONS,
    "ventilator": VENTILATOR_OPTIONS,
    "boost": AN_AUS_OPTIONS,
}

ENUM_SOURCE_KEYS: Final[dict[str, str]] = {
    "timer": "timer_raw",
    "betriebsart": "betriebsart_raw",
    "legionellen": "legio_raw",
    "pv_modus": "pv_modus_raw",
    "ferien": "holiday_raw",
    "kompressor": "kompressor_raw",
    "heizstab": "heizstab_raw",
    "ventilator": "ventilator_raw",
    "boost": "boost_raw",
}
