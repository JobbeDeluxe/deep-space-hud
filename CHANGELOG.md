# Änderungen

## v1.2.0 · 09.11.2026

- Netzwerk-Verläufe wahlweise automatisch oder mit getrennten festen Upload-/
  Download-Grenzen; Einheitenwechsel erhält die Bandbreite, Überlaufmarkierung.
- Drehrichtung für alle fünf Ringmarkierungen einstellbar: wechselnd, zufällig,
  rechtsherum, linksherum. Einstellbares Wechselintervall, Standard vier Sekunden.

- Mbit/s mit drei Nachkommastellen als Standard; kbit/s und Gbit/s sowie
  Bit-Automatik ergänzt. Byte-Einheiten und Byte-Automatik bleiben verfügbar.
- Uplink-Verlaufskurve und Messwertblock getauscht: Kurve links außen.

- Netzwerk-Einheit wählbar: feste Bit-/Byte-Einheiten oder Automatik; siehe oben.
- Downlink-Pfeil vor dem Schriftzug; eigene Upload-/Download-Verlaufskurven.
- Beschriftete Zeitachsen für echte 60-Sekunden-Fenster; CPU/GPU-Prozentskalen
  und dynamische Netzwerk-Werteskalen, Unterbrechungen als Lücken.
- README-GIF auf 24 Sekunden verlängert, mit langen orangefarbenen Lastphasen.

- Dezenter perspektivischer Sternenflug mit CPU-abhängigem Tempo und Spuren.
- Gespeicherter Schalter und Sichtbarkeitsregler im Setup; reduzierte Bewegung.
- Animierte Demo in der README, englische Kurzbeschreibung und bereinigte Dopplung.

## v1.1.0 · 09.11.2026

- Kontinuierliche Animation statt Positionssprüngen durch Laufzeit × CPU-Last.
- Freie, unabhängige CPU-/GPU-Markierungen mit sanften zufälligen Tempo- und
  Richtungswechseln; Geschwindigkeit folgt der jeweiligen Auslastung.
- Adaptive Glättung: schnelle Reaktion auf große Lastsprünge in beide Richtungen.
- Deutlich höhere und schnellere CPU-Wellen bei hoher Last.
- Warnfarben für CPU-/GPU-Temperaturen (65/75 °C) und alle Prozentwerte (70/80 %).
  Die CPU-Wellen verwenden dieselben konfigurierbaren Prozentgrenzen.
- Setup mit persistenten Grenzwerten, Glättung und Animationstempo.
- Windows-Paket und deutsche Dokumentation aktualisiert.

## v1.0.0 · 08.11.2026

- Erstveröffentlichung mit lokalem Sensorservice, HDMI-HUD und Windows-Starter.
