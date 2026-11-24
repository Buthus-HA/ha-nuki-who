"""Décodage de lockActionEvent (API MQTT Nuki) – fonctions pures, testables sans HA.

Format : LockAction,Trigger,Auth-ID,Code-ID[,Auto-Unlock / type d'appui]
Si Code-ID vaut 0 la personne est identifiée par l'Auth-ID ; sinon (clavier) par le Code-ID.
"""
from __future__ import annotations

from dataclasses import dataclass

LOCK_ACTIONS: dict[int, tuple[str, str]] = {
    0: ("none", "aucune action"),
    1: ("unlock", "déverrouillage"),
    2: ("lock", "verrouillage"),
    3: ("unlatch", "ouverture"),
    4: ("lock_n_go", "lock'n'go"),
    5: ("lock_n_go_unlatch", "lock'n'go avec ouverture"),
    6: ("full_lock", "verrouillage complet"),
}
TRIGGERS: dict[int, str] = {
    0: "appli / Bluetooth",
    1: "manuel",
    2: "bouton",
    3: "automatique",
    6: "verrouillage automatique",
    171: "Matter / HomeKit",
    172: "Home Assistant (MQTT)",
}
# Déclencheurs sans utilisateur identifiable : on nomme la source plutôt que « Inconnu ».
SYSTEM_TRIGGERS: dict[int, str] = {
    2: "Bouton de la serrure",
    3: "Automatique",
    6: "Verrouillage automatique",
    171: "Matter / HomeKit",
    172: "Home Assistant",
}
EVENT_TYPES = sorted({key for key, _ in LOCK_ACTIONS.values()} | {"other"})


@dataclass(frozen=True)
class LockActionEvent:
    action: int
    trigger: int
    auth_id: int
    code_id: int
    extra: int | None

    @property
    def action_key(self) -> str:
        return LOCK_ACTIONS.get(self.action, ("other", ""))[0]

    @property
    def action_label(self) -> str:
        return LOCK_ACTIONS.get(self.action, ("other", f"action {self.action}"))[1]

    @property
    def trigger_label(self) -> str:
        return TRIGGERS.get(self.trigger, f"déclencheur {self.trigger}")

    @property
    def via_keypad(self) -> bool:
        return self.code_id != 0


def parse(payload: str) -> LockActionEvent:
    """Décode le message ; lève ValueError s'il est invalide."""
    parts = [p.strip() for p in str(payload).strip().split(",")]
    if len(parts) < 4:
        raise ValueError(f"lockActionEvent incomplet : {payload!r}")
    nums = [int(p) for p in parts[:5]]
    return LockActionEvent(nums[0], nums[1], nums[2], nums[3], nums[4] if len(nums) > 4 else None)


def parse_people(text: str) -> dict[str, str]:
    """Lit le texte de configuration « ID = Nom ».

    - « 123456 = Alice »   : Auth-ID (appli, Bluetooth, porte-clés…)
    - « code:12 = Bob »   : Code-ID du clavier
    Les lignes vides et celles qui commencent par # sont ignorées.
    """
    people: dict[str, str] = {}
    for n, raw in enumerate((text or "").splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise ValueError(f"ligne {n} : format attendu « ID = Nom »")
        key, name = (s.strip() for s in line.split("=", 1))
        kind = "auth"
        if key.lower().startswith("code:"):
            kind, key = "code", key[5:].strip()
        if not key.isdigit() or not name:
            raise ValueError(f"ligne {n} : identifiant numérique et nom requis")
        people[f"{kind}:{int(key)}"] = name
    return people


def who(event: LockActionEvent, people: dict[str, str]) -> tuple[str, bool]:
    """Retourne (nom affiché, identifié ?)."""
    if event.via_keypad:
        name = people.get(f"code:{event.code_id}")
        return (name, True) if name else (f"Code clavier inconnu ({event.code_id})", False)
    if event.auth_id:
        name = people.get(f"auth:{event.auth_id}")
        return (name, True) if name else (f"Utilisateur inconnu ({event.auth_id})", False)
    if event.trigger in SYSTEM_TRIGGERS:
        return SYSTEM_TRIGGERS[event.trigger], True
    if event.trigger == 1:
        return "Manuel (molette / clé)", True
    return "Inconnu", False
