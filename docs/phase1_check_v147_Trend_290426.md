# Prüfung Phase 1 (Tiefenentladung) – Vergleich v146 vs v147

## Ausgangslage
- Datengrundlage: `Trend_290426.csv` (aufgenommen mit `zendure_v146.yaml`).
- Ziel: Prüfen, ob das in `zendure_v147.yaml` eingebaute Verhalten das beobachtete Problem von Phase 1 behebt.

## Befund aus Trend_290426 (v146)

### Unit 1
- Minimaler SoC: **5.0 %** am **2026-04-29T05:09:50.241Z**.
- Minimaler Zellwert (`cell_min_vol`): **3.13 V** am **2026-04-29T05:48:48.780Z**.

Interpretation:
- In v146 endet Phase 1 nur über den Spannungs-Trigger (`cell_min_vol <= 2.86V`).
- Da Unit 1 zwar auf 5 % SoC gefallen ist, aber **nicht** auf 2.86 V, wurde Phase 1 nicht sauber beendet.
- Genau dieses Verhalten passt zu deiner Beobachtung („5 % erreicht, aber Phase 1 endet nicht“).

### Unit 2
- `output_block_reason` wechselte mehrfach zwischen:
  - `discharging_calib`
  - `vguard_latch`
  - später `freigegeben`

Interpretation:
- Das ist konsistent mit einer laufenden/unterbrochenen Entladephase unter aktivem Voltage-Guard.
- Der Wechsel ist bei v146 plausibel, weil nur die Spannungs-Bedingung die Entladephase final abschließt.

## Relevante Änderungen in v147 für Phase 1

1. **Neue End-Bedingung via SoC**
   - Neue Trigger `empty_soc_u1` und `empty_soc_u2`:
     - aktiv, wenn Entladephase läuft **und** SoC <= **5.0 %** (für 2 Minuten).
   - Abschlusslogik reagiert jetzt auf `empty_u*` **oder** `empty_soc_u*`.

2. **Start-/Resume-Logik robuster gegen PV-Einfluss**
   - `pv_ready_u*` jetzt strenger (PV <= 10 W für 15 min statt <= 20 W für 5 min).
   - Entlade-Pause erfolgt nun über `pv_resume_u*` (PV >= konfigurierbarer High-Threshold für 5 min), statt hartem Tages-Cutoff um 10:00.

3. **Force-Flag-Setzung um 20:00 entkoppelt**
   - 20:00 setzt nur die Force-Flags, der eigentliche Start hängt an den passenden Bedingungen.

## Ergebnis
Für das konkrete Problem aus v146 ist v147 fachlich korrekt verbessert:
- Wenn eine Unit in Phase 1 am Hardware-Limit (5 %) hängt, aber die Zellspannung nicht bis 2.86 V fällt, beendet v147 Phase 1 trotzdem zuverlässig über den neuen SoC-Trigger.
- Die mehrfachen Statuswechsel bei Unit 2 sind mit der alten v146-Logik erklärbar; v147 reduziert hier die Wahrscheinlichkeit von „hängenbleibender“ Entladephase deutlich.

## Empfehlung für Live-Verifikation mit v147
Für den nächsten Kalibrierzyklus in HA (Trend-Export):
- mitloggen:
  - `input_boolean.zendure_calib_discharge_u1/u2`
  - `sensor.solarflow_1/2_battery_level`
  - `sensor.solarflow_1/2_cell_min_vol`
  - `sensor.solarflow_1/2_output_block_reason`
- Akzeptanzkriterium:
  - Bei laufender Phase 1 muss bei `SoC <= 5%` (stabil >= 2 min) das jeweilige `zendure_calib_discharge_u*` auf `off` gehen und Phase 2 freigegeben werden, auch wenn `cell_min_vol > 2.86V` bleibt.
