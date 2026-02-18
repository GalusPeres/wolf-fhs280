# Wolf FHS280 (Home Assistant Custom Integration)

Custom integration for Wolf FHS 280 via Modbus TCP.

## Features

- HACS installable custom integration
- Config flow (UI setup in Home Assistant)
- Freely selectable during setup:
  - Converter IP
  - Port
  - Modbus ID (slave ID)
  - Poll interval
  - Timeout
- Exposes:
  - Sensors (raw + mapped text states)
  - Writable numbers (setpoint, times, days)
  - Writable selects (mode, legionella, PV mode, holiday mode)
  - Writable switches (timer, boost)

## Install via HACS

1. Push this repo to GitHub.
2. In Home Assistant, open HACS.
3. `Integrations` -> menu `...` -> `Custom repositories`.
4. Add your GitHub repo URL and choose category `Integration`.
5. Install `Wolf FHS280` via HACS.
6. Restart Home Assistant.

## Setup in Home Assistant

1. `Settings` -> `Devices & Services` -> `Add Integration`.
2. Search for `Wolf FHS280`.
3. Enter:
   - Converter IP (for example `192.168.2.254`)
   - Port (usually `502`)
   - Modbus ID (choose your device ID here)
   - Poll interval
   - Timeout

No YAML is required for this integration.


