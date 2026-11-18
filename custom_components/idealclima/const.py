"""Constants for the Ideal Clima integration."""

from enum import StrEnum

DOMAIN = "idealclima"
ATTR_MANUFACTURER = "Ideal Clima"

CONF_BAUDRATE = "baudrate"
CONF_UNIT_ID = "unit_id"

DEFAULT_BAUDRATE = 9600
DEFAULT_PORT = 502
DEFAULT_UNIT_ID = 1

MIN_UNIT_ID = 1
MAX_UNIT_ID = 32
FACTORY_DEFAULT_UNIT_ID = 15

SCAN_INTERVAL = 15

TYPE_SERIAL = "serial"
TYPE_TCP = "tcp"


class IdealclimaModel(StrEnum):
    """Supported Ideal Clima fan coil models."""

    IKARO_HW = "ikaro_hw"
    SKUDO_DC_INVERTER = "skudo_dc_inverter"


MODEL_NAMES: dict[IdealclimaModel, str] = {
    IdealclimaModel.IKARO_HW: "Comfosplit IKARO HW",
    IdealclimaModel.SKUDO_DC_INVERTER: "Radiantore SKUDO DC Inverter",
}
