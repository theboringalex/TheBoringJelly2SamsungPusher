# TheBoringJelly2SamsungPusher – Dokumentation

## Was das Add-on macht

Das Add-on bringt das Samsung-Tizen-CLI (`sdb`, `tizen`) mit und installiert einen fertigen
Build von [jellyfin-tizen](https://github.com/jellyfin/jellyfin-tizen) auf deinen TV.
Die Builds stammen aus [jeppevinkel/jellyfin-tizen-builds](https://github.com/jeppevinkel/jellyfin-tizen-builds),
das den offiziellen Code per GitHub Actions automatisch baut. Ein Selbstbau von `jellyfin-web`
im Add-on ist bewusst nicht enthalten (mehrere GB RAM, sehr lange Laufzeit, kein Vorteil).

Ablauf pro Installation:

1. Passenden Release über die GitHub-API auflösen und die `.wgt`-Datei laden
2. SHA-256-Prüfsumme gegen den von GitHub gemeldeten Wert prüfen
3. Per `sdb connect` mit dem TV verbinden (TCP 26101)
4. Optional mit eigenem Samsung-Zertifikat neu signieren
5. Optional die bestehende Installation entfernen
6. `tizen install` ausführen, danach optional die App starten

## Einmalige Vorbereitung am TV

1. TV einschalten, **Apps** öffnen.
2. Auf der Fernbedienung **12345** eingeben (bei Modellen ohne Zifferntasten über die „123“-Taste).
3. **Developer mode** auf **On** stellen.
4. Als **Host PC IP** die IP-Adresse deines **Home-Assistant-Hosts** eintragen
   (bei einer HA-VM die IP der VM, nicht die des Docker-Containers).
5. TV **neu starten** (Netzstecker ziehen oder über das Menü). Erst danach gilt die Einstellung.

## Add-on einrichten

**Variante A: über das Repository (empfohlen)**

1. **Einstellungen → Add-ons → Add-on-Store → ⋮ → Repositories** und
   `https://github.com/theboringalex/TheBoringJelly2SamsungPusher` hinzufügen.
2. „TheBoringJelly2SamsungPusher“ im Store öffnen und **Installieren**. Der erste Build lädt das
   Tizen-CLI-Image (mehrere hundert MB) und dauert einige Minuten.
3. **Starten**, dann in der Seitenleiste **TheBoringJelly2SamsungPusher** öffnen.

**Variante B: als lokales Add-on**

1. Den Ordner `theboringjelly2samsungpusher` in das Verzeichnis `/addons/` deines HA-Hosts kopieren
   (Samba-Freigabe „addons“ oder SSH-Add-on).
2. **Einstellungen → Add-ons → Add-on-Store → ⋮ → Nach Updates suchen** (oder Seite neu laden).
3. Unter **Lokale Add-ons** „TheBoringJelly2SamsungPusher“ öffnen und **Installieren**, dann **Starten**.

## Bedienung

In der Seitenleiste **TheBoringJelly2SamsungPusher** öffnen, IP des TV eintragen, Variante wählen, **Installieren**.
Der Ablauf erscheint live im Log. Derselbe Ablauf steht auch im Reiter **Protokoll** des Add-ons.

Alternativ lassen sich IP und Variante im Reiter **Konfiguration** vorgeben. Mit
**Beim Start automatisch installieren** läuft die Installation direkt nach dem Start des Add-ons.

## Konfiguration

| Option | Bedeutung |
|---|---|
| `tv_ip` | IPv4-Adresse des TV, Vorgabe für die Oberfläche und den Autostart |
| `build_variant` | Welcher Build installiert wird (siehe unten) |
| `jellyfin_url` | Optional, z. B. `http://192.168.1.10:8096`. Der Installer liest die Server-Version über den öffentlichen Endpunkt `/System/Info/Public` und wählt bei Variante `Jellyfin` automatisch `Jellyfin-10.11.z` oder `Jellyfin-12.z` |
| `release_tag` | Optional, bestimmten Release festlegen (z. B. `2026-10-17-1707`), leer = neuester |
| `uninstall_first` | Bestehende Jellyfin-App vorher vom TV entfernen (die Anmeldung in der App geht verloren) |
| `launch_after_install` | App nach der Installation starten |
| `auto_install` | Beim Start des Add-ons automatisch installieren |
| `certificate_password` | Passwort für eigene Samsung-Zertifikate (siehe unten) |
| `distributor_password` | Nur falls es vom Autor-Passwort abweicht |

### Build-Varianten

Die Web-Version im Build sollte zur Version deines Jellyfin-Servers passen.

| Variante | Bedeutung |
|---|---|
| `Jellyfin` | neueste stabile jellyfin-web-Version |
| `Jellyfin-10.11.z` / `Jellyfin-12.z` | aktueller Stand des jeweiligen Release-Branches, passend zu Server 10.11.x bzw. 12.x |
| `Jellyfin-master` / `Jellyfin-prerelease` | Entwicklungsstand bzw. Vorabversion |
| `Jellyfin-secondary` | wie stabil, aber mit eigener App-ID (zweites Konto parallel möglich) |
| `Jellyfin-OblongIcon` | Querformat-Icon für TVs, die es verlangen |
| `Jellyfin-SmartHub` | Samsung-Smart-Hub-Preview-Integration |
| `Jellyfin-OSA` | OblongIcon + SmartHub + experimenteller AVPlay-Player (bessere Codec-Unterstützung) |
| `Jellyfin-TrailerFix` | behebt YouTube-Trailer-Fehler 153 auf neuen Tizen-Versionen |
| `Jellyfin-GrayFix` | könnte graue Balken über/unter dem Video beheben |

Weitere Kombinationen (z. B. `10.11.z-OSA`) stehen im Auswahlmenü. Fehlt ein Build im gewählten Release,
listet das Log alle verfügbaren Namen auf.

## Neuere Samsung-TVs: eigenes Zertifikat

Ältere TVs akzeptieren das Standardprofil des Tizen-CLI. Neuere Modelle verlangen ein
Samsung-Zertifikat, das die DUID des TV enthält. Typisches Fehlerbild:
`install failed[118, -12], reason: Check certificate error`.

1. Auf einem Rechner mit Tizen Studio (Certificate Manager + Samsung Certificate Extension) ein
   **Samsung-Zertifikat** für deinen TV erstellen (Samsung-Konto nötig; das Add-on legt keine Konten an
   und fragt keine Zugangsdaten ab).
2. `author.p12` und `distributor.p12` in den Konfigurationsordner des Add-ons legen:
   `/addon_configs/<Add-on-Slug-Präfix>_theboringjelly2samsungpusher/` auf dem HA-Host
   (im Container erscheint er als `/config`; den genauen Pfad zeigt dir der Samba-Share „addon_configs“).
3. Das Zertifikats-Passwort im Reiter Konfiguration eintragen (`certificate_password`).
4. Add-on neu starten und die Installation wiederholen.

Wichtig: Die App lässt sich später nur mit **demselben** Autor-Zertifikat aktualisieren. Wechselst du das
Zertifikat, hilft `uninstall_first`.

## Fehlersuche

| Meldung / Symptom | Ursache und Lösung |
|---|---|
| „Keine Verbindung zum TV“ | Developer Mode aus, TV nicht neu gestartet, falsche Host-PC-IP im Developer-Dialog, oder Firewall/VLAN blockt TCP 26101 vom HA-Host zum TV |
| Status `unauthorized` oder `offline` | Developer Mode am TV aus- und wieder einschalten, Host-PC-IP prüfen, TV neu starten |
| `install failed[118, -11]`, „Author certificate not match“ | Jellyfin ist mit anderem Zertifikat installiert. Am TV im Apps-Menü entfernen (Entfernen aus der App-Leiste genügt nicht) oder `uninstall_first` aktivieren |
| `install failed[118, -12]`, „Invalid certificate chain“ | TV verlangt ein Samsung-Zertifikat mit DUID, siehe oben |
| „SHA-256-Prüfsumme stimmt nicht“ | Download beschädigt, Installation erneut starten |
| Build-Variante nicht in Release | Log zeigt die verfügbaren Namen; Variante oder `release_tag` anpassen |
| Add-on lässt sich nicht installieren / nicht gebaut | Nur amd64 wird unterstützt. Auf ARM-Hosts (z. B. Raspberry Pi) funktioniert das Tizen-CLI nicht |

Wenn die Verbindung trotz korrekter Einstellungen scheitert, hilft es, im TV-Developer-Dialog die
Host-PC-IP zu kontrollieren: Das Add-on greift aus dem Docker-Netz heraus zu, der TV sieht dabei die
IP des HA-Hosts.

## Sicherheit und Datenschutz

- Die Weboberfläche ist nur über Home-Assistant-Ingress erreichbar; der Server nimmt ausschließlich
  Verbindungen des Supervisors (172.30.32.2) an. Es wird kein Port nach außen veröffentlicht.
- Eingaben (IP, Variante, Tag, URL) werden streng validiert und per Umgebungsvariablen übergeben,
  nie in Shell-Befehle eingesetzt.
- Zertifikats-Passwörter stehen nur in den Add-on-Optionen. Sie werden aus dem Log maskiert, und die
  temporär geänderte Tizen-Profildatei wird nach jedem Lauf wiederhergestellt.
- Die installierten Builds stammen von einem Drittanbieter-Repository (nicht von Jellyfin direkt).
  Das Add-on prüft die von GitHub gemeldete SHA-256-Prüfsumme. Das schützt vor beschädigten
  Downloads, nicht vor einem kompromittierten Release. Wer das ausschließen will, baut
  [jellyfin-tizen](https://github.com/jellyfin/jellyfin-tizen) selbst und installiert die eigene `.wgt`.
- Der Developer Mode am TV öffnet einen Debug-Zugang. Nach der Installation kann er wieder
  ausgeschaltet werden; die App bleibt installiert.

## Credits

- [jellyfin/jellyfin-tizen](https://github.com/jellyfin/jellyfin-tizen) (MPL-2.0)
- [jeppevinkel/jellyfin-tizen-builds](https://github.com/jeppevinkel/jellyfin-tizen-builds) für die fertigen Builds
- [Georift/install-jellyfin-tizen](https://github.com/Georift/install-jellyfin-tizen) als Vorlage für den Docker-basierten Ablauf
- [vitalets/docker-tizen-webos-sdk](https://github.com/vitalets/docker-tizen-webos-sdk) als Basis-Image mit Tizen-CLI
