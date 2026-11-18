"""Diagnostics support for the Ideal Clima integration."""

from enum import Enum
from typing import Any

from modbus_connection.model import Component

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant

from .coordinator import IdealclimaConfigEntry

TO_REDACT = {CONF_HOST}


def _serialize_component(component: Component) -> dict[str, Any]:
    """Serialize all declared fields of a Modbus model component."""
    result: dict[str, Any] = {}
    for field_name in component.declared_fields:
        value = getattr(component, field_name)
        result[field_name] = value.name.lower() if isinstance(value, Enum) else value
    return result


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: IdealclimaConfigEntry,
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = entry.runtime_data
    device = coordinator.device
    report = coordinator.data

    return {
        "entry": {
            "entry_id": entry.entry_id,
            "title": entry.title,
            "data": async_redact_data(entry.data, TO_REDACT),
        },
        "coordinator": {
            "last_update_success": coordinator.last_update_success,
            "last_exception": (
                str(coordinator.last_exception)
                if coordinator.last_exception is not None
                else None
            ),
            "update_interval_seconds": (
                coordinator.update_interval.total_seconds()
                if coordinator.update_interval is not None
                else None
            ),
        },
        "device": {
            "model": type(device).__name__,
            "readings": _serialize_component(device.readings),
            "settings": _serialize_component(device.settings),
            "last_update_report": (
                {
                    "complete": report.complete,
                    "updated": sorted(report.updated),
                }
                if report is not None
                else None
            ),
        },
    }
