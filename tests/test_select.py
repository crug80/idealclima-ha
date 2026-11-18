"""Tests for the Ideal Clima select platform."""

from modbus_connection import ModbusError
from modbus_connection.mock import MockModbusConnection
import pytest
from pytest_homeassistant.common import MockConfigEntry

from homeassistant.components.select import (
    ATTR_OPTION,
    ATTR_OPTIONS,
    DOMAIN as SELECT_DOMAIN,
    SERVICE_SELECT_OPTION,
)
from homeassistant.const import ATTR_ENTITY_ID, STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from . import MOCK_UNIT_ID

SELECT_ENTITY_ID = "select.radiantore_skudo_dc_inverter_21_display_temperature_unit"


async def test_skudo_select_read_and_write(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    mock_connection: MockModbusConnection,
) -> None:
    """Test reading and changing the SKUDO display temperature unit select."""
    unit = mock_connection.for_unit(MOCK_UNIT_ID)
    assert (state := hass.states.get(SELECT_ENTITY_ID)) is not None
    assert state.state == "celsius"
    assert state.attributes[ATTR_OPTIONS] == ["celsius", "fahrenheit"]

    await hass.services.async_call(
        SELECT_DOMAIN,
        SERVICE_SELECT_OPTION,
        {ATTR_ENTITY_ID: SELECT_ENTITY_ID, ATTR_OPTION: "fahrenheit"},
        blocking=True,
    )

    assert unit.holding[28319] == 1
    assert (state := hass.states.get(SELECT_ENTITY_ID)) is not None
    assert state.state == "fahrenheit"

    coordinator = init_integration.runtime_data
    coordinator.device.settings._values.clear()
    coordinator.async_update_listeners()
    await hass.async_block_till_done()

    assert (state := hass.states.get(SELECT_ENTITY_ID)) is not None
    assert state.state == STATE_UNKNOWN


@pytest.mark.usefixtures("init_integration")
async def test_select_write_error(
    hass: HomeAssistant,
    mock_connection: MockModbusConnection,
) -> None:
    """Test a ModbusError when writing a select option raises HomeAssistantError."""
    mock_connection.for_unit(MOCK_UNIT_ID).fail_write(28319, ModbusError("busy"))

    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            SELECT_DOMAIN,
            SERVICE_SELECT_OPTION,
            {ATTR_ENTITY_ID: SELECT_ENTITY_ID, ATTR_OPTION: "fahrenheit"},
            blocking=True,
        )


@pytest.mark.usefixtures("init_ikaro_integration")
async def test_ikaro_has_no_selects(hass: HomeAssistant) -> None:
    """Test IKARO HW does not create any select entities."""
    assert hass.states.async_entity_ids(SELECT_DOMAIN) == []
