# DEEP SPACE — Cyan Flow

Lokales PC-Statuspanel für ein HDMI-Display mit **1024 × 600 Pixeln**, Windows 10/11.
Neu aufgebaut nach deiner TelemetryForge-Vorlage. Eigenständige Anzeige im Browser;
kein InfoPanel-Import und kein TelemetryForge erforderlich.

## Schnellstart

1. Den ZIP-Ordner vollständig entpacken, z. B. nach `Dokumente\Deep-Space-HUD`.
2. Falls noch nicht vorhanden: **Python 3.10 oder neuer, 64 Bit** von
   <https://www.python.org/downloads/windows/> installieren. Im Installer
   **Add python.exe to PATH** aktivieren.
3. **START.cmd** doppelklicken. Beim ersten Start richtet sie eine Python-Umgebung
   im Unterordner `.venv` ein und lädt `psutil` sowie `pycaw` mit Abhängigkeiten
   von PyPI. Dafür wird einmalig Internet benötigt. Das Terminal offen lassen.
4. Windows → Einstellungen → System → Anzeige: **Diese Anzeigen erweitern**,
   beim HDMI-Display **1024 × 600** einstellen. Für scharfe Schrift möglichst
   100 % Windows-Skalierung und 100 % Browser-Zoom verwenden.
5. Das automatisch geöffnete Browserfenster auf das HDMI-Display ziehen
   (alternativ **Windows + Umschalt + Pfeil links/rechts**). **F** oder **F11**
   aktiviert Vollbild. **Esc** beendet das per F aktivierte Vollbild;
   das Browser-Vollbild per F11 wird mit F11 beendet.

Das Panel läuft unter <http://127.0.0.1:8765>. Es passt sich proportional an
andere Auflösungen an; abweichende Seitenverhältnisse ergeben schwarze Ränder.
Zum Beenden im Terminal **Strg+C** drücken. Ein offenes Panel zeigt dann
„SENSOREN OFFLINE“ und entfernt die Messwerte.

## Erst einmal das Design ansehen

**Deep-Space-HUD.html** direkt doppelklicken. Ohne Sensorservice startet die
Datei ausdrücklich in einer **Demo mit simulierten Werten**. Dafür sind weder
Python noch Internet nötig. Diese Ansicht liest keine echten PC-Sensoren aus.

- **S** oder das Zahnrad: Einstellungen öffnen.
- **D**: Demo einschalten/ausschalten. Die Demo wird gelb gekennzeichnet.
- **F**: Vollbild ein-/ausschalten.
- Demo-CPU-Last: automatisch, 10 %, 50 % oder 95 %. Damit kannst du den
  Unterschied zwischen ruhiger und hoher Last direkt ansehen.
- Bewegung, Effektstärke, Glättung und Animationstempo lassen sich einstellen
  und werden lokal im Browser gespeichert. Die Betriebssystem-Einstellung für
  reduzierte Bewegung wird beim ersten Start berücksichtigt.
- Die kleinen CPU-/GPU-Markierungen laufen frei und unabhängig. Ihre Position
  ist kein Prozentzeiger; ihre Geschwindigkeit reagiert auf die jeweilige Last.
  Zufällige Tempo- und Richtungswechsel werden sanft überblendet.
- Große Lastsprünge reagieren schnell, kleine Schwankungen werden geglättet.
- Temperaturzahlen werden standardmäßig ab **65 °C orange**, ab **75 °C rot**.
  Prozentzahlen und Auslastungsringe werden ab **70 % orange**, ab **80 % rot**;
  das gilt auch für VRAM und Lautstärke. Die gesamte CPU-Welle folgt denselben
  Prozentgrenzen. Unterhalb der Grenzen bleiben die normalen Farben erhalten.
- Im Setup können beide Warnstufen getrennt für Temperaturen und Prozentwerte
  eingestellt werden. Die rote Grenze bleibt immer über der orangefarbenen.
  Warnfarben und Zahlen folgen den aktuellen Messwerten, unabhängig von der
  Glättung der Animation. Die Sensorabfrage erfolgt ungefähr einmal pro Sekunde.

## Was die Anzeige misst

| Anzeige | Bedeutung und Quelle |
|---|---|
| CPU | Gesamte Prozessorauslastung, `psutil`, etwa einmal pro Sekunde |
| RAM | Belegter Arbeitsspeicher in Prozent, `psutil` |
| SSD | Belegung des konfigurierten Laufwerks, standardmäßig C:; keine Aktivität und keine SSD-Gesundheit |
| VOLUME | Windows-Lautstärkeeinstellung des Standard-Ausgabegeräts, `pycaw`; bei Mute steht „STUMMGESCHALTET“ |
| CPU TEMP | LibreHardwareMonitor: bevorzugt Package/Tctl/Tdie, sonst ein verfügbarer CPU-Temperatursensor |
| GPU / GPU TEMP / VRAM | LibreHardwareMonitor; alternativ bei NVIDIA `nvidia-smi`, wenn LHM keine GPU-Werte liefert |
| UP / DOWN | Gesendete/empfangene Bytes pro Sekunde, dezimale KB/s bzw. MB/s |
| Uhr / Datum | Lokale Zeit und Zeitzone deines Windows-PCs |

Die mittlere **CPU RESPONSE** ist eine Designanimation: höhere gemessene
CPU-Last erzeugt höhere Ausschläge und schnellere Bewegung. Ihre einzelnen
Balken sind **keine CPU-Kerne oder echten Frequenzmessungen**. Die kleinen
CPU-/GPU-Kurven zeigen dagegen den Verlauf der Messwerte über etwa 60 Sekunden.
Die Volume-Anzeige ist **kein Musik-Equalizer**.

Fehlende oder abgebrochene Sensorquellen ergeben **„—“**, niemals erfundene
Live-Werte. „LIVE / TEILWEISE“ bedeutet, dass der lokale Service läuft, aber
nicht alle Sensoren verfügbar sind. Die Einstellungen nennen fehlende Sensoren
und die zugeordneten Quellen.

## Temperaturen und GPU: LibreHardwareMonitor

CPU-Auslastung, RAM, Laufwerk, Netzwerk und Lautstärke benötigen kein LHM.
Windows stellt CPU-Temperaturen nicht über eine universelle Standard-Schnittstelle
bereit. Für Temperaturen und AMD-/Intel-GPU-Sensoren:

1. LibreHardwareMonitor aus den offiziellen Releases laden:
   <https://github.com/LibreHardwareMonitor/LibreHardwareMonitor/releases>
2. Entpacken und starten; für bestimmte Hardware braucht LHM Administratorrechte.
   Der HUD-Start selbst benötigt keine Administratorrechte.
3. In LHM unter **Options → Remote Web Server** den Webserver aktivieren
   (**Run**, Port **8085**). Möglichst an **127.0.0.1** binden. Keine
   Router-Portfreigabe ist nötig. Menübezeichnungen können je nach Version abweichen.
4. Prüfen, ob <http://127.0.0.1:8085/data.json> im Browser Sensoren anzeigt.
5. LHM geöffnet lassen. Das Panel übernimmt verfügbare Werte automatisch.

Deine alte Vorlage verweist auf eine DLL von FanControl. Dieses neue Panel
lädt diese DLL nicht. Ein laufendes FanControl ersetzt den LHM-Webserver nicht.
Einige Hardwaremodelle stellen trotzdem nicht alle Sensoren bereit.

Bei NVIDIA kann das mit dem Treiber installierte `nvidia-smi` GPU-Last,
GPU-Temperatur und VRAM auch ohne LHM liefern. CPU-Temperatur benötigt weiterhin
LHM. Hardwareabfragen laufen separat und blockieren die Animation nicht.

## Optional anpassen

`config.json` mit einem Texteditor öffnen. Nach Änderungen den Sensorservice
mit Strg+C stoppen und START.cmd erneut starten.

- `disk_path`: beispielsweise `"D:\\"`, um D: anzuzeigen.
- `network_interface`: leer = Summe der aktiven Adapter ohne Loopback. Mit VPN
  oder virtuellen Adaptern können Daten mehrfach enthalten sein. Für genaue
  Werte einen Adapter eintragen, z. B. `"Ethernet"` oder `"WLAN"`.
  Die Namen findest du im PowerShell-Befehl `Get-NetAdapter`.
- `port`: lokaler Panel-Port, standardmäßig 8765.
- `lhm_url`: lokaler LHM-Endpunkt, standardmäßig `http://127.0.0.1:8085/data.json`.
- `gpu_index`: 0 = erste GPU, 1 = zweite. Die Reihenfolge folgt der jeweiligen
  Quelle; sie kann zwischen LHM und NVIDIA abweichen.
- `sensor_overrides`: bei Bedarf exakte `SensorId` aus LHM verwenden, z. B.:

```json
"sensor_overrides": {
  "cpu_temp": "/amdcpu/0/temperature/0",
  "gpu": "/gpu-nvidia/0/load/0"
}
```

Die Beispiel-IDs müssen zu deiner Hardware passen. Unterstützte Schlüssel:
`cpu_temp`, `gpu`, `gpu_temp`, `vram`. Bevorzugt werden numerische `RawValue`-Werte;
bei älteren LHM-Versionen ohne diese Felder bitte Celsius als Temperatureinheit
einstellen. Für nur über Datenmengen gemeldeten VRAM ohne Prozent-Sensor kann
die automatische LHM-Erkennung fehlen.

## Wenn etwas nicht funktioniert

- **START.cmd meldet Python fehlt:** Python installieren und den Installer-PATH
  aktivieren. Danach Terminal und START.cmd neu öffnen.
- **Installation schlägt fehl:** Internetverbindung prüfen. Das Terminal zeigt
  die eigentliche pip-Fehlermeldung. Dateien vollständig entpacken und einen
  beschreibbaren Ordner verwenden.
- **Port belegt:** Eine zweite Instanz schließen oder `port` in `config.json`
  ändern. Die neue URL wird im Terminal ausgegeben.
- **Nur Demo zu sehen:** Echte Werte gibt es über START.cmd und die lokale
  HTTP-Adresse. Direkt geöffnete HTML-Dateien sind zunächst im Demo-Modus.
- **Keine GPU/Temperatur:** LHM-Webserver und `data.json` prüfen. Ein normaler
  HDMI-Anschluss transportiert das Bild, liefert aber keine Sensoren.
- **Keine Lautstärke:** Standard-Wiedergabegerät in Windows prüfen. Ohne
  verfügbares Audiogerät bleibt dieser Wert leer.
- **Fenster landet auf dem Hauptbildschirm:** Auf den HDMI-Bildschirm verschieben,
  dann Vollbild aktivieren. Dieses Paket verändert keine Windows-Anzeigeeinstellungen
  und richtet keinen Autostart ein.

## Technik und Prüfung

Die Anzeige verwendet SVG, Canvas und lokale Systemfonts, ohne CDNs oder externe
Designressourcen. Das UI ist frei skalierbar, zeichnet maximal etwa 30 Bilder/s
und fragt den lokalen Service etwa einmal pro Sekunde ab. Es verwendet einen
Browserprozess; dessen tatsächlicher Verbrauch hängt von GPU, Browser und PC ab.

Der Sensorservice bindet ausschließlich an 127.0.0.1. Er sendet keine Messwerte
an einen Cloud-Dienst. Nur die erste Paketinstallation lädt Abhängigkeiten aus
dem Internet. Es wird keine Software automatisch als Administrator gestartet.

Browser-Darstellung und Bedienung, Demo-/Live-Wechsel, Ausfallverhalten,
Lastreaktion und Sensorparser werden in der mitgelieferten `PRUEFUNG.txt`
dokumentiert. Für v1.1.0 wurden zusätzlich die Animationen, Warnfarben und
gespeicherten Einstellungen unter Windows/Chrome geprüft. Lokale Windows-
Telemetrie einschließlich Lautstärke und LibreHardwareMonitor-Temperaturen
wurde live empfangen. Eine frische Erstinstallation bleibt ungeprüft.
