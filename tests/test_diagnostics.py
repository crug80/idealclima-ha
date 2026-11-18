"""Tests for the Ideal Clima diagnostics platform."""

from datetime import timedelta

from freezegun.api import FrozenDateTimeFactory
from modbus_connection import ModbusTimeoutError
from modbus_connection.mock import MockModbusConnection
from pytest_homeassistant.common import MockConfigEntry, async_fire_time_changed

from custom_components.idealclima.const import SCAN_INTERVAL
from custom_components.idealclima.diagnostics import (
    async_get_config_entry_diagnostics,
)
from homeassistant.components.diagnostics import REDACTED
from homeassistant.const import CONF_HOST
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
    }


async def test_ikaro_diagnostics_after_failed_poll(
    hass: HomeAssistant,
    init_ikaro_integration: MockConfigEntry,
    mock_connection: MockModbusConnection,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test diagnostics captures IKARO state and coordinator failure details."""
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
