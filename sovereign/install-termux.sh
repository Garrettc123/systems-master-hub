#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PREFIX_BIN="${PREFIX:-/data/data/com.termux/files/usr}/bin"
CONFIG_DIR="${HOME}/.config/garcar-sovereign"

if ! command -v python >/dev/null 2>&1; then
  echo "Python is required. In Termux run: pkg install python"
  exit 1
fi

mkdir -p "$PREFIX_BIN" "$CONFIG_DIR"
install -m 0755 "$SCRIPT_DIR/garcar.py" "$PREFIX_BIN/garcar"
install -m 0644 "$SCRIPT_DIR/garcar.deploy.example.json" "$CONFIG_DIR/garcar.deploy.example.json"
install -m 0644 "$SCRIPT_DIR/garcar.ci.example.json" "$CONFIG_DIR/garcar.ci.example.json"

python "$PREFIX_BIN/garcar" init
echo "Installed Garcar Sovereign CLI."
echo "Next: garcar --help"
echo "No secrets were read, changed, or copied."
