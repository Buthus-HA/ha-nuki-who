import pytest

from custom_components.nuki_who import model

PEOPLE = model.parse_people("""
# commentaire
111111 = Personne A
222222 = Personne B
code:7 = Personne C (clavier)
""")


def test_parse_people():
    assert PEOPLE == {"auth:111111": "Personne A", "auth:222222": "Personne B", "code:7": "Personne C (clavier)"}
    with pytest.raises(ValueError):
        model.parse_people("pas de signe égal")
    with pytest.raises(ValueError):
        model.parse_people("abc = Nom")


@pytest.mark.parametrize(
    ("payload", "person", "known", "action", "trigger"),
    [
        ("1,0,111111,0", "Personne A", True, "unlock", "appli / Bluetooth"),       # appli
        ("2,0,222222,0,0", "Personne B", True, "lock", "appli / Bluetooth"),       # 5e champ présent
        ("1,0,999999,0", "Utilisateur inconnu (999999)", False, "unlock", "appli / Bluetooth"),
        ("3,0,333333,7", "Personne C (clavier)", True, "unlatch", "appli / Bluetooth"),  # clavier : Code-ID prime
        ("1,0,333333,9", "Code clavier inconnu (9)", False, "unlock", "appli / Bluetooth"),
        ("2,172,0,0", "Home Assistant", True, "lock", "Home Assistant (MQTT)"),
        ("2,2,0,0,1", "Bouton de la serrure", True, "lock", "bouton"),
        ("2,6,0,0", "Verrouillage automatique", True, "lock", "verrouillage automatique"),
        ("1,1,0,0", "Manuel (molette / clé)", True, "unlock", "manuel"),
        ("42,99,0,0", "Inconnu", False, "other", "déclencheur 99"),
    ],
)
def test_who(payload, person, known, action, trigger):
    ev = model.parse(payload)
    assert model.who(ev, PEOPLE) == (person, known)
    assert ev.action_key == action
    assert ev.trigger_label == trigger


def test_invalid():
    with pytest.raises(ValueError):
        model.parse("1,2")
    with pytest.raises(ValueError):
        model.parse("a,b,c,d")
