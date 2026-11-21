"""Tests for the Ideal Clima diagnostics platform."""

from datetime import timedelta
from unittest.mock import MagicMock

from freezegun.api import FrozenDateTimeFactory
from modbus_connection import ModbusError, ModbusTimeoutError
from modbus_connection.mock import MockModbusConnection
from pytest_homeassistant.common import MockConfigEntry, async_fire_time_changed

from custom_components.idealclima.const import (
    CONF_BAUDRATE,
    CONF_UNIT_ID,
    DOMAIN,
    SCAN_INTERVAL,
    TYPE_SERIAL,
    IdealclimaModel,
)
from custom_components.idealclima.diagnostics import (
    async_get_config_entry_diagnostics,
)
from homeassistant.components.diagnostics import REDACTED
from homeassistant.const import CONF_DEVICE, CONF_HOST, CONF_MODEL, CONF_TYPE
from homeassistant.core import HomeAssistant

from . import MOCK_UNIT_ID


async def test_skudo_diagnostics(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Test diagnostics output for a SKUDO DC Inverter entry."""
    result = await async_get_config_entry_diagnostics(hass, init_integration)

    assert result["entry"]["entry_id"] == init_integration.entry_id
    assert result["entry"]["title"] == init_integration.title
    assert result["entry"]["data"][CONF_HOST] == REDACTED
    assert result["entry"]["data"]["unit_id"] == MOCK_UNIT_ID

    assert result["coordinator"]["last_update_success"] is True
    assert result["coordinator"]["last_exception"] is None
    assert result["coordinator"]["update_interval_seconds"] == float(SCAN_INTERVAL)

    device = result["device"]
    assert device["model"] == "SkudoDCInverter"
    assert device["readings"]["ambient_temperature"] == 22.5
    assert device["readings"]["running_mode"] == "heat"
    assert device["settings"]["mode"] == "heat"
    assert device["settings"]["fan_speed"] == "low"
    assert device["settings"]["temperature_unit"] == "celsius"
    assert device["last_update_report"] == {
        "complete": True,
        "updated": ["readings", "settings"],
        "failed": [],
    }


async def test_ikaro_diagnostics_after_failed_poll(
    hass: HomeAssistant,
    init_ikaro_integration: MockConfigEntry,
    mock_connection: MockModbusConnection,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test diagnostics captures IKARO state and clears report on timeout."""
    mock_connection.for_unit(MOCK_UNIT_ID).fail_requests(ModbusTimeoutError("timeout"))
    freezer.tick(timedelta(seconds=SCAN_INTERVAL))
    async_fire_time_changed(hass)
    await hass.async_block_till_done(wait_background_tasks=True)

    result = await async_get_config_entry_diagnostics(hass, init_ikaro_integration)

    assert result["coordinator"]["last_update_success"] is False
    assert result["coordinator"]["last_exception"] is not None
    assert result["device"]["model"] == "IkaroHW"
    assert result["device"]["readings"]["ambient_temperature"] == 23.5
    assert result["device"]["settings"]["mode"] == "heat"
    assert result["device"]["last_update_report"] is None


async def test_skudo_diagnostics_after_partial_poll_failure(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    mock_connection: MockModbusConnection,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test diagnostics reports partial failure instead of previous success."""
    mock_connection.for_unit(MOCK_UNIT_ID).fail_read(
        28301, ModbusError("settings read failed")
    )
    freezer.tick(timedelta(seconds=SCAN_INTERVAL))
    async_fire_time_changed(hass)
    await hass.async_block_till_done(wait_background_tasks=True)

    result = await async_get_config_entry_diagnostics(hass, init_integration)

    assert result["coordinator"]["last_update_success"] is False
    assert result["coordinator"]["last_exception"] is not None
    assert result["device"]["last_update_report"] == {
        "complete": False,
        "updated": ["readings"],
        "failed": ["settings"],
    }


async def test_serial_socket_device_redacted_in_diagnostics(
    hass: HomeAssistant,
    mock_get_unit: MagicMock,
) -> None:
    """Test serial device endpoints (including socket:// URLs) are redacted."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_MODEL: IdealclimaModel.SKUDO_DC_INVERTER,
            CONF_TYPE: TYPE_SERIAL,
            CONF_DEVICE: "socket://192.168.1.50:5000",
            CONF_BAUDRATE: 9600,
            CONF_UNIT_ID: MOCK_UNIT_ID,
        },
        title=f"Radiantore SKUDO DC Inverter ({MOCK_UNIT_ID})",
        entry_id="01JIDEALCLIMASERIAL000001",
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done(wait_background_tasks=True)

    result = await async_get_config_entry_diagnostics(hass, entry)

    assert result["entry"]["data"][CONF_DEVICE] == REDACTED
