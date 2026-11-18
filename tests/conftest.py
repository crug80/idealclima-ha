"""Fixtures for the Ideal Clima integration tests."""

from collections.abc import Generator
from unittest.mock import AsyncMock, MagicMock, patch

from modbus_connection.mock import MockModbusConnection
import pytest
from pytest_homeassistant.common import MockConfigEntry

from custom_components.idealclima.const import DOMAIN
from homeassistant.core import HomeAssistant

from . import (
    MOCK_IKARO_TCP_ENTRY_DATA,
    MOCK_TCP_ENTRY_DATA,
    MOCK_UNIT_ID,
    seed_ikaro,
    seed_skudo,
)


@pytest.fixture
def mock_setup_entry() -> Generator[AsyncMock]:
    """Override async_setup_entry."""
    with patch(
        "custom_components.idealclima.async_setup_entry",
        new_callable=AsyncMock,
        return_value=None,
    ) as mock_setup_entry:
        yield mock_setup_entry


@pytest.fixture
def mock_connection() -> MockModbusConnection:
    """Return a fake Modbus connection seeded as a SKUDO DC Inverter."""
    connection = MockModbusConnection()
    seed_skudo(connection.for_unit(MOCK_UNIT_ID))
    return connection


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """Return a MockConfigEntry for a SKUDO DC Inverter."""
    return MockConfigEntry(
        domain=DOMAIN,
        data=MOCK_TCP_ENTRY_DATA,
        title=f"Radiantore SKUDO DC Inverter ({MOCK_UNIT_ID})",
        entry_id="01JIDEALCLIMASKUDO00000001",
    )


@pytest.fixture
def mock_ikaro_config_entry() -> MockConfigEntry:
    """Return a MockConfigEntry for an IKARO HW."""
    return MockConfigEntry(
        domain=DOMAIN,
        data=MOCK_IKARO_TCP_ENTRY_DATA,
        title=f"Comfosplit IKARO HW ({MOCK_UNIT_ID})",
        entry_id="01JIDEALCLIMAIKARO00000001",
    )


@pytest.fixture
def mock_get_unit(mock_connection: MockModbusConnection) -> Generator[MagicMock]:
    """Hand out units on the mock connection when the entry sets up."""
    with patch(
        "custom_components.idealclima.async_get_unit",
        side_effect=lambda hass, entry, params, unit_id: mock_connection.for_unit(
            unit_id
        ),
    ) as mock_get_unit:
        yield mock_get_unit


@pytest.fixture
async def init_integration(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_get_unit: MagicMock,
) -> MockConfigEntry:
    """Set up the Ideal Clima integration for a SKUDO DC Inverter."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done(wait_background_tasks=True)
    return mock_config_entry


@pytest.fixture
async def init_ikaro_integration(
    hass: HomeAssistant,
    mock_ikaro_config_entry: MockConfigEntry,
    mock_connection: MockModbusConnection,
    mock_get_unit: MagicMock,
) -> MockConfigEntry:
    """Set up the Ideal Clima integration for an IKARO HW."""
    unit = mock_connection.for_unit(MOCK_UNIT_ID)
    unit.input.clear()
    unit.holding.clear()
    seed_ikaro(unit)
    mock_ikaro_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_ikaro_config_entry.entry_id)
    await hass.async_block_till_done(wait_background_tasks=True)
    return mock_ikaro_config_entry
