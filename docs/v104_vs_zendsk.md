# Vergleich: v104-Regelung vs. Zendure-Integration (ZENSDK-Manager)

## Kurzfazit

- **Schneller reagierend** ist in der Regel der **ZENSDK-Manager** der Integration, weil er ereignisgetrieben auf P1-Leistungsänderungen reagiert und zusätzlich einen Fast-Pfad hat.
- **Genauer in Sonderfällen/Sicherheitslogik** ist häufig **v104**, weil dort sehr viele Zustände (Temperatur, Zellspannung, Frischechecks, Drift-Recovery, Bypass/Notfall/Kalibrierung) in die Entscheidung einfließen.
- In einer typischen Netznachregelung (Import/Export schnell ausregeln) gewinnt meist ZENSDK bei der Dynamik, v104 bei der Robustheit.

## Warum ZENSDK meist schneller ist

- ZENSDK regelt über P1-State-Events und nutzt zwei Zeitfenster:
  - Normalpfad (`TIMEZERO = 4s`)
  - Fast-Pfad (`TIMEFAST = 2.2s`) bei signifikanten Sprüngen
- Zusätzlich wird auf statistische Abweichungen (Standardabweichung) geprüft, um auf echte Lastsprünge schneller zu reagieren.

## Warum v104 oft robuster/genauer wirkt

- v104 verarbeitet viele Plausibilitäts- und Sicherheitsbedingungen (Sensor-Frische, Zell-Min-Volt, Temperaturlimits, SoC-Grenzen, Bypass-/Emergency-/Calib-/VGuard-Zustände).
- Es gibt spezielle Mechanismen wie Ack-/Drift-Recovery und Ghost-Load-Abfanglogik.
- Dadurch sinken Fehlreaktionen bei instabilen/alten Sensordaten, allerdings auf Kosten der Reaktionszeit.

## Konkrete Änderungen, damit v104 schneller UND genauer wird

1. **Loop-Intervall reduzieren**
   - Von `seconds: "/5"` auf `"/2"` oder `"/3"`.
2. **Event-getriebene Fast-Trigger ergänzen**
   - Trigger auf signifikante P1-Änderung (`state` + Template auf Delta), nicht nur auf feste Grenzwerte.
3. **Adaptive Fast/Normal-Logik wie im ZENSDK einbauen**
   - Bei Lastsprung für kurze Zeit aggressiver nachregeln, danach wieder normal.
4. **Glättung vor Stellwertberechnung**
   - Kurze Historie/Median für Grid-Signal verwenden, um Rauschen zu dämpfen und Over/Undershoot zu vermeiden.
5. **Hysterese dynamisch machen**
   - Bei stabiler Last kleiner, bei starkem Rauschen größer.
6. **Ack-/Drift-Fenster straffen**
   - Zeitfenster reduzieren, damit bei Command/Actual-Drift schneller nachgeregelt wird.
7. **Frischefenster für Kernsensoren enger setzen**
   - Dadurch weniger Entscheidungen auf potenziell veralteten Werten.

## Empfehlung für die Praxis

- Wenn Ziel primär **Netz-Nullung mit schneller Dynamik** ist: ZENSDK-Regelung als Basis.
- Wenn Ziel primär **Batterieschonung/Sicherheitslogik** ist: v104 als Basis.
- Bestes Ergebnis oft als Hybrid:
  - **ZENSDK-Reaktionsmechanik** (Fast/Normal, Event-getrieben)
  - **v104-Sicherheits- und Plausibilitätslogik**.
