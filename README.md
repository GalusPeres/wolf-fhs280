# Wolf FHS280 (Home Assistant Custom Integration)

Custom integration for Wolf FHS280 via Modbus TCP.

## Important Change

This integration now reuses Home Assistant's built-in `modbus` hub from `configuration.yaml`.
It does **not** open a second direct TCP connection anymore.

## Required YAML (Gateway Head)

Add this in `configuration.yaml` (adjust `host` if needed):

```yaml
modbus:
  - name: waveshare_modbus_gateway
    type: tcp
    host: 192.168.2.254
    port: 502
    timeout: 5
    message_wait_milliseconds: 50
```

You can keep your other modbus sensors/meters in the same `modbus:` block.

## Features

- HACS installable custom integration
- Config flow (UI setup in Home Assistant)
- Setup fields in UI:
  - Device name
  - Modbus hub name from YAML (exact, e.g. `waveshare_modbus_gateway`)
  - Modbus ID (slave ID, e.g. `3`)
  - Poll interval
- Exposes:
  - Sensors (temperatures and key status values)
  - Read-only sensor for device clock (`Geräteuhrzeit`)
  - Writable numbers (setpoint, limits, days). Setpoint is limited by device `t_max`.
  - Writable time entities (start/stop time)
  - Button to sync device clock once with Home Assistant time
  - Writable selects (mode, legionella, PV mode, holiday mode)
  - Writable switches (timer, boost)

## Install via HACS

1. In Home Assistant, open HACS.
2. `Integrations` -> menu `...` -> `Custom repositories`.
3. Add this GitHub repo URL and choose category `Integration`.
4. Install `Wolf FHS280` via HACS.
5. Restart Home Assistant.

## Setup in Home Assistant

1. Ensure the YAML `modbus:` hub is configured (see above).
2. Restart Home Assistant after YAML changes.
3. Go to `Settings` -> `Devices & Services` -> `Add Integration`.
4. Search for `Wolf FHS280`.
5. Enter:
   - Device name
   - Modbus hub name from YAML (exact, e.g. `waveshare_modbus_gateway`)
   - Modbus ID (e.g. `3`)
   - Poll interval
