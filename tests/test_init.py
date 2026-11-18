"""Tests for the Ideal Clima integration setup and unload."""

from datetime import timedelta
from typing import Any
from unittest.mock import patch

from freezegun.api import FrozenDateTimeFactory
from modbus_connection import (
    ModbusConnectionError,
    ModbusError,
    ModbusSerialParams,
    ModbusTcpParams,
    ModbusTimeoutError,
)
from modbus_connection.mock import MockModbusConnection
import pytest
from pytest_homeassistant.common import MockConfigEntry, async_fire_time_changed

from custom_components.idealclima.const import (
    CONF_BAUDRATE,
    DOMAIN,
    SCAN_INTERVAL,
)
from custom_components.idealclima.coordinator import (
    IdealclimaDataUpdateCoordinator,
)
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_PORT, STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant

from . import (
    MOCK_DEVICE,
    MOCK_HOST,
    MOCK_SERIAL_ENTRY_DATA,
    MOCK_TCP_ENTRY_DATA,
    MOCK_UNIT_ID,
)


async def test_setup_and_unload_entry(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Test a config entry sets up and unloads with runtime_data populated."""
    assert init_integration.state is ConfigEntryState.LOADED
    assert isinstance(init_integration.runtime_data, IdealclimaDataUpdateCoordinator)

    await hass.config_entries.async_unload(init_integration.entry_id)
    await hass.async_block_till_done()

    assert not hass.config_entries.async_loaded_entries(DOMAIN)


@pytest.mark.parametrize(
    ("data", "expected_params"),
    [
        pytest.param(
            {**MOCK_TCP_ENTRY_DATA, CONF_PORT: 1502},
            ModbusTcpParams(host=MOCK_HOST, port=1502),
            id="tcp",
        ),
        pytest.param(
            {**MOCK_SERIAL_ENTRY_DATA, CONF_BAUDRATE: 19200},
            ModbusSerialParams(device=MOCK_DEVICE, baudrate=19200),
            id="serial",
        ),
    ],
)
async def test_setup_connects_over_configured_link(
    hass: HomeAssistant,
    mock_connection: MockModbusConnection,
    data: dict[str, Any],
    expected_params: ModbusSerialParams | ModbusTcpParams,
) -> None:
    """Test setup opens the link the entry is configured for."""
    entry = MockConfigEntry(domain=DOMAIN, data=data)
    entry.add_to_hass(hass)

    with patch(
        "custom_components.idealclima.async_get_unit",
        side_effect=lambda hass, entry, params, unit_id: mock_connection.for_unit(
            unit_id
        ),
    ) as mock_get_unit:
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done(wait_background_tasks=True)

    mock_get_unit.assert_called_once_with(hass, entry, expected_params, MOCK_UNIT_ID)


@pytest.mark.parametrize(
    "error",
    [
        pytest.param(ModbusTimeoutError("timeout"), id="timeout"),
        pytest.param(ModbusConnectionError("disconnected"), id="connection"),
        pytest.param(ModbusError("bus error"), id="modbus_error"),
    ],
)
@pytest.mark.usefixtures("mock_get_unit")
async def test_setup_retry_on_error(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_connection: MockModbusConnection,
    error: Exception,
) -> None:
    """Test setup enters SETUP_RETRY when the initial refresh fails."""
    mock_config_entry.add_to_hass(hass)
    mock_connection.for_unit(MOCK_UNIT_ID).fail_requests(error)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done(wait_background_tasks=True)

    assert mock_config_entry.state is ConfigEntryState.SETUP_RETRY


@pytest.mark.usefixtures("mock_get_unit")
async def test_setup_retry_on_incomplete_report(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_connection: MockModbusConnection,
) -> None:
    """Test setup enters SETUP_RETRY when a holding register read fails."""
    mock_config_entry.add_to_hass(hass)
    mock_connection.for_unit(MOCK_UNIT_ID).fail_read(28301, ModbusError("busy"))

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done(wait_background_tasks=True)

    assert mock_config_entry.state is ConfigEntryState.SETUP_RETRY


async def test_coordinator_direct_modbus_error(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test a direct non-connection ModbusError raised by async_update."""
    coordinator = init_integration.runtime_data
    entity_id = "climate.radiantore_skudo_dc_inverter_21"

    with patch.object(
        coordinator.device,
        "async_update",
        side_effect=ModbusError("direct error"),
    ):
        freezer.tick(timedelta(seconds=SCAN_INTERVAL))
        async_fire_time_changed(hass)
        await hass.async_block_till_done(wait_background_tasks=True)

    assert (state := hass.states.get(entity_id)) is not None
    assert state.state == STATE_UNAVAILABLE
