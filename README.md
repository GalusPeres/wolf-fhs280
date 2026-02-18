# Wolf FHS280 (Home Assistant Custom Integration)

Custom integration for Wolf FHS280 using the existing Home Assistant Modbus integration.

## Features

- HACS installable custom integration
- Config flow (UI setup in Home Assistant)
- Uses your existing `modbus:` hub from Home Assistant YAML
- Freely selectable during setup:
  - Device name
  - Modbus hub name
  - Modbus ID (slave ID)
  - Poll interval
- Exposes:
  - Sensors (raw + mapped text states)
  - Writable numbers (setpoint, times, days)
  - Writable selects (mode, legionella, PV mode, holiday mode)
  - Writable switches (timer, boost)

## Prerequisite

Configure Home Assistant Modbus first (for example):

```yaml
modbus:
  - name: waveshare_modbus_gateway
    type: tcp
    host: 192.168.2.254
    port: 502
```

## Install via HACS

1. In Home Assistant, open HACS.
2. `Integrations` -> menu `...` -> `Custom repositories`.
3. Add this GitHub repo URL and choose category `Integration`.
4. Install `Wolf FHS280` via HACS.
5. Restart Home Assistant.

## Setup in Home Assistant

1. `Settings` -> `Devices & Services` -> `Add Integration`.
2. Search for `Wolf FHS280`.
3. Enter:
   - Device name
   - Modbus hub name (for example `waveshare_modbus_gateway`)
   - Modbus ID (for example `3`)
   - Poll interval