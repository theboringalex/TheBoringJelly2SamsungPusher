# TheBoringJelly2SamsungPusher

[![Open your Home Assistant instance and show the add app repository dialog with this repository pre-filled.](https://my.home-assistant.io/badges/supervisor_add_addon_repository.svg)](https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https%3A%2F%2Fgithub.com%2Ftheboringalex%2FTheBoringJelly2SamsungPusher)

A Home Assistant add-on that installs the [Jellyfin](https://jellyfin.org) app on a Samsung Smart TV (Tizen)
with a single click. Enter the IP address of your TV in the web UI and the add-on does the rest: it downloads a
prebuilt Jellyfin build, verifies its checksum, connects to the TV, installs the app and launches it.

![Web UI of TheBoringJelly2SamsungPusher after a successful installation](docs/screenshot.jpg)

## Features

- One-click installation of Jellyfin on Samsung Tizen TVs, straight from the Home Assistant sidebar
- Live installation log in the web UI
- Picks the build that matches your Jellyfin server version (optional server URL)
- Verifies the SHA-256 checksum of the download against the value reported by GitHub
- Optional signing with your own Samsung certificate for newer TV models
- Only reachable through Home Assistant Ingress, no port is exposed

## Installation

1. Click the button above, or in Home Assistant go to **Settings → Add-ons → Add-on Store → ⋮ → Repositories**
   and add this URL:

   ```
   https://github.com/theboringalex/TheBoringJelly2SamsungPusher
   ```

2. Open **TheBoringJelly2SamsungPusher** in the store and click **Install**. The first build downloads the Tizen CLI
   image (several hundred MB) and takes a few minutes.
3. Click **Start**, then open **TheBoringJelly2SamsungPusher** in the sidebar.

The add-on supports **amd64** systems only (the Tizen CLI is not available for ARM).

## Usage

1. **Prepare the TV (once):** open **Apps**, enter **12345** on the remote, switch **Developer mode** to **On** and
   enter the IP address of your **Home Assistant host** as **Host PC IP**. Restart the TV afterwards.
2. **Install:** open the add-on, enter the IP address of the TV, choose a build variant and click **Install**.
3. **Done:** Jellyfin appears on the TV under **Apps** (possibly at the very end of the list). You can switch
   Developer mode off again, the app stays installed.

All options, build variants, certificate handling and troubleshooting are described in the
[add-on documentation](theboringjelly2samsungpusher/DOCS.md).

## Credits

- [jellyfin/jellyfin-tizen](https://github.com/jellyfin/jellyfin-tizen) (MPL-2.0)
- [jeppevinkel/jellyfin-tizen-builds](https://github.com/jeppevinkel/jellyfin-tizen-builds) for the prebuilt packages
- [Georift/install-jellyfin-tizen](https://github.com/Georift/install-jellyfin-tizen) as a template for the Docker-based flow
- [vitalets/docker-tizen-webos-sdk](https://github.com/vitalets/docker-tizen-webos-sdk) as the base image with the Tizen CLI
