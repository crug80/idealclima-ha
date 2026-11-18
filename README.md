# Ideal Clima — Home Assistant Integration

Custom integration for **Ideal Clima** hydronic fan coil units connected over **Modbus TCP** or **Modbus RTU (RS-485)**, built on [`idealclima-modbus`](https://pypi.org/project/idealclima-modbus/) and Home Assistant's shared [`modbus-connection`](https://github.com/home-assistant-libs/modbus-connection) infrastructure (`homeassistant.components.modbus.async_get_unit`).

## Supported Models

- **Comfosplit IKARO HW**
- **Radiantore SKUDO DC Inverter** (with onboard controller `TQCT02`)

## Prerequisites

- **Home Assistant `2026.11.0` or newer**.
- **Modbus unit ID (`1–32`, excluding `15`)**: the unit's Modbus address **must be changed from the factory default `15`** before adding it to Home Assistant. Address `15` is reserved by Ideal Clima hardware for address programming only and does not support normal polling or control; the integration rejects `15` during setup and reconfiguration.
- **RS-485 serial parameters**: Ideal Clima factory default is `9600 bps`, `8N1`.
- **Modbus TCP**: reachable TCP gateway/bridge (default port `502`).

## Installation

### Option 1: HACS / Custom Repository

1. Open **HACS** in Home Assistant.
2. Open the top-right menu (`⋮`) → **Custom repositories**.
3. Add `https://github.com/crug80/idealclima-ha` with category **Integration**.
4. Search for **Ideal Clima**, click **Download**, and restart Home Assistant.

### Option 2: Manual Installation

1. Download the latest release from [GitHub Releases](https://github.com/crug80/idealclima-ha/releases).
2. Copy the `custom_components/idealclima` directory into `<config>/custom_components/idealclima` inside your Home Assistant configuration folder.
3. Restart Home Assistant.

## Configuration

1. In Home Assistant, go to **Settings** → **Devices & services** → **Add integration** and select **Ideal Clima**.
2. Choose how the fan coil is connected:
   - **Modbus TCP**: select the **Model**, and enter **Host**, **Port** (default `502`), and **Modbus unit ID** (`1–32`, excluding `15`).
   - **Serial port (Modbus RTU)**: select the **Model**, **Serial port** (local port or network serial proxy), **Baud rate** (default `9600`), and **Modbus unit ID** (`1–32`, excluding `15`).
3. Home Assistant probes the unit before creating the config entry. On success, the device is created as `<Model Name> (<unit_id>)`.

### Reconfiguration

To change the **Model**, **Modbus unit ID**, **Host/Port**, **Serial port/Baud rate**, or even switch an existing unit between **Modbus TCP** and **Serial (Modbus RTU)** without losing entity IDs or history:

1. Go to **Settings** → **Devices & services** → **Ideal Clima**.
2. Open the menu (`⋮`) next to the device entry and select **Reconfigure**.
3. Pick the connection type and update the pre-filled settings.

## Data Updates & Bus Sharing

- **Polling interval**: both live readings (`0x04` input registers) and configuration settings (`0x03` holding registers) are polled every **15 seconds**, so changes made on the onboard panel or via IR remote are reflected in Home Assistant.
- **Immediate refresh**: after any command from Home Assistant, the coordinator triggers an immediate refresh.
- **Shared Modbus link**: connections are leased through Home Assistant's `modbus` integration (`async_get_unit`). Multiple Ideal Clima units (or other `modbus-connection` integrations) sharing the same RS-485 bus or TCP gateway automatically serialize requests without port conflicts.

## Supported Platforms & Entities

| Platform | Models | Entities & Notes |
| :--- | :--- | :--- |
| `climate` | IKARO HW, SKUDO DC Inverter | Main thermostat (`0.5 °C` step, `18.0–30.0 °C` default range or `28308`/`28309` limits on SKUDO; modes `OFF`, `COOL`, `DRY`, `FAN_ONLY`, `HEAT`, plus `AUTO` on SKUDO; fan modes `super_silence`, `low`, `medium`, `high`, `auto`) |
| `sensor` | IKARO HW, SKUDO DC Inverter | Ambient temperature (`46801`); on SKUDO also Coil temperature (`46802`), Fan speed RPM (`46804`), Active operating regime (`46807`: `cool` / `heat`) |
| `binary_sensor` | SKUDO DC Inverter | Valve command (`46805`); Diagnostic: Power state (`46806`), DC inverter motor alarm (`46808`), Ambient sensor alarm (`46809`), Coil sensor alarm (`46810`) |
| `switch` | SKUDO DC Inverter | Sleep mode (`28305`); Config: Key lock (`28304`), Anti-draft (`28315`), Super silence speed enabled (`28316`), Water valve actuator present (`28317`), Key lock function enabled (`28322`), IR remote active with key lock (`28323`), Onboard panel password protection (`28324`), Intermittent fan at target temperature (`28327`) |
| `number` | SKUDO DC Inverter | Auto-off timer (`28306`), Auto-on timer (`28307`); Config: Maximum target temperature (`28308`), Minimum target temperature (`28309`), Anti-draft threshold temperature (`28314`) |
| `select` | SKUDO DC Inverter | Config: Display temperature unit (`28319`: `Celsius` / `Fahrenheit`) |

## Known Limitations & Model Notes

- **Factory address `15`**: units still set to `unit_id = 15` cannot be polled or controlled and are blocked by the config flow.
- **Comfosplit IKARO HW**:
  - Turning the unit off sets fan speed register `28303` to `0` (`OFF`); turning it back on restores the last active fan speed automatically.
  - `AUTO` mode and SKUDO configuration/diagnostic registers are not supported by IKARO HW hardware and are omitted.

## Diagnostics & Troubleshooting

If you encounter communication or register issues:

1. Go to **Settings** → **Devices & services** → **Ideal Clima** and open the affected device.
2. Click **Download diagnostics** (`⋮` → **Download diagnostics**).
3. The exported JSON contains coordinator status, device model, and all mapped `readings` and `settings` fields, with `host` automatically redacted.
4. Attach the diagnostics file when opening an issue on the [GitHub issue tracker](https://github.com/crug80/idealclima-ha/issues).

## Removal

1. Go to **Settings** → **Devices & services** → **Ideal Clima**.
2. Open the menu (`⋮`) next to each entry and select **Delete**.
3. If installed via HACS, remove the integration from HACS; if installed manually, delete `<config>/custom_components/idealclima` and restart Home Assistant.

## Development & Testing

```bash
uv run --no-sync pytest
uv run --no-sync ruff check .
uv run --no-sync mypy custom_components tests
```
