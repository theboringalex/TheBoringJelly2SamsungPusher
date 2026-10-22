# TheBoringJelly2SamsungPusher

Home-Assistant-Add-on-Repository mit **TheBoringJelly2SamsungPusher**: installiert die Jellyfin-App
per Klick aus Home Assistant auf einen Samsung-Smart-TV (Tizen, Developer Mode).

## Einbinden

In Home Assistant: **Einstellungen → Add-ons → Add-on-Store → ⋮ → Repositories** und diese URL hinzufügen:

```
https://github.com/theboringalex/TheBoringJelly2SamsungPusher
```

Danach erscheint **TheBoringJelly2SamsungPusher** im Store. Details stehen in der Dokumentation des Add-ons
([theboringjelly2samsungpusher/DOCS.md](theboringjelly2samsungpusher/DOCS.md)).

## Bedienung

1. Am TV den Developer Mode aktivieren (Apps → **12345** → Developer mode **On**, als Host PC IP die IP deines
   Home-Assistant-Hosts eintragen) und den TV neu starten.
2. In Home Assistant das Add-on öffnen, die IP des TV eintragen, die Build-Variante wählen und **Installieren** klicken.
3. Der Ablauf erscheint live im Log. Danach findest du Jellyfin am TV unter **Apps**.

![Weboberfläche von TheBoringJelly2SamsungPusher nach erfolgreicher Installation](docs/screenshot.jpg)

Nur für amd64-Systeme (das Tizen-CLI gibt es nicht für ARM).
