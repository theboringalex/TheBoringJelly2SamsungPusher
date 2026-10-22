# Basis: Ubuntu 22.04 (amd64) mit Samsung Tizen CLI (tizen, sdb), läuft als root.
# Quelle: https://github.com/vitalets/docker-tizen-webos-sdk
# Das Image wird bewusst direkt referenziert (nicht über BUILD_FROM), damit der
# Supervisor kein Home-Assistant-Base-Image darüberlegt.
FROM --platform=linux/amd64 vitalets/tizen-webos-sdk:latest

USER root

# python3: kleine Ingress-Weboberfläche (nur Standardbibliothek)
# jq/curl/unzip: Release-Auflösung, Download, Paket-Metadaten
RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 jq curl unzip ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Info im Build-Log; schlägt bewusst nicht fehl, falls das CLI eine andere Ausgabe liefert.
RUN (tizen version; sdb version) || true

COPY run.sh install.sh server.py /app/
RUN chmod +x /app/run.sh /app/install.sh

WORKDIR /home/developer
ENTRYPOINT ["/app/run.sh"]
