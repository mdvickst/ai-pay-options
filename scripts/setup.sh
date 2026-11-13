#!/usr/bin/env bash
set -euo pipefail

DOMAIN="${1:?Usage: scripts/setup.sh <public-domain, e.g. my-demo.ngrok.app>}"
DOMAIN="${DOMAIN#https://}"
DOMAIN="${DOMAIN%/}"
ENV_FILE="${ENV_FILE:-.env}"
VOICE_URL="https://$DOMAIN/voice/incoming"
STATUS_URL="https://$DOMAIN/voice/status"

command -v twilio >/dev/null || { echo "Twilio CLI not found: https://www.twilio.com/docs/twilio-cli" >&2; exit 1; }
[ -f "$ENV_FILE" ] || cp .env.example "$ENV_FILE"

env_get() {
  python3 - "$ENV_FILE" "$1" <<'PY'
import sys
path, key = sys.argv[1], sys.argv[2]
for line in open(path):
    if line.startswith(key + "="):
        print(line.split("=", 1)[1].strip())
        break
PY
}

env_set() {
  python3 - "$ENV_FILE" "$1" "$2" <<'PY'
import sys
path, key, value = sys.argv[1:4]
lines = open(path).read().splitlines()
for i, line in enumerate(lines):
    if line.startswith(key + "="):
        lines[i] = f"{key}={value}"
        break
else:
    lines.append(f"{key}={value}")
open(path, "w").write("\n".join(lines) + "\n")
PY
}

json_field() {
  python3 -c 'import json,sys; d=json.load(sys.stdin); d=d[0] if isinstance(d,list) else d; print(d[sys.argv[1]])' "$1"
}

APP_SID="$(env_get TWILIO_TWIML_APP_SID)"
if [ -n "$APP_SID" ]; then
  APP_JSON="$(twilio api:core:applications:update --sid "$APP_SID" --voice-url "$VOICE_URL" --voice-method POST --status-callback "$STATUS_URL" --status-callback-method POST -o json)"
  echo "Updated TwiML App $APP_SID"
else
  APP_JSON="$(twilio api:core:applications:create --friendly-name "ACME Pay Options" --voice-url "$VOICE_URL" --voice-method POST --status-callback "$STATUS_URL" --status-callback-method POST -o json)"
  APP_SID="$(echo "$APP_JSON" | json_field sid)"
  env_set TWILIO_TWIML_APP_SID "$APP_SID"
  echo "Created TwiML App $APP_SID"
fi
env_set TWILIO_ACCOUNT_SID "$(echo "$APP_JSON" | json_field accountSid)"

if [ -z "$(env_get TWILIO_API_KEY)" ]; then
  KEY_JSON="$(twilio api:core:keys:create --friendly-name "acme-pay-options" -o json)"
  env_set TWILIO_API_KEY "$(echo "$KEY_JSON" | json_field sid)"
  env_set TWILIO_API_SECRET "$(echo "$KEY_JSON" | json_field secret)"
  echo "Created API key"
fi

if [ -z "$(env_get TWILIO_AUTH_TOKEN)" ]; then
  read -rsp "Twilio Auth Token: " TOKEN
  echo
  env_set TWILIO_AUTH_TOKEN "$TOKEN"
fi

PHONE="$(env_get TWILIO_PHONE_NUMBER)"
if [ -n "$PHONE" ]; then
  twilio phone-numbers:update "$PHONE" --voice-url "$VOICE_URL" >/dev/null
  echo "Pointed $PHONE at $VOICE_URL"
fi

env_set TWILIO_VOICE_PUBLIC_DOMAIN "$DOMAIN"
echo "Wrote $ENV_FILE for $DOMAIN"
