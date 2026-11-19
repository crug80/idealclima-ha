"""Helpers for the Ideal Clima integration."""

from collections.abc import Mapping
from typing import Any

from idealclima_modbus import IkaroHW, SkudoDCInverter
from modbus_connection import ModbusSerialParams, ModbusTcpParams, ModbusUnit

from homeassistant.const import CONF_DEVICE, CONF_HOST, CONF_MODEL, CONF_PORT, CONF_TYPE

from .const import CONF_BAUDRATE, TYPE_SERIAL, IdealclimaModel

type IdealclimaDevice = IkaroHW | SkudoDCInverter


def create_modbus_params(
    data: Mapping[str, Any],
) -> ModbusSerialParams | ModbusTcpParams:
    """Build the Modbus link parameters from config entry data."""
    if data[CONF_TYPE] == TYPE_SERIAL:
        return ModbusSerialParams(
            device=data[CONF_DEVICE], baudrate=data[CONF_BAUDRATE]
        )
    return ModbusTcpParams(host=data[CONF_HOST].strip(), port=data[CONF_PORT])


def create_device(unit: ModbusUnit, data: Mapping[str, Any]) -> IdealclimaDevice:
    """Instantiate the appropriate Ideal Clima device model for a Modbus unit."""
    if data[CONF_MODEL] == IdealclimaModel.IKARO_HW:
        return IkaroHW(unit)
    return SkudoDCInverter(unit)
