"""Tests for the Ideal Clima climate platform."""

import asyncio
from datetime import timedelta
import gc
from unittest.mock import patch
import warnings

from freezegun.api import FrozenDateTimeFactory
from modbus_connection import ModbusError
from modbus_connection.mock import MockModbusConnection
import pytest
from pytest_homeassistant.common import MockConfigEntry, async_fire_time_changed

from custom_components.idealclima.climate import FAN_SUPER_SILENCE
from custom_components.idealclima.const import SCAN_INTERVAL
from homeassistant.components.climate import (
    ATTR_CURRENT_TEMPERATURE,
    ATTR_FAN_MODE,
    ATTR_FAN_MODES,
    ATTR_HVAC_MODE,
    ATTR_HVAC_MODES,
    ATTR_MAX_TEMP,
    ATTR_MIN_TEMP,
    ATTR_TARGET_TEMP_STEP,
    DOMAIN as CLIMATE_DOMAIN,
    FAN_AUTO,
    FAN_HIGH,
    FAN_LOW,
    FAN_MEDIUM,
    FAN_OFF,
    SERVICE_SET_FAN_MODE,
    SERVICE_SET_HVAC_MODE,
    SERVICE_SET_TEMPERATURE,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    HVACMode,
)
from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN
from homeassistant.const import ATTR_ENTITY_ID, ATTR_TEMPERATURE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError

from . import MOCK_UNIT_ID

SKUDO_ENTITY_ID = "climate.radiantore_skudo_dc_inverter_21"
IKARO_ENTITY_ID = "climate.comfosplit_ikaro_hw_21"


async def test_skudo_climate_initial_state(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Test initial state and attributes of a SKUDO DC Inverter climate entity."""
    state = hass.states.get(SKUDO_ENTITY_ID)
    assert state is not None
    assert state.state == HVACMode.HEAT
    assert state.attributes[ATTR_CURRENT_TEMPERATURE] == 22.5
    assert state.attributes[ATTR_TEMPERATURE] == 20.5
    assert state.attributes[ATTR_MIN_TEMP] == 18.0
    assert state.attributes[ATTR_MAX_TEMP] == 30.0
    assert state.attributes[ATTR_TARGET_TEMP_STEP] == 0.5
    assert state.attributes[ATTR_FAN_MODE] == FAN_LOW
    assert state.attributes[ATTR_FAN_MODES] == [
        FAN_SUPER_SILENCE,
        FAN_LOW,
        FAN_MEDIUM,
        FAN_HIGH,
        FAN_AUTO,
    ]
    assert state.attributes[ATTR_HVAC_MODES] == [
        HVACMode.OFF,
        HVACMode.AUTO,
        HVACMode.COOL,
        HVACMode.DRY,
        HVACMode.FAN_ONLY,
        HVACMode.HEAT,
    ]


async def test_ikaro_climate_initial_state(
    hass: HomeAssistant, init_ikaro_integration: MockConfigEntry
) -> None:
    """Test initial state and attributes of an IKARO HW climate entity."""
    state = hass.states.get(IKARO_ENTITY_ID)
    assert state is not None
    assert state.state == HVACMode.HEAT
    assert state.attributes[ATTR_CURRENT_TEMPERATURE] == 23.5
    assert state.attributes[ATTR_TEMPERATURE] == 21.0
    assert state.attributes[ATTR_MIN_TEMP] == 18.0
    assert state.attributes[ATTR_MAX_TEMP] == 30.0
    assert state.attributes[ATTR_FAN_MODE] == FAN_MEDIUM
    assert state.attributes[ATTR_HVAC_MODES] == [
        HVACMode.OFF,
        HVACMode.COOL,
        HVACMode.DRY,
        HVACMode.FAN_ONLY,
        HVACMode.HEAT,
    ]


@pytest.mark.parametrize(
    ("hvac_mode", "expected_mode_reg", "expected_target_temp"),
    [
        pytest.param(HVACMode.COOL, 1, 25.5, id="cool"),
        pytest.param(HVACMode.DRY, 2, 25.5, id="dry"),
        pytest.param(HVACMode.FAN_ONLY, 3, None, id="fan_only"),
        pytest.param(HVACMode.HEAT, 4, 20.5, id="heat"),
        pytest.param(HVACMode.AUTO, 0, 20.0, id="auto_heat"),
    ],
)
async def test_skudo_set_hvac_mode(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    mock_connection: MockModbusConnection,
    hvac_mode: HVACMode,
    expected_mode_reg: int,
    expected_target_temp: float | None,
) -> None:
    """Test changing HVAC modes on SKUDO DC Inverter."""
    unit = mock_connection.for_unit(MOCK_UNIT_ID)
    await hass.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_SET_HVAC_MODE,
        {ATTR_ENTITY_ID: SKUDO_ENTITY_ID, ATTR_HVAC_MODE: hvac_mode},
        blocking=True,
    )

    assert unit.holding[28302] == expected_mode_reg
    state = hass.states.get(SKUDO_ENTITY_ID)
    assert state is not None
    assert state.state == hvac_mode
    assert state.attributes.get(ATTR_TEMPERATURE) == expected_target_temp


async def test_skudo_auto_mode_cool_running_regime(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    mock_connection: MockModbusConnection,
) -> None:
    """Test SKUDO in AUTO mode uses auto_cool setpoint when running_mode is COOL."""
    unit = mock_connection.for_unit(MOCK_UNIT_ID)
    unit.input[46807] = 0

    await hass.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_SET_HVAC_MODE,
        {ATTR_ENTITY_ID: SKUDO_ENTITY_ID, ATTR_HVAC_MODE: HVACMode.AUTO},
        blocking=True,
    )

    state = hass.states.get(SKUDO_ENTITY_ID)
    assert state is not None
    assert state.state == HVACMode.AUTO
    assert state.attributes[ATTR_TEMPERATURE] == 26.0

    await hass.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_SET_TEMPERATURE,
        {ATTR_ENTITY_ID: SKUDO_ENTITY_ID, ATTR_TEMPERATURE: 24.5},
        blocking=True,
    )

    assert unit.holding[28312] == 245
    state = hass.states.get(SKUDO_ENTITY_ID)
    assert state is not None
    assert state.attributes[ATTR_TEMPERATURE] == 24.5


async def test_skudo_auto_unknown_running_mode(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    mock_connection: MockModbusConnection,
) -> None:
    """Test SKUDO in AUTO with unknown 46807 reports None and rejects writes."""
    unit = mock_connection.for_unit(MOCK_UNIT_ID)
    unit.input[46807] = 0xFFFF

    await hass.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_SET_HVAC_MODE,
        {ATTR_ENTITY_ID: SKUDO_ENTITY_ID, ATTR_HVAC_MODE: HVACMode.AUTO},
        blocking=True,
    )

    state = hass.states.get(SKUDO_ENTITY_ID)
    assert state is not None
    assert state.state == HVACMode.AUTO
    assert state.attributes.get(ATTR_TEMPERATURE) is None

    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            CLIMATE_DOMAIN,
            SERVICE_SET_TEMPERATURE,
            {ATTR_ENTITY_ID: SKUDO_ENTITY_ID, ATTR_TEMPERATURE: 23.0},
            blocking=True,
        )

    assert unit.holding[28312] == 260
    assert unit.holding[28313] == 200


async def test_skudo_contextual_switch_to_auto_uses_refreshed_running_mode(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    mock_connection: MockModbusConnection,
) -> None:
    """Test set_temperature switching to AUTO polls 46807 before writing setpoint."""
    unit = mock_connection.for_unit(MOCK_UNIT_ID)
    await hass.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_TURN_OFF,
        {ATTR_ENTITY_ID: SKUDO_ENTITY_ID},
        blocking=True,
    )
    # Initial cached running_mode is HEAT (1); switching to AUTO flips 46807 to COOL (0)
    unsub = unit.on_write(
        lambda event: (
            unit.input.__setitem__(46807, 0)
            if event.address == 28302 and event.values == [0]
            else None
        )
    )
    try:
        await hass.services.async_call(
            CLIMATE_DOMAIN,
            SERVICE_SET_TEMPERATURE,
            {
                ATTR_ENTITY_ID: SKUDO_ENTITY_ID,
                ATTR_HVAC_MODE: HVACMode.AUTO,
                ATTR_TEMPERATURE: 24.5,
            },
            blocking=True,
        )
    finally:
        unsub()

    assert unit.holding[28301] == 1
    assert unit.holding[28302] == 0
    assert unit.holding[28312] == 245
    assert unit.holding[28313] == 200


async def test_skudo_invalid_temp_bounds_fallback_to_defaults(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    mock_connection: MockModbusConnection,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test invalid or inverted SKUDO min/max temp registers fall back to defaults."""
    unit = mock_connection.for_unit(MOCK_UNIT_ID)
    unit.holding[28309] = 280
    unit.holding[28308] = 200

    freezer.tick(timedelta(seconds=SCAN_INTERVAL))
    async_fire_time_changed(hass)
    await hass.async_block_till_done(wait_background_tasks=True)

    state = hass.states.get(SKUDO_ENTITY_ID)
    assert state is not None
    assert state.attributes[ATTR_MIN_TEMP] == 18.0
    assert state.attributes[ATTR_MAX_TEMP] == 30.0


async def test_skudo_set_hvac_mode_off_and_back_on(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    mock_connection: MockModbusConnection,
) -> None:
    """Test turning SKUDO off via HVACMode.OFF and back on via HVACMode.COOL."""
    unit = mock_connection.for_unit(MOCK_UNIT_ID)

    await hass.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_SET_HVAC_MODE,
        {ATTR_ENTITY_ID: SKUDO_ENTITY_ID, ATTR_HVAC_MODE: HVACMode.OFF},
        blocking=True,
    )

    assert unit.holding[28301] == 0
    state = hass.states.get(SKUDO_ENTITY_ID)
    assert state is not None
    assert state.state == HVACMode.OFF
    assert state.attributes.get(ATTR_TEMPERATURE) is None

    await hass.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_SET_HVAC_MODE,
        {ATTR_ENTITY_ID: SKUDO_ENTITY_ID, ATTR_HVAC_MODE: HVACMode.COOL},
        blocking=True,
    )

    assert unit.holding[28301] == 1
    assert unit.holding[28302] == 1
    state = hass.states.get(SKUDO_ENTITY_ID)
    assert state is not None
    assert state.state == HVACMode.COOL


async def test_ikaro_turn_off_stops_fan_and_turn_on_restores_fan(
    hass: HomeAssistant,
    init_ikaro_integration: MockConfigEntry,
    mock_connection: MockModbusConnection,
) -> None:
    """Test IKARO HW stops fan on turn_off and restores last fan speed on turn_on."""
    unit = mock_connection.for_unit(MOCK_UNIT_ID)
    assert unit.holding[28303] == 3

    await hass.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_TURN_OFF,
        {ATTR_ENTITY_ID: IKARO_ENTITY_ID},
        blocking=True,
    )

    assert unit.holding[28301] == 0
    assert unit.holding[28303] == 0
    state = hass.states.get(IKARO_ENTITY_ID)
    assert state is not None
    assert state.state == HVACMode.OFF
    assert state.attributes[ATTR_FAN_MODE] == FAN_OFF

    await hass.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: IKARO_ENTITY_ID},
        blocking=True,
    )

    assert unit.holding[28301] == 1
    assert unit.holding[28303] == 3
    state = hass.states.get(IKARO_ENTITY_ID)
    assert state is not None
    assert state.state == HVACMode.HEAT
    assert state.attributes[ATTR_FAN_MODE] == FAN_MEDIUM


async def test_ikaro_set_hvac_mode_from_off(
    hass: HomeAssistant,
    init_ikaro_integration: MockConfigEntry,
    mock_connection: MockModbusConnection,
) -> None:
    """Test setting an active HVACMode on IKARO when off restores fan."""
    unit = mock_connection.for_unit(MOCK_UNIT_ID)

    await hass.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_SET_HVAC_MODE,
        {ATTR_ENTITY_ID: IKARO_ENTITY_ID, ATTR_HVAC_MODE: HVACMode.OFF},
        blocking=True,
    )
    assert unit.holding[28301] == 0
    assert unit.holding[28303] == 0

    await hass.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_SET_HVAC_MODE,
        {ATTR_ENTITY_ID: IKARO_ENTITY_ID, ATTR_HVAC_MODE: HVACMode.COOL},
        blocking=True,
    )
    assert unit.holding[28301] == 1
    assert unit.holding[28302] == 1
    assert unit.holding[28303] == 3


@pytest.mark.parametrize(
    ("fan_mode", "expected_reg"),
    [
        pytest.param(FAN_SUPER_SILENCE, 1, id="super_silence"),
        pytest.param(FAN_LOW, 2, id="low"),
        pytest.param(FAN_MEDIUM, 3, id="medium"),
        pytest.param(FAN_HIGH, 4, id="high"),
        pytest.param(FAN_AUTO, 6, id="auto"),
    ],
)
async def test_set_fan_mode(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    mock_connection: MockModbusConnection,
    fan_mode: str,
    expected_reg: int,
) -> None:
    """Test setting each supported fan mode."""
    unit = mock_connection.for_unit(MOCK_UNIT_ID)

    await hass.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_SET_FAN_MODE,
        {ATTR_ENTITY_ID: SKUDO_ENTITY_ID, ATTR_FAN_MODE: fan_mode},
        blocking=True,
    )

    assert unit.holding[28303] == expected_reg
    state = hass.states.get(SKUDO_ENTITY_ID)
    assert state is not None
    assert state.attributes[ATTR_FAN_MODE] == fan_mode


@pytest.mark.parametrize(
    ("initial_mode_reg", "temperature", "expected_reg"),
    [
        pytest.param(1, 24.0, 28310, id="cool"),
        pytest.param(2, 23.5, 28310, id="dry"),
        pytest.param(4, 21.5, 28311, id="heat"),
        pytest.param(0, 19.5, 28313, id="auto_heat"),
    ],
)
async def test_skudo_set_temperature_in_current_mode(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    mock_connection: MockModbusConnection,
    freezer: FrozenDateTimeFactory,
    initial_mode_reg: int,
    temperature: float,
    expected_reg: int,
) -> None:
    """Test setting target temperature writes the register matching the active mode."""
    unit = mock_connection.for_unit(MOCK_UNIT_ID)
    unit.holding[28302] = initial_mode_reg
    freezer.tick(timedelta(seconds=SCAN_INTERVAL))
    async_fire_time_changed(hass)
    await hass.async_block_till_done(wait_background_tasks=True)

    await hass.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_SET_TEMPERATURE,
        {ATTR_ENTITY_ID: SKUDO_ENTITY_ID, ATTR_TEMPERATURE: temperature},
        blocking=True,
    )

    assert unit.holding[expected_reg] == int(temperature * 10)


async def test_set_temperature_with_hvac_mode_from_off(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    mock_connection: MockModbusConnection,
) -> None:
    """Test set_temperature with hvac_mode while off turns on, sets mode and temp."""
    unit = mock_connection.for_unit(MOCK_UNIT_ID)
    await hass.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_TURN_OFF,
        {ATTR_ENTITY_ID: SKUDO_ENTITY_ID},
        blocking=True,
    )

    await hass.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_SET_TEMPERATURE,
        {
            ATTR_ENTITY_ID: SKUDO_ENTITY_ID,
            ATTR_HVAC_MODE: HVACMode.COOL,
            ATTR_TEMPERATURE: 24.5,
        },
        blocking=True,
    )

    assert unit.holding[28301] == 1
    assert unit.holding[28302] == 1
    assert unit.holding[28310] == 245


async def test_ikaro_set_temperature_with_hvac_mode_and_off(
    hass: HomeAssistant,
    init_ikaro_integration: MockConfigEntry,
    mock_connection: MockModbusConnection,
) -> None:
    """Test set_temperature with hvac_mode on IKARO HW (active mode and OFF)."""
    unit = mock_connection.for_unit(MOCK_UNIT_ID)

    await hass.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_SET_TEMPERATURE,
        {
            ATTR_ENTITY_ID: IKARO_ENTITY_ID,
            ATTR_HVAC_MODE: HVACMode.COOL,
            ATTR_TEMPERATURE: 24.0,
        },
        blocking=True,
    )
    assert unit.holding[28302] == 1
    assert unit.holding[28310] == 240

    await hass.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_SET_TEMPERATURE,
        {
            ATTR_ENTITY_ID: IKARO_ENTITY_ID,
            ATTR_HVAC_MODE: HVACMode.OFF,
            ATTR_TEMPERATURE: 22.0,
        },
        blocking=True,
    )
    assert unit.holding[28301] == 0


async def test_ikaro_set_temperature_writes_setpoint_before_power_on(
    hass: HomeAssistant,
    init_ikaro_integration: MockConfigEntry,
    mock_connection: MockModbusConnection,
) -> None:
    """Test turning IKARO on via set_temperature writes setpoint before power on."""
    unit = mock_connection.for_unit(MOCK_UNIT_ID)
    await hass.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_TURN_OFF,
        {ATTR_ENTITY_ID: IKARO_ENTITY_ID},
        blocking=True,
    )

    writes: list[tuple[int, list[int] | list[bool]]] = []
    unsub = unit.on_write(lambda event: writes.append((event.address, event.values)))
    try:
        await hass.services.async_call(
            CLIMATE_DOMAIN,
            SERVICE_SET_TEMPERATURE,
            {
                ATTR_ENTITY_ID: IKARO_ENTITY_ID,
                ATTR_HVAC_MODE: HVACMode.HEAT,
                ATTR_TEMPERATURE: 26.0,
            },
            blocking=True,
        )
    finally:
        unsub()

    assert writes == [
        (28302, [4]),
        (28311, [260]),
        (28301, [1]),
        (28303, [3]),
    ]


@pytest.mark.parametrize(
    ("hvac_mode", "ambient_raw", "target_reg", "expected_fallback_raw"),
    [
        pytest.param(HVACMode.HEAT, 235, 28311, 255, id="heat_valid_ambient"),
        pytest.param(HVACMode.HEAT, 0, 28311, 210, id="heat_invalid_ambient"),
        pytest.param(HVACMode.COOL, 235, 28310, 215, id="cool_valid_ambient"),
        pytest.param(HVACMode.COOL, 999, 28310, 240, id="cool_invalid_ambient"),
    ],
)
async def test_ikaro_fallback_setpoint_when_uninitialized(
    hass: HomeAssistant,
    init_ikaro_integration: MockConfigEntry,
    mock_connection: MockModbusConnection,
    hvac_mode: HVACMode,
    ambient_raw: int,
    target_reg: int,
    expected_fallback_raw: int,
) -> None:
    """Test IKARO writes a safe fallback setpoint before power on if register is 0."""
    unit = mock_connection.for_unit(MOCK_UNIT_ID)
    unit.input[46801] = ambient_raw
    unit.holding[target_reg] = 0
    await hass.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_TURN_OFF,
        {ATTR_ENTITY_ID: IKARO_ENTITY_ID},
        blocking=True,
    )

    writes: list[tuple[int, list[int] | list[bool]]] = []
    unsub = unit.on_write(lambda event: writes.append((event.address, event.values)))
    try:
        await hass.services.async_call(
            CLIMATE_DOMAIN,
            SERVICE_SET_HVAC_MODE,
            {ATTR_ENTITY_ID: IKARO_ENTITY_ID, ATTR_HVAC_MODE: hvac_mode},
            blocking=True,
        )
    finally:
        unsub()

    expected_mode = 4 if hvac_mode is HVACMode.HEAT else 1
    assert writes == [
        (28302, [expected_mode]),
        (target_reg, [expected_fallback_raw]),
        (28301, [1]),
        (28303, [3]),
    ]


async def test_ikaro_turn_on_and_fan_only_fallback_handling(
    hass: HomeAssistant,
    init_ikaro_integration: MockConfigEntry,
    mock_connection: MockModbusConnection,
) -> None:
    """Test turn_on applies fallback when setpoint is 0 and skips it for FAN_ONLY."""
    unit = mock_connection.for_unit(MOCK_UNIT_ID)
    unit.holding[28311] = 0
    await hass.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_TURN_OFF,
        {ATTR_ENTITY_ID: IKARO_ENTITY_ID},
        blocking=True,
    )

    writes: list[tuple[int, list[int] | list[bool]]] = []
    unsub = unit.on_write(lambda event: writes.append((event.address, event.values)))
    try:
        await hass.services.async_call(
            CLIMATE_DOMAIN,
            SERVICE_TURN_ON,
            {ATTR_ENTITY_ID: IKARO_ENTITY_ID},
            blocking=True,
        )
    finally:
        unsub()

    assert writes == [
        (28311, [255]),
        (28301, [1]),
        (28303, [3]),
    ]

    await hass.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_TURN_OFF,
        {ATTR_ENTITY_ID: IKARO_ENTITY_ID},
        blocking=True,
    )
    writes.clear()
    unsub = unit.on_write(lambda event: writes.append((event.address, event.values)))
    try:
        await hass.services.async_call(
            CLIMATE_DOMAIN,
            SERVICE_SET_HVAC_MODE,
            {ATTR_ENTITY_ID: IKARO_ENTITY_ID, ATTR_HVAC_MODE: HVACMode.FAN_ONLY},
            blocking=True,
        )
    finally:
        unsub()

    assert writes == [
        (28302, [3]),
        (28301, [1]),
        (28303, [3]),
    ]


async def test_write_error_raises_home_assistant_error(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    mock_connection: MockModbusConnection,
) -> None:
    """Test a ModbusError during a write translates to HomeAssistantError."""
    unit = mock_connection.for_unit(MOCK_UNIT_ID)
    unit.fail_write(28303, ModbusError("write failed"))

    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            CLIMATE_DOMAIN,
            SERVICE_SET_FAN_MODE,
            {ATTR_ENTITY_ID: SKUDO_ENTITY_ID, ATTR_FAN_MODE: FAN_HIGH},
            blocking=True,
        )


async def test_compound_write_first_error_no_unawaited_warning(
    hass: HomeAssistant,
    init_ikaro_integration: MockConfigEntry,
    mock_connection: MockModbusConnection,
) -> None:
    """Test failing the first write in a compound call emits no RuntimeWarning."""
    unit = mock_connection.for_unit(MOCK_UNIT_ID)
    await hass.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_TURN_OFF,
        {ATTR_ENTITY_ID: IKARO_ENTITY_ID},
        blocking=True,
    )
    unit.fail_write(28302, ModbusError("mode write failed"))

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", RuntimeWarning)
        with pytest.raises(HomeAssistantError) as err_info:
            await hass.services.async_call(
                CLIMATE_DOMAIN,
                SERVICE_SET_TEMPERATURE,
                {
                    ATTR_ENTITY_ID: IKARO_ENTITY_ID,
                    ATTR_HVAC_MODE: HVACMode.HEAT,
                    ATTR_TEMPERATURE: 26.0,
                },
                blocking=True,
            )
        gc.collect()

    assert isinstance(err_info.value.__cause__, ModbusError)
    assert not [w for w in caught if issubclass(w.category, RuntimeWarning)]
    assert unit.holding[28311] == 210
    assert unit.holding[28301] == 0


async def test_compound_write_partial_error_refreshes_state(
    hass: HomeAssistant,
    init_ikaro_integration: MockConfigEntry,
    mock_connection: MockModbusConnection,
) -> None:
    """Test a failure after partial writes refreshes coordinator state and re-raises."""
    unit = mock_connection.for_unit(MOCK_UNIT_ID)
    await hass.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_TURN_OFF,
        {ATTR_ENTITY_ID: IKARO_ENTITY_ID},
        blocking=True,
    )
    unit.fail_write(28301, ModbusError("power write failed"))

    with pytest.raises(HomeAssistantError) as err_info:
        await hass.services.async_call(
            CLIMATE_DOMAIN,
            SERVICE_SET_TEMPERATURE,
            {
                ATTR_ENTITY_ID: IKARO_ENTITY_ID,
                ATTR_HVAC_MODE: HVACMode.HEAT,
                ATTR_TEMPERATURE: 26.0,
            },
            blocking=True,
        )

    assert isinstance(err_info.value.__cause__, ModbusError)
    coordinator = init_ikaro_integration.runtime_data
    assert coordinator.device.settings.target_temp_heat == 26.0


async def test_device_command_lock_serializes_across_platforms(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    mock_connection: MockModbusConnection,
) -> None:
    """Test per-device command_lock prevents cross-platform write interleaving."""
    unit = mock_connection.for_unit(MOCK_UNIT_ID)
    await hass.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_TURN_OFF,
        {ATTR_ENTITY_ID: SKUDO_ENTITY_ID},
        blocking=True,
    )

    coordinator = init_integration.runtime_data
    first_write_started = asyncio.Event()
    release_first_write = asyncio.Event()
    original_set_mode = coordinator.device.async_set_mode

    async def _slow_set_mode(mode: object) -> None:
        first_write_started.set()
        await release_first_write.wait()
        await original_set_mode(mode)  # type: ignore[arg-type]

    writes: list[int] = []
    unsub = unit.on_write(lambda event: writes.append(event.address))
    try:
        with patch.object(coordinator.device, "async_set_mode", _slow_set_mode):
            climate_task = asyncio.create_task(
                hass.services.async_call(
                    CLIMATE_DOMAIN,
                    SERVICE_SET_TEMPERATURE,
                    {
                        ATTR_ENTITY_ID: SKUDO_ENTITY_ID,
                        ATTR_HVAC_MODE: HVACMode.COOL,
                        ATTR_TEMPERATURE: 24.5,
                    },
                    blocking=True,
                )
            )
            await first_write_started.wait()
            switch_task = asyncio.create_task(
                hass.services.async_call(
                    SWITCH_DOMAIN,
                    SERVICE_TURN_ON,
                    {
                        ATTR_ENTITY_ID: (
                            "switch.radiantore_skudo_dc_inverter_21_sleep_mode"
                        )
                    },
                    blocking=True,
                )
            )
            await asyncio.sleep(0)
            release_first_write.set()
            await asyncio.gather(climate_task, switch_task)
    finally:
        unsub()

    assert writes == [28302, 28310, 28301, 28305]


async def test_none_settings_handling(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    init_ikaro_integration: MockConfigEntry,
) -> None:
    """Test properties return None/defaults cleanly if settings fields are None."""
    skudo_coord = init_integration.runtime_data
    skudo_settings = skudo_coord.device.settings
    skudo_settings._values.clear()
    skudo_coord.async_update_listeners()
    await hass.async_block_till_done()

    state = hass.states.get(SKUDO_ENTITY_ID)
    assert state is not None
    assert state.state == STATE_UNKNOWN
    assert state.attributes[ATTR_MIN_TEMP] == 18.0
    assert state.attributes[ATTR_MAX_TEMP] == 30.0

    # Power True but mode None on both SKUDO and IKARO
    skudo_settings._values["power"] = True
    skudo_coord.async_update_listeners()

    ikaro_coord = init_ikaro_integration.runtime_data
    ikaro_settings = ikaro_coord.device.settings
    ikaro_settings._values.clear()
    ikaro_settings._values["power"] = True
    ikaro_coord.async_update_listeners()
    await hass.async_block_till_done()

    assert (skudo_state := hass.states.get(SKUDO_ENTITY_ID)) is not None
    assert skudo_state.state == STATE_UNKNOWN
    assert (ikaro_state := hass.states.get(IKARO_ENTITY_ID)) is not None
    assert ikaro_state.state == STATE_UNKNOWN
