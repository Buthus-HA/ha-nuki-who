# Changelog

## 0.1.0 — 2026-11-24
- Version initiale : décodage de `lockActionEvent` (API MQTT locale Nuki), identification par Auth-ID ou par code clavier.
- Détection automatique des serrures sur MQTT à l'installation.
- Capteurs « Dernière personne » / « Dernière action » (restaurés au redémarrage), entité événement, événement `nuki_who_lock_action`.
- Liste des personnes gérée dans les options de l'intégration (stockée localement dans HA, jamais dans le dépôt).
