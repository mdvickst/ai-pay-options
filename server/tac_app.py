from tac import TAC, TACConfig
from tac.channels.voice import VoiceChannel
from tac.channels.voice.conversation_relay.config import ConversationRelayProviderConfig
from tac.models.voice import VoiceTwiMLOptionsConversationRelay
from tac.session import ThreadSafeSessionManager

from server.settings import settings

tac = TAC(config=TACConfig.from_env())
voice_channel = VoiceChannel(tac, config=ConversationRelayProviderConfig(session_manager=ThreadSafeSessionManager()))


def agent_relay_options(greeting: str) -> VoiceTwiMLOptionsConversationRelay:
    """Returns the agent's ConversationRelay options with the greeting and the TTS/STT settings from the environment."""
    speech = {
        "tts_provider": settings.tts_provider,
        "voice": settings.voice,
        "transcription_provider": settings.transcription_provider,
        "speech_model": settings.speech_model,
    }
    return VoiceTwiMLOptionsConversationRelay(welcome_greeting=greeting, events="speaker-events tokens-played", **{k: v for k, v in speech.items() if v})
