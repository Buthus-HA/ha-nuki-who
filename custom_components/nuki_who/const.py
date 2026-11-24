"""Constantes."""
from __future__ import annotations

import json
from pathlib import Path

DOMAIN = "nuki_who"
VERSION: str = json.loads((Path(__file__).parent / "manifest.json").read_text(encoding="utf-8"))["version"]

CONF_NUKI_ID = "nuki_id"
CONF_LOCK_NAME = "lock_name"
CONF_TOPIC_PREFIX = "topic_prefix"
CONF_PEOPLE = "people"          # texte "ID = Nom", une ligne par personne

DEFAULT_TOPIC_PREFIX = "nuki"
DISCOVERY_TIMEOUT = 3           # secondes d'écoute des messages retenus nuki/+/name

EVENT_LOCK_ACTION = "nuki_who_lock_action"
SIGNAL_LOCK_ACTION = "nuki_who_lock_action_{}"
