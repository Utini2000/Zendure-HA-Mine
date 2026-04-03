# Comparison: `custom_components/zendure_ha` vs `zendure_v104.yaml` for multiple SolarFlow 800 Pro

## Scope
This comparison focuses on multi-device behavior, especially two or more SolarFlow 800 Pro units.

## Executive summary
- **Best default choice for most users:** `custom_components/zendure_ha`
  - Auto-discovers devices from Zendure API, supports SF800 Pro directly, has built-in fuse-group logic, and is easier to maintain across device changes.
- **Best for highly customized dual-unit control experiments:** `zendure_v104.yaml`
  - Extremely aggressive and detailed 5-second control loop with many safety and balancing heuristics, but it is hardcoded to two specific device IDs and a specific meter entity.

## Key differences

| Area | `custom_components/zendure_ha` | `zendure_v104.yaml` |
|---|---|---|
| Device onboarding | Dynamic via token/API device list and product model mapping. | Manual + static topics and IDs. |
| SF800 Pro support | Native class (`SolarFlow800Pro`) with off-grid sensors and limits. | Implicit support only through MQTT topic naming; no Python device model abstraction. |
| Scale beyond 2 devices | Designed for N devices + fuse groups. | Built around Unit 1 + Unit 2 only. |
| Control cadence | Event-driven by P1 updates + internal minimum timing. | Time pattern every 5s plus extra triggers. |
| Maintainability | Structured Python integration in HA config flow/HACS style. | Large monolithic YAML automation (~1700 lines). |
| Portability | Higher (device IDs learned from API). | Lower (hardcoded serial-based topic paths + specific Shelly entity). |
| Safety logic | Manager modes, device status handling, split fuse groups. | Rich custom safety (kill switch, anti-drift, vguard, emergency/manual routines). |
| Reliability risk profile | Lower configuration drift risk, less manual wiring. | Higher human error risk due to many manual helpers/topics/templates. |

## If you prefer `zendure_v104.yaml`: best features to import from `custom_components/zendure_ha`

Below is the practical “best-of-both-worlds” import backlog.

### Priority 1 (high impact)
1. **Dynamic device registry (remove hardcoded IDs)**
   - Build a mapping layer (`unit_name -> device_id/topic prefix`) and generate entities/scripts from that map.
   - Outcome: your YAML scales from 2 devices to N devices without copy/paste blocks.

2. **Fuse-group abstraction and shared limits**
   - Introduce a group model similar to `group800`, `group1200`, `group2400`, etc., with per-group max/min power.
   - Outcome: safer allocation when multiple SF800 Pro units share a circuit.

3. **Event-driven + adaptive update rate (not only fixed 5s loop)**
   - Keep your fast loop, but add statistical trigger logic (stddev-based) to avoid unnecessary writes when grid is stable.
   - Outcome: keeps responsiveness while reducing MQTT chatter and command thrashing.

4. **Multi-source connection strategy (cloud + local preference + status)**
   - Track effective connection path and fail over more predictably.
   - Outcome: improved resilience when local/cloud broker quality changes.

### Priority 2 (stability and observability)
5. **Structured connection status model**
   - Add a unified status sensor/state machine that distinguishes offline, SOC-limited, HEMS state, and active connection path.
   - Outcome: easier troubleshooting and fewer “mystery states”.

6. **Restore-based aggregate energy counters**
   - Port aggregate counters (charge/discharge/grid/solar/home/off-grid) with persistent restore behavior.
   - Outcome: better long-term analytics and fewer resets after HA restarts.

7. **Battery pack-aware capacity calculation**
   - Auto-calculate total kWh and available kWh from pack data instead of static assumptions.
   - Outcome: better dispatch decisions when packs are added/removed.

8. **Calibration scheduling metadata**
   - Add/standardize next-calibration timestamp logic and status exposure.
   - Outcome: predictable maintenance behavior and simpler automations.

### Priority 3 (security and maintainability)
9. **Automatic local MQTT technical-user handling (optional)**
   - Add opt-in provisioning/rotation for per-device MQTT credentials.
   - Outcome: easier secure rollout when devices change.

10. **Persisted bootstrap data fallback**
   - Cache last known device list/mqtt parameters and start from cache if cloud lookup fails.
   - Outcome: improved cold-start reliability.

11. **Modularize YAML into packages**
   - Split into `helpers.yaml`, `sensors.yaml`, `control_loop.yaml`, `safety.yaml`, `calibration.yaml`, `devices.yaml`.
   - Outcome: lower risk when editing; easier review/testing.

## Suggested “master integration” architecture
- Keep your **existing advanced control/safety logic** from `zendure_v104.yaml`.
- Add a **thin dynamic device layer** (from integration ideas) that provides per-device metadata and generated topics.
- Add a **fuse-group allocator module** for fair and safe power distribution across N units.
- Replace only the most duplicated hardcoded parts first (topics, IDs, per-unit scripts).

## Practical recommendation
1. Keep `zendure_v104.yaml` as your decision engine (because you prefer its feature richness and speed).
2. Import **Priority 1** items first; this gives the biggest reliability/scalability gain.
3. Then add Priority 2/3 in small steps and validate each step for a full day of operation before proceeding.

## Calibration and low-voltage handling: `zendure_ha` vs `zendure_v104`

### Calibration behavior
- `custom_components/zendure_ha`
  - Tracks calibration metadata (`nextCalibration`) and updates it when SoC status indicates reset conditions or battery reaches 100%.
  - This is mostly **state tracking/telemetry**; there is no large built-in multi-step calibration state machine in this repo.
- `zendure_v104.yaml`
  - Implements explicit calibration control paths with dedicated booleans and startup initialization logic (`zendure_calib_mode_*`, `zendure_force_calib_*`, timestamp helpers).
  - Includes periodic AC-mode reconcile logic that avoids breaking protection charging while calibration/emergency state is active.

### Low-voltage behavior
- `custom_components/zendure_ha`
  - Uses device-level SoC boundaries (`minSoc`, `socSet`, `socLimit`) to classify states (`SOCEMPTY`, `SOCFULL`) and guide manager power logic.
  - Does not implement explicit cell-min-voltage guard latches comparable to your custom `vguard` workflow.
- `zendure_v104.yaml`
  - Adds **explicit cell-voltage safety guards** (`vguard`) and hard/soft emergency triggers based on `cell_min_vol`, SoC, output power, freshness, and temperature checks.
  - In control loop, dynamically clamps/derates output at low cell voltage (e.g., zero at very low Vmin, staged limits around 3.05/3.10V) and can force emergency charge mode.

### Bottom line
- For **calibration automation depth** and **low-voltage protection sophistication**, `zendure_v104.yaml` is currently stronger.
- For **clean core device-state handling and maintainability**, `custom_components/zendure_ha` is cleaner but less aggressive on custom low-voltage workflows.

## Tuning profiles for your `zendure_v104` (Safe / Balanced / Aggressive)

### Is current `v104` already optimal?
- **No single profile is globally optimal.**
- Your current logic is already very advanced and safety-aware, but it is tuned toward a fairly assertive export-control behavior with strong emergency fallback.
- In practice, “optimal” depends on your goal priority: battery longevity, grid-tracking precision, or max self-consumption.

### Current `v104` baseline (from templates/default fallbacks)
- Typical fallback thresholds observed in templates:
  - `soc_off ≈ 20%`
  - emergency start around `15%`, stop around `25%`
  - vguard set near `vmin <= 3.02V` (normal) or `<= 2.95V` (hard)
  - hard voltage emergency at `vmin <= 3.00V` for short persistence
  - output derating bands around `<3.10V`, `<3.05V`, and cut near `<3.00V`

This is already a **Balanced/Aggressive hybrid**: good grid performance, but more cycling stress than a conservative profile.

### Recommended profiles

| Profile | Goal | Suggested settings vs current baseline | Why it can be better |
|---|---|---|---|
| **Safe (battery-first)** | Maximize longevity and voltage headroom | Increase `soc_off` to 25–30%; increase emergency start to 18–22%; increase emergency stop to 30–35%; trigger vguard earlier (e.g. around 3.08/3.02 instead of 3.02/2.95); reduce max output cap per unit under low-voltage bands; increase hysteresis/min-change to reduce chatter. | Less deep discharge, less time in low cell-voltage region, lower thermal stress, fewer rapid mode flips. |
| **Balanced (recommended default)** | Keep strong self-consumption with moderate wear | Keep `soc_off` around 20–22%; emergency start 14–17%; stop 25–28%; keep existing derating bands but soften export aggressiveness (slightly higher hysteresis and min-change). | Good compromise between bill savings and battery stress. |
| **Aggressive (yield/grid-following)** | Maximize discharge and export matching | Lower `soc_off` to 12–18%; emergency start 10–14%; stop 20–24%; allow later vguard trigger and lower hysteresis/min-change for faster control action. | Best short-term grid tracking / self-consumption, but higher cycle depth and more low-voltage exposure. |

### Concrete first-step values (easy to apply)
If you want a safer but still responsive setup, start with this **Balanced+** profile:
- `input_number.zendure_conf_soc_off`: **22**
- `input_number.zendure_conf_soc_emerg_start`: **16**
- `input_number.zendure_conf_soc_emerg_stop`: **28**
- `input_number.zendure_conf_hysteresis`: **12–15** (from 10)
- `input_number.zendure_conf_min_change`: **8–10** (from 5)
- Keep global max output as-is first; only reduce if you still see repeated vguard/emergency events.

### How these differ from current `v104` and when they win
- **Safe / Balanced+** improves battery protection by entering protective states earlier than current defaults and by reducing command oscillation.
- **Aggressive** can outperform on short-term import/export matching but is not better for battery health over time.
- So: your current `v104` is **not wrong**; it is just tuned more performance-forward than battery-conservative.

## Wertevergleich (Kalibrierung & Not-Stopp) und Einordnung

### 1) Kalibrierung – konkrete Vorgaben

**`zendure_v104.yaml`**
- Eigene Kalibrier-Helfer/Flags pro Unit (`zendure_calib_mode_u*`, `zendure_force_calib_u*`) + Initialisierungslogik beim HA-Start.
- Kalibrier-Intervall als Konfiguration vorhanden: `zendure_conf_calib_days` mit Bereich **1..60 Tage**.
- Umschalt-Schwellen für Kalibrier-Kontext:
  - `zendure_conf_calib_pv_low` initial **40 W**
  - `zendure_conf_calib_pv_high` initial **70 W**

**`custom_components/zendure_ha`**
- Kein umfangreicher Kalibrier-Automat mit separaten Start/Stop-Schwellen.
- Stattdessen `nextCalibration`-Zeitstempel, der bei SoC-/100%-Ereignissen auf **+30 Tage** gesetzt wird.

### 2) Not-Stopp / Schutzladung – konkrete Vorgaben

**`zendure_v104.yaml` (explizit, mehrstufig)**
- SoC-basierter Not-Start (Fallback typ. `soc_emerg_start` ~15%).
- Spannungsbasierte Not-Starts:
  - „soft“ bei `cell_min_vol <= 3.05V` (mit Persistenz)
  - „hard“ bei `cell_min_vol <= 3.00V` (kurze Persistenz)
- Not-Stopp typischerweise bei Erholung:
  - `soc >= soc_emerg_stop` (Fallback ~25%) **und** `cell_min_vol >= 3.25V`
  - oder ausreichend PV / Fehlerfall / Temperaturbedingung.
- Zusätzlich VGuard-Latch bereits früher (z. B. um ~3.02V bzw. ~2.95V je nach SoC-Kontext), plus Leistungs-Derating im Control-Loop unter ~3.10/3.05/3.00V.

**`custom_components/zendure_ha` (implizit, zustandsbasiert)**
- Kein eigener YAML-ähnlicher Not-Stopp-Block mit Zellspannungs-Schwellen.
- Schutz hauptsächlich über SoC-Grenzen (`minSoc`, `socSet`, `socLimit`) und Gerätezustände (`SOCEMPTY`/`SOCFULL`).

### 3) Ist `v104` zu restriktiv?

**Kurzantwort:** Eher **nicht pauschal zu restriktiv**, aber in Kombination aus VGuard + Emergency + Derating definitiv **schutzorientiert**.

- Für **Batteriegesundheit und Zellschutz** macht `v104` oft „mehr richtig“, weil es Zellspannung, Temperatur, Freshness und Last gleichzeitig bewertet.
- Für **maximale Abgabe / maximale kurzfristige Netzfolge** kann es sich teils zu vorsichtig anfühlen (früheres Abregeln, frühere Schutzzustände).
- Ob „zu vorsichtig“ hängt von deinem Ziel ab:
  - Wenn Batterie-Lebensdauer und Stabilität Priorität haben: eher passend.
  - Wenn maximale Entladung/Ertrag Priorität hat: ggf. Schwellen etwas lockern (Aggressive-Profil).

### 4) Praxistipp zur Entscheidung
- Wenn bei dir häufig VGuard/Emergency triggert, obwohl Zellen sauber bleiben: etwas weniger konservativ testen.
- Wenn du selten triggert, aber gelegentlich tiefe Zellspannungen siehst: lieber bei konservativerem Profil bleiben oder noch leicht anheben.

## Konkrete Bewertung: Macht `v104` etwas falsch oder fehlen Grundfunktionen?

### Was `v104` **nicht falsch** macht (Stärken)
- Sehr robuste Schutzlogik bei kritischen Zuständen (VGuard, mehrstufige Emergency-Trigger, Temperatur-/Freshness-Prüfungen).
- Sehr schnelle Regelung durch 5s-Loop + Ereignis-Trigger.
- Gute Plausibilitätsfilter für Sensorwerte und explizite Guard-Rails im Control-Loop.

### Was in `v104` kritisch/fehleranfällig sein kann
1. **Stark hardcodiert (Geräte + Zähler-Entity):**
   - Feste Device-IDs/Topics und fester Shelly-Entityname erhöhen Migrations- und Wartungsaufwand.
2. **Duplizierte Logik für U1/U2:**
   - Viele nahezu identische Blöcke -> höheres Risiko für Copy/Paste-Divergenz.
3. **Hohe Komplexität in einem Monolith:**
   - Sehr großes YAML mit vielen ineinander greifenden Flags/Zuständen; Änderungen sind regressionsanfälliger.
4. **Hohe Schreib-/Regelaktivität:**
   - Häufige Trigger + wiederholte MQTT-Setzbefehle können unnötige Last erzeugen (insb. bei stabilen Netzlagen).

### Welche wichtigen Grundfunktionen gegenüber `zendure_ha` fehlen
- **Dynamische Device-Erkennung/Onboarding** aus API-DeviceList.
- **Persistenter Fallback** der zuletzt bekannten Device-/MQTT-Daten.
- **Native N-Device-Skalierung** mit zentraler FuseGroup-Logik statt explizit Unit1/Unit2.
- **Saubere Integrationsstruktur (Config Flow / Runtime Data / Entitäten-Lifecycle)** statt ausschließlich Paketlogik.

### Effizienz-/Wartungs-Fazit
- **Regeltechnisch:** `v104` ist schnell und wirkungsvoll.
- **Betrieblich:** bei mehr Geräten meist umständlicher und potenziell fehleranfälliger als die Integration.
- **Langfristig:** für 2 feste Units sehr stark; für 3+ Units ohne Refactoring nicht ideal.

## Implementierung im Repo: Local Dynamic Extension für v104

Zur direkten Umsetzung der gewünschten Punkte wurde eine **lokale Erweiterungsdatei** ergänzt:
- `zendure_v104_dynamic_local.yaml`

Sie bietet (ohne externen Netzwerkzugriff):
- dynamische lokale Geräteerkennung via MQTT-Topic-Listener,
- persistente lokale Device-Registry (JSON in HA-Helpern),
- optionale N-Device-Fusegroup-Verteilung via Script,
- automatisch aktivierten Schalter `input_boolean.zendure_dynamic_mode` (default `on`) inkl. Auto-Bootstrap der MQTT-Discovery für bereits bekannte Geräte.

Die Basisdatei `zendure_v104.yaml` bleibt dabei unverändert/stabil.

## Erweiterung: Vollautomatische 1..5+ Geräte-Steuerung inkl. Erweiterungsbatterien

Die lokale Dynamic-Extension unterstützt jetzt:
- AutoControl-Scheduler (alle 5s) für automatische Zielwertbildung und Verteilung,
- flexible Nutzung von 1 bis n Geräten (keine hardcodierten Device-IDs),
- Berücksichtigung von Erweiterungsbatterien über Kapazitätsmodell:
  - automatisch über `packNum` (Fallback 1.92 kWh * Pack-Anzahl),
  - optional über explizites JSON-Mapping `input_text.zendure_device_capacity_kwh`.

Damit ist die Steuerung für unterschiedliche Setups (1x bis 5x SF800 Pro) ohne Datei-Umbau nutzbar.

## Präzision vs. Min-Step/Dedup (Warum beides existiert)

- **Hysterese** (wie in v104) wirkt auf die Regelentscheidung (ob eine Neuverteilung nötig ist).
- **Min-Step/Dedup** wirkt auf den *Write-Pfad* (ob ein neuer MQTT-Setzpunkt wirklich gesendet wird).

Das ist nicht identisch:
- Hysterese verhindert ständiges Hin-und-her im Regler.
- Min-Step verhindert redundante Kleinst-Updates bei praktisch gleichem Setpoint.

Für maximale Genauigkeit wurde die Dynamic-Extension jetzt so angepasst:
- `zendure_dynamic_min_step` kann auf **0** gesetzt werden (Dedup praktisch aus).
- Zusätzlich gibt es `zendure_dynamic_adaptive_step`:
  - bei großer Netzabweichung wird Min-Step automatisch auf 1..2W abgesenkt,
  - bei ruhiger Lage greift dein eingestellter Basiswert.

Damit bleibt die Steuerung schnell/präzise bei echten Laständerungen, ohne bei Rauschen unnötig viele MQTT-Updates zu erzeugen.
