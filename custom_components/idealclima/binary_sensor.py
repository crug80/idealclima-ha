"""Binary sensor platform for the Ideal Clima integration."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import override

from idealclima_modbus import SkudoDCInverter

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import IdealclimaConfigEntry, IdealclimaDataUpdateCoordinator
from .entity import IdealclimaEntity

PARALLEL_UPDATES = 1


@dataclass(frozen=True, kw_only=True)
class IdealclimaBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Describe an Ideal Clima binary sensor entity."""

    value_fn: Callable[[SkudoDCInverter], bool | None]


SKUDO_BINARY_SENSOR_DESCRIPTIONS: tuple[
    IdealclimaBinarySensorEntityDescription, ...
] = (
    IdealclimaBinarySensorEntityDescription(
        key="valve_command",
        translation_key="valve_command",
        device_class=BinarySensorDeviceClass.OPENING,
        value_fn=lambda device: device.readings.valve_command,
    ),
    IdealclimaBinarySensorEntityDescription(
        key="power_state",
        translation_key="power_state",
        device_class=BinarySensorDeviceClass.RUNNING,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda device: device.readings.power_state,
    ),
    IdealclimaBinarySensorEntityDescription(
        key="motor_alarm",
        translation_key="motor_alarm",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda device: device.readings.motor_alarm,
    ),
    IdealclimaBinarySensorEntityDescription(
        key="ambient_sensor_alarm",
        translation_key="ambient_sensor_alarm",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda device: device.readings.ambient_sensor_alarm,
    ),
    IdealclimaBinarySensorEntityDescription(
        key="coil_sensor_alarm",
        translation_key="coil_sensor_alarm",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda device: device.readings.coil_sensor_alarm,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: IdealclimaConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Ideal Clima binary sensors from a config entry."""
    coordinator = entry.runtime_data
    if not isinstance(coordinator.device, SkudoDCInverter):
        return
    async_add_entities(
        IdealclimaBinarySensorEntity(coordinator, coordinator.device, description)
        for description in SKUDO_BINARY_SENSOR_DESCRIPTIONS
    )


class IdealclimaBinarySensorEntity(IdealclimaEntity, BinarySensorEntity):
    """Representation of an Ideal Clima binary sensor entity."""

    entity_description: IdealclimaBinarySensorEntityDescription

    def __init__(
        self,
        coordinator: IdealclimaDataUpdateCoordinator,
        device: SkudoDCInverter,
        description: IdealclimaBinarySensorEntityDescription,
    ) -> None:
        """Initialize the binary sensor entity."""
        super().__init__(coordinator, description)
        self._skudo = device

    @property
    @override
    def is_on(self) -> bool | None:
        """Return true if the binary sensor is on."""
        return self.entity_description.value_fn(self._skudo)
