"""Entité événement : chaque action de la serrure, visible dans le journal."""
from __future__ import annotations

from homeassistant.components.event import EventEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import NukiWho, NukiWhoConfigEntry
from .entity import device_info
from .model import EVENT_TYPES


async def async_setup_entry(
    hass: HomeAssistant, entry: NukiWhoConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    async_add_entities([LockActionEventEntity(entry.runtime_data)])


class LockActionEventEntity(EventEntity):
    _attr_has_entity_name = True
    _attr_translation_key = "lock_action"
    _attr_event_types = EVENT_TYPES
    _attr_icon = "mdi:door-open"

    def __init__(self, data: NukiWho) -> None:
        self._data = data
        self._attr_unique_id = f"{data.nuki_id}_lock_action"
        self._attr_device_info = device_info(data)

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(async_dispatcher_connect(self.hass, self._data.signal, self._handle))

    @callback
    def _handle(self) -> None:
        last = dict(self._data.last or {})
        self._trigger_event(last.pop("action", "other"), last)
        self.async_write_ha_state()
