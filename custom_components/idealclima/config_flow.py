"""Config flow for the Ideal Clima integration."""

from collections.abc import Mapping
import logging
from typing import Any, override

from modbus_connection import ModbusError
import probatio

from homeassistant.components.modbus import async_get_temporary_unit
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_DEVICE, CONF_HOST, CONF_MODEL, CONF_PORT, CONF_TYPE
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    SerialPortSelector,
    TextSelector,
)

from .const import (
    CONF_BAUDRATE,
    CONF_UNIT_ID,
    DEFAULT_BAUDRATE,
    DEFAULT_PORT,
    DEFAULT_UNIT_ID,
    DOMAIN,
    FACTORY_DEFAULT_UNIT_ID,
    MAX_UNIT_ID,
    MIN_UNIT_ID,
    MODEL_NAMES,
    TYPE_SERIAL,
    TYPE_TCP,
    IdealclimaModel,
)
from .helpers import create_device, create_modbus_params

_LOGGER = logging.getLogger(__name__)

MODEL_SELECTOR = SelectSelector(
    SelectSelectorConfig(
        options=list(IdealclimaModel),
        translation_key=CONF_MODEL,
        mode=SelectSelectorMode.DROPDOWN,
    )
)

UNIT_ID_SELECTOR = probatio.All(
    NumberSelector(
        NumberSelectorConfig(
            mode=NumberSelectorMode.BOX, min=MIN_UNIT_ID, max=MAX_UNIT_ID
        )
    ),
    probatio.Coerce(int),
)

STEP_TCP_DATA_SCHEMA = probatio.Schema(
    {
        probatio.Required(
            CONF_MODEL, default=IdealclimaModel.SKUDO_DC_INVERTER
        ): MODEL_SELECTOR,
        probatio.Required(CONF_HOST): TextSelector(),
        probatio.Required(CONF_PORT, default=DEFAULT_PORT): probatio.All(
            NumberSelector(
                NumberSelectorConfig(mode=NumberSelectorMode.BOX, min=1, max=65535)
            ),
            probatio.Coerce(int),
        ),
        probatio.Required(CONF_UNIT_ID, default=DEFAULT_UNIT_ID): UNIT_ID_SELECTOR,
    }
)

STEP_SERIAL_DATA_SCHEMA = probatio.Schema(
    {
        probatio.Required(
            CONF_MODEL, default=IdealclimaModel.SKUDO_DC_INVERTER
        ): MODEL_SELECTOR,
        probatio.Required(CONF_DEVICE): SerialPortSelector(),
        probatio.Required(CONF_BAUDRATE, default=DEFAULT_BAUDRATE): probatio.All(
            NumberSelector(NumberSelectorConfig(mode=NumberSelectorMode.BOX, min=1)),
            probatio.Coerce(int),
        ),
        probatio.Required(CONF_UNIT_ID, default=DEFAULT_UNIT_ID): UNIT_ID_SELECTOR,
    }
)


async def _async_probe(hass: HomeAssistant, data: Mapping[str, Any]) -> None:
    """Connect to the unit and verify it answers a full update, or raise."""
    async with async_get_temporary_unit(
        hass, create_modbus_params(data), data[CONF_UNIT_ID]
    ) as unit:
        device = create_device(unit, data)
        report = await device.async_update()
        if not report.complete:
            raise next(iter(report.failed.values()))


class IdealclimaConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle an Ideal Clima config flow."""

    VERSION = 1

    @override
    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Let the user pick how the fan coil is reached."""
        return self.async_show_menu(
            step_id="user", menu_options=[TYPE_TCP, TYPE_SERIAL]
        )

    async def async_step_tcp(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle a fan coil reached over Modbus TCP."""
        return await self._async_step_link(TYPE_TCP, STEP_TCP_DATA_SCHEMA, user_input)

    async def async_step_serial(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle a fan coil reached over a serial port."""
        return await self._async_step_link(
            TYPE_SERIAL, STEP_SERIAL_DATA_SCHEMA, user_input
        )

    async def _async_step_link(
        self,
        connection_type: str,
        schema: probatio.Schema,
        user_input: dict[str, Any] | None,
    ) -> ConfigFlowResult:
        """Validate the link settings and probe the fan coil."""
        errors: dict[str, str] = {}
        if user_input is not None:
            unit_id = user_input[CONF_UNIT_ID]
            if unit_id == FACTORY_DEFAULT_UNIT_ID:
                errors[CONF_UNIT_ID] = "factory_default_unit_id"
            else:
                if connection_type == TYPE_TCP:
                    self._async_abort_entries_match(
                        {
                            CONF_TYPE: TYPE_TCP,
                            CONF_HOST: user_input[CONF_HOST],
                            CONF_PORT: user_input[CONF_PORT],
                            CONF_UNIT_ID: unit_id,
                        }
                    )
                else:
                    self._async_abort_entries_match(
                        {
                            CONF_TYPE: TYPE_SERIAL,
                            CONF_DEVICE: user_input[CONF_DEVICE],
                            CONF_UNIT_ID: unit_id,
                        }
                    )

                data = {CONF_TYPE: connection_type, **user_input}
                try:
                    await _async_probe(self.hass, data)
                except ModbusError, HomeAssistantError:
                    errors["base"] = "cannot_connect"
                except Exception:
                    _LOGGER.exception("Unexpected exception")
                    errors["base"] = "unknown"
                else:
                    model_name = MODEL_NAMES[IdealclimaModel(data[CONF_MODEL])]
                    return self.async_create_entry(
                        title=f"{model_name} ({unit_id})",
                        data=data,
                    )

        return self.async_show_form(
            step_id=connection_type,
            data_schema=self.add_suggested_values_to_schema(schema, user_input),
            errors=errors,
        )
