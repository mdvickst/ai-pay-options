#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
mkdir -p "$TMP/bin"
cat > "$TMP/bin/twilio" <<'STUB'
#!/usr/bin/env bash
echo "$*" >> "$STUB_LOG"
case "$1" in
  api:core:keys:create) echo '[{"sid":"SKstub","secret":"stubsecret"}]' ;;
  api:core:applications:create|api:core:applications:update) echo '[{"sid":"APstub","accountSid":"ACstub"}]' ;;
  *) echo '[]' ;;
esac
STUB
chmod +x "$TMP/bin/twilio"
cp "$ROOT/.env.example" "$TMP/.env"
sed -i.bak -e 's/^TWILIO_AUTH_TOKEN=$/TWILIO_AUTH_TOKEN=tok/' -e 's/^TWILIO_PHONE_NUMBER=$/TWILIO_PHONE_NUMBER=+15550001111/' "$TMP/.env"
export STUB_LOG="$TMP/log" ENV_FILE="$TMP/.env" PATH="$TMP/bin:$PATH"

cd "$ROOT" && scripts/setup.sh https://first.ngrok.app/ >/dev/null
grep -q '^TWILIO_ACCOUNT_SID=ACstub$' "$TMP/.env"
grep -q '^TWILIO_API_KEY=SKstub$' "$TMP/.env"
grep -q '^TWILIO_API_SECRET=stubsecret$' "$TMP/.env"
grep -q '^TWILIO_TWIML_APP_SID=APstub$' "$TMP/.env"
grep -q '^TWILIO_VOICE_PUBLIC_DOMAIN=first.ngrok.app$' "$TMP/.env"
grep -q 'applications:create.*--voice-url https://first.ngrok.app/voice/incoming' "$TMP/log"
grep -q 'phone-numbers:update +15550001111 --voice-url https://first.ngrok.app/voice/incoming' "$TMP/log"

scripts/setup.sh second.ngrok.app >/dev/null
grep -q '^TWILIO_VOICE_PUBLIC_DOMAIN=second.ngrok.app$' "$TMP/.env"
grep -q 'applications:update --sid APstub.*--voice-url https://second.ngrok.app/voice/incoming' "$TMP/log"
[ "$(grep -c 'keys:create' "$TMP/log")" = "1" ]
[ "$(grep -c '^TWILIO_API_KEY=' "$TMP/.env")" = "1" ]
echo "setup.sh OK"
