# ACME Pay Options

Demo of four ways to take a card payment on Twilio Programmable Voice, fronted by an AI agent (Twilio Agent Connect + ConversationRelay + an OpenAI-compatible LLM endpoint such as a LiteLLM proxy). Switch scenarios and edit their parameters in the web UI, then call the agent from the browser.

| # | Scenario | How card data is collected |
|---|---|---|
| 1 | `<Pay>` verb | Call redirects to Twilio `<Pay>`; keypad entry through a Pay Connector |
| 2 | Payments API | Agent stays on the call; the server runs the keypad capture sequence and the LLM handles only unscripted speech |
| 3 | ConversationRelay pay socket | Call moves to a second ConversationRelay session parsed in-process (speech or keypad) |
| 4 | `<Gather>` | Speech + keypad `<Gather>` loop with class-token hints |

[docs/voice-payment-options.html](docs/voice-payment-options.html) is a customer-facing guide to the four options: pros and cons, PCI scope, effort, and lessons learned building this demo.

## Prerequisites

- Python 3.12 + [uv](https://docs.astral.sh/uv/), Node 20+, Twilio CLI logged in to the target account, ngrok.
- A Twilio phone number (`TWILIO_PHONE_NUMBER`) and PCI Mode enabled on the account (Voice → Settings). PCI Mode can't be turned off once it's on, so use a dedicated account or subaccount.
- A Pay Connector installed in Console. To use the built-in mock processor, install a Generic Pay Connector with endpoint URL `https://<domain>/payresults` and HTTP Basic credentials matching `PAY_CONNECTOR_USERNAME` / `PAY_CONNECTOR_PASSWORD`. Put the connector's unique name (not its SID) in `PAY_CONNECTOR`. The mock Luhn-checks the card, declines a fixed test card, and returns a fake `charge_id` / `token_id`.
- An OpenAI-compatible chat completions endpoint (`LITELLM_BASE_URL`, `LITELLM_API_KEY`) serving `LLM_MODEL`. The default is `claude-haiku-5-5`, run with thinking disabled. Leave `LITELLM_BASE_URL` blank to use the OpenAI API directly.
- For scenario 2 in a real PCI workflow, ask your Twilio account team to set the account flag that stops call audio transmission during digit collection.

## Run locally

```bash
uv sync
(cd web && npm install && npm run build)
cp .env.example .env            # fill LITELLM_*, LLM_MODEL, TWILIO_PHONE_NUMBER, PAY_CONNECTOR, PAY_CONNECTOR_PASSWORD, VOICE
ngrok http 8000 --domain <your-domain>.ngrok.app
scripts/setup.sh <your-domain>.ngrok.app
uv run python -m server.main
```

`scripts/setup.sh` uses the active Twilio CLI profile, so check `twilio profiles:list` first. The script creates or updates the TwiML App, creates an API key, points the phone number at the app, and writes the results to `.env`. It asks for your Auth Token on the first run.

Open http://localhost:8000, pick a scenario, press **Call the agent**, and ask to pay your balance. You can also dial `TWILIO_PHONE_NUMBER`.

For UI development, run `cd web && npm run dev` and open http://localhost:5173 (it proxies `/api` to :8000).

## Configuration

| Variable | Purpose |
|---|---|
| `TTS_PROVIDER`, `VOICE` | Agent voice for ConversationRelay. Scenario 4's `<Say>` uses the same ElevenLabs voice ID. |
| `TRANSCRIPTION_PROVIDER`, `SPEECH_MODEL` | Agent speech-to-text, for example `Deepgram` / `flux`. |
| `LOG_LLM` | Log LLM prompts, responses, and tool calls (`acme.llm`). |
| `LOG_WS` | Log every ConversationRelay WebSocket text frame (`acme.ws`). |
| `LOG_PAY_CONNECTOR` | Log Pay Connector requests and responses with card fields masked (`acme.pay_connector`). |
| `CONFIG_PATH` | Where UI changes are saved. The default is `data/config.json`; saved settings reload on restart. |

The logging flags default to `true` and accept `true`/`false`, `1`/`0`, `on`/`off`, or `yes`/`no`. Turn `LOG_WS` and `LOG_LLM` off anywhere real card data could flow.

## Tests

```bash
uv run pytest -q
bash tests/setup_sh_test.sh
```

## Deploy to Fly.io

State is in memory, so run exactly one machine.

```bash
fly launch --no-deploy --copy-config --name <app-name>
scripts/setup.sh <app-name>.fly.dev      # repoints the TwiML App and phone number at Fly
fly secrets import < .env
fly deploy --ha=false
```

The Pay Connector's endpoint URL is set in Console. Change it to `https://<app-name>.fly.dev/payresults` while running on Fly. `data/config.json` isn't on a volume, so UI changes reset on each deploy unless you mount a volume and set `CONFIG_PATH` to a path on it.

To go back to local development, rerun `scripts/setup.sh <your-domain>.ngrok.app` and point the connector back at `https://<your-domain>.ngrok.app/payresults`.
