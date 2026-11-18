"""Tests for the Ideal Clima switch platform."""

from modbus_connection import ModbusError
from modbus_connection.mock import MockModbusConnection
import pytest

from homeassistant.components.switch import (
    DOMAIN as SWITCH_DOMAIN,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
)
from homeassistant.const import ATTR_ENTITY_ID, STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from . import MOCK_UNIT_ID


@pytest.mark.parametrize(
    ("entity_id", "register", "initial_state"),
    [
        pytest.param(
            "switch.radiantore_skudo_dc_inverter_21_sleep_mode",
            28305,
            STATE_OFF,
            id="sleep",
        ),
        pytest.param(
            "switch.radiantore_skudo_dc_inverter_21_key_lock",
            28304,
            STATE_OFF,
            id="key_lock",
        ),
        pytest.param(
            "switch.radiantore_skudo_dc_inverter_21_anti_draft",
            28315,
            STATE_ON,
            id="anti_draft_enabled",
        ),
        pytest.param(
            "switch.radiantore_skudo_dc_inverter_21_super_silence_speed_enabled",
            28316,
            STATE_ON,
            id="super_silence_enabled",
        ),
        pytest.param(
            "switch.radiantore_skudo_dc_inverter_21_water_valve_actuator_present",
            28317,
            STATE_ON,
            id="valve_present",
        ),
        pytest.param(
            "switch.radiantore_skudo_dc_inverter_21_key_lock_function_enabled",
            28322,
            STATE_OFF,
            id="key_lock_enabled",
        ),
        pytest.param(
            "switch.radiantore_skudo_dc_inverter_21_ir_remote_active_with_key_lock",
            28323,
            STATE_OFF,
            id="remote_enabled_with_key_lock",
        ),
        pytest.param(
            "switch.radiantore_skudo_dc_inverter_21_onboard_panel_password_protection",
            28324,
            STATE_OFF,
            id="password_enabled",
        ),
        pytest.param(
            "switch.radiantore_skudo_dc_inverter_21_intermittent_fan_at_target_temperature",
            28327,
            STATE_OFF,
            id="fan_intermittent",
        ),
    ],
)
@pytest.mark.usefixtures("init_integration")
async def test_skudo_switches_turn_on_and_off(
    hass: HomeAssistant,
    mock_connection: MockModbusConnection,
    entity_id: str,
    register: int,
    initial_state: str,
) -> None:
    """Test initial state, turn_on, and turn_off for every SKUDO switch."""
    unit = mock_connection.for_unit(MOCK_UNIT_ID)
    assert (state := hass.states.get(entity_id)) is not None
    assert state.state == initial_state

    await hass.services.async_call(
        SWITCH_DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: entity_id},
        blocking=True,
    )
    assert unit.holding[register] == 1
    assert (state := hass.states.get(entity_id)) is not None
    assert state.state == STATE_ON

    await hass.services.async_call(
        SWITCH_DOMAIN,
        SERVICE_TURN_OFF,
        {ATTR_ENTITY_ID: entity_id},
        blocking=True,
    )
    assert unit.holding[register] == 0
    assert (state := hass.states.get(entity_id)) is not None
    assert state.state == STATE_OFF


@pytest.mark.usefixtures("init_integration")
async def test_switch_write_error(
    hass: HomeAssistant,
    mock_connection: MockModbusConnection,
) -> None:
    """Test a ModbusError when writing a switch raises HomeAssistantError."""
    entity_id = "switch.radiantore_skudo_dc_inverter_21_sleep_mode"
    mock_connection.for_unit(MOCK_UNIT_ID).fail_write(28305, ModbusError("busy"))

    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            SWITCH_DOMAIN,
            SERVICE_TURN_ON,
            {ATTR_ENTITY_ID: entity_id},
            blocking=True,
        )


@pytest.mark.usefixtures("init_ikaro_integration")
async def test_ikaro_has_no_switches(hass: HomeAssistant) -> None:
    """Test IKARO HW does not create any switch entities."""
    assert hass.states.async_entity_ids(SWITCH_DOMAIN) == []
