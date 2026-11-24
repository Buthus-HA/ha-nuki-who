"""Installation : détection des serrures sur MQTT, puis liste des personnes en options."""
from __future__ import annotations

import asyncio
from typing import Any

import voluptuous as vol

from homeassistant.components import mqtt
from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    TextSelector,
    TextSelectorConfig,
)

from . import model
from .const import (
    CONF_LOCK_NAME,
    CONF_NUKI_ID,
    CONF_PEOPLE,
    CONF_TOPIC_PREFIX,
    DEFAULT_TOPIC_PREFIX,
    DISCOVERY_TIMEOUT,
    DOMAIN,
)

MANUAL = "__manual__"
PEOPLE_HELP = "# Une ligne par personne :  ID = Nom\n# Code clavier :  code:ID = Nom\n"


class NukiWhoConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        self._found: dict[str, str] = {}

    async def _discover(self, prefix: str) -> dict[str, str]:
        """Écoute brièvement <prefix>/+/name (messages retenus) pour lister les serrures."""
        found: dict[str, str] = {}

        @callback
        def _msg(msg: mqtt.ReceiveMessage) -> None:
            parts = msg.topic.split("/")
            if len(parts) == 3:
                found[parts[1]] = str(msg.payload).strip() or parts[1]

        unsub = await mqtt.async_subscribe(self.hass, f"{prefix}/+/name", _msg)
        await asyncio.sleep(DISCOVERY_TIMEOUT)
        unsub()
        return found

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if not await mqtt.async_wait_for_mqtt_client(self.hass):
            return self.async_abort(reason="mqtt_not_ready")
        if user_input is not None:
            if user_input[CONF_NUKI_ID] == MANUAL:
                return await self.async_step_manual()
            nuki_id = user_input[CONF_NUKI_ID]
            return await self._create(nuki_id, self._found.get(nuki_id, ""), DEFAULT_TOPIC_PREFIX)

        self._found = await self._discover(DEFAULT_TOPIC_PREFIX)
        options = [SelectOptionDict(value=k, label=f"{v} ({k})") for k, v in sorted(self._found.items())]
        options.append(SelectOptionDict(value=MANUAL, label="Saisir l'identifiant à la main…"))
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required(CONF_NUKI_ID): SelectSelector(SelectSelectorConfig(options=options))}),
            description_placeholders={"count": str(len(self._found))},
        )

    async def async_step_manual(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            nuki_id = user_input[CONF_NUKI_ID].strip().upper()
            if not nuki_id.isalnum():
                errors[CONF_NUKI_ID] = "invalid_id"
            else:
                return await self._create(
                    nuki_id, user_input.get(CONF_LOCK_NAME, ""), user_input.get(CONF_TOPIC_PREFIX, DEFAULT_TOPIC_PREFIX)
                )
        return self.async_show_form(
            step_id="manual",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_NUKI_ID): str,
                    vol.Optional(CONF_LOCK_NAME, default=""): str,
                    vol.Optional(CONF_TOPIC_PREFIX, default=DEFAULT_TOPIC_PREFIX): str,
                }
            ),
            errors=errors,
        )

    async def _create(self, nuki_id: str, name: str, prefix: str) -> ConfigFlowResult:
        await self.async_set_unique_id(nuki_id)
        self._abort_if_unique_id_configured()
        return self.async_create_entry(
            title=name or f"Nuki {nuki_id}",
            data={CONF_NUKI_ID: nuki_id, CONF_LOCK_NAME: name, CONF_TOPIC_PREFIX: prefix},
            options={CONF_PEOPLE: PEOPLE_HELP},
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return NukiWhoOptionsFlow()


class NukiWhoOptionsFlow(OptionsFlow):
    """Liste des personnes : stockée uniquement dans la configuration locale de HA."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        placeholders = {"error": ""}
        if user_input is not None:
            try:
                model.parse_people(user_input[CONF_PEOPLE])
            except ValueError as err:
                errors[CONF_PEOPLE] = "invalid_people"
                placeholders["error"] = str(err)
            else:
                return self.async_create_entry(data=user_input)
        current = self.config_entry.options.get(CONF_PEOPLE, PEOPLE_HELP)
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {vol.Required(CONF_PEOPLE, default=current): TextSelector(TextSelectorConfig(multiline=True))}
            ),
            errors=errors,
            description_placeholders=placeholders,
        )
