"""Tests for the Ideal Clima number platform."""

from modbus_connection import ModbusError
from modbus_connection.mock import MockModbusConnection
import pytest
from pytest_homeassistant.common import MockConfigEntry

from homeassistant.components.number import (
    ATTR_VALUE,
    DOMAIN as NUMBER_DOMAIN,
    SERVICE_SET_VALUE,
)
from homeassistant.const import ATTR_ENTITY_ID, STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError

from . import MOCK_UNIT_ID


@pytest.mark.parametrize(
    ("entity_id", "register", "initial_state", "new_value", "expected_raw"),
    [
        pytest.param(
            "number.radiantore_skudo_dc_inverter_21_auto_off_timer",
            28306,
            "0.0",
            4,
            4,
            id="timer_off_hours",
        ),
        pytest.param(
            "number.radiantore_skudo_dc_inverter_21_auto_on_timer",
            28307,
            "0.0",
            6,
            6,
            id="timer_on_hours",
        ),
        pytest.param(
            "number.radiantore_skudo_dc_inverter_21_maximum_target_temperature",
            28308,
            "30.0",
            28.5,
            285,
            id="max_target_temp",
        ),
        pytest.param(
            "number.radiantore_skudo_dc_inverter_21_minimum_target_temperature",
            28309,
            "18.0",
            19.5,
            195,
            id="min_target_temp",
        ),
        pytest.param(
            "number.radiantore_skudo_dc_inverter_21_anti_draft_threshold_temperature",
            28314,
            "25.0",
            27.0,
            270,
            id="anti_draft_threshold",
        ),
    ],
)
@pytest.mark.usefixtures("init_integration")
async def test_skudo_numbers_read_and_write(
    hass: HomeAssistant,
    mock_connection: MockModbusConnection,
    entity_id: str,
    register: int,
    initial_state: str,
    new_value: float,
    expected_raw: int,
) -> None:
    """Test initial value and set_value for every SKUDO number entity."""
    unit = mock_connection.for_unit(MOCK_UNIT_ID)
    assert (state := hass.states.get(entity_id)) is not None
    assert state.state == initial_state

    await hass.services.async_call(
        NUMBER_DOMAIN,
        SERVICE_SET_VALUE,
        {ATTR_ENTITY_ID: entity_id, ATTR_VALUE: new_value},
        blocking=True,
    )

    assert unit.holding[register] == expected_raw
    assert (state := hass.states.get(entity_id)) is not None
    assert state.state == str(float(new_value))


async def test_number_none_and_write_error(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    mock_connection: MockModbusConnection,
) -> None:
    """Test number entity handles None value and ModbusError on write."""
    entity_id = "number.radiantore_skudo_dc_inverter_21_auto_off_timer"
    mock_connection.for_unit(MOCK_UNIT_ID).fail_write(28306, ModbusError("busy"))

    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            NUMBER_DOMAIN,
            SERVICE_SET_VALUE,
            {ATTR_ENTITY_ID: entity_id, ATTR_VALUE: 2},
            blocking=True,
        )

    coordinator = init_integration.runtime_data
    coordinator.device.settings._values.clear()
    coordinator.async_update_listeners()
    await hass.async_block_till_done()

    assert (state := hass.states.get(entity_id)) is not None
    assert state.state == STATE_UNKNOWN


@pytest.mark.parametrize(
    ("entity_id", "register", "invalid_value", "unchanged_raw"),
    [
        pytest.param(
            "number.radiantore_skudo_dc_inverter_21_minimum_target_temperature",
            28309,
            30.0,
            180,
            id="min_at_or_above_max",
        ),
        pytest.param(
            "number.radiantore_skudo_dc_inverter_21_maximum_target_temperature",
            28308,
            18.0,
            300,
            id="max_at_or_below_min",
        ),
    ],
)
@pytest.mark.usefixtures("init_integration")
async def test_skudo_temperature_limits_reject_crossing(
    hass: HomeAssistant,
    mock_connection: MockModbusConnection,
    entity_id: str,
    register: int,
    invalid_value: float,
    unchanged_raw: int,
) -> None:
    """Test setting min >= max or max <= min raises ServiceValidationError."""
    unit = mock_connection.for_unit(MOCK_UNIT_ID)

    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            NUMBER_DOMAIN,
            SERVICE_SET_VALUE,
            {ATTR_ENTITY_ID: entity_id, ATTR_VALUE: invalid_value},
            blocking=True,
        )

    assert unit.holding[register] == unchanged_raw


@pytest.mark.usefixtures("init_ikaro_integration")
async def test_ikaro_has_no_numbers(hass: HomeAssistant) -> None:
    """Test IKARO HW does not create any number entities."""
    assert hass.states.async_entity_ids(NUMBER_DOMAIN) == []
