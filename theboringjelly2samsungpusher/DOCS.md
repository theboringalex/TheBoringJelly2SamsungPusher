# TheBoringJelly2SamsungPusher – Documentation

## What the add-on does

The add-on ships the Samsung Tizen CLI (`sdb`, `tizen`) and installs a prebuilt build of
[jellyfin-tizen](https://github.com/jellyfin/jellyfin-tizen) on your TV. The builds come from
[jeppevinkel/jellyfin-tizen-builds](https://github.com/jeppevinkel/jellyfin-tizen-builds), which builds the official
code automatically with GitHub Actions. Building `jellyfin-web` inside the add-on is deliberately not included
(several GB of RAM, very long runtime, no benefit).

Steps of each installation:

1. Resolve the matching release through the GitHub API and download the `.wgt` file
2. Verify the SHA-256 checksum against the value reported by GitHub
3. Connect to the TV with `sdb connect` (TCP 26101)
4. Optionally re-sign the package with your own Samsung certificate
5. Optionally remove the existing installation
6. Run `tizen install`, then optionally launch the app

## One-time preparation on the TV

1. Turn on the TV and open **Apps**.
2. Enter **12345** on the remote (on remotes without number keys, use the "123" button).
3. Switch **Developer mode** to **On**.
4. Enter the IP address of your **Home Assistant host** as **Host PC IP**
   (for an HA VM, use the IP of the VM, not of the Docker container).
5. **Restart** the TV (pull the power plug or use the menu). The setting only takes effect afterwards.

## Setting up the add-on

**Option A: via the repository (recommended)**

1. **Settings → Add-ons → Add-on Store → ⋮ → Repositories** and add
   `https://github.com/theboringalex/TheBoringJelly2SamsungPusher`.
2. Open "TheBoringJelly2SamsungPusher" in the store and click **Install**. The first build downloads the
   Tizen CLI image (several hundred MB) and takes a few minutes.
3. Click **Start**, then open **TheBoringJelly2SamsungPusher** in the sidebar.

**Option B: as a local add-on**

1. Copy the folder `theboringjelly2samsungpusher` into the `/addons/` directory of your HA host
   (Samba share "addons" or the SSH add-on).
2. **Settings → Add-ons → Add-on Store → ⋮ → Check for updates** (or reload the page).
3. Open "TheBoringJelly2SamsungPusher" under **Local add-ons**, click **Install**, then **Start**.

## Usage

Open **TheBoringJelly2SamsungPusher** in the sidebar, enter the IP of the TV, choose a variant and click **Install**.
The progress is shown live in the log. The same output is available in the add-on's **Log** tab.

![Web UI of TheBoringJelly2SamsungPusher after a successful installation](https://raw.githubusercontent.com/theboringalex/TheBoringJelly2SamsungPusher/main/docs/screenshot.jpg)

Alternatively, IP and variant can be preset in the **Configuration** tab. With
**Install on add-on start** the installation runs right after the add-on starts.

## Configuration

| Option | Meaning |
|---|---|
| `tv_ip` | IPv4 address of the TV, default for the UI and for auto install |
| `build_variant` | Which build is installed (see below) |
| `jellyfin_url` | Optional, e.g. `http://192.168.1.10:8096`. The installer reads the server version from the public endpoint `/System/Info/Public` and, for the variant `Jellyfin`, automatically picks `Jellyfin-10.11.z` or `Jellyfin-12.z` |
| `release_tag` | Optional, pin a specific release (e.g. `2026-10-17-1707`), empty = latest |
| `uninstall_first` | Remove an existing Jellyfin app from the TV first (the login inside the app is lost) |
| `launch_after_install` | Launch the app after installation |
| `auto_install` | Install automatically when the add-on starts |
| `certificate_password` | Password for custom Samsung certificates (see below) |
| `distributor_password` | Only if it differs from the author password |

### Build variants

The web version inside the build should match the version of your Jellyfin server.

| Variant | Meaning |
|---|---|
| `Jellyfin` | latest stable jellyfin-web version |
| `Jellyfin-10.11.z` / `Jellyfin-12.z` | current state of the respective release branch, for server 10.11.x or 12.x |
| `Jellyfin-master` / `Jellyfin-prerelease` | development state or pre-release |
| `Jellyfin-secondary` | like stable, but with its own app ID (allows a second account in parallel) |
| `Jellyfin-OblongIcon` | landscape icon for TVs that require it |
| `Jellyfin-SmartHub` | Samsung Smart Hub preview integration |
| `Jellyfin-OSA` | OblongIcon + SmartHub + experimental AVPlay player (better codec support) |
| `Jellyfin-TrailerFix` | fixes YouTube trailer error 153 on newer Tizen versions |
| `Jellyfin-GrayFix` | may fix gray bars above/below the video |

More combinations (e.g. `10.11.z-OSA`) are available in the dropdown. If a build is missing in the selected
release, the log lists all available names.

## Newer Samsung TVs: custom certificate

Older TVs accept the default profile of the Tizen CLI. Newer models require a Samsung certificate that contains
the DUID of the TV. Typical error: `install failed[118, -12], reason: Check certificate error`.

1. On a computer with Tizen Studio (Certificate Manager + Samsung Certificate Extension), create a
   **Samsung certificate** for your TV (a Samsung account is required; the add-on does not create accounts and
   does not ask for credentials).
2. Put `author.p12` and `distributor.p12` into the add-on's configuration folder:
   `/addon_configs/<add-on-slug-prefix>_theboringjelly2samsungpusher/` on the HA host
   (it appears as `/config` inside the container; the Samba share "addon_configs" shows the exact path).
3. Enter the certificate password in the Configuration tab (`certificate_password`).
4. Restart the add-on and repeat the installation.

Important: the app can later only be updated with the **same** author certificate. If you change the certificate,
use `uninstall_first`.

## Troubleshooting

| Message / symptom | Cause and solution |
|---|---|
| "Keine Verbindung zum TV" (no connection to the TV) | Developer mode is off, the TV was not restarted, wrong Host PC IP in the developer dialog, or a firewall/VLAN blocks TCP 26101 from the HA host to the TV |
| Status `unauthorized` or `offline` | Switch Developer mode off and on again, check the Host PC IP, restart the TV |
| `install failed[118, -11]`, "Author certificate not match" | Jellyfin is installed with a different certificate. Remove it in the TV's Apps menu (removing it from the app bar is not enough) or enable `uninstall_first` |
| `install failed[118, -12]`, "Invalid certificate chain" | The TV requires a Samsung certificate with DUID, see above |
| "SHA-256-Prüfsumme stimmt nicht" (checksum mismatch) | Download corrupted, start the installation again |
| Build variant not in release | The log shows the available names; adjust the variant or `release_tag` |
| Add-on cannot be installed / not built | Only amd64 is supported. The Tizen CLI does not work on ARM hosts (e.g. Raspberry Pi) |

If the connection fails despite correct settings, double-check the Host PC IP in the TV's developer dialog:
the add-on connects from inside the Docker network, and the TV sees the IP of the HA host.

## Security and privacy

- The web UI is only reachable through Home Assistant Ingress; the server only accepts connections from the
  Supervisor (172.30.32.2). No port is published.
- Inputs (IP, variant, tag, URL) are strictly validated and passed through environment variables,
  never inserted into shell commands.
- Certificate passwords are only stored in the add-on options. They are masked in the log, and the
  temporarily modified Tizen profile file is restored after every run.
- The installed builds come from a third-party repository (not directly from Jellyfin).
  The add-on verifies the SHA-256 checksum reported by GitHub. This protects against corrupted downloads,
  not against a compromised release. If you want to rule that out, build
  [jellyfin-tizen](https://github.com/jellyfin/jellyfin-tizen) yourself and install your own `.wgt`.
- Developer mode on the TV opens a debug interface. You can switch it off again after the installation;
  the app stays installed.

## Credits

- [jellyfin/jellyfin-tizen](https://github.com/jellyfin/jellyfin-tizen) (MPL-2.0)
- [jeppevinkel/jellyfin-tizen-builds](https://github.com/jeppevinkel/jellyfin-tizen-builds) for the prebuilt packages
- [Georift/install-jellyfin-tizen](https://github.com/Georift/install-jellyfin-tizen) as a template for the Docker-based flow
- [vitalets/docker-tizen-webos-sdk](https://github.com/vitalets/docker-tizen-webos-sdk) as the base image with the Tizen CLI
