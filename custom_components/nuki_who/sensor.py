"""Capteurs : dernière personne et dernière action (restaurés au redémarrage)."""
from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import RestoreSensor, SensorEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import NukiWho, NukiWhoConfigEntry
from .entity import device_info


async def async_setup_entry(
    hass: HomeAssistant, entry: NukiWhoConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    d = entry.runtime_data
    async_add_entities([LastPersonSensor(d), LastActionSensor(d)])


class _Base(RestoreSensor, SensorEntity):
    _attr_has_entity_name = True
    _attr_should_poll = False
    _key = ""
    _field = ""

    def __init__(self, data: NukiWho) -> None:
        self._data = data
        self._attr_unique_id = f"{data.nuki_id}_{self._key}"
        self._attr_translation_key = self._key
        self._attr_device_info = device_info(data)
        self._attrs: dict[str, Any] = {}

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if (last := await self.async_get_last_state()) is not None and last.state not in ("unknown", "unavailable"):
            self._attr_native_value = last.state
            self._attrs = dict(last.attributes)
        self.async_on_remove(async_dispatcher_connect(self.hass, self._data.signal, self._update))

    @callback
    def _update(self) -> None:
        last = self._data.last or {}
        self._attr_native_value = last.get(self._field)
        self._attrs = {k: v for k, v in last.items() if k != self._field}
        self.async_write_ha_state()

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {k: v for k, v in self._attrs.items() if k not in ("friendly_name", "icon")}


class LastPersonSensor(_Base):
    _key = "last_person"
    _field = "person"
    _attr_icon = "mdi:account-key"


class LastActionSensor(_Base):
    _key = "last_action"
    _field = "action_label"
    _attr_icon = "mdi:lock-clock"
