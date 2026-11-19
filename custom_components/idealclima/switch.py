"""Switch platform for the Ideal Clima integration."""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, override

from idealclima_modbus import SkudoDCInverter

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import IdealclimaConfigEntry, IdealclimaDataUpdateCoordinator
from .entity import IdealclimaEntity

PARALLEL_UPDATES = 1


@dataclass(frozen=True, kw_only=True)
class IdealclimaSwitchEntityDescription(SwitchEntityDescription):
    """Describe an Ideal Clima switch entity."""

    value_fn: Callable[[SkudoDCInverter], bool | None]
    write_fn: Callable[[SkudoDCInverter, bool], Awaitable[None]]


SKUDO_SWITCH_DESCRIPTIONS: tuple[IdealclimaSwitchEntityDescription, ...] = (
    IdealclimaSwitchEntityDescription(
        key="sleep",
        translation_key="sleep",
        value_fn=lambda device: device.settings.sleep,
        write_fn=lambda device, value: device.async_set_sleep(value),
    ),
    IdealclimaSwitchEntityDescription(
        key="key_lock",
        translation_key="key_lock",
        entity_category=EntityCategory.CONFIG,
        value_fn=lambda device: device.settings.key_lock,
        write_fn=lambda device, value: device.async_set_key_lock(value),
    ),
    IdealclimaSwitchEntityDescription(
        key="anti_draft_enabled",
        translation_key="anti_draft_enabled",
        entity_category=EntityCategory.CONFIG,
        value_fn=lambda device: device.settings.anti_draft_enabled,
        write_fn=lambda device, value: device.async_set_anti_draft_enabled(value),
    ),
    IdealclimaSwitchEntityDescription(
        key="super_silence_enabled",
        translation_key="super_silence_enabled",
        entity_category=EntityCategory.CONFIG,
        value_fn=lambda device: device.settings.super_silence_enabled,
        write_fn=lambda device, value: device.async_set_super_silence_enabled(value),
    ),
    IdealclimaSwitchEntityDescription(
        key="valve_present",
        translation_key="valve_present",
        entity_category=EntityCategory.CONFIG,
        value_fn=lambda device: device.settings.valve_present,
        write_fn=lambda device, value: device.async_set_valve_present(value),
    ),
    IdealclimaSwitchEntityDescription(
        key="key_lock_enabled",
        translation_key="key_lock_enabled",
        entity_category=EntityCategory.CONFIG,
        value_fn=lambda device: device.settings.key_lock_enabled,
        write_fn=lambda device, value: device.async_set_key_lock_enabled(value),
    ),
    IdealclimaSwitchEntityDescription(
        key="remote_enabled_with_key_lock",
        translation_key="remote_enabled_with_key_lock",
        entity_category=EntityCategory.CONFIG,
        value_fn=lambda device: device.settings.remote_enabled_with_key_lock,
        write_fn=lambda device, value: device.async_set_remote_enabled_with_key_lock(
            value
        ),
    ),
    IdealclimaSwitchEntityDescription(
        key="password_enabled",
        translation_key="password_enabled",
        entity_category=EntityCategory.CONFIG,
        value_fn=lambda device: device.settings.password_enabled,
        write_fn=lambda device, value: device.async_set_password_enabled(value),
    ),
    IdealclimaSwitchEntityDescription(
        key="fan_intermittent",
        translation_key="fan_intermittent",
        entity_category=EntityCategory.CONFIG,
        value_fn=lambda device: device.settings.fan_intermittent,
        write_fn=lambda device, value: device.async_set_fan_intermittent(value),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: IdealclimaConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Ideal Clima switches from a config entry."""
    coordinator = entry.runtime_data
    if not isinstance(coordinator.device, SkudoDCInverter):
        return
    async_add_entities(
        IdealclimaSwitchEntity(coordinator, coordinator.device, description)
        for description in SKUDO_SWITCH_DESCRIPTIONS
    )


class IdealclimaSwitchEntity(IdealclimaEntity, SwitchEntity):
    """Representation of an Ideal Clima switch entity."""

    entity_description: IdealclimaSwitchEntityDescription

    def __init__(
        self,
        coordinator: IdealclimaDataUpdateCoordinator,
        device: SkudoDCInverter,
        description: IdealclimaSwitchEntityDescription,
    ) -> None:
        """Initialize the switch entity."""
        super().__init__(coordinator, description)
        self._skudo = device

    @property
    @override
    def is_on(self) -> bool | None:
        """Return true if the switch is on."""
        return self.entity_description.value_fn(self._skudo)

    @override
    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        await self._async_execute(
            lambda: self.entity_description.write_fn(self._skudo, True)
        )

    @override
    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        await self._async_execute(
            lambda: self.entity_description.write_fn(self._skudo, False)
        )
