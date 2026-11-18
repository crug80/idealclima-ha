# Radiantore SKUDO DC Inverter — Modbus RTU Specification

Extracted from *Radiantore SKUDO DC Inverter – Manuale per l'utente e per l'installatore* (pp. 14–17 / 36, §5.3 MODBUS RTU).

## Connection & Bus Settings

- **Hardware prerequisite**: Modbus RTU is only available when equipped with onboard controller **`TQCT02`**.
- **Connector**: RS-485 wires (`A` and `B`) on connector `NET2` outside the electrical box.
- **Termination**: size the bus termination resistor according to the RS-485 network topology.
- **Serial parameters**: `9600 bps`, `8` data bits, `no` parity, `1` stop bit (`8N1`).
- **Default Modbus address**: **`15`** (range `1–32`).
- **Supported Modbus functions**:
  - `0x03`: Read Holding Registers
  - `0x04`: Read Input Registers
  - `0x10`: Write Multiple Registers

## Input Registers (`0x04`, Read-Only)

| Address | Description | Type | Format / Encoding | Default |
| :--- | :--- | :--- | :--- | :--- |
| `46801` | Measured ambient temperature | `Int16 signed` | Tenths of °C (`24 °C = 240`), `0.5 °C` precision | `-` |
| `46802` | Measured coil temperature | `Int16 signed` | Tenths of °C (`24 °C = 240`), `0.5 °C` precision | `-` |
| `46803` | Fan speed | `Int16 signed` | `0` = off, `1` = super silence, `2` = low, `3` = medium, `4` = high, `5` = very high, `6` = auto | `-` |
| `46804` | Fan speed (RPM) | `Int16 signed` | Revolutions per minute | `-` |
| `46805` | Valve command | `Int16 signed` | `0` = no command, `1` = phase sent to valve (`Out 1`) | `-` |
| `46806` | Unit power state | `Int16 signed` | `0` = off, `1` = on | `-` |
| `46807` | Active operating regime | `Int16 signed` | `0` = cooling mode, `1` = heating mode | `-` |
| `46808` | DC Inverter motor alarm | `Int16 signed` | `0` = no alarm, `1` = motor fault | `-` |
| `46809` | Ambient temperature sensor alarm | `Int16 signed` | `0` = no alarm, `1` = sensor fault | `-` |
| `46810` | Coil temperature sensor alarm | `Int16 signed` | `0` = no alarm, `1` = sensor fault | `-` |

## Holding Registers (`0x03` / `0x10`, Read/Write)

| Address | Description | Type | Format / Encoding | Default |
| :--- | :--- | :--- | :--- | :--- |
| `28301` | Unit power | `Int16 signed` | `0` = off, `1` = on | `-` |
| `28302` | Operating mode | `Int16 signed` | `0` = auto, `1` = cooling, `2` = dehumidification, `3` = fan only, `4` = heating | `-` |
| `28303` | Fan speed | `Int16 signed` | `1` = super silence, `2` = low, `3` = medium, `4` = high, `6` = auto | `-` |
| `28304` | Key lock (public buildings) | `Int16 signed` | `0` = panel unlocked, `1` = panel locked (requires `28322 = 1`) | `-` |
| `28305` | Sleep mode (night setback) | `Int16 signed` | `0` = off, `1` = on | `-` |
| `28306` | Auto-off timer | `Int16 signed` | `0` = disabled, `1–11` = hours until auto-off | `-` |
| `28307` | Auto-on timer | `Int16 signed` | `0` = disabled, `1–11` = hours until auto-on | `-` |
| `28308` | Maximum target temperature limit | `Int16 signed` | Tenths of °C (`24 °C = 240`) | `300` |
| `28309` | Minimum target temperature limit | `Int16 signed` | Tenths of °C (`24 °C = 240`) | `180` |
| `28310` | Target temperature (cooling) | `Int16 signed` | Tenths of °C (`24 °C = 240`) | `-` |
| `28311` | Target temperature (heating) | `Int16 signed` | Tenths of °C (`24 °C = 240`) | `-` |
| `28312` | Target temperature (auto cooling) | `Int16 signed` | Tenths of °C (`24 °C = 240`) | `-` |
| `28313` | Target temperature (auto heating) | `Int16 signed` | Tenths of °C (`24 °C = 240`) | `-` |
| `28314` | Anti-draft threshold temperature | `Int16 signed` | Tenths of °C; coil temp below which fan stays off in heating | `250` |
| `28315` | Anti-draft enabled | `Int16 signed` | `0` = disabled, `1` = enabled | `1` |
| `28316` | Super silence speed enabled | `Int16 signed` | `0` = disabled, `1` = enabled | `0` |
| `28317` | Water valve actuator present | `Int16 signed` | `0` = disabled (`OUT1` not driven), `1` = enabled (`OUT1` driven) | `0` |
| `28318` | Reserved | `Int16 signed` | Reserved, do not use | `0` |
| `28319` | Display temperature unit | `Int16 signed` | `0` = °C, `1` = °F *(manual p. 17 has a typo listing both as `0`; p. 14 Par. 12 confirms `0 = °C`, `1 = °F`)* | `0` |
| `28320` | Reserved | `Int16 signed` | Reserved, do not use | `0` |
| `28321` | Unit Modbus address | `Int16 signed` | Valid range `1–32` | `15` |
| `28322` | Key lock function enabled | `Int16 signed` | `0` = disabled, `1` = enabled | `-` |
| `28323` | IR remote allowed with key lock | `Int16 signed` | `0` = IR remote disabled when locked, `1` = IR remote allowed | `-` |
| `28324` | Onboard panel password protection | `Int16 signed` | `0` = no password required, `1` = password required | `0` |
| `28325` | Reserved | `Int16 signed` | Reserved, do not use | `0` |
| `28326` | Reserved | `Int16 signed` | Reserved, do not use | `0` |
| `28327` | Intermittent fan at target temp | `Int16 signed` | `0` = fan stops at target, `1` = fan runs intermittently to maintain target | `0` |

## Onboard Controller Parameters (Manual p. 14, Par. 7–20)

Parameters configurable from the onboard `TQCT02` panel (also exposed via Modbus RTU where mapped above):

| Par. | Parameter | Description | Default | Range |
| :--- | :--- | :--- | :--- | :--- |
| `7` | Anti-draft | Min coil temp (°C) before fan starts in heating (`0` = off) | `25` | `0–40` |
| `8` | Anti-hot-air | In cooling, wait for coil < `23 °C` before fan starts (`0` = off, `1` = on) | `0` | `0–1` |
| `9` | Reserved | Reserved, do not modify | `1` | `0–1` |
| `10` | Actuator command | Drive valve actuator (`0` = no, `1` = yes) | `1` | `0–1` |
| `11` | Reserved | Fixed value | `0` | `0–1` |
| `12` | Temperature scale | `0` = Celsius, `1` = Fahrenheit | `0` | `0–1` |
| `13` | Standalone unit | `1` = independent, `0` = requires `Remote IN` contact closed | `1` | `0–1` |
| `14` | Modbus address | Slave address on RS-485 bus | `15` | `1–32` |
| `15` | Sleep remote behavior | `0` = fan stops after 1h, `1` = fan drops to min after 1h | `1` | `0–1` |
| `16` | Remote with key lock | `0` = IR remote disabled when locked, `1` = enabled | `0` | `0–1` |
| `17` | Reserved | Fixed value | `0` | `0–1` |
| `18` | Reserved | Fixed value | `0` | `0–99` |
| `19` | Reserved | Fixed value | `0` | `0–99` |
| `20` | Intermittent fan | `0` = disabled, `1` = intermittent fan at target temp | `1` | `0–1` |
