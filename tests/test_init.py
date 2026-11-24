from unittest.mock import patch

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_capture_events,
    async_fire_mqtt_message,
)

from custom_components.nuki_who.const import CONF_PEOPLE, DOMAIN, EVENT_LOCK_ACTION

LOCK = "ABCD1234"  # identifiant fictif


async def test_config_flow_discovery(hass: HomeAssistant, mqtt_mock) -> None:
    with patch("custom_components.nuki_who.config_flow.DISCOVERY_TIMEOUT", 0.05):
        async_fire_mqtt_message(hass, f"nuki/{LOCK}/name", "Porte test", retain=True)
        result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
        assert result["type"] is FlowResultType.FORM and result["step_id"] == "user"
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {"nuki_id": "__manual__"})
        assert result["step_id"] == "manual"
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"nuki_id": LOCK.lower(), "lock_name": "Porte test", "topic_prefix": "nuki"}
        )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"]["nuki_id"] == LOCK and result["title"] == "Porte test"
    await hass.async_block_till_done()


async def test_events_and_options(hass: HomeAssistant, mqtt_mock) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN, unique_id=LOCK,
        data={"nuki_id": LOCK, "lock_name": "Porte test", "topic_prefix": "nuki"},
        options={CONF_PEOPLE: "111111 = Personne A\ncode:7 = Personne C"},
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    events = async_capture_events(hass, EVENT_LOCK_ACTION)

    async_fire_mqtt_message(hass, f"nuki/{LOCK}/lockActionEvent", "1,0,111111,0,0")
    await hass.async_block_till_done()
    person = [s for s in hass.states.async_all("sensor") if "person" in s.entity_id][0]
    action = [s for s in hass.states.async_all("sensor") if "action" in s.entity_id][0]
    assert person.state == "Personne A" and person.attributes["trigger_label"] == "appli / Bluetooth"
    assert action.state == "déverrouillage"
    ev = hass.states.async_all("event")[0]
    assert ev.attributes["event_type"] == "unlock" and ev.attributes["person"] == "Personne A"
    assert events[-1].data["person"] == "Personne A" and events[-1].data["lock"] == "Porte test"

    async_fire_mqtt_message(hass, f"nuki/{LOCK}/lockActionEvent", "3,0,555,7")
    await hass.async_block_till_done()
    assert hass.states.get(person.entity_id).state == "Personne C"
    assert hass.states.get(person.entity_id).attributes["via_keypad"] is True

    # message invalide : ignoré sans erreur
    async_fire_mqtt_message(hass, f"nuki/{LOCK}/lockActionEvent", "n'importe quoi")
    await hass.async_block_till_done()
    assert hass.states.get(person.entity_id).state == "Personne C"

    # options : format invalide refusé, puis valide
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(result["flow_id"], {CONF_PEOPLE: "sans égal"})
    assert result["errors"] == {CONF_PEOPLE: "invalid_people"}
    result = await hass.config_entries.options.async_configure(result["flow_id"], {CONF_PEOPLE: "999 = Personne Z"})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    async_fire_mqtt_message(hass, f"nuki/{LOCK}/lockActionEvent", "1,0,999,0")
    await hass.async_block_till_done()
    assert hass.states.get(person.entity_id).state == "Personne Z"
