import os

for key, value in {
    "TWILIO_ACCOUNT_SID": "ACtest",
    "TWILIO_AUTH_TOKEN": "test",
    "TWILIO_API_KEY": "SKtest",
    "TWILIO_API_SECRET": "test",
    "TWILIO_PHONE_NUMBER": "+15555550000",
    "TWILIO_VOICE_PUBLIC_DOMAIN": "example.ngrok.app",
    "LITELLM_API_KEY": "test",
    "PAY_CONNECTOR_USERNAME": "test",
    "PAY_CONNECTOR_PASSWORD": "secret",
}.items():
    os.environ.setdefault(key, value)
