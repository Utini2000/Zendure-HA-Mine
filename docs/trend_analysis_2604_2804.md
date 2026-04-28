# Trendanalyse 26.04–28.04 (v146)

## Kurzfazit

- Das beobachtete Problem „Notladung während Kalibrier-Entladung (Phase 1)“ ist in den Daten sichtbar.
- Hauptursache in `v146`: Der Auto-Emergency-Start blockierte nur `calib_mode`, aber nicht `calib_discharge`.
- Zusätzlich gab es in einzelnen Zeitfenstern Lastverteilungen, bei denen die volle Unit trotz vorhandener Priorisierung nicht dominant genug entladen hat.

## Ereignisse aus `Trend_2604_2804.csv` (UTC / Europe/Berlin)

- 27.04.2026 04:39 UTC / 06:39 CEST: `zendure_emergency_u2 -> on`, Blockgrund U2 `emergency_charge`.
- 27.04.2026 04:43 UTC / 06:43 CEST: `zendure_emergency_u1 -> on`, Blockgrund U1 `emergency_charge`.
- 27.04.2026 06:42 UTC / 08:42 CEST: Notladung beendet, beide wieder `discharging_calib`.
- 28.04.2026 01:35 UTC / 03:35 CEST: `zendure_emergency_u2 -> on`.
- 28.04.2026 01:53 UTC / 03:53 CEST: `zendure_emergency_u1 -> on`.
- 28.04.2026 05:47 UTC / 07:47 CEST und 06:02 UTC / 08:02 CEST: Rückkehr auf `discharging_calib`.

Diese Übergänge passen zum Verhalten „Phase 1 gestartet, dann morgens Notladung, danach wieder zurück“.

## Bewertung Lastverteilung (gewünschte Fenster)

### 27.04.2026 15:12–16:30 CEST

- Mittelwerte im Fenster:
  - `output_limit_u1` ≈ 216 W
  - `output_limit_u2` ≈ 196 W
  - `soc_u1` ≈ 99 %, `soc_u2` ≈ 96,9 %
- Bei `soc_u1 >= 99%` lag der mittlere Output-Anteil bei ca. **62/38** (U1/U2), also grundsätzlich schon mit Priorität auf U1.
- Es gab aber ein klar erkennbares Teilfenster um ~16:19–16:25 CEST, in dem U1 trotz höherem PV (z. B. ~407 W vs ~61 W) nur ~37 % vom Output-Limit bekam.
- Hauptursache dort: **Temperatur-Softcap** auf U1 (`t1 >= 48°C`), wodurch die verfügbare U1-Kapazität in diesem Moment technisch begrenzt wurde.

### 26.04.2026 14:40–18:40 CEST

- Mittelwerte im Fenster:
  - `output_limit_u1` ≈ 153 W
  - `output_limit_u2` ≈ 118 W
- Bei `soc_u1 >= 99%`: mittlere Verteilung ~**68/32** (U1/U2).
- Bei `soc_u2 >= 99%`: mittlere Verteilung ~**49/51** (U1/U2), also nahezu neutral.
- Fazit: Insgesamt brauchbar, aber in Full-SoC-Phasen nicht immer maximal „headroom-orientiert“.
- In diesem Fenster waren häufiger **beide SoC nahe 99%**, wodurch Prioritätswechsel (plus Rampen-/Step-Limits) kurzfristig „träge“ wirken konnten.

## Phase-1-Sicherheit (wichtige Antwort auf die Sicherheitsfrage)

Phase 1 ist weiterhin abgesichert und nicht „schutzlos“:

1. **Abbruch-/Übergangslogik der Kalibrierung**: Bei `vmin <= 2.86V` wird von Entladung auf Phase 2 gewechselt.
2. **Zusätzliche Unterspannungsgrenze im Guard Layer**: Bei `vmin < 2.85V` wird die verfügbare Entladekapazität auf 0 gesetzt.
3. **Notladung bleibt als Schutz für Normalbetrieb** aktiv, startet aber nicht mehr in aktiver Phase 1 (verhindert den zuvor beobachteten Konflikt).

Damit ist Phase 1 weiterhin eine kontrollierte, begrenzte Tiefentladung für die Kalibrierung und kein ungeschütztes „Leerziehen“.

## Umgesetzte Korrekturen / Klarstellung

1. **Emergency-vs-Calibration Konflikt behoben**
   - Auto-Emergency-Start (SoC/Voltage/Boot) startet nur, wenn `calib_discharge_* == off`.

2. **Gewichtung bereits vorhanden (und aggressiv)**
   - Im bestehenden Script gibt es bereits eine Full-SoC-Bias-Regel:
     - U1 voll (`soc1>=99` und `soc2<99`) => `w = w + 0.25`
     - U2 voll (`soc2>=99` und `soc1<99`) => `w = w - 0.25`
   - Das ist deutlich stärker als ein 55/45-Mindestanteil bei typischer Basis um ~50/50.
   - Abweichungen im Trendfenster entstehen daher eher aus **anderen Limits** (z. B. Rampen/Cap/Temperatur/Spillover), nicht aus fehlender Full-SoC-Priorisierung.

3. **Robustheit verbessert (Rebalance-Trigger)**
   - Zusätzlich wurde die Rebalance-Bedingung erweitert:
     - Neben der bisherigen SoC-Gap-Prüfung reagiert der Loop jetzt auch auf **Full-SoC-Fehlverteilung**.
     - Beispiel: U1 ist voll (`>=99%`) und U2 deutlich niedriger (`<=97%`), aber U1-Anteil liegt trotzdem unter 55% -> Rebalance wird aktiv forciert.
   - Ziel: schnelleres Nachführen in genau den von dir genannten „gefühlt falschen“ Zeitfenstern.
