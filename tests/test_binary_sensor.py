"""Tests for the Ideal Clima binary sensor platform."""

from datetime import timedelta

from freezegun.api import FrozenDateTimeFactory
from modbus_connection.mock import MockModbusConnection
import pytest
from pytest_homeassistant.common import async_fire_time_changed

from custom_components.idealclima.const import SCAN_INTERVAL
from homeassistant.components.binary_sensor import (
    DOMAIN as BINARY_SENSOR_DOMAIN,
    BinarySensorDeviceClass,
)
from homeassistant.const import ATTR_DEVICE_CLASS, STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant

from . import MOCK_UNIT_ID


@pytest.mark.parametrize(
    ("entity_id", "expected_state", "expected_device_class"),
    [
        pytest.param(
            "binary_sensor.radiantore_skudo_dc_inverter_21_valve_command",
            STATE_ON,
            BinarySensorDeviceClass.OPENING,
            id="valve_command",
        ),
        pytest.param(
            "binary_sensor.radiantore_skudo_dc_inverter_21_power_state",
            STATE_ON,
            BinarySensorDeviceClass.RUNNING,
            id="power_state",
        ),
        pytest.param(
            "binary_sensor.radiantore_skudo_dc_inverter_21_dc_inverter_motor_alarm",
            STATE_OFF,
            BinarySensorDeviceClass.PROBLEM,
            id="motor_alarm",
        ),
        pytest.param(
            "binary_sensor.radiantore_skudo_dc_inverter_21_ambient_temperature_sensor_alarm",
            STATE_OFF,
            BinarySensorDeviceClass.PROBLEM,
            id="ambient_sensor_alarm",
        ),
        pytest.param(
            "binary_sensor.radiantore_skudo_dc_inverter_21_coil_temperature_sensor_alarm",
            STATE_OFF,
            BinarySensorDeviceClass.PROBLEM,
            id="coil_sensor_alarm",
        ),
    ],
)
@pytest.mark.usefixtures("init_integration")
async def test_skudo_binary_sensors(
    hass: HomeAssistant,
    entity_id: str,
    expected_state: str,
    expected_device_class: BinarySensorDeviceClass,
) -> None:
    """Test SKUDO DC Inverter binary sensor states and device classes."""
    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state == expected_state
    assert state.attributes[ATTR_DEVICE_CLASS] == expected_device_class


@pytest.mark.usefixtures("init_integration")
async def test_skudo_alarm_state_change(
    hass: HomeAssistant,
    mock_connection: MockModbusConnection,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test binary sensor state updates when an alarm register turns on."""
    entity_id = "binary_sensor.radiantore_skudo_dc_inverter_21_dc_inverter_motor_alarm"
    unit = mock_connection.for_unit(MOCK_UNIT_ID)
    unit.input[46808] = 1

    freezer.tick(timedelta(seconds=SCAN_INTERVAL))
    async_fire_time_changed(hass)
    await hass.async_block_till_done(wait_background_tasks=True)

    assert (state := hass.states.get(entity_id)) is not None
    assert state.state == STATE_ON


@pytest.mark.usefixtures("init_ikaro_integration")
async def test_ikaro_has_no_binary_sensors(hass: HomeAssistant) -> None:
    """Test IKARO HW does not create any binary sensors."""
    assert hass.states.async_entity_ids(BINARY_SENSOR_DOMAIN) == []
