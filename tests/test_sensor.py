"""Tests for the Ideal Clima sensor platform."""

from datetime import timedelta

from freezegun.api import FrozenDateTimeFactory
from modbus_connection.mock import MockModbusConnection
import pytest
from pytest_homeassistant.common import MockConfigEntry, async_fire_time_changed

from custom_components.idealclima.const import SCAN_INTERVAL
from homeassistant.components.sensor import (
    ATTR_STATE_CLASS,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.const import (
    ATTR_DEVICE_CLASS,
    ATTR_UNIT_OF_MEASUREMENT,
    REVOLUTIONS_PER_MINUTE,
    STATE_UNKNOWN,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant

from . import MOCK_UNIT_ID


@pytest.mark.parametrize(
    ("entity_id", "expected_state", "expected_unit", "expected_device_class"),
    [
        pytest.param(
            "sensor.radiantore_skudo_dc_inverter_21_ambient_temperature",
            "22.5",
            UnitOfTemperature.CELSIUS,
            SensorDeviceClass.TEMPERATURE,
            id="ambient_temperature",
        ),
        pytest.param(
            "sensor.radiantore_skudo_dc_inverter_21_coil_temperature",
            "41.0",
            UnitOfTemperature.CELSIUS,
            SensorDeviceClass.TEMPERATURE,
            id="coil_temperature",
        ),
        pytest.param(
            "sensor.radiantore_skudo_dc_inverter_21_fan_speed",
            "680",
            REVOLUTIONS_PER_MINUTE,
            None,
            id="fan_rpm",
        ),
        pytest.param(
            "sensor.radiantore_skudo_dc_inverter_21_active_operating_regime",
            "heat",
            None,
            SensorDeviceClass.ENUM,
            id="running_mode",
        ),
    ],
)
@pytest.mark.usefixtures("init_integration")
async def test_skudo_sensors(
    hass: HomeAssistant,
    entity_id: str,
    expected_state: str,
    expected_unit: str | None,
    expected_device_class: SensorDeviceClass | None,
) -> None:
    """Test SKUDO DC Inverter sensor states and attributes."""
    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state == expected_state
    assert state.attributes.get(ATTR_UNIT_OF_MEASUREMENT) == expected_unit
    assert state.attributes.get(ATTR_DEVICE_CLASS) == expected_device_class


@pytest.mark.usefixtures("init_ikaro_integration")
async def test_ikaro_sensors(hass: HomeAssistant) -> None:
    """Test IKARO HW creates only the ambient temperature sensor."""
    ambient = hass.states.get("sensor.comfosplit_ikaro_hw_21_ambient_temperature")
    assert ambient is not None
    assert ambient.state == "23.5"
    assert ambient.attributes[ATTR_STATE_CLASS] == SensorStateClass.MEASUREMENT

    assert hass.states.get("sensor.comfosplit_ikaro_hw_21_coil_temperature") is None
    assert hass.states.get("sensor.comfosplit_ikaro_hw_21_fan_speed") is None
    assert (
        hass.states.get("sensor.comfosplit_ikaro_hw_21_active_operating_regime") is None
    )


async def test_skudo_running_mode_updates_and_none(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    mock_connection: MockModbusConnection,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test running_mode sensor updates to cool and handles None."""
    entity_id = "sensor.radiantore_skudo_dc_inverter_21_active_operating_regime"
    unit = mock_connection.for_unit(MOCK_UNIT_ID)
    unit.input[46807] = 0

    freezer.tick(timedelta(seconds=SCAN_INTERVAL))
    async_fire_time_changed(hass)
    await hass.async_block_till_done(wait_background_tasks=True)

    assert (state := hass.states.get(entity_id)) is not None
    assert state.state == "cool"

    coordinator = init_integration.runtime_data
    coordinator.device.readings._values.clear()
    coordinator.async_update_listeners()
    await hass.async_block_till_done()

    assert (state := hass.states.get(entity_id)) is not None
    assert state.state == STATE_UNKNOWN
