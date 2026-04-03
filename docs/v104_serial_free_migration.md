# v104 Serial-Free Base Refactor (Migration)

Diese Migration entfernt feste Zendure-Seriennummern aus `zendure_v104.yaml`.
Alle Zendure-MQTT-Topics werden jetzt über `!secret`-Keys aufgelöst.

## Schritt 1: Secrets ergänzen

1. Öffne deine `secrets.yaml`.
2. Kopiere die Einträge aus `docs/secrets_v104_serial_free.example.yaml` in deine `secrets.yaml`.
3. Passe die Werte (Topics/Entities) an deine Umgebung an.

Zusätzlich sind folgende Keys erforderlich:

```yaml
telegram_id1: "notify.telegram_bot_..."
telegram_id2: "notify.telegram_bot_..."
power_meter_total_consumption: "sensor.<dein_power_meter_total>"
zendure_gridoffmode_entity_u1: "select.<dein_u1_gridoffmode_entity>"
zendure_gridoffmode_entity_u2: "select.<dein_u2_gridoffmode_entity>"
```

## Schritt 2: HA prüfen

- Konfiguration prüfen und HA neu starten.
- Danach prüfen, ob alle MQTT-Sensoren/Automationen wieder grün sind.

## Hinweis

Die v104-Datei enthält danach keine festen `EEA...`-Seriennummern mehr.
