# Wolf FHS280 (Home Assistant Custom Integration)

Custom integration for Wolf FHS280 via Modbus TCP.

## Features

- HACS installable custom integration
- Config flow (UI setup in Home Assistant)
- Setup fields in UI:
  - Device name
  - Converter IP
  - Port
  - Modbus ID (slave ID)
  - Poll interval
  - Timeout
- Exposes:
  - Sensors (temperatures and key status values)
  - Writable numbers (setpoint, limits, days)
  - Writable time entities (start/stop time, current clock)
  - Writable selects (mode, legionella, PV mode, holiday mode)
  - Writable switches (timer, boost)

## Install via HACS

1. In Home Assistant, open HACS.
2. `Integrations` -> menu `...` -> `Custom repositories`.
3. Add this GitHub repo URL and choose category `Integration`.
4. Install `Wolf FHS280` via HACS.
5. Restart Home Assistant.

## Setup in Home Assistant

1. `Settings` -> `Devices & Services` -> `Add Integration`.
2. Search for `Wolf FHS280`.
3. Enter your Modbus TCP settings:
   - Device name
   - Converter IP (for example `192.168.2.254`)
   - Port (for example `502`)
   - Modbus ID (for example `3`)
   - Poll interval
   - Timeout
