# Änderungen

## v1.2.2 · 09.11.2026

- START.cmd öffnet ein separates Chrome-/Edge-HUD-Fenster mit eigenem Profil
  und Parametern gegen Hintergrunddrosselung und Fenster-Verdeckungserkennung.
  Energie-/Speichersparen und automatisches Einfrieren sind dort initial aus.
- START-BROWSER.cmd bleibt als Alternative für den normalen Standardbrowser.
  Das eigene HUD-Profil benötigt einmalig die gewünschten HUD-Einstellungen.
- Windows-CoreAudio-Abfrage aus der CPU-/Netzwerk-Messschleife ausgegliedert.
  Ein blockierendes Audiogerät hält die Verlaufssammlung nicht mehr auf.
- Fester Messtakt statt einer zusätzlichen Sekunde Pause nach jeder Abfrage.
- ConnectionAbortedError / WinError 10053 und weitere normale Verbindungsabbrüche
  werden auch beim Schreiben von HTTP-Headern und beim Abschluss abgefangen.

## v1.2.1 · 09.11.2026

- Live-Datenstrom (Server-Sent Events) mit HTTP-Rückfall und Wiederverbindung.
- CPU-/GPU-/Netzwerk-Verläufe werden serverseitig für 60 Sekunden gesammelt
  und nach pausierter Animation oder eingefrorenem Tab erneut übertragen.
- Sofortige Aktualisierung bei Fokus, Sichtbarkeit und Wiederaufnahme des Tabs.
- Kurze Verbindungsfehler leeren gültige Werte nicht sofort; echte Ausfälle
  bleiben erkennbar. Demo und Live-Daten bleiben getrennt.
- Neu aufgenommenes README-GIF mit sichtbarer Versionskennung und versioniertem
  Dateinamen, damit die geänderte Vorschau nicht dieselbe Cache-Adresse verwendet.

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
