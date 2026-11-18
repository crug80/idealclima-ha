"""Tests for the Ideal Clima integration."""

from typing import Any

from modbus_connection.mock import MockModbusUnit

from custom_components.idealclima.const import (
    CONF_BAUDRATE,
    CONF_UNIT_ID,
    DEFAULT_BAUDRATE,
    DEFAULT_PORT,
    TYPE_SERIAL,
    TYPE_TCP,
    IdealclimaModel,
)
from homeassistant.const import CONF_DEVICE, CONF_HOST, CONF_MODEL, CONF_PORT, CONF_TYPE

MOCK_HOST = "192.168.1.100"
MOCK_DEVICE = "/dev/ttyUSB0"
MOCK_UNIT_ID = 21

MOCK_TCP_INPUT: dict[str, Any] = {
    CONF_MODEL: IdealclimaModel.SKUDO_DC_INVERTER,
    CONF_HOST: MOCK_HOST,
    CONF_PORT: DEFAULT_PORT,
    CONF_UNIT_ID: MOCK_UNIT_ID,
}

MOCK_TCP_ENTRY_DATA: dict[str, Any] = {
    CONF_TYPE: TYPE_TCP,
    **MOCK_TCP_INPUT,
}

MOCK_SERIAL_INPUT: dict[str, Any] = {
    CONF_MODEL: IdealclimaModel.SKUDO_DC_INVERTER,
    CONF_DEVICE: MOCK_DEVICE,
    CONF_BAUDRATE: DEFAULT_BAUDRATE,
    CONF_UNIT_ID: MOCK_UNIT_ID,
}

MOCK_SERIAL_ENTRY_DATA: dict[str, Any] = {
    CONF_TYPE: TYPE_SERIAL,
    **MOCK_SERIAL_INPUT,
}

MOCK_IKARO_TCP_ENTRY_DATA: dict[str, Any] = {
    CONF_TYPE: TYPE_TCP,
    CONF_MODEL: IdealclimaModel.IKARO_HW,
    CONF_HOST: MOCK_HOST,
    CONF_PORT: DEFAULT_PORT,
    CONF_UNIT_ID: MOCK_UNIT_ID,
}


def seed_ikaro(unit: MockModbusUnit) -> None:
    """Populate a MockModbusUnit with valid Comfosplit IKARO HW registers."""
    unit.input[46801] = 235
    unit.holding.update(
        {
            28301: 1,
            28302: 4,
            28303: 3,
            28310: 250,
            28311: 210,
        }
    )


def seed_skudo(unit: MockModbusUnit) -> None:
    """Populate a MockModbusUnit with valid Radiantore SKUDO DC Inverter registers."""
    unit.input.update(
        {
            46801: 225,
            46802: 410,
            46803: 2,
            46804: 680,
            46805: 1,
            46806: 1,
            46807: 1,
            46808: 0,
            46809: 0,
            46810: 0,
        }
    )
    unit.holding.update(
        {
            28301: 1,
            28302: 4,
            28303: 2,
            28304: 0,
            28305: 0,
            28306: 0,
            28307: 0,
            28308: 300,
            28309: 180,
            28310: 255,
            28311: 205,
            28312: 260,
            28313: 200,
            28314: 250,
            28315: 1,
            28316: 1,
            28317: 1,
            28319: 0,
            28322: 0,
            28323: 0,
            28324: 0,
            28327: 0,
        }
    )
