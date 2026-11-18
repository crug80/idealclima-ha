# Ideal Clima — Home Assistant Integration

Custom integration for **Ideal Clima** hydronic fan coil units connected over **Modbus TCP** or **Modbus RTU (RS-485)**, built on top of [`idealclima-modbus`](https://pypi.org/project/idealclima-modbus/) and Home Assistant's shared [`modbus-connection`](https://github.com/home-assistant-libs/modbus-connection) infrastructure (`modbus.async_get_unit`).

## Supported Models

- **Comfosplit IKARO HW**
- **Radiantore SKUDO DC Inverter** (with onboard controller `TQCT02`)

## Prerequisites

- The unit's Modbus address (`unit_id`, range `1–32`) **must be changed from the factory default `15`** before adding it to Home Assistant. Address `15` is reserved by Ideal Clima hardware for address programming only and does not allow normal polling or control.
- Default RS-485 serial parameters: `9600 bps`, `8N1`.

## Supported Platforms

| Platform | Models | Entities |
| :--- | :--- | :--- |
| `climate` | IKARO HW, SKUDO DC Inverter | Main thermostat (`OFF`, `COOL`, `DRY`, `FAN_ONLY`, `HEAT`, plus `AUTO` on SKUDO; fan modes `super_silence`, `low`, `medium`, `high`, `auto`) |
| `sensor` | IKARO HW, SKUDO DC Inverter | Ambient temperature (`46801`); on SKUDO also Coil temperature (`46802`), Fan speed RPM (`46804`), Active operating regime (`46807`) |
| `binary_sensor` | SKUDO DC Inverter | Valve command (`46805`), Power state (`46806`), DC inverter motor alarm (`46808`), Ambient sensor alarm (`46809`), Coil sensor alarm (`46810`) |
| `switch` | SKUDO DC Inverter | Sleep mode (`28305`), Key lock (`28304`), Anti-draft (`28315`), Super silence enabled (`28316`), Water valve present (`28317`), Key lock enabled (`28322`), IR remote with key lock (`28323`), Password protection (`28324`), Intermittent fan (`28327`) |
| `number` | SKUDO DC Inverter | Auto-off timer (`28306`), Auto-on timer (`28307`), Maximum target temperature (`28308`), Minimum target temperature (`28309`), Anti-draft threshold (`28314`) |
| `select` | SKUDO DC Inverter | Display temperature unit (`28319`: `Celsius` / `Fahrenheit`) |

## Development & Testing

```bash
uv run pytest
uv run ruff check .
uv run mypy custom_components tests
```
