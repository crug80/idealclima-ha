"""Tests for the Ideal Clima config flow."""

from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from typing import Any
from unittest.mock import AsyncMock, MagicMock, _patch, patch

from modbus_connection import (
    ModbusError,
    ModbusSerialParams,
    ModbusTcpParams,
    ModbusTimeoutError,
)
from modbus_connection.mock import MockModbusConnection, MockModbusUnit
import pytest
from pytest_homeassistant.common import MockConfigEntry

from custom_components.idealclima.const import (
    CONF_BAUDRATE,
    CONF_UNIT_ID,
    DOMAIN,
    FACTORY_DEFAULT_UNIT_ID,
    TYPE_SERIAL,
    TYPE_TCP,
    IdealclimaModel,
)
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_MODEL, CONF_PORT, CONF_TYPE
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.exceptions import HomeAssistantError

from . import (
    MOCK_DEVICE,
    MOCK_HOST,
    MOCK_IKARO_TCP_ENTRY_DATA,
    MOCK_SERIAL_ENTRY_DATA,
    MOCK_SERIAL_INPUT,
    MOCK_TCP_ENTRY_DATA,
    MOCK_TCP_INPUT,
    MOCK_UNIT_ID,
    seed_ikaro,
    seed_skudo,
)


def _patch_temporary_unit(
    connection: MockModbusConnection,
) -> _patch[MagicMock | AsyncMock]:
    """Stand in for async_get_temporary_unit, handing out a unit on connection."""

    @asynccontextmanager
    async def _get_temporary_unit(
        hass: HomeAssistant,
        params: ModbusSerialParams | ModbusTcpParams,
        unit_id: int,
    ) -> AsyncIterator[MockModbusUnit]:
        yield connection.for_unit(unit_id)

    return patch(
        "custom_components.idealclima.config_flow.async_get_temporary_unit",
        side_effect=_get_temporary_unit,
    )


class _RaisingTemporaryUnit:
    """Stand in for a temporary-unit context whose __aenter__ raises."""

    def __init__(self, error: Exception) -> None:
        """Initialize with the error to raise on entry."""
        self._error = error

    async def __aenter__(self) -> None:
        raise self._error

    async def __aexit__(self, *args: object) -> None:
        """No cleanup: entry never succeeded."""


async def _start_flow(hass: HomeAssistant, connection_type: str) -> str:
    """Open the flow, pick a connection type, and return the flow ID."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] is FlowResultType.MENU
    assert result["step_id"] == "user"
    assert result["menu_options"] == [TYPE_TCP, TYPE_SERIAL]

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"next_step_id": connection_type}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == connection_type
    assert result["errors"] == {}

    return result["flow_id"]


@pytest.mark.parametrize(
    (
        "connection_type",
        "seed",
        "user_input",
        "expected_params",
        "expected_title",
        "expected_data",
    ),
    [
        pytest.param(
            TYPE_TCP,
            seed_skudo,
            {**MOCK_TCP_INPUT, CONF_PORT: 1502},
            ModbusTcpParams(host=MOCK_HOST, port=1502),
            f"Radiantore SKUDO DC Inverter ({MOCK_UNIT_ID})",
            {**MOCK_TCP_ENTRY_DATA, CONF_PORT: 1502},
            id="tcp_skudo",
        ),
        pytest.param(
            TYPE_TCP,
            seed_ikaro,
            {**MOCK_TCP_INPUT, CONF_MODEL: IdealclimaModel.IKARO_HW},
            ModbusTcpParams(host=MOCK_HOST, port=502),
            f"Comfosplit IKARO HW ({MOCK_UNIT_ID})",
            MOCK_IKARO_TCP_ENTRY_DATA,
            id="tcp_ikaro",
        ),
        pytest.param(
            TYPE_SERIAL,
            seed_skudo,
            {**MOCK_SERIAL_INPUT, CONF_BAUDRATE: 19200},
            ModbusSerialParams(device=MOCK_DEVICE, baudrate=19200),
            f"Radiantore SKUDO DC Inverter ({MOCK_UNIT_ID})",
            {**MOCK_SERIAL_ENTRY_DATA, CONF_BAUDRATE: 19200},
            id="serial_skudo",
        ),
    ],
)
async def test_user_step_success(
    hass: HomeAssistant,
    mock_setup_entry: AsyncMock,
    connection_type: str,
    seed: Callable[[MockModbusUnit], None],
    user_input: dict[str, Any],
    expected_params: ModbusSerialParams | ModbusTcpParams,
    expected_title: str,
    expected_data: dict[str, Any],
) -> None:
    """Test each connection type and model probes the unit and creates an entry."""
    mock_conn = MockModbusConnection()
    seed(mock_conn.for_unit(MOCK_UNIT_ID))
    flow_id = await _start_flow(hass, connection_type)

    with _patch_temporary_unit(mock_conn) as mock_temporary_unit:
        result = await hass.config_entries.flow.async_configure(flow_id, user_input)

    mock_temporary_unit.assert_called_once_with(hass, expected_params, MOCK_UNIT_ID)
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == expected_title
    assert result["data"] == expected_data
    assert len(mock_setup_entry.mock_calls) == 1


@pytest.mark.usefixtures("mock_setup_entry")
async def test_factory_default_unit_id_rejected(hass: HomeAssistant) -> None:
    """Test unit ID 15 is rejected with a dedicated error and can recover."""
    flow_id = await _start_flow(hass, TYPE_TCP)

    result = await hass.config_entries.flow.async_configure(
        flow_id,
        {**MOCK_TCP_INPUT, CONF_UNIT_ID: FACTORY_DEFAULT_UNIT_ID},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == TYPE_TCP
    assert result["errors"] == {CONF_UNIT_ID: "factory_default_unit_id"}

    mock_conn = MockModbusConnection()
    seed_skudo(mock_conn.for_unit(MOCK_UNIT_ID))
    with _patch_temporary_unit(mock_conn):
        result = await hass.config_entries.flow.async_configure(flow_id, MOCK_TCP_INPUT)

    assert result["type"] is FlowResultType.CREATE_ENTRY


def _seed_timeout(connection: MockModbusConnection) -> None:
    """Fail all unit requests with a timeout."""
    connection.for_unit(MOCK_UNIT_ID).fail_requests(ModbusTimeoutError("timeout"))


def _seed_incomplete_poll(connection: MockModbusConnection) -> None:
    """Seed readings but fail a holding register read."""
    unit = connection.for_unit(MOCK_UNIT_ID)
    seed_skudo(unit)
    unit.fail_read(28301, ModbusError("illegal address"))


@pytest.mark.parametrize(
    "seed",
    [
        pytest.param(_seed_timeout, id="timeout"),
        pytest.param(_seed_incomplete_poll, id="incomplete_poll"),
    ],
)
@pytest.mark.usefixtures("mock_setup_entry")
async def test_user_step_cannot_connect(
    hass: HomeAssistant,
    seed: Callable[[MockModbusConnection], None],
) -> None:
    """Test connection and register errors report cannot_connect and recover."""
    mock_conn = MockModbusConnection()
    seed(mock_conn)
    flow_id = await _start_flow(hass, TYPE_TCP)

    with _patch_temporary_unit(mock_conn):
        result = await hass.config_entries.flow.async_configure(flow_id, MOCK_TCP_INPUT)

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == TYPE_TCP
    assert result["errors"] == {"base": "cannot_connect"}

    working_conn = MockModbusConnection()
    seed_skudo(working_conn.for_unit(MOCK_UNIT_ID))
    with _patch_temporary_unit(working_conn):
        result = await hass.config_entries.flow.async_configure(flow_id, MOCK_TCP_INPUT)

    assert result["type"] is FlowResultType.CREATE_ENTRY


@pytest.mark.parametrize(
    ("error", "expected_error"),
    [
        pytest.param(HomeAssistantError("in use"), "cannot_connect", id="link_clash"),
        pytest.param(RuntimeError("boom"), "unknown", id="unexpected"),
    ],
)
@pytest.mark.usefixtures("mock_setup_entry")
async def test_user_step_context_exceptions(
    hass: HomeAssistant,
    error: Exception,
    expected_error: str,
) -> None:
    """Test HomeAssistantError and unexpected exceptions are handled and recover."""
    flow_id = await _start_flow(hass, TYPE_TCP)

    with patch(
        "custom_components.idealclima.config_flow.async_get_temporary_unit",
        return_value=_RaisingTemporaryUnit(error),
    ):
        result = await hass.config_entries.flow.async_configure(flow_id, MOCK_TCP_INPUT)

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": expected_error}

    working_conn = MockModbusConnection()
    seed_skudo(working_conn.for_unit(MOCK_UNIT_ID))
    with _patch_temporary_unit(working_conn):
        result = await hass.config_entries.flow.async_configure(flow_id, MOCK_TCP_INPUT)

    assert result["type"] is FlowResultType.CREATE_ENTRY


@pytest.mark.parametrize(
    ("connection_type", "entry_data", "user_input"),
    [
        pytest.param(TYPE_TCP, MOCK_TCP_ENTRY_DATA, MOCK_TCP_INPUT, id="tcp"),
        pytest.param(
            TYPE_SERIAL, MOCK_SERIAL_ENTRY_DATA, MOCK_SERIAL_INPUT, id="serial"
        ),
    ],
)
async def test_already_configured(
    hass: HomeAssistant,
    connection_type: str,
    entry_data: dict[str, Any],
    user_input: dict[str, Any],
) -> None:
    """Test aborting when the same link endpoint and unit ID are already configured."""
    entry = MockConfigEntry(domain=DOMAIN, data=entry_data)
    entry.add_to_hass(hass)

    flow_id = await _start_flow(hass, connection_type)
    result = await hass.config_entries.flow.async_configure(flow_id, user_input)

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def _start_reconfigure_flow(
    hass: HomeAssistant, entry: MockConfigEntry, connection_type: str
) -> str:
    """Open the reconfigure flow, pick a connection type, and return the flow ID."""
    result = await entry.start_reconfigure_flow(hass)

    assert result["type"] is FlowResultType.MENU
    assert result["step_id"] == "reconfigure"
    assert result["menu_options"] == [TYPE_TCP, TYPE_SERIAL]

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"next_step_id": connection_type}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == connection_type
    assert result["errors"] == {}

    return result["flow_id"]


@pytest.mark.usefixtures("mock_setup_entry")
async def test_reconfigure_tcp_and_switch_to_serial(hass: HomeAssistant) -> None:
    """Test reconfiguring TCP settings and switching connection type to serial."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=MOCK_TCP_ENTRY_DATA,
        title=f"Radiantore SKUDO DC Inverter ({MOCK_UNIT_ID})",
    )
    entry.add_to_hass(hass)

    flow_id = await _start_reconfigure_flow(hass, entry, TYPE_TCP)
    mock_conn = MockModbusConnection()
    seed_ikaro(mock_conn.for_unit(MOCK_UNIT_ID))

    updated_tcp = {
        CONF_MODEL: IdealclimaModel.IKARO_HW,
        CONF_HOST: "192.168.1.200",
        CONF_PORT: 1502,
        CONF_UNIT_ID: MOCK_UNIT_ID,
    }
    with _patch_temporary_unit(mock_conn) as mock_temporary_unit:
        result = await hass.config_entries.flow.async_configure(flow_id, updated_tcp)

    mock_temporary_unit.assert_called_once_with(
        hass, ModbusTcpParams(host="192.168.1.200", port=1502), MOCK_UNIT_ID
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert entry.data == {CONF_TYPE: TYPE_TCP, **updated_tcp}
    assert entry.title == f"Comfosplit IKARO HW ({MOCK_UNIT_ID})"

    # Now switch from TCP to Serial
    flow_id = await _start_reconfigure_flow(hass, entry, TYPE_SERIAL)
    serial_conn = MockModbusConnection()
    seed_skudo(serial_conn.for_unit(MOCK_UNIT_ID))
    with _patch_temporary_unit(serial_conn) as mock_temporary_unit:
        result = await hass.config_entries.flow.async_configure(
            flow_id, MOCK_SERIAL_INPUT
        )

    mock_temporary_unit.assert_called_once_with(
        hass, ModbusSerialParams(device=MOCK_DEVICE, baudrate=9600), MOCK_UNIT_ID
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert entry.data == MOCK_SERIAL_ENTRY_DATA
    assert entry.title == f"Radiantore SKUDO DC Inverter ({MOCK_UNIT_ID})"


@pytest.mark.usefixtures("mock_setup_entry")
async def test_reconfigure_errors_and_duplicate_check(hass: HomeAssistant) -> None:
    """Test reconfigure handles validation errors, probe errors, and duplicates."""
    entry1 = MockConfigEntry(domain=DOMAIN, data=MOCK_TCP_ENTRY_DATA)
    entry2 = MockConfigEntry(
        domain=DOMAIN, data={**MOCK_TCP_ENTRY_DATA, CONF_UNIT_ID: 22}
    )
    entry1.add_to_hass(hass)
    entry2.add_to_hass(hass)

    # Factory default unit ID 15 is rejected, then probe error, then self-keep succeeds
    flow_id = await _start_reconfigure_flow(hass, entry1, TYPE_TCP)
    result = await hass.config_entries.flow.async_configure(
        flow_id, {**MOCK_TCP_INPUT, CONF_UNIT_ID: FACTORY_DEFAULT_UNIT_ID}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {CONF_UNIT_ID: "factory_default_unit_id"}

    failing_conn = MockModbusConnection()
    _seed_timeout(failing_conn)
    with _patch_temporary_unit(failing_conn):
        result = await hass.config_entries.flow.async_configure(flow_id, MOCK_TCP_INPUT)
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}

    working_conn = MockModbusConnection()
    seed_skudo(working_conn.for_unit(MOCK_UNIT_ID))
    with _patch_temporary_unit(working_conn):
        result = await hass.config_entries.flow.async_configure(flow_id, MOCK_TCP_INPUT)
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"

    # Colliding with entry2 aborts with already_configured
    flow_id = await _start_reconfigure_flow(hass, entry1, TYPE_TCP)
    result = await hass.config_entries.flow.async_configure(
        flow_id, {**MOCK_TCP_INPUT, CONF_UNIT_ID: 22}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
