"""Sensor platform for the Ideal Clima integration."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, override

from idealclima_modbus import SkudoDCInverter

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import REVOLUTIONS_PER_MINUTE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.typing import StateType

from .coordinator import IdealclimaConfigEntry, IdealclimaDataUpdateCoordinator
from .entity import IdealclimaEntity
from .helpers import IdealclimaDevice

PARALLEL_UPDATES = 1


@dataclass(frozen=True, kw_only=True)
class IdealclimaSensorEntityDescription[D: IdealclimaDevice](SensorEntityDescription):
    """Describe an Ideal Clima sensor entity."""

    value_fn: Callable[[D], StateType]


COMMON_SENSOR_DESCRIPTIONS: tuple[
    IdealclimaSensorEntityDescription[IdealclimaDevice], ...
] = (
    IdealclimaSensorEntityDescription(
        key="ambient_temperature",
        translation_key="ambient_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=1,
        value_fn=lambda device: device.readings.ambient_temperature,
    ),
)

SKUDO_SENSOR_DESCRIPTIONS: tuple[
    IdealclimaSensorEntityDescription[SkudoDCInverter], ...
] = (
    IdealclimaSensorEntityDescription(
        key="coil_temperature",
        translation_key="coil_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=1,
        value_fn=lambda device: device.readings.coil_temperature,
    ),
    IdealclimaSensorEntityDescription(
        key="fan_rpm",
        translation_key="fan_rpm",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=REVOLUTIONS_PER_MINUTE,
        value_fn=lambda device: device.readings.fan_rpm,
    ),
    IdealclimaSensorEntityDescription(
        key="running_mode",
        translation_key="running_mode",
        device_class=SensorDeviceClass.ENUM,
        options=["cool", "heat"],
        value_fn=lambda device: (
            None
            if device.readings.running_mode is None
            else device.readings.running_mode.name.lower()
        ),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: IdealclimaConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Ideal Clima sensors from a config entry."""
    coordinator = entry.runtime_data
    entities: list[IdealclimaSensorEntity[Any]] = [
        IdealclimaSensorEntity(coordinator, coordinator.device, description)
        for description in COMMON_SENSOR_DESCRIPTIONS
    ]
    if isinstance(coordinator.device, SkudoDCInverter):
        entities.extend(
            IdealclimaSensorEntity(coordinator, coordinator.device, description)
            for description in SKUDO_SENSOR_DESCRIPTIONS
        )
    async_add_entities(entities)


class IdealclimaSensorEntity[D: IdealclimaDevice](IdealclimaEntity, SensorEntity):
    """Representation of an Ideal Clima sensor entity."""

    entity_description: IdealclimaSensorEntityDescription[D]

    def __init__(
        self,
        coordinator: IdealclimaDataUpdateCoordinator,
        device: D,
        description: IdealclimaSensorEntityDescription[D],
    ) -> None:
        """Initialize the sensor entity."""
        super().__init__(coordinator, description)
        self._typed_device = device

    @property
    @override
    def native_value(self) -> StateType:
        """Return the state of the sensor."""
        return self.entity_description.value_fn(self._typed_device)
