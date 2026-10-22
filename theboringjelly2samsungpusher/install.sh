#!/usr/bin/env bash
# Installiert einen fertigen jellyfin-tizen-Build (.wgt) per sdb/tizen-CLI auf einen Samsung-TV.
#
# Eingabe ausschließlich über Umgebungsvariablen (nie per Shell-Interpolation):
#   TV_IP, BUILD_VARIANT, RELEASE_TAG, JELLYFIN_URL, UNINSTALL_FIRST, LAUNCH_AFTER
#   CERT_PASSWORD, DISTRIBUTOR_PASSWORD   (nur für eigene Samsung-Zertifikate)
set -uo pipefail

REPO="jeppevinkel/jellyfin-tizen-builds"
CERT_DIR="${CERT_DIR:-/config}"
HOME="${HOME:-/home/developer}"
PROFILES="${PROFILES:-$HOME/tizen-studio-data/profile/profiles.xml}"
PROFILE_NAME="jellyfin_addon_custom"

TV_IP="${TV_IP:-}"
BUILD_VARIANT="${BUILD_VARIANT:-Jellyfin}"
RELEASE_TAG="${RELEASE_TAG:-}"
JELLYFIN_URL="${JELLYFIN_URL:-}"
UNINSTALL_FIRST="${UNINSTALL_FIRST:-false}"
LAUNCH_AFTER="${LAUNCH_AFTER:-true}"
CERT_PASSWORD="${CERT_PASSWORD:-}"
DISTRIBUTOR_PASSWORD="${DISTRIBUTOR_PASSWORD:-}"

WORK="$(mktemp -d)"
PROFILES_BAK=""

log() { printf '[%s] %s\n' "$(date +%H:%M:%S)" "$*"; }
die() { log "FEHLER: $*"; exit 1; }

cleanup() {
    # Profil-Datei mit evtl. eingetragenen Zertifikats-Passwörtern wiederherstellen
    if [ -n "$PROFILES_BAK" ] && [ -f "$PROFILES_BAK" ]; then
        cp -f "$PROFILES_BAK" "$PROFILES" 2>/dev/null || true
    fi
    [ -n "$TV_IP" ] && timeout 10 sdb disconnect "$TV_IP" >/dev/null 2>&1 || true
    rm -rf "$WORK"
}
trap cleanup EXIT

valid_ip() {
    local ip="$1" o
    [[ "$ip" =~ ^([0-9]{1,3})\.([0-9]{1,3})\.([0-9]{1,3})\.([0-9]{1,3})$ ]] || return 1
    for o in "${BASH_REMATCH[@]:1}"; do
        (( 10#$o <= 255 )) || return 1
    done
}

[[ "$BUILD_VARIANT" =~ ^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$ ]] || die "Ungültiger Varianten-Name."
[[ "$RELEASE_TAG" =~ ^[A-Za-z0-9._-]{0,64}$ ]] || die "Ungültiger Release-Tag."
valid_ip "$TV_IP" || die "Bitte eine gültige IPv4-Adresse des TV angeben (z. B. 192.168.1.50)."

# --- 1. Passende Variante zur Server-Version wählen (optional) -------------------------------
if [ -n "$JELLYFIN_URL" ]; then
    if [[ "$JELLYFIN_URL" =~ ^https?://[^[:space:]\"\'\<\>]{1,200}$ ]]; then
        info="$(curl -fsS -m 10 "${JELLYFIN_URL%/}/System/Info/Public" 2>/dev/null || true)"
        server_ver="$(jq -r '.Version // empty' <<<"$info" 2>/dev/null || true)"
        if [ -n "$server_ver" ]; then
            major="${server_ver%%.*}"
            rest="${server_ver#*.}"
            minor="${rest%%.*}"
            log "Jellyfin-Server gefunden, Version $server_ver."
            want=""
            if   [ "$major" = "10" ] && [ "$minor" = "11" ]; then want="Jellyfin-10.11.z"
            elif [ "$major" = "12" ];                        then want="Jellyfin-12.z"
            fi
            if [ -z "$want" ]; then
                log "WARNUNG: Für Server $server_ver gibt es keinen passenden Branch-Build; es bleibt bei '$BUILD_VARIANT'."
            elif [ "$BUILD_VARIANT" = "Jellyfin" ]; then
                log "Wähle Variante '$want' passend zur Server-Version."
                BUILD_VARIANT="$want"
            else
                log "Hinweis: Zur Server-Version passt '$want'; gewählt ist '$BUILD_VARIANT' (bleibt unverändert)."
            fi
        else
            log "WARNUNG: Server-Version unter der angegebenen URL nicht lesbar; Variante bleibt '$BUILD_VARIANT'."
        fi
    else
        log "WARNUNG: Jellyfin-URL ungültig, wird ignoriert."
    fi
fi

# --- 2. Release auflösen und .wgt herunterladen ----------------------------------------------
# RELEASES_API ist nur für Tests gedacht (lokaler Fake-Server); im Add-on ist sie nie gesetzt.
API="${RELEASES_API:-https://api.github.com/repos/$REPO/releases}"
if [ -n "$RELEASE_TAG" ]; then api_url="$API/tags/$RELEASE_TAG"; else api_url="$API/latest"; fi

log "Suche Build '$BUILD_VARIANT' (${RELEASE_TAG:-neuester Release}) ..."
curl -fsSL -m 30 --retry 2 -H 'Accept: application/vnd.github+json' "$api_url" -o "$WORK/release.json" \
    || die "Release-Informationen von GitHub nicht abrufbar (Internetzugang oder Tag prüfen)."

tag="$(jq -r '.tag_name // empty' "$WORK/release.json")"
asset="$(jq -c --arg n "$BUILD_VARIANT.wgt" '.assets[]? | select(.name == $n)' "$WORK/release.json" | head -n1)"
if [ -z "$asset" ]; then
    log "Verfügbare Builds in Release $tag:"
    jq -r '.assets[]?.name' "$WORK/release.json" | sed 's/\.wgt$//' | sed 's/^/  - /'
    die "Build '$BUILD_VARIANT' ist in Release $tag nicht enthalten."
fi
dl_url="$(jq -r '.browser_download_url' <<<"$asset")"
digest="$(jq -r '.digest // empty' <<<"$asset")"

WGT_NAME="$BUILD_VARIANT.wgt"
log "Lade $WGT_NAME aus Release $tag ..."
curl -fsSL -m 300 --retry 2 -o "$WORK/$WGT_NAME" "$dl_url" || die "Download fehlgeschlagen."

if [[ "$digest" == sha256:* ]]; then
    ( cd "$WORK" && echo "${digest#sha256:}  $WGT_NAME" | sha256sum -c --status - ) \
        || die "SHA-256-Prüfsumme stimmt nicht mit GitHub überein. Abbruch."
    log "SHA-256-Prüfsumme gegen GitHub verifiziert."
else
    log "WARNUNG: GitHub liefert keine Prüfsumme für dieses Asset; Integrität nicht geprüft."
fi
unzip -tq "$WORK/$WGT_NAME" >/dev/null 2>&1 || die "Heruntergeladene Datei ist kein gültiges Paket."

meta="$(unzip -p "$WORK/$WGT_NAME" config.xml 2>/dev/null || true)"
PKG_ID="$(grep -o 'package="[^"]*"' <<<"$meta" | head -n1 | cut -d'"' -f2)"
APP_ID="$(grep -o 'tizen:application [^>]*' <<<"$meta" | grep -o ' id="[^"]*"' | head -n1 | cut -d'"' -f2)"
log "Paket-ID: ${PKG_ID:-unbekannt}, App-ID: ${APP_ID:-unbekannt}"

# --- 3. Mit dem TV verbinden -----------------------------------------------------------------
log "Verbinde mit TV $TV_IP (Port 26101) ..."
sdb start-server >/dev/null 2>&1 || true
conn_out="$(timeout 30 sdb connect "$TV_IP" 2>&1 || true)"
log "sdb: $conn_out"
sleep 2
dev_line="$(sdb devices 2>/dev/null | awk -v ip="$TV_IP" 'index($1, ip ":") == 1 { print }' | head -n1)"
if [ -z "$dev_line" ]; then
    log "Der TV ist nicht erreichbar. Bitte prüfen:"
    log "  - Developer Mode am TV ist EIN und der TV wurde danach neu gestartet"
    log "  - Im Developer-Mode-Dialog ist als 'Host PC IP' die IP des Home-Assistant-Hosts eingetragen"
    log "  - Firewall/VLAN erlaubt TCP 26101 vom HA-Host zum TV"
    die "Keine Verbindung zum TV."
fi
serial="$(awk '{ print $1 }' <<<"$dev_line")"
state="$(awk '{ print $2 }' <<<"$dev_line")"
TV_NAME="$(awk '{ $1=""; $2=""; sub(/^ +/, ""); print }' <<<"$dev_line")"
if [ "$state" != "device" ]; then
    die "TV meldet Status '$state' statt 'device'. Developer Mode neu starten und die Host-PC-IP prüfen."
fi
[ -n "$TV_NAME" ] || TV_NAME="$serial"
log "Verbunden mit '$TV_NAME'."
timeout 15 sdb -s "$serial" capability 2>/dev/null \
    | grep -E '^(platform_version|model_name|cpu_arch|secure_protocol):' \
    | sed 's/^/    /' || true

# --- 4. Optional: mit eigenem Samsung-Zertifikat neu signieren -------------------------------
cd "$WORK" || die "Arbeitsverzeichnis nicht erreichbar."
if [ -f "$CERT_DIR/author.p12" ] && [ -f "$CERT_DIR/distributor.p12" ]; then
    if [ -z "$CERT_PASSWORD" ]; then
        log "WARNUNG: author.p12/distributor.p12 gefunden, aber kein Zertifikats-Passwort gesetzt. Nutze das Standardprofil."
    else
        log "Signiere Paket mit eigenem Zertifikat aus $CERT_DIR ..."
        [ -f "$PROFILES" ] || die "Tizen-Profildatei nicht gefunden ($PROFILES)."
        PROFILES_BAK="$WORK/profiles.xml.bak"
        cp -f "$PROFILES" "$PROFILES_BAK"
        export PROFILES PROFILE_NAME CERT_DIR CERT_PASSWORD
        export DISTRIBUTOR_PASSWORD="${DISTRIBUTOR_PASSWORD:-$CERT_PASSWORD}"
        python3 -I - <<'PY' || die "Zertifikatsprofil konnte nicht angelegt werden."
import os, re
from xml.sax.saxutils import quoteattr

path = os.environ["PROFILES"]
name = os.environ["PROFILE_NAME"]
cdir = os.environ["CERT_DIR"]
author_pw = quoteattr(os.environ["CERT_PASSWORD"])
dist_pw = quoteattr(os.environ["DISTRIBUTOR_PASSWORD"])

with open(path, encoding="utf-8") as fh:
    xml = fh.read()

# evtl. altes Profil gleichen Namens entfernen
xml = re.sub(r'<profile name="%s">.*?</profile>\s*' % re.escape(name), "", xml, flags=re.S)

block = (
    '<profile name="%s">\n'
    '<profileitem ca="" distributor="0" key="%s/author.p12" password=%s rootca=""/>\n'
    '<profileitem ca="" distributor="1" key="%s/distributor.p12" password=%s rootca=""/>\n'
    '<profileitem ca="" distributor="2" key="" password="" rootca=""/>\n'
    '</profile>\n'
) % (name, cdir, author_pw, cdir, dist_pw)

if "</profiles>" not in xml:
    raise SystemExit("profiles.xml hat ein unerwartetes Format")
xml = xml.replace("</profiles>", block + "</profiles>", 1)

with open(path, "w", encoding="utf-8") as fh:
    fh.write(xml)
PY
        sign_out="$(timeout 120 tizen package -t wgt -s "$PROFILE_NAME" -- "$WORK/$WGT_NAME" 2>&1)"; sign_rc=$?
        # Passwort aus der Ausgabe entfernen, falls das CLI es je zurückgeben sollte
        echo "${sign_out//"$CERT_PASSWORD"/***}"
        [ "$sign_rc" -eq 0 ] || die "Signieren mit eigenem Zertifikat fehlgeschlagen."
        signed_path="$(grep -o 'Package File Location: .*' <<<"$sign_out" | head -n1 | sed 's/^Package File Location: //; s/[[:space:]]*$//')"
        if [ -n "$signed_path" ] && [ -f "$signed_path" ]; then
            cp -f "$signed_path" "$WORK/$WGT_NAME" 2>/dev/null || true
        fi
        log "Paket signiert."
    fi
elif [ -f "$CERT_DIR/author.p12" ] || [ -f "$CERT_DIR/distributor.p12" ]; then
    log "WARNUNG: Es liegt nur eine der beiden Zertifikatsdateien (author.p12 / distributor.p12) vor. Nutze das Standardprofil."
else
    log "Kein eigenes Zertifikat hinterlegt, nutze das Standardprofil des Tizen-CLI."
fi

# --- 5. Optional: vorhandene Installation entfernen ------------------------------------------
if [ "$UNINSTALL_FIRST" = "true" ]; then
    if [ -n "$PKG_ID" ]; then
        log "Entferne vorhandene Installation (Paket $PKG_ID) ..."
        timeout 120 tizen uninstall -p "$PKG_ID" -t "$TV_NAME" 2>&1 | sed 's/^/    /' || true
    else
        log "WARNUNG: Paket-ID nicht ermittelbar, überspringe Deinstallation."
    fi
fi

# --- 6. Installieren --------------------------------------------------------------------------
log "Installiere $WGT_NAME auf '$TV_NAME' ..."
inst_out="$(timeout 300 tizen install -n "$WGT_NAME" -t "$TV_NAME" 2>&1)"; inst_rc=$?
echo "$inst_out" | sed 's/^/    /'

if grep -qi 'install failed' <<<"$inst_out"; then
    if grep -q -- '-11\|Author certificate not match' <<<"$inst_out"; then
        log "Hinweis: Auf dem TV ist Jellyfin bereits mit einem anderen Zertifikat installiert."
        log "  -> Option 'Vorher deinstallieren' aktivieren oder die App am TV im Apps-Menü entfernen"
        log "     (das Entfernen aus der App-Leiste reicht nicht)."
    elif grep -q -- '-12\|certificate chain' <<<"$inst_out"; then
        log "Hinweis: Dieser TV verlangt ein Samsung-Zertifikat, das die TV-DUID enthält."
        log "  -> author.p12 und distributor.p12 in den Add-on-Konfigurationsordner legen und das Passwort setzen (siehe Dokumentation)."
    fi
    die "Installation auf dem TV fehlgeschlagen."
fi
[ "$inst_rc" -eq 0 ] || die "tizen install endete mit Fehlercode $inst_rc."

if grep -qi 'successfully installed\|install completed' <<<"$inst_out"; then
    log "Installation erfolgreich."
else
    log "WARNUNG: Die Ausgabe enthält keine eindeutige Erfolgsmeldung. Bitte am TV prüfen, ob die App unter 'Apps' erscheint."
fi

# --- 7. Optional: App starten -----------------------------------------------------------------
if [ "$LAUNCH_AFTER" = "true" ] && [ -n "$APP_ID" ]; then
    log "Starte die App auf dem TV ..."
    timeout 60 tizen run -p "$APP_ID" -t "$TV_NAME" 2>&1 | sed 's/^/    /' || true
fi

log "Fertig. Jellyfin findest du am TV unter 'Apps' (ggf. ganz am Ende der Liste)."
exit 0
