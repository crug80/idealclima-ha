# Comfosplit IKARO HW — Modbus RTU Specification

Extracted from *Comfosplit IKARO HW – Manuale per l'utente e per l'installatore* (§4.5 MODBUS RTU, pp. 14–15 / 68).

## Connection & Bus Settings

- **Connector**: 3-position RS-485 Modbus connector under the unit cover:
  - `1 - A+` (Yellow)
  - `2 - B-` (Green)
  - `3 - GND` (Grey)
- **Termination**: size the bus termination resistor according to the RS-485 network topology.
- **Serial parameters**: `9600 bps`, `8` data bits, `no` parity, `1` stop bit (`8N1`).
- **Default Modbus address**: **`15`** (range `1–32`).
  - When set to address `15`, the unit **only allows changing the Modbus address**; normal polling and parameter writes are disabled.
  - Before using the unit on a Modbus network or in Home Assistant, assign an address other than `15`.
- **Supported Modbus functions**:
  - `0x03`: Read Holding Registers
  - `0x04`: Read Input Registers
  - `0x10`: Write Multiple Registers

## Input Registers (`0x04`, Read-Only)

| Address | Description | Type | Format / Encoding | Default |
| :--- | :--- | :--- | :--- | :--- |
| `46801` | Measured ambient temperature | `Int16 signed` | Tenths of °C (`24 °C = 240`), `0.5 °C` precision | `-` |
| `46803` | Fan speed | `Int16 signed` | `0` = off, `1` = super silence, `2` = low, `3` = medium, `4` = high, `5` = very high, `6` = auto | `-` |

## Holding Registers (`0x03` / `0x10`, Read/Write)

| Address | Description | Type | Format / Encoding | Default |
| :--- | :--- | :--- | :--- | :--- |
| `28301` | Unit power | `Int16 signed` | `0` = unit off, `1` = unit on | `-` |
| `28302` | Operating mode | `Int16 signed` | `1` = cooling, `2` = dehumidification, `3` = fan only, `4` = heating | `-` |
| `28303` | Fan speed | `Int16 signed` | `1` = super silence, `2` = low, `3` = medium, `4` = high, `6` = auto | `-` |
| `28310` | Target temperature (cooling) | `Int16 signed` | Tenths of °C (`24 °C = 240`) | `-` |
| `28311` | Target temperature (heating) | `Int16 signed` | Tenths of °C (`24 °C = 240`) | `-` |
| `28321` | Unit Modbus address | `Int16 signed` | Valid range `1–32` | `15` |

## Changing the Modbus Address

The Modbus address at register `28321` can be updated via function `0x10` (Write Multiple Registers). To prevent accidental overwrites, address changes are **only accepted while a jumper is installed between `1 - COM` (Red) and `2 - LOW` (Black)** on the thermostat terminal block.
