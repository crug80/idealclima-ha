# AGENTS.md — `idealclima-ha`

Guidelines for AI coding agents working in this Home Assistant custom integration repository.

## Project Overview

- **Integration domain**: `idealclima` (`custom_components/idealclima/`)
- **Supported hardware**:
  - **Comfosplit IKARO HW**
  - **Radiantore SKUDO DC Inverter** (onboard controller `TQCT02`)
- **Device library**: [`idealclima-modbus`](https://pypi.org/project/idealclima-modbus/) (latest version pinned in `manifest.json` / `pyproject.toml`), built on `modbus-connection`.
- **Modbus protocol specs**: see [docs/modbus/ikaro-hw.md](docs/modbus/ikaro-hw.md) and [docs/modbus/skudo-dc-inverter.md](docs/modbus/skudo-dc-inverter.md).

## Architecture & Coding Rules

1. **Follow Home Assistant Modbus internals** (`https://contributors.home-assistant.io/core/internals/modbus/`):
   - Never open raw TCP sockets or direct `pymodbus`/`tmodbus` clients.
   - Always lease shared units from `homeassistant.components.modbus`:
     - `async_get_unit` in `custom_components/idealclima/__init__.py`
     - `async_get_temporary_unit` in `custom_components/idealclima/config_flow.py`
2. **Quality & Typing Standards**:
   - Strict typing (`mypy` `strict = true`), `@override` on overridden methods, concise docstrings, no duplicated logic.
   - Keep `ruff` lint (`E`, `F`, `I`, `UP`, `B`, `SIM`, `ASYNC`, `RUF`) and formatting clean.
   - Maintain **100% test coverage** (`--cov-fail-under=100` in `pyproject.toml`).
3. **Hardware & Domain Invariants**:
   - **Factory address `15`**: Modbus `unit_id = 15` only allows address reprogramming on hardware and must remain blocked in `config_flow.py` (`factory_default_unit_id`). Valid range: `1–32` excluding `15`.
   - **Temperature precision & limits**: `0.5 °C` step (`PRECISION_HALVES`); default range `18.0–30.0 °C` (SKUDO dynamically reads `28309` / `28308` with fallback to defaults).
   - **IKARO HW specifics**: powering off sets `28303` (`fan_speed`) to `0` (`OFF`); powering back on restores the last active fan speed via `idealclima_modbus.IkaroHW`.
   - **SKUDO `AUTO` mode**: uses input register `46807` (`running_mode`) to select between `target_temp_auto_cool` (`28312`) and `target_temp_auto_heat` (`28313`).
   - **Coordinator writes**: `IdealclimaEntity._async_execute` must translate `ModbusError` into translated `HomeAssistantError` and call `await self.coordinator.async_refresh()`.
4. **Translations & Metadata**:
   - Keep `custom_components/idealclima/strings.json`, `translations/en.json`, and `translations/it.json` synchronized (with `[%key:...%]` expanded in `translations/*.json`).
   - Keep keys in `custom_components/idealclima/manifest.json` sorted alphabetically after `domain` and `name`.
5. **Custom Integration & Git Workflow**:
   - Do not add a `quality_scale` key to `manifest.json` (reserved for `home-assistant/core`).
   - Make changes on feature branches and submit via Pull Requests so CI (`Tests`, `Hassfest validation`, and `HACS validation`) runs before merging to `main`.

## Verification Commands

```bash
uv sync --locked
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run mypy custom_components tests
```
