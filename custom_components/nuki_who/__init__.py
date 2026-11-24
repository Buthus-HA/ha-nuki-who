"""Nuki – qui a ouvert ? Décode lockActionEvent (API MQTT locale Nuki)."""
from __future__ import annotations

import logging
from datetime import datetime

from homeassistant.components import mqtt
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.util import dt as dt_util

from . import model
from .const import (
    CONF_LOCK_NAME,
    CONF_NUKI_ID,
    CONF_PEOPLE,
    CONF_TOPIC_PREFIX,
    DEFAULT_TOPIC_PREFIX,
    EVENT_LOCK_ACTION,
    SIGNAL_LOCK_ACTION,
)

_LOGGER = logging.getLogger(__name__)
PLATFORMS = [Platform.SENSOR, Platform.EVENT]


class NukiWho:
    """État partagé d'une serrure : dernier événement décodé."""

    def __init__(self, entry: ConfigEntry) -> None:
        self.entry = entry
        self.nuki_id: str = entry.data[CONF_NUKI_ID]
        self.lock_name: str = entry.data.get(CONF_LOCK_NAME) or f"Nuki {self.nuki_id}"
        prefix = entry.data.get(CONF_TOPIC_PREFIX, DEFAULT_TOPIC_PREFIX)
        self.topic = f"{prefix}/{self.nuki_id}/lockActionEvent"
        self.people = model.parse_people(entry.options.get(CONF_PEOPLE, ""))
        self.last: dict | None = None

    @property
    def signal(self) -> str:
        return SIGNAL_LOCK_ACTION.format(self.entry.entry_id)


type NukiWhoConfigEntry = ConfigEntry[NukiWho]


async def async_setup_entry(hass: HomeAssistant, entry: NukiWhoConfigEntry) -> bool:
    data = NukiWho(entry)
    entry.runtime_data = data

    @callback
    def _message(msg: mqtt.ReceiveMessage) -> None:
        try:
            ev = model.parse(msg.payload)
        except ValueError as err:
            _LOGGER.warning("Message ignoré sur %s : %s", msg.topic, err)
            return
        name, known = model.who(ev, data.people)
        when: datetime = dt_util.utcnow()
        data.last = {
            "person": name,
            "identified": known,
            "action": ev.action_key,
            "action_label": ev.action_label,
            "trigger": ev.trigger,
            "trigger_label": ev.trigger_label,
            "auth_id": ev.auth_id,
            "code_id": ev.code_id,
            "via_keypad": ev.via_keypad,
            "extra": ev.extra,
            "time": when.isoformat(),
        }
        hass.bus.async_fire(EVENT_LOCK_ACTION, {"lock": data.lock_name, "nuki_id": data.nuki_id, **data.last})
        async_dispatcher_send(hass, data.signal)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(await mqtt.async_subscribe(hass, data.topic, _message, qos=1))
    entry.async_on_unload(entry.add_update_listener(_reload))
    return True


async def _reload(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: NukiWhoConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
