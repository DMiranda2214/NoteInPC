#!/usr/bin/env bash
# Instala el visor como servicio de usuario (systemd --user). No requiere sudo.
#   deploy/install.sh            instala y arranca
#   deploy/install.sh --uninstall  lo quita
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UNIT_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
UNIT="$UNIT_DIR/notein-viewer.service"
CONF_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/notein-viewer"

if [[ "${1:-}" == "--uninstall" ]]; then
  systemctl --user disable --now notein-viewer.service 2>/dev/null || true
  rm -f "$UNIT"
  systemctl --user daemon-reload
  echo "Servicio eliminado (la configuracion en $CONF_DIR se conserva)."
  exit 0
fi

command -v python3 >/dev/null || { echo "Falta python3" >&2; exit 1; }
command -v pdftoppm >/dev/null || echo "Aviso: falta pdftoppm (sudo apt install poppler-utils); los fondos PDF no se mostraran." >&2
command -v rclone >/dev/null || echo "Aviso: falta rclone; el boton Sincronizar no funcionara." >&2

mkdir -p "$UNIT_DIR" "$CONF_DIR"
sed "s|@REPO@|$REPO|g" "$REPO/deploy/notein-viewer.service" > "$UNIT"

if [[ ! -f "$CONF_DIR/env" ]]; then
  cat > "$CONF_DIR/env" <<EOF
# Configuracion del visor (ver docs/CONFIGURATION.md). Descomenta lo que quieras cambiar.
#NOTEIN_DATA=$REPO/NoteInDataSync
#NOTEIN_PORT=8765
#NOTEIN_REMOTE=gdrive:NoteInDataSync
EOF
fi

systemctl --user daemon-reload
systemctl --user enable --now notein-viewer.service
sleep 1
systemctl --user --no-pager --lines=3 status notein-viewer.service || true
echo
echo "Listo: http://127.0.0.1:${NOTEIN_PORT:-8765}"
