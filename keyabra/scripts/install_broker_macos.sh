#!/bin/zsh
set -euo pipefail

# Install a root-owned Noldorian capability broker.  The daemon owns credential
# custody; the selected desktop user can only query and invoke registered
# operations through the Unix socket.

SCRIPT_DIR="${0:A:h}"
KEYABRA_ROOT="${SCRIPT_DIR:h}"
BROKER_USER="${SUDO_USER:-}"
TUNNEL_CLIENT_BIN="/opt/homebrew/Cellar/tunnel-client/0.0.13/libexec/tunnel-client"
PYTHON_BIN="/usr/bin/python3"
CAPABILITY_SPEC=""

while (( $# > 0 )); do
  case "$1" in
    --user)
      BROKER_USER="$2"
      shift 2
      ;;
    --tunnel-client-bin)
      TUNNEL_CLIENT_BIN="$2"
      shift 2
      ;;
    --python)
      PYTHON_BIN="$2"
      shift 2
      ;;
    --capability)
      CAPABILITY_SPEC="$2"
      shift 2
      ;;
    *)
      print -u2 "unknown option: $1"
      exit 2
      ;;
  esac
done

if (( EUID != 0 )); then
  print -u2 "run with sudo: sudo $0 --user <desktop-user>"
  exit 2
fi
if [[ -z "$BROKER_USER" ]]; then
  print -u2 "--user is required when SUDO_USER is unavailable"
  exit 2
fi
if [[ ! -x "$TUNNEL_CLIENT_BIN" ]]; then
  print -u2 "tunnel-client is not executable: $TUNNEL_CLIENT_BIN"
  exit 2
fi
if [[ ! -x "$PYTHON_BIN" ]]; then
  print -u2 "python is not executable: $PYTHON_BIN"
  exit 2
fi
if [[ -n "$CAPABILITY_SPEC" && ! -f "$CAPABILITY_SPEC" ]]; then
  print -u2 "capability specification does not exist: $CAPABILITY_SPEC"
  exit 2
fi

BROKER_UID="$(id -u "$BROKER_USER")"
BROKER_GID="$(id -g "$BROKER_USER")"
INSTALL_ROOT="/Library/Application Support/NoldorianKeyBroker"
APP_DIR="$INSTALL_ROOT/app"
STATE_DIR="$INSTALL_ROOT/state"
SOCKET_PATH="/var/run/noldorian-key-broker.sock"
PLIST_PATH="/Library/LaunchDaemons/com.everplay.noldorian-key-broker.plist"
PYZ_PATH="$APP_DIR/keyabrad.pyz"
INSTALLED_TUNNEL_CLIENT="$APP_DIR/tunnel-client"
TEMP_PYZ="$(mktemp /tmp/keyabrad.XXXXXX.pyz)"

cleanup() {
  /bin/rm -f "$TEMP_PYZ"
}
trap cleanup EXIT

"$PYTHON_BIN" -m zipapp "$KEYABRA_ROOT/src" \
  -m "keyabra.broker_server:main" \
  -o "$TEMP_PYZ"

/bin/mkdir -p "$APP_DIR" "$STATE_DIR"
/usr/sbin/chown -R root:wheel "$INSTALL_ROOT"
/bin/chmod 0755 "$INSTALL_ROOT" "$APP_DIR"
/bin/chmod 0700 "$STATE_DIR"
/usr/bin/install -o root -g wheel -m 0555 "$TEMP_PYZ" "$PYZ_PATH"
/usr/bin/install -o root -g wheel -m 0555 "$TUNNEL_CLIENT_BIN" "$INSTALLED_TUNNEL_CLIENT"

/bin/launchctl bootout system "$PLIST_PATH" >/dev/null 2>&1 || true

/bin/cat > "$PLIST_PATH" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.everplay.noldorian-key-broker</string>
  <key>ProgramArguments</key>
  <array>
    <string>$PYTHON_BIN</string>
    <string>$PYZ_PATH</string>
    <string>--state-dir</string>
    <string>$STATE_DIR</string>
    <string>--socket</string>
    <string>$SOCKET_PATH</string>
    <string>--tunnel-client-bin</string>
    <string>$INSTALLED_TUNNEL_CLIENT</string>
    <string>--allowed-uid</string>
    <string>$BROKER_UID</string>
    <string>--owner-uid</string>
    <string>0</string>
    <string>--socket-gid</string>
    <string>$BROKER_GID</string>
    <string>--socket-mode</string>
    <string>0660</string>
  </array>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <true/>
  <key>ProcessType</key>
  <string>Interactive</string>
  <key>StandardOutPath</key>
  <string>/var/log/noldorian-key-broker.log</string>
  <key>StandardErrorPath</key>
  <string>/var/log/noldorian-key-broker.log</string>
</dict>
</plist>
PLIST

/usr/sbin/chown root:wheel "$PLIST_PATH"
/bin/chmod 0644 "$PLIST_PATH"
/usr/bin/plutil -lint "$PLIST_PATH"
/bin/launchctl bootstrap system "$PLIST_PATH"

for _attempt in {1..50}; do
  [[ -S "$SOCKET_PATH" ]] && break
  /bin/sleep 0.1
done
if [[ ! -S "$SOCKET_PATH" ]]; then
  print -u2 "broker socket did not appear; inspect /var/log/noldorian-key-broker.log"
  exit 1
fi

REGISTERED_CAPABILITY=""
if [[ -n "$CAPABILITY_SPEC" ]]; then
  REGISTER_RESPONSE="$(
    /usr/bin/jq -c \
      '{id:"install-capability",action:"register",capability:.}' \
      "$CAPABILITY_SPEC" |
      /usr/bin/nc -U "$SOCKET_PATH"
  )"
  if ! print -r -- "$REGISTER_RESPONSE" | /usr/bin/jq -e '.ok == true' >/dev/null; then
    print -u2 "broker rejected the capability specification"
    print -r -- "$REGISTER_RESPONSE" | /usr/bin/jq -c '{ok,error}' >&2
    exit 1
  fi
  REGISTERED_CAPABILITY="$(
    print -r -- "$REGISTER_RESPONSE" | /usr/bin/jq -r '.result.id'
  )"
fi

print "noldorian-key-broker installed"
print "socket=$SOCKET_PATH"
print "allowed_uid=$BROKER_UID"
print "state=$STATE_DIR"
if [[ -n "$REGISTERED_CAPABILITY" ]]; then
  print "registered_capability=$REGISTERED_CAPABILITY"
fi
