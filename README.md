# Nuki – qui a ouvert ? (Home Assistant)

Savoir **qui** a verrouillé ou déverrouillé une serrure Nuki, et **comment**, en restant 100 % local :
l'intégration écoute l'**API MQTT locale** de la serrure (sujet `nuki/<ID>/lockActionEvent`), sans cloud ni abonnement.

Projet personnel non affilié à Nuki Home Solutions.

## Prérequis

- Intégration **MQTT** de Home Assistant configurée (broker Mosquitto par ex.).
- Dans l'appli Nuki : *Fonctionnalités & configuration → MQTT* activé et connecté au même broker.

## Installation

HACS → ⋮ → Dépôts personnalisés → `https://github.com/Buthus-HA/ha-nuki-who` (catégorie *Intégration*),
puis **Paramètres → Appareils et services → Ajouter une intégration → Nuki – qui a ouvert ?**.
Les serrures présentes sur MQTT sont détectées automatiquement.

## Personnes (données privées)

**Configurer** sur l'intégration, une ligne par personne :

```text
123456 = Alice          # Auth-ID (appli, porte-clés, Bluetooth…)
code:12 = Bob           # code clavier (Code-ID)
```

Pour connaître un Auth-ID : faites une ouverture, le capteur « Dernière personne » affiche
« Utilisateur inconnu (123456) ». Cette liste est enregistrée **uniquement** dans la configuration
locale de Home Assistant ; elle ne fait pas partie de ce dépôt.

Les actions sans utilisateur sont nommées d'après leur source : *Home Assistant*, *Bouton de la serrure*,
*Verrouillage automatique*, *Manuel (molette / clé)*, *Matter / HomeKit*.

## Entités

| Entité | État | Attributs |
|---|---|---|
| `sensor.<serrure>_derniere_personne` | nom | `action`, `action_label`, `trigger_label`, `auth_id`, `code_id`, `via_keypad`, `time` |
| `sensor.<serrure>_derniere_action` | `déverrouillage`, `verrouillage`… | idem, avec `person` |
| `event.<serrure>_action` | type : `unlock`, `lock`, `unlatch`… | `person`, `trigger_label`… |

## Événement

`nuki_who_lock_action` : `lock`, `nuki_id`, `person`, `identified`, `action`, `action_label`,
`trigger`, `trigger_label`, `auth_id`, `code_id`, `via_keypad`, `time`.

```yaml
triggers:
  - trigger: event
    event_type: nuki_who_lock_action
    event_data: { action: unlock }
actions:
  - action: notify.mobile_app_xxx
    data:
      message: "{{ trigger.event.data.person }} a déverrouillé ({{ trigger.event.data.trigger_label }})"
```

## Format décodé

`LockAction,Trigger,Auth-ID,Code-ID[,…]` selon la spécification MQTT de Nuki :
si `Code-ID` ≠ 0 la personne est identifiée par son code clavier, sinon par son Auth-ID.
